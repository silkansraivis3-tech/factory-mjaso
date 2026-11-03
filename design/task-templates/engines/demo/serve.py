#!/usr/bin/env python3
"""Serve the plugin folder with caching off, for the task demos.

    python plugin/resources/engines/demo/serve.py [port]

Then open http://127.0.0.1:<port>/resources/engines/demo/ . The root is plugin/, so a demo
can reach the shared token file in skills/course-module-ui/ by a relative path.

POST /save?name=<file> stores the request body as demo/img/<file> - so a picture made in a
browser tab (Gemini) goes straight into the folder without a save dialog. Local only
(127.0.0.1), image names only, nothing else on disk can be written.
"""
import base64, http.server, os, re, sys, urllib.parse

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))


IMG = os.path.join(ROOT, 'resources', 'engines', 'demo', 'img')
NAME = re.compile(r'[A-Za-z0-9_.-]{1,80}\.(jpg|jpeg|png|webp|webm|mp4|mp3|wav|glb)')


class NoCache(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *a, **k):
        super().__init__(*a, directory=ROOT, **k)

    def end_headers(self):
        self.send_header('Cache-Control', 'no-store')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.send_header('Access-Control-Allow-Private-Network', 'true')
        super().end_headers()

    def handle_one_request(self):
        # the standard library stops at 64 KB per request line; a picture in the address needs ~4 MB
        try:
            self.raw_requestline = self.rfile.readline(4 * 1024 * 1024 + 1)
            if len(self.raw_requestline) > 4 * 1024 * 1024:
                self.send_error(414); return
            if not self.raw_requestline:
                self.close_connection = True; return
            if not self.parse_request():
                return
            m = getattr(self, 'do_' + self.command, None)
            if not m:
                self.send_error(501); return
            m()
            self.wfile.flush()
        except TimeoutError:
            self.close_connection = True

    def do_GET(self):
        # GET /save64?name=<file>&d=<base64url> - for a page whose own rules block every request
        # to this server but still allow opening a new address. Answers with a page that goes back.
        u = urllib.parse.urlparse(self.path)
        if u.path != '/save64':
            return super().do_GET()
        # several pictures in one address: name=a.jpg&d=...&name=b.jpg&d=... (paired in order)
        q = urllib.parse.parse_qs(u.query)
        names, datas = q.get('name') or [], q.get('d') or []
        if not names or len(names) != len(datas) or not all(NAME.fullmatch(n) for n in names):
            self.send_response(400); self.end_headers(); return
        done = []
        # a big file comes in parts: part=0 starts it, later parts are appended
        part = int((q.get('part') or ['0'])[0])
        for name, data in zip(names, datas):
            raw = base64.urlsafe_b64decode(data + '=' * (-len(data) % 4))
            with open(os.path.join(IMG, name), 'ab' if part > 0 else 'wb') as f:
                f.write(raw)
            done.append('%s %d bytes' % (name, len(raw)))
        self.send_response(200)
        self.send_header('Content-Type', 'text/html; charset=utf-8')
        self.end_headers()
        self.wfile.write(('<p>saved: %s</p><script>setTimeout(function(){history.back()},300)</script>' % '; '.join(done)).encode())

    def do_OPTIONS(self):
        self.send_response(204)
        self.end_headers()

    def do_POST(self):
        u = urllib.parse.urlparse(self.path)
        name = (urllib.parse.parse_qs(u.query).get('name') or [''])[0]
        if u.path != '/save' or not NAME.fullmatch(name):
            self.send_response(400); self.end_headers(); return
        n = int(self.headers.get('Content-Length') or 0)
        if n <= 0 or n > 15 * 1024 * 1024:
            self.send_response(413); self.end_headers(); return
        dest = os.path.join(IMG, name)
        with open(dest, 'wb') as f:
            f.write(self.rfile.read(n))
        self.send_response(200); self.end_headers()
        self.wfile.write(('saved %s %d bytes' % (name, n)).encode())

    def log_message(self, *a):
        pass


if __name__ == '__main__':
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8765
    print('http://127.0.0.1:%d/resources/engines/demo/' % port, flush=True)
    http.server.ThreadingHTTPServer(('127.0.0.1', port), NoCache).serve_forever()
