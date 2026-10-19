#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Nothing is generated without the person's yes, and every picture is counted and priced (1.2.0);
a hard spending cap, a paid video never lost, and the client's own confirmation dialog (1.3.1).

    python test_nano_banana.py

No key and no network: Google is replaced by a stand-in that hands back a tiny picture.
"""
import base64
import importlib.util
import json
import os
import shutil
import subprocess
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

        def call(tool, args):
            r = nb.handle({"jsonrpc": "2.0", "id": 9, "method": "tools/call",
                           "params": {"name": tool, "arguments": args}})
            return r, r["content"][0]["text"]

        img = {"prompt": "an LNG carrier at sea", "out_path": os.path.join(tmp, "cap.png"), "approved_by_user": "yes"}
        vid = {"prompt": "slow orbit", "out_path": os.path.join(tmp, "v.mp4"), "approved_by_user": "yes", "wait_seconds": 0}

        print("\n-- a hard spending cap, not only an instruction", file=REAL_STDOUT)
        # usage so far today: 2 pictures at EUR 0.12 + 1 clip at EUR 1.50 = EUR 1.74
        os.environ["NANO_BANANA_DAILY_LIMIT_EUR"] = "1.80"
        sent.clear()
        nb.ensure_key = no_key
        nb.http = lambda *a, **k: sent.append(a) or {}
        r, text = call("generate_image", img)
        check("a picture that would pass the daily cap is refused", r.get("isError") and "spending cap" in text, text)
        check("... and the refusal says how only the person can raise it",
              "NANO_BANANA_DAILY_LIMIT_EUR" in text and "settings.json" in text and "restart" in text, text)
        check("... before the key is asked for and before anything is sent", not sent, sent)
        os.environ["NANO_BANANA_DAILY_LIMIT_EUR"] = "100"
        os.environ["NANO_BANANA_MONTHLY_LIMIT_EUR"] = "2"
        r, text = call("generate_video", vid)
        check("a clip that would pass the monthly cap is refused", r.get("isError")
              and "NANO_BANANA_MONTHLY_LIMIT_EUR" in text and "video clip" in text and not sent, text)
        os.environ.pop("NANO_BANANA_MONTHLY_LIMIT_EUR")
        u = nb.usage_summary()
        check("the monthly default cap is EUR 50, and today's spend is counted (EUR 1.74)",
              (nb.daily_limit(), nb.monthly_limit()) == (100.0, 50.0) and u["eur_today"] == 1.74, u)
        os.environ.pop("NANO_BANANA_DAILY_LIMIT_EUR")
        check("... and the daily default cap is EUR 5", nb.daily_limit() == 5.0)

        print("\n-- a paid video is never lost", file=REAL_STDOUT)
        nb.ensure_key = lambda: None
        OP = "models/veo/operations/op-123"

        def flaky(method, url, *a, **k):
            if method == "POST":
                return {"name": OP}
            raise nb.ApiError(503, "HTTP 503: backend unavailable")
        nb.http = flaky
        r, text = call("generate_video", dict(vid, wait_seconds=60))
        res = json.loads(text) if not r.get("isError") else {}
        check("a failed status poll returns status running, not an error",
              not r.get("isError") and res.get("status") == "running", text)
        check("... with the operation name to collect it later", res.get("operation") == OP and "get_video" in res.get("next", ""), res)
        rows = [json.loads(l) for l in open(os.environ["NANO_BANANA_USAGE_FILE"], encoding="utf-8").read().splitlines()]
        check("the operation is in usage.jsonl the moment the clip starts", rows[-1].get("operation") == OP and rows[-1]["kind"] == "video", rows[-1])
        check("nano_banana_status lists recent video operations",
              any(o["operation"] == OP for o in nb.usage_summary()["recent_video_operations"]))

        def offline(method, url, *a, **k):
            raise nb.ApiError(0, "network error: timed out")
        nb.http = offline
        r, text = call("get_video", {"operation": OP, "out_path": vid["out_path"], "wait_seconds": 0})
        check("get_video on a dropped network also answers running + operation",
              not r.get("isError") and json.loads(text)["operation"] == OP, text)

        nb.http = lambda *a, **k: {"done": True, "error": {"message": "safety filter"}}
        r, text = call("get_video", {"operation": OP, "out_path": vid["out_path"], "wait_seconds": 0})
        check("a video that really failed is an error - and still names the operation",
              r.get("isError") and "safety filter" in text and OP in text, text)

        print("\n-- 1.3.2: the cap fails closed", file=REAL_STDOUT)
        keep = {k: os.environ.get(k) for k in ("NANO_BANANA_USAGE_FILE", "NANO_BANANA_DAILY_LIMIT_EUR", "NANO_BANANA_MONTHLY_LIMIT_EUR")}
        os.environ.update({"NANO_BANANA_DAILY_LIMIT_EUR": "100", "NANO_BANANA_MONTHLY_LIMIT_EUR": "100"})
        fresh = os.path.join(tmp, "usage2.jsonl")
        os.environ["NANO_BANANA_USAGE_FILE"] = fresh
        nb.ensure_key = lambda: None
        nb.http = lambda *a, **k: {"candidates": [{"content": {"parts": [{"inlineData": {"mimeType": "image/png", "data": PNG}}]}}]}
        blocker = os.path.join(tmp, "a_file")
        open(blocker, "w").write("x")
        r, text = call("generate_image", dict(img, out_path=os.path.join(blocker, "sub", "x.png")))
        rows2 = open(fresh, encoding="utf-8").read().splitlines() if os.path.isfile(fresh) else []
        check("a paid picture whose file cannot be saved is still counted (recorded before the write)",
              r.get("isError") and len(rows2) == 1 and json.loads(rows2[0])["kind"] == "image", (text, rows2))
        sent.clear()
        nb.http = lambda *a, **k: sent.append(a) or {}
        os.environ["NANO_BANANA_USAGE_FILE"] = tmp                  # a folder: it cannot be read as the log
        r, text = call("generate_image", img)
        check("a usage log that cannot be read refuses the next picture - unknown is not EUR 0",
              r.get("isError") and "cannot be checked" in text and not sent, text)
        os.environ["NANO_BANANA_USAGE_FILE"] = fresh
        nb.UNCOUNTED.append("Permission denied")
        r, text = call("generate_image", img)
        check("a usage-log write that failed earlier refuses the next picture too",
              r.get("isError") and "cannot be checked" in text and "Permission denied" in text and not sent, text)
        nb.UNCOUNTED.clear()

        print("\n-- 1.3.2: Pro fails, the same picture once with Flash", file=REAL_STDOUT)
        asked_models = []

        def pro_busy(method, url, body=None, *a, **k):
            m = (body or {}).get("model") or url.split("/models/")[-1].split(":")[0]
            asked_models.append(m)
            if m == nb.PRO_IMAGE_MODEL:
                raise nb.ApiError(503, "HTTP 503: the model is overloaded")
            return {"candidates": [{"content": {"parts": [{"inlineData": {"mimeType": "image/png", "data": PNG}}]}}]}
        nb.http = pro_busy
        before = len(open(fresh, encoding="utf-8").read().splitlines())
        r, text = call("generate_image", dict(img, model="pro", out_path=os.path.join(tmp, "fb.png")))
        res = {} if r.get("isError") else json.loads(text)
        after = len(open(fresh, encoding="utf-8").read().splitlines())
        check("Pro overloaded: the picture is made with Flash, and the result says so",
              res.get("model") == nb.DEFAULT_IMAGE_MODEL and res.get("fell_back_from", {}).get("from") == nb.PRO_IMAGE_MODEL
              and "503" in res["fell_back_from"]["why"] and "Flash" in res["next"] and os.path.isfile(os.path.join(tmp, "fb.png")), text)
        check("... Pro asked once, Flash once, and one picture counted", asked_models == [nb.PRO_IMAGE_MODEL, nb.DEFAULT_IMAGE_MODEL]
              and after - before == 1, (asked_models, after - before))

        def both_fail(method, url, body=None, *a, **k):
            raise nb.ApiError(503, "HTTP 503: overloaded")
        nb.http = both_fail
        r, text = call("generate_image", dict(img, model="pro"))
        check("both fail: an error that names both models, nothing counted",
              r.get("isError") and nb.PRO_IMAGE_MODEL in text and nb.DEFAULT_IMAGE_MODEL in text
              and len(open(fresh, encoding="utf-8").read().splitlines()) == after, text)
        asked_models.clear()
        nb.http = lambda method, url, body=None, *a, **k: asked_models.append(1) or (_ for _ in ()).throw(nb.ApiError(400, "API key not valid"))
        r, text = call("generate_image", dict(img, model="pro"))
        check("a key problem is not retried with Flash", r.get("isError") and len(asked_models) == 1, (asked_models, text))
        asked_models.clear()
        nb.http = pro_busy
        r, text = call("generate_image", dict(img, model=nb.DEFAULT_IMAGE_MODEL, out_path=os.path.join(tmp, "fl.png")))
        check("a Flash request is never 'fallen back' - one request", not r.get("isError") and asked_models == [nb.DEFAULT_IMAGE_MODEL]
              and "fell_back_from" not in json.loads(text), text)
        for k, v in keep.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v

        print("\n-- a yes Claude cannot type: the client's confirmation dialog", file=REAL_STDOUT)
        init = lambda caps: nb.handle({"jsonrpc": "2.0", "id": 0, "method": "initialize",
                                       "params": {"protocolVersion": "2025-06-18", "capabilities": caps}})
        init({})
        check("a client without elicitation: approved_by_user stands alone", nb.CLIENT["elicitation"] is False)
        init({"elicitation": {"url": {}}})
        check("a client with URL-mode elicitation only has no form dialog", nb.CLIENT["elicitation"] is False)
        init({"elicitation": {"form": {}, "url": {}}})
        check("a client that declares form elicitation is detected (Claude Code's shape)", nb.CLIENT["elicitation"] is True)
        init({"elicitation": {}})
        check("... and so is the original empty {}", nb.CLIENT["elicitation"] is True)

        asked = []
        real_send = nb.send

        def answering(action, generate=True):
            def fake_send(msg):
                asked.append(msg)
                nb.INBOX.put(json.dumps({"jsonrpc": "2.0", "method": "notifications/progress"}))   # unrelated, kept
                nb.INBOX.put(json.dumps({"jsonrpc": "2.0", "id": msg["id"],
                                         "result": {"action": action, "content": {"generate": generate}}}))
            return fake_send

        nb.http = lambda *a, **k: {"candidates": [{"content": {"parts": [{"inlineData": {"mimeType": "image/png", "data": PNG}}]}}]}
        nb.send = answering("accept")
        r, text = call("generate_image", img)
        check("the person is asked in the dialog, with the prompt and the price",
              asked and asked[-1]["method"] == "elicitation/create" and "LNG carrier" in asked[-1]["params"]["message"]
              and "EUR" in asked[-1]["params"]["message"], asked[-1:])
        check("... a yes there generates it", not r.get("isError") and json.loads(text)["confirmed_in_dialog"] is True, text)
        check("... and a message that arrived meanwhile is kept for the main loop",
              any("notifications/progress" in l for l in nb.BACKLOG))
        nb.BACKLOG.clear()

        for action, gen, why in (("decline", False, "decline"), ("accept", False, "accept with the box unticked"),
                                 ("cancel", False, "cancel")):
            sent.clear()
            nb.http = lambda *a, **k: sent.append(a) or {}
            nb.send = answering(action, gen)
            r, text = call("generate_image", img)
            check("a %s in the dialog is refused, nothing sent" % why, r.get("isError") and "did not confirm" in text and not sent, text)
            nb.BACKLOG.clear()

        nb.send = lambda msg: asked.append(msg)          # the client never answers
        nb.CONFIRM_TIMEOUT = 0.2
        r, text = call("generate_image", img)
        check("no answer from the dialog is refused too", r.get("isError") and "no answer" in text, text)
        nb.send = real_send
        nb.CLIENT["elicitation"] = False

        # the same over real stdio: the server asks mid-call and reads the answer off the same pipe
        lines = [{"jsonrpc": "2.0", "id": 1, "method": "initialize",
                  "params": {"protocolVersion": "2025-06-18", "capabilities": {"elicitation": {}}}},
                 {"jsonrpc": "2.0", "id": 2, "method": "tools/call",
                  "params": {"name": "generate_image", "arguments": img}},
                 {"jsonrpc": "2.0", "id": "nb-1", "result": {"action": "decline"}}]
        p = subprocess.run([sys.executable, os.path.join(HERE, "nano_banana_mcp.py")],
                           input="".join(json.dumps(l) + "\n" for l in lines), capture_output=True,
                           text=True, encoding="utf-8", timeout=60,
                           env=dict(os.environ, GEMINI_API_KEY="", GOOGLE_API_KEY=""))
        got = [json.loads(l) for l in p.stdout.splitlines() if l.strip()]
        ask = [m for m in got if m.get("method") == "elicitation/create"]
        fin = [m for m in got if m.get("id") == 2]
        check("over real stdio the server asks the client and honours its decline",
              ask and fin and fin[0]["result"].get("isError") and "did not confirm" in fin[0]["result"]["content"][0]["text"],
              p.stdout[-400:] + p.stderr[-300:])
    finally:
        sys.stdout = REAL_STDOUT
        for v in ("NANO_BANANA_DAILY_LIMIT_EUR", "NANO_BANANA_MONTHLY_LIMIT_EUR", "NANO_BANANA_EUR_PER_IMAGE"):
            os.environ.pop(v, None)
        shutil.rmtree(tmp, ignore_errors=True)
    print("\n" + "=" * 72 + "\n%d passed, %d failed" % (len(PASS), len(FAIL)))
    if not FAIL:
        print("Nothing is generated without the person's yes, and every picture is counted and priced.")
    return 1 if FAIL else 0


if __name__ == "__main__":
    sys.exit(main())
