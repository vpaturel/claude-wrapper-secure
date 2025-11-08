#!/usr/bin/env python3
"""
MITM Proxy with CONNECT support for capturing HTTPS traffic
Generates certificates on-the-fly for each domain
"""

import http.server
import socket
import ssl
import json
import os
import threading
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse
import subprocess

# Configuration
CAPTURES_DIR = Path('/home/tincenv/analyse-claude-ai/captures')
CERTS_DIR = Path('/home/tincenv/analyse-claude-ai/certs')
PORT = 8080
CA_CERT = CERTS_DIR / 'ca-cert.pem'
CA_KEY = CERTS_DIR / 'ca-key.pem'

class MITMProxyHandler(http.server.BaseHTTPRequestHandler):
    """MITM proxy handler with CONNECT support"""

    def log_message(self, format, *args):
        """Custom logging"""
        print(f"[{datetime.now().strftime('%H:%M:%S')}] {format % args}")

    def do_CONNECT(self):
        """Handle CONNECT method for HTTPS tunneling"""
        print(f"\n🔐 CONNECT request: {self.path}")

        # Parse host and port
        host, port = self.path.split(':')
        port = int(port)

        # Send 200 Connection Established
        self.send_response(200, 'Connection Established')
        self.end_headers()

        # Generate certificate for this domain
        cert_file = self._get_or_create_cert(host)

        try:
            # Wrap client socket with SSL
            context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
            # cert_file already contains both key + cert combined
            context.load_cert_chain(cert_file)

            client_socket = self.connection
            client_ssl = context.wrap_socket(client_socket, server_side=True)

            # Create new handler for HTTPS traffic
            print(f"✅ SSL handshake OK for {host}")

            # Handle the HTTPS request
            self._handle_https_request(client_ssl, host, port)

        except Exception as e:
            print(f"❌ SSL Error: {e}")

    def _get_or_create_cert(self, hostname):
        """Generate or retrieve certificate for hostname"""
        cert_file = CERTS_DIR / f"{hostname}.pem"

        if cert_file.exists():
            return cert_file

        print(f"📜 Generating certificate for {hostname}")

        # Generate key
        subprocess.run([
            'openssl', 'genrsa',
            '-out', CERTS_DIR / f"{hostname}-key.pem",
            '2048'
        ], capture_output=True)

        # Generate CSR
        subprocess.run([
            'openssl', 'req', '-new',
            '-key', CERTS_DIR / f"{hostname}-key.pem",
            '-out', CERTS_DIR / f"{hostname}.csr",
            '-subj', f"/CN={hostname}"
        ], capture_output=True)

        # Create extensions file with SAN
        ext_file = CERTS_DIR / f"{hostname}.ext"
        with open(ext_file, 'w') as f:
            f.write(f"subjectAltName=DNS:{hostname}\n")

        # Sign with CA (with SAN extension)
        subprocess.run([
            'openssl', 'x509', '-req',
            '-in', CERTS_DIR / f"{hostname}.csr",
            '-CA', CA_CERT,
            '-CAkey', CA_KEY,
            '-CAcreateserial',
            '-out', CERTS_DIR / f"{hostname}-cert.pem",
            '-days', '365',
            '-extfile', str(ext_file)
        ], capture_output=True)

        # Combine key + cert
        with open(cert_file, 'w') as f:
            with open(CERTS_DIR / f"{hostname}-key.pem") as key:
                f.write(key.read())
            with open(CERTS_DIR / f"{hostname}-cert.pem") as cert:
                f.write(cert.read())

        print(f"✅ Certificate created: {cert_file}")
        return cert_file

    def _handle_https_request(self, client_ssl, host, port):
        """Handle decrypted HTTPS request"""
        try:
            # Read HTTP request from client
            request_line = b""
            while True:
                chunk = client_ssl.recv(1)
                if not chunk:
                    break
                request_line += chunk
                if b"\r\n\r\n" in request_line:
                    break

            if not request_line:
                return

            # Parse request
            headers_end = request_line.find(b"\r\n\r\n")
            headers_raw = request_line[:headers_end].decode('utf-8')
            lines = headers_raw.split('\r\n')

            if not lines:
                return

            method, path, protocol = lines[0].split(' ', 2)
            print(f"\n📥 {method} https://{host}{path}")

            # Parse headers
            headers = {}
            for line in lines[1:]:
                if ':' in line:
                    key, value = line.split(':', 1)
                    headers[key.strip()] = value.strip()

            # Read body if POST
            body = b""
            if method == 'POST':
                content_length = int(headers.get('Content-Length', 0))
                if content_length > 0:
                    body = request_line[headers_end+4:]
                    while len(body) < content_length:
                        body += client_ssl.recv(content_length - len(body))

            # Capture request
            timestamp = datetime.now()
            request_data = {
                'timestamp': timestamp.isoformat(),
                'method': method,
                'url': f"https://{host}{path}",
                'path': path,
                'headers': headers,
                'body': body.decode('utf-8', errors='ignore') if body else None
            }

            # Forward to real server
            server_socket = socket.create_connection((host, port))
            # Create SSL context for proxy→server connection with SNI
            server_context = ssl.create_default_context()
            server_ssl = server_context.wrap_socket(server_socket, server_hostname=host)

            # Send request to server
            server_ssl.sendall(request_line)
            if body:
                server_ssl.sendall(body)

            # Read response
            response_data = b""
            while True:
                chunk = server_ssl.recv(4096)
                if not chunk:
                    break
                response_data += chunk
                # Simple heuristic: stop if we got full response
                if b"</html>" in response_data or b"\r\n0\r\n\r\n" in response_data:
                    break

            # Parse response
            response_lines = response_data.split(b'\r\n')
            status_line = response_lines[0].decode('utf-8', errors='ignore')

            print(f"📤 Response: {status_line}")

            # Save capture
            self._save_capture(timestamp, request_data, response_data.decode('utf-8', errors='ignore'))

            # Forward response to client
            client_ssl.sendall(response_data)

            # Close connections
            server_ssl.close()
            client_ssl.close()

        except Exception as e:
            print(f"❌ HTTPS handling error: {e}")
            import traceback
            traceback.print_exc()

    def _save_capture(self, timestamp, request_data, response_raw):
        """Save captured data"""
        filename = timestamp.strftime('%Y%m%d_%H%M%S') + '_oauth_capture.json'

        # Detect if OAuth-related
        path = request_data.get('path', '')
        if 'oauth' in path or 'token' in path:
            subdir = CAPTURES_DIR / 'oauth'
        else:
            subdir = CAPTURES_DIR / 'requests'

        subdir.mkdir(parents=True, exist_ok=True)

        capture_data = {
            'request': request_data,
            'response_raw': response_raw[:5000],  # Limit for JSON
            'response_length': len(response_raw)
        }

        filepath = subdir / filename
        with open(filepath, 'w') as f:
            json.dump(capture_data, f, indent=2)

        print(f"💾 Saved: {filepath}")

def run_proxy():
    """Run MITM proxy server"""
    print(f"""
╔═══════════════════════════════════════════════════════╗
║       MITM Proxy for Claude OAuth Capture            ║
╠═══════════════════════════════════════════════════════╣
║  Port: {PORT}                                             ║
║  CA Cert: {CA_CERT}                    ║
║  Captures: {CAPTURES_DIR}/oauth/          ║
╚═══════════════════════════════════════════════════════╝
""")

    server = http.server.HTTPServer(('0.0.0.0', PORT), MITMProxyHandler)
    print(f"\n🚀 Proxy listening on port {PORT}...\n")

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n\n🛑 Proxy stopped")

if __name__ == '__main__':
    # Ensure directories exist
    CAPTURES_DIR.mkdir(exist_ok=True)
    CERTS_DIR.mkdir(exist_ok=True)

    run_proxy()
