#!/usr/bin/env python3
"""Simple HTTP proxy to capture Claude Code API requests"""

import http.server
import urllib.request
import json
import sys
from datetime import datetime

capture_file = '/home/tincenv/analyse-claude-ai/claude_capture.json'
captures = []

class ProxyHandler(http.server.BaseHTTPRequestHandler):
    def do_POST(self):
        # Read request body
        content_length = int(self.headers.get('Content-Length', 0))
        body = self.rfile.read(content_length).decode('utf-8') if content_length > 0 else ""

        # Capture request
        request_data = {
            'timestamp': datetime.now().isoformat(),
            'method': 'POST',
            'path': self.path,
            'headers': dict(self.headers),
            'body': json.loads(body) if body else None
        }

        # Forward to real API
        target_url = f"https://api.anthropic.com{self.path}"
        req = urllib.request.Request(target_url, data=body.encode('utf-8'), method='POST')

        # Copy headers (except Host)
        for key, value in self.headers.items():
            if key.lower() != 'host':
                req.add_header(key, value)

        try:
            with urllib.request.urlopen(req, timeout=30) as response:
                response_body = response.read().decode('utf-8')
                response_data = {
                    'status': response.status,
                    'headers': dict(response.headers),
                    'body': response_body[:500] + '...' if len(response_body) > 500 else response_body
                }

                # Save capture
                captures.append({
                    'request': request_data,
                    'response': response_data
                })

                with open(capture_file, 'w') as f:
                    json.dump(captures, f, indent=2)

                # Send response back
                self.send_response(response.status)
                for key, value in response.headers.items():
                    self.send_header(key, value)
                self.end_headers()
                self.wfile.write(response_body.encode('utf-8'))

                print(f"✅ Captured request to {self.path}")

        except Exception as e:
            print(f"❌ Error: {e}")
            self.send_error(502, str(e))

    def log_message(self, format, *args):
        pass  # Silence logs

if __name__ == '__main__':
    PORT = 8000
    print(f"🔍 Proxy listening on http://localhost:{PORT}")
    print(f"📝 Captures will be saved to {capture_file}")
    server = http.server.HTTPServer(('localhost', PORT), ProxyHandler)
    server.serve_forever()
