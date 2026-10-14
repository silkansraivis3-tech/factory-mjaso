#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Nothing is generated without the person's yes, and every picture is counted and priced (1.2.0).

    python test_nano_banana.py

No key and no network: Google is replaced by a stand-in that hands back a tiny picture.
"""
import base64
import importlib.util
import json
import os
import shutil
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
PASS, FAIL = [], []
REAL_STDOUT = sys.stdout


def check(name, ok, detail=""):
    (PASS if ok else FAIL).append(name)
    print(("  ok    " if ok else "  FAIL  ") + name + ("" if ok else "  -> %s" % str(detail)[:400]), file=REAL_STDOUT)


def load():
    spec = importlib.util.spec_from_file_location("nb", os.path.join(HERE, "nano_banana_mcp.py"))
    nb = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(nb)
    sys.stdout = REAL_STDOUT                       # the server points stdout at stderr; the test wants it back
    return nb


PNG = base64.b64encode(bytes.fromhex("89504e470d0a1a0a0000000d49484452000000010000000108020000009077"
                                     "53de0000000c4944415408d763f8ffff3f0005fe02fea7d6a4b40000000049454e44ae426082")).decode()


def main():
    tmp = tempfile.mkdtemp(prefix="nb_")
    os.environ["NANO_BANANA_USAGE_FILE"] = os.path.join(tmp, "usage.jsonl")
    os.environ.pop("NANO_BANANA_EUR_PER_IMAGE", None)
    try:
        nb = load()
        sent = []

        def no_key():
            raise AssertionError("asked for the key before the person said yes")
        nb.ensure_key = no_key
        nb.http = lambda *a, **k: sent.append(a) or {}

        print("-- nothing is generated without the person's yes", file=REAL_STDOUT)
        for tool, args in (("generate_image", {"prompt": "an LNG carrier at sea", "out_path": os.path.join(tmp, "a.png")}),
                           ("generate_video", {"prompt": "slow orbit", "out_path": os.path.join(tmp, "a.mp4")})):
            r = nb.handle({"jsonrpc": "2.0", "id": 1, "method": "tools/call", "params": {"name": tool, "arguments": args}})
            text = r["content"][0]["text"]
            check("%s without approved_by_user is refused, with how to ask" % tool,
                  r.get("isError") and "Not generated - every picture costs money" in text and "Generate this one picture?" in text, text)
            r = nb.handle({"jsonrpc": "2.0", "id": 1, "method": "tools/call", "params": {"name": tool, "arguments": dict(args, approved_by_user=" ")}})
            check("... and so is an empty yes", r.get("isError"), r)
        check("... before the key is asked for and before anything is sent to Google", not sent, sent)
        tools = {t["name"]: t for t in nb.TOOLS}
        for t in ("generate_image", "generate_video"):
            check("%s says it costs money, and requires approved_by_user" % t,
                  "approved_by_user" in tools[t]["inputSchema"]["required"] and "COSTS" in tools[t]["description"])

        print("\n-- with a yes: one picture, counted and priced", file=REAL_STDOUT)
        nb.ensure_key = lambda: None
        nb.http = lambda *a, **k: {"candidates": [{"content": {"parts": [{"inlineData": {"mimeType": "image/png", "data": PNG}}]}}]}
        out = os.path.join(tmp, "assets", "lng_carrier.png")
        r = nb.handle({"jsonrpc": "2.0", "id": 2, "method": "tools/call", "params": {"name": "generate_image", "arguments": {
            "prompt": "an LNG carrier at sea", "out_path": out, "approved_by_user": "Yes, generate it"}}})
        res = json.loads(r["content"][0]["text"])
        check("the picture is saved", os.path.isfile(out), r)
        check("the result says what it cost: picture 1 today, about EUR 0.10",
              res["cost"]["images_today"] == 1 and res["cost"]["images_today_eur"] == 0.1
              and "Picture 1 today on this computer, about EUR 0.10" in res["cost"]["tell_the_person"], res.get("cost"))
        check("... and tells Claude to show it and ask before any change", "needs their yes again" in res["next"], res["next"])
        line = json.loads(open(os.environ["NANO_BANANA_USAGE_FILE"], encoding="utf-8").read().splitlines()[0])
        check("the usage log keeps the person's words, the model and the file", line["approved_by_user"] == "Yes, generate it"
              and line["kind"] == "image" and line["out_path"] == out and line["model"], line)
        nb.record_use("image", "m", "b.png", "yes")
        nb.record_use("video", "veo", "c.mp4", "yes")
        u = nb.usage_summary()
        check("today and this month are counted, pictures and clips apart", u["images_today"] == 2 and u["videos_today"] == 1
              and u["images_this_month"] == 2 and abs(u["images_this_month_eur"] - 0.2) < 1e-9, u)
        os.environ["NANO_BANANA_EUR_PER_IMAGE"] = "0.12"
        check("the price per picture can be set (NANO_BANANA_EUR_PER_IMAGE)", abs(nb.usage_summary()["images_today_eur"] - 0.24) < 1e-9)
        st = nb.status()
        check("nano_banana_status shows the usage too", "usage" in st and st["usage"]["images_today"] == 2, st)
    finally:
        sys.stdout = REAL_STDOUT
        shutil.rmtree(tmp, ignore_errors=True)
    print("\n" + "=" * 72 + "\n%d passed, %d failed" % (len(PASS), len(FAIL)))
    if not FAIL:
        print("Nothing is generated without the person's yes, and every picture is counted and priced.")
    return 1 if FAIL else 0


if __name__ == "__main__":
    sys.exit(main())
