#!/usr/bin/env python3
"""Local server for the Polaris site with clean-URL -> .html routing.

    python3 tools/serve.py [port]   # default 4173
"""
import http.server, socketserver, os, sys, urllib.parse

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PORT = int(sys.argv[1]) if len(sys.argv) > 1 else 4173

CLEAN = {
    "/": "index.html",
    "/collection": "collection.html",
    "/terms": "terms.html",
    "/privacy": "privacy.html",
    "/cookies": "cookies.html",
    "/credits": "credits.html",
    "/printer": "printer.html",
    "/printer-fig": "printer-fig.html",
}


class Server(socketserver.TCPServer):
    allow_reuse_address = True


class Handler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *a, **kw):
        super().__init__(*a, directory=ROOT, **kw)

    def do_GET(self):
        path = urllib.parse.urlsplit(self.path).path
        if path in CLEAN:
            self.path = "/" + CLEAN[path]
        super().do_GET()


if __name__ == "__main__":
    os.chdir(ROOT)
    with Server(("127.0.0.1", PORT), Handler) as httpd:
        print(f"Polaris -> http://127.0.0.1:{PORT}/  (Ctrl-C to stop)")
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            pass
