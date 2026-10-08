#!/usr/bin/env python3
"""minimal local server to run the offline LiveMCQ viewer:
    python3 viewer/serve.py
then open http://localhost:8000/viewer/   (Ctrl+C to stop)"""
import http.server, os, socketserver, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PORT = int(os.environ.get("LIVEMCQ_PORT", "8000"))

class H(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *a, **kw):
        super().__init__(*a, directory=ROOT, **kw)
    def end_headers(self):
        self.send_header("Cache-Control", "no-store")
        super().end_headers()

os.chdir(ROOT)
with socketserver.TCPServer(("0.0.0.0", PORT), H) as httpd:
    print(f"\n  LiveMCQ offline archive →  http://localhost:{PORT}/viewer/")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n  stopped.")