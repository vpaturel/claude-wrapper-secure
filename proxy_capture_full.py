#!/usr/bin/env python3
"""
Improved HTTP proxy to capture complete Claude API requests/responses
- No truncation (captures full SSE streams)
- Parses SSE events properly
- Structured file saving
"""

import http.server
import urllib.request
import json
import sys
import os
from datetime import datetime
from pathlib import Path

# Configuration
CAPTURES_DIR = Path('/home/tincenv/analyse-claude-ai/captures')
PORT = 8000

class ProxyHandler(http.server.BaseHTTPRequestHandler):
    """Proxy handler that captures full requests and streaming responses"""

    def do_POST(self):
        """Handle POST requests to API"""
        timestamp = datetime.now()

        # Read request body
        content_length = int(self.headers.get('Content-Length', 0))
        body = self.rfile.read(content_length).decode('utf-8') if content_length > 0 else ""

        # Parse request
        try:
            body_json = json.loads(body) if body else None
        except json.JSONDecodeError:
            body_json = body

        # Capture request data
        request_data = {
            'timestamp': timestamp.isoformat(),
            'method': 'POST',
            'path': self.path,
            'headers': dict(self.headers),
            'body': body_json
        }

        # Forward to real API
        target_url = f"https://api.anthropic.com{self.path}"
        req = urllib.request.Request(target_url, data=body.encode('utf-8'), method='POST')

        # Copy headers (except Host)
        for key, value in self.headers.items():
            if key.lower() != 'host':
                req.add_header(key, value)

        try:
            with urllib.request.urlopen(req, timeout=60) as response:
                # Read FULL response (NO TRUNCATION)
                response_body_raw = response.read().decode('utf-8')

                # Detect if streaming (SSE)
                content_type = response.headers.get('Content-Type', '')
                is_streaming = 'text/event-stream' in content_type

                if is_streaming:
                    # Parse SSE events
                    events = self._parse_sse_events(response_body_raw)
                    response_body_processed = {
                        'format': 'sse',
                        'events_count': len(events),
                        'events': events,
                        'raw': response_body_raw  # Keep raw for debugging
                    }
                else:
                    # Regular JSON response
                    try:
                        response_body_processed = json.loads(response_body_raw)
                    except json.JSONDecodeError:
                        response_body_processed = response_body_raw

                # Capture response data (FULL, no truncation)
                response_data = {
                    'status': response.status,
                    'headers': dict(response.headers),
                    'body': response_body_processed,
                    'size_bytes': len(response_body_raw),
                    'is_streaming': is_streaming
                }

                # Save capture to structured files
                self._save_capture(timestamp, request_data, response_data, is_streaming)

                # Send response back to client
                self.send_response(response.status)
                for key, value in response.headers.items():
                    self.send_header(key, value)
                self.end_headers()
                self.wfile.write(response_body_raw.encode('utf-8'))

                # Log success
                size_kb = len(response_body_raw) / 1024
                event_info = f" ({len(events)} events)" if is_streaming else ""
                print(f"✅ Captured {size_kb:.1f}KB from {self.path}{event_info}")

        except urllib.error.HTTPError as e:
            # Capture HTTP errors (401, 429, 500, etc.)
            error_body = e.read().decode('utf-8')

            try:
                error_json = json.loads(error_body)
            except json.JSONDecodeError:
                error_json = error_body

            error_data = {
                'status': e.code,
                'headers': dict(e.headers),
                'body': error_json,
                'error': True
            }

            # Save error capture
            self._save_capture(timestamp, request_data, error_data, is_streaming=False, is_error=True)

            # Forward error to client
            self.send_response(e.code)
            for key, value in e.headers.items():
                self.send_header(key, value)
            self.end_headers()
            self.wfile.write(error_body.encode('utf-8'))

            print(f"⚠️  Captured error {e.code} from {self.path}")

        except Exception as e:
            print(f"❌ Proxy error: {e}")
            self.send_error(502, str(e))

    def _parse_sse_events(self, raw_sse: str) -> list:
        """
        Parse Server-Sent Events format

        Format:
            event: message_start
            data: {"type":"message_start",...}

            event: content_block_delta
            data: {"type":"content_block_delta",...}

            event: message_stop
            data: {"type":"message_stop"}
        """
        events = []
        current_event = {}

        for line in raw_sse.split('\n'):
            line = line.strip()

            if line.startswith('event:'):
                current_event['event'] = line[6:].strip()

            elif line.startswith('data:'):
                data_str = line[5:].strip()
                try:
                    current_event['data'] = json.loads(data_str)
                except json.JSONDecodeError:
                    current_event['data'] = data_str

            elif line == '' and current_event:
                # Empty line marks end of event
                events.append(current_event)
                current_event = {}

        # Add last event if not empty
        if current_event:
            events.append(current_event)

        return events

    def _save_capture(self, timestamp: datetime, request_data: dict, response_data: dict,
                      is_streaming: bool, is_error: bool = False):
        """Save capture to structured directory"""

        # Create capture structure
        capture = {
            'timestamp': timestamp.isoformat(),
            'request': request_data,
            'response': response_data,
            'metadata': {
                'is_streaming': is_streaming,
                'is_error': is_error,
                'size_bytes': response_data.get('size_bytes', 0)
            }
        }

        # Determine subdirectory
        if is_error:
            subdir = CAPTURES_DIR / 'errors'
            status_code = response_data.get('status', 'unknown')
            filename = f"{timestamp.strftime('%Y%m%d_%H%M%S')}_error_{status_code}.json"
        elif is_streaming:
            subdir = CAPTURES_DIR / 'streaming'
            filename = f"{timestamp.strftime('%Y%m%d_%H%M%S')}_stream.json"
        else:
            subdir = CAPTURES_DIR / 'responses'
            filename = f"{timestamp.strftime('%Y%m%d_%H%M%S')}_response.json"

        # Create directory if not exists
        subdir.mkdir(parents=True, exist_ok=True)

        # Save to file
        filepath = subdir / filename
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(capture, f, indent=2, ensure_ascii=False)

        # Also save request separately for reference
        request_dir = CAPTURES_DIR / 'requests'
        request_dir.mkdir(parents=True, exist_ok=True)
        request_file = request_dir / f"{timestamp.strftime('%Y%m%d_%H%M%S')}_request.json"
        with open(request_file, 'w', encoding='utf-8') as f:
            json.dump(request_data, f, indent=2, ensure_ascii=False)

    def log_message(self, format, *args):
        """Silence default HTTP logs"""
        pass

def main():
    """Start proxy server"""
    print("=" * 70)
    print("🚀 CLAUDE API PROXY - FULL CAPTURE MODE")
    print("=" * 70)
    print(f"")
    print(f"🔍 Proxy listening on http://localhost:{PORT}")
    print(f"📁 Captures directory: {CAPTURES_DIR}")
    print(f"")
    print(f"Features:")
    print(f"  ✅ Full response capture (no truncation)")
    print(f"  ✅ SSE event parsing")
    print(f"  ✅ Structured file saving")
    print(f"  ✅ Error capture (401, 429, etc.)")
    print(f"")
    print(f"Usage:")
    print(f"  export ANTHROPIC_BASE_URL=http://localhost:{PORT}")
    print(f"  echo 'test' | claude")
    print(f"")
    print(f"Press Ctrl+C to stop")
    print("=" * 70)
    print("")

    # Create captures directory
    CAPTURES_DIR.mkdir(parents=True, exist_ok=True)

    # Start server
    server = http.server.HTTPServer(('localhost', PORT), ProxyHandler)

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n\n🛑 Proxy stopped")
        print(f"📊 Captures saved in: {CAPTURES_DIR}")

if __name__ == '__main__':
    main()
