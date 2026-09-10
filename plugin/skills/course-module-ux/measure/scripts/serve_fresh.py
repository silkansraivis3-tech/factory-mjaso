#!/usr/bin/env python3
"""Serve a directory on a fresh, previously-unused port — and print its PID.

Two habits this exists to enforce, both of which cost real passes:

1.  **A fresh port after every edit.** The browser's disk cache will happily hand
    a probe the file from before your fix, on the same port. You then measure the
    old build, conclude the fix did nothing, and "fix" it again.

2.  **Kill only your own server, by PID** -- a broad pattern kill once destroyed
    about forty unrelated servers on this machine -- and then **confirm the port
    actually freed by probing it.** A zero exit code from `kill` means the stop
    command ran, not that the process is gone: kill a shell wrapper instead of
    the server and it still exits 0 while the port stays bound. This prints both
    the PID and the confirm command.

Also: serve over HTTP, never open the page as file://. A file:// page hides real
behaviour and blocks the storage the runner depends on.

Usage
-----
    python serve_fresh.py [DIR] [--host 127.0.0.1] [--state PATH]

It prints, one per line:

    URL  http://127.0.0.1:<port>/
    PID  <pid>
    STOP kill <pid>   then CONFIRM by probing the port
         (if it is still bound, Windows fallback: taskkill //F //PID <pid>)

Exit codes
----------
    0  serving (blocks until interrupted)
    2  the directory does not exist, or no free unused port could be found
"""

import argparse
import functools
import http.server
import io
import json
import os
import socket
import socketserver
import sys

DEFAULT_STATE = os.path.join(
    os.path.expanduser("~"), ".course_module_ux_used_ports.json"
)
PORT_LOW = 8300
PORT_HIGH = 8999


def load_used(state_path):
    try:
        with io.open(state_path, encoding="utf-8") as fh:
            data = json.load(fh)
        return set(int(p) for p in data.get("used", []))
    except Exception:                                    # noqa: BLE001 - first run
        return set()


def save_used(state_path, used):
    try:
        with io.open(state_path, "w", encoding="utf-8") as fh:
            json.dump({"used": sorted(used)}, fh)
    except Exception as exc:                             # noqa: BLE001
        sys.stderr.write(
            "warning: could not record used ports in %s (%s). The next run may "
            "reuse this port and measure a cached file.\n" % (state_path, exc)
        )


def free_port(host, used):
    for port in range(PORT_LOW, PORT_HIGH + 1):
        if port in used:
            continue
        s = socket.socket()
        try:
            s.bind((host, port))
            return port
        except OSError:
            continue
        finally:
            s.close()
    return None


class QuietHandler(http.server.SimpleHTTPRequestHandler):
    def log_message(self, fmt, *args):
        pass                                             # the probe output is the signal

    def end_headers(self):
        # Belt as well as braces: a fresh port defeats the disk cache, and these
        # headers defeat it again if a port ever does get reused.
        self.send_header("Cache-Control", "no-store, no-cache, must-revalidate")
        self.send_header("Pragma", "no-cache")
        self.send_header("Expires", "0")
        http.server.SimpleHTTPRequestHandler.end_headers(self)


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    p.add_argument("directory", nargs="?", default=".")
    p.add_argument("--host", default="127.0.0.1")
    p.add_argument("--state", default=DEFAULT_STATE)
    args = p.parse_args(argv)

    root = os.path.abspath(args.directory)
    if not os.path.isdir(root):
        sys.stderr.write("not a directory: %s\n" % root)
        return 2

    used = load_used(args.state)
    port = free_port(args.host, used)
    if port is None:
        sys.stderr.write(
            "no unused port left in %d-%d. Delete %s to start the range again — "
            "but clear the browser cache when you do.\n"
            % (PORT_LOW, PORT_HIGH, args.state)
        )
        return 2
    used.add(port)
    save_used(args.state, used)

    handler = functools.partial(QuietHandler, directory=root)
    socketserver.TCPServer.allow_reuse_address = False
    httpd = socketserver.TCPServer((args.host, port), handler)

    print("URL  http://%s:%d/" % (args.host, port))
    print("PID  %d" % os.getpid())
    # `kill <pid>` works, on Windows too. What does NOT follow is that a zero exit
    # code means the port is free: kill the wrong pid -- a shell wrapper rather
    # than this process -- and the stop command still succeeds while the port
    # stays bound. So the durable rule is: confirm by PROBING the port, never by
    # trusting the exit code of whatever you used to stop the server.
    print("STOP kill %d   then CONFIRM: python -c \"import socket;"
          "s=socket.socket();s.bind(('%s',%d));print('freed')\""
          % (os.getpid(), args.host, port))
    print("     if the port is still bound, Windows fallback: taskkill //F //PID %d"
          % os.getpid())
    print("ROOT %s" % root)
    sys.stdout.flush()

    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        httpd.server_close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
