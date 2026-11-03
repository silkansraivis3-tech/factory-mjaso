"""Read-only demo server for real tablets and phones on the same Wi-Fi.

serve.py is for this computer only (it can save files). This one can be reached from the
network, so it does less: GET and HEAD only, nothing written, no folder listings, and only
the files the demo pages need - the engines folder and the course-module-ui templates.
usage: python tablet_serve.py [port=8790]   then open http://<this computer's address>:8790/
"""
import http.server
import os
import socket
import sys
import urllib.parse

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))  # plugin/
ALLOW = ('resources/engines/', 'skills/course-module-ui/templates/')
START = '/resources/engines/demo/'


class ReadOnly(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *a, **k):
        super().__init__(*a, directory=ROOT, **k)

    def _allowed(self):
        path = urllib.parse.unquote(urllib.parse.urlsplit(self.path).path).lstrip('/')
        if '..' in path.split('/'):
            return False
        return path.startswith(ALLOW)

    def do_GET(self):
        if urllib.parse.urlsplit(self.path).path in ('', '/'):
            self.send_response(302); self.send_header('Location', START); self.end_headers(); return
        if not self._allowed():
            self.send_error(404); return
        full = self.translate_path(self.path)
        if os.path.isdir(full) and not os.path.exists(os.path.join(full, 'index.html')):
            self.send_error(404); return  # no folder listings
        super().do_GET()

    def do_HEAD(self):
        if not self._allowed():
            self.send_error(404); return
        super().do_HEAD()

    def end_headers(self):
        self.send_header('Cache-Control', 'no-store')  # a tablet always gets the latest version
        super().end_headers()

    def log_message(self, fmt, *args):
        sys.stderr.write('%s %s\n' % (self.address_string(), fmt % args))


def lan_address():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(('10.255.255.255', 1))  # no packet is sent; this only picks the outgoing interface
        return s.getsockname()[0]
    except OSError:
        return '127.0.0.1'
    finally:
        s.close()


if __name__ == '__main__':
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8790
    print('Tablet demo server: http://%s:%d/  (read-only)' % (lan_address(), port), flush=True)
    http.server.ThreadingHTTPServer(('0.0.0.0', port), ReadOnly).serve_forever()
