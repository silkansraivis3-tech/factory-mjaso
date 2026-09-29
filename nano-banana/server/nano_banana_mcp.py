#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Nano Banana MCP server - Gemini image and Veo video generation for Claude Code.

    python nano_banana_mcp.py            # speaks MCP over stdio (Claude Code starts it)
    python nano_banana_mcp.py --selftest # checks the key and lists the image/video models

WHY THIS EXISTS
Asked for a "realistic" or "3D" picture, a language model draws vectors: a gradient,
three boxes and a glow. That is not a render. This server hands the pixels to the
model that actually makes them (Nano Banana for stills, Veo for motion) and gives
Claude back a file on disk, so Claude still owns the whole job - the brief, the
prompt, looking at the result, rejecting it, packaging it and placing it.

STANDARD LIBRARY ONLY. No pip install, nothing to break on a colleague's machine.

THE KEY - first one found wins:
  1. NANO_BANANA_API_KEY  (the plugin's userConfig fills this in)
  2. GEMINI_API_KEY       (a Windows/user environment variable)
  3. GOOGLE_API_KEY
  4. the file  <CLAUDE_PLUGIN_DATA>/gemini_api_key
  5. the file  ~/.config/nano-banana/gemini_api_key
The userConfig value has its own variable name on purpose: an empty userConfig
must never blank out a GEMINI_API_KEY the user set in their environment.
The key is never printed, logged or returned in a tool result.
"""
from __future__ import annotations

import base64
import json
import mimetypes
import os
import sys
import time
import urllib.error
import urllib.request

VERSION = "1.0.0"
API = "https://generativelanguage.googleapis.com/v1beta"

DEFAULT_IMAGE_MODEL = "gemini-3.1-flash-image"   # Nano Banana 2 - the generalist
PRO_IMAGE_MODEL = "gemini-3-pro-image"           # Nano Banana Pro - hardest scenes
DEFAULT_VIDEO_MODEL = "veo-3.1-fast-generate-preview"

IMAGE_ASPECTS = ["1:1", "3:2", "2:3", "3:4", "4:3", "4:5", "5:4", "9:16", "16:9", "21:9"]
IMAGE_SIZES = ["512px", "1K", "2K", "4K"]
VIDEO_ASPECTS = ["16:9", "9:16"]
VIDEO_RES = ["720p", "1080p", "4k"]
VIDEO_SECONDS = ["4", "6", "8"]

# stdout is the MCP channel. Anything human-readable goes to stderr.
OUT = sys.stdout
sys.stdout = sys.stderr


def log(*a):
    print("[nano-banana]", *a, file=sys.stderr, flush=True)


# ---------------------------------------------------------------- key & config

def _read_file(p):
    try:
        with open(p, encoding="utf-8") as f:
            return f.read().strip()
    except OSError:
        return ""


def api_key():
    for var in ("NANO_BANANA_API_KEY", "GEMINI_API_KEY", "GOOGLE_API_KEY"):
        v = os.environ.get(var, "").strip()
        if v and not v.startswith("${"):          # an unsubstituted ${user_config.x}
            return v, var
    candidates = []
    data = os.environ.get("CLAUDE_PLUGIN_DATA", "")
    if data:
        candidates.append(os.path.join(data, "gemini_api_key"))
    candidates.append(os.path.join(os.path.expanduser("~"), ".config", "nano-banana",
                                   "gemini_api_key"))
    for p in candidates:
        v = _read_file(p)
        if v:
            return v, p
    return "", ""


def cfg(name, default):
    v = os.environ.get(name, "").strip()
    return default if (not v or v.startswith("${")) else v


# ---------------------------------------------------------------- HTTP

class ApiError(Exception):
    def __init__(self, status, message):
        super().__init__(message)
        self.status = status


def _redact(text):
    k, _ = api_key()
    return text.replace(k, "***") if k else text


def http(method, url, body=None, timeout=300, raw=False):
    key, _ = api_key()
    if not key:
        raise ApiError(0, NO_KEY)
    data = json.dumps(body).encode("utf-8") if body is not None else None
    req = urllib.request.Request(url, data=data, method=method, headers={
        "x-goog-api-key": key,
        "Content-Type": "application/json",
        "User-Agent": "nano-banana-mcp/" + VERSION,
    })
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            payload = r.read()
    except urllib.error.HTTPError as e:
        detail = e.read().decode("utf-8", "replace")
        try:
            j = json.loads(detail)
            if isinstance(j, list) and j:       # the Interactions API wraps it in a list
                j = j[0]
            detail = j.get("error", {}).get("message", detail)
        except (ValueError, AttributeError):
            pass
        raise ApiError(e.code, _redact("HTTP %s: %s" % (e.code, detail[:800])))
    except urllib.error.URLError as e:
        raise ApiError(0, "network error: %s" % e.reason)
    if raw:
        return payload
    return json.loads(payload.decode("utf-8")) if payload else {}


NO_KEY = ("No Gemini API key yet. NOVIKONTAS uses one shared key - ask Raivis "
          "(raivis.silkans@novikontas.org) for it, then paste it yourself in "
          "/plugin -> nano-banana -> Configure (or set the Windows environment variable "
          "GEMINI_API_KEY) and restart Claude Code. Never paste the key into the chat.")


# ---------------------------------------------------------------- helpers

def _abs(path):
    return os.path.abspath(os.path.expanduser(path))


def _load_image(path):
    p = _abs(path)
    with open(p, "rb") as f:
        b = f.read()
    mime = mimetypes.guess_type(p)[0] or "image/png"
    return mime, base64.b64encode(b).decode("ascii")


def _find_images(node, found):
    """Walk any response shape and collect every base64 image in it.

    The Interactions API returns {"type": "image", "data", "mime_type"} blocks,
    generateContent returns {"inlineData": {"mimeType", "data"}}. Walking the
    tree instead of hard-coding one path means a renamed wrapper field does not
    silently lose the picture."""
    if isinstance(node, dict):
        if node.get("data") and isinstance(node.get("data"), str) and (
                node.get("type") == "image"
                or str(node.get("mime_type") or node.get("mimeType") or "").startswith("image/")):
            found.append((node.get("mime_type") or node.get("mimeType") or "image/png",
                          node["data"]))
            return
        for v in node.values():
            if isinstance(v, (dict, list)):
                _find_images(v, found)
    elif isinstance(node, list):
        for v in node:
            _find_images(v, found)


def _find_text(node, out):
    if isinstance(node, dict):
        if isinstance(node.get("text"), str) and node.get("thought") is not True:
            out.append(node["text"])
        for v in node.values():
            if isinstance(v, (dict, list)):
                _find_text(v, out)
    elif isinstance(node, list):
        for v in node:
            _find_text(v, out)


EXT = {"image/png": ".png", "image/jpeg": ".jpg", "image/webp": ".webp"}


def _out_paths(out_path, n, mime):
    base, ext = os.path.splitext(_abs(out_path))
    if ext.lower() not in (".png", ".jpg", ".jpeg", ".webp"):
        base, ext = base + ext, ""
    # The extension follows the bytes: never write JPEG data into a .png name.
    ext = EXT.get(mime, ext or ".png")
    if n == 1:
        return [base + ext]
    return ["%s_%d%s" % (base, i + 1, ext) for i in range(n)]


def _dims(b):
    """Width x height from PNG/JPEG/WEBP header bytes, without Pillow."""
    try:
        if b[:8] == b"\x89PNG\r\n\x1a\n":
            return int.from_bytes(b[16:20], "big"), int.from_bytes(b[20:24], "big")
        if b[:2] == b"\xff\xd8":
            i = 2
            while i < len(b) - 9:
                if b[i] != 0xFF:
                    i += 1
                    continue
                marker = b[i + 1]
                seg = int.from_bytes(b[i + 2:i + 4], "big")
                if marker in (0xC0, 0xC1, 0xC2, 0xC3, 0xC5, 0xC6, 0xC7, 0xC9, 0xCA, 0xCB,
                              0xCD, 0xCE, 0xCF):
                    return int.from_bytes(b[i + 7:i + 9], "big"), int.from_bytes(b[i + 5:i + 7], "big")
                i += 2 + seg
        if b[:4] == b"RIFF" and b[8:12] == b"WEBP" and b[12:16] == b"VP8X":
            return (int.from_bytes(b[24:27], "little") + 1,
                    int.from_bytes(b[27:30], "little") + 1)
    except (IndexError, ValueError):
        pass
    return None


# ---------------------------------------------------------------- image

def _interactions_body(model, prompt, refs, aspect, size, mime_out):
    blocks = [{"type": "text", "text": prompt}]
    for mime, data in refs:
        blocks.append({"type": "image", "mime_type": mime, "data": data})
    fmt = {"type": "image", "mime_type": mime_out}
    if aspect:
        fmt["aspect_ratio"] = aspect
    if size:
        fmt["image_size"] = size
    return {"model": model, "input": blocks, "response_format": fmt, "store": False}


def _generate_content_body(prompt, refs, aspect, size):
    parts = [{"text": prompt}]
    for mime, data in refs:
        parts.append({"inline_data": {"mime_type": mime, "data": data}})
    image_cfg = {}
    if aspect:
        image_cfg["aspectRatio"] = aspect
    if size:
        image_cfg["imageSize"] = size
    gen = {"responseModalities": ["TEXT", "IMAGE"]}
    if image_cfg:
        gen["imageConfig"] = image_cfg
    return {"contents": [{"role": "user", "parts": parts}], "generationConfig": gen}


def generate_image(a):
    prompt = (a.get("prompt") or "").strip()
    if not prompt:
        raise ValueError("prompt is required")
    out_path = a.get("out_path") or ""
    if not out_path:
        raise ValueError("out_path is required - the file the image is saved to")
    model = a.get("model") or cfg("NANO_BANANA_IMAGE_MODEL", DEFAULT_IMAGE_MODEL)
    if model in ("pro", "nano-banana-pro"):
        model = PRO_IMAGE_MODEL
    aspect = a.get("aspect_ratio") or "16:9"
    size = a.get("image_size") or "2K"
    if size == "512":
        size = "512px"
    mime_out = "image/png" if a.get("format", "png") == "png" else "image/jpeg"
    refs = [_load_image(p) for p in (a.get("reference_images") or [])]
    if len(refs) > 14:
        raise ValueError("at most 14 reference images")

    route = "interactions"
    try:
        resp = http("POST", API + "/interactions",
                    _interactions_body(model, prompt, refs, aspect, size, mime_out))
    except ApiError as e:
        # Older keys/regions, or a model the Interactions API does not serve yet:
        # fall back to the classic endpoint rather than failing the user.
        if e.status not in (400, 404, 405, 501) or "api key" in str(e).lower():
            raise
        log("interactions refused (%s), falling back to generateContent" % e.status)
        route = "generateContent"
        resp = http("POST", "%s/models/%s:generateContent" % (API, model),
                    _generate_content_body(prompt, refs, aspect, size))

    images = []
    _find_images(resp, images)
    texts = []
    _find_text(resp, texts)
    if not images:
        reason = ""
        for c in resp.get("candidates", []) if isinstance(resp, dict) else []:
            reason = c.get("finishReason", "") or reason
        block = (resp.get("promptFeedback") or {}).get("blockReason", "") if isinstance(resp, dict) else ""
        raise ApiError(0, "The model returned no image. %s%s%s" % (
            ("blocked: %s. " % block) if block else "",
            ("finish reason: %s. " % reason) if reason else "",
            ("Model said: " + " ".join(texts)[:600]) if texts else ""))

    written = []
    paths = _out_paths(out_path, len(images), images[0][0])
    for (mime, data), p in zip(images, paths):
        d = os.path.dirname(p)
        if d:
            os.makedirs(d, exist_ok=True)
        b = base64.b64decode(data)
        with open(p, "wb") as f:
            f.write(b)
        dims = _dims(b)
        written.append({"path": p, "mime": mime, "bytes": len(b),
                        "size": ("%dx%d" % dims) if dims else "unknown"})

    return {
        "saved": written,
        "model": model,
        "route": route,
        "aspect_ratio": aspect,
        "image_size": size,
        "model_text": " ".join(texts)[:1000],
        "watermark": "SynthID (invisible) - this is an AI-generated image",
        "next": "Open each saved file with Read and check it against the brief before using it.",
    }


# ---------------------------------------------------------------- video

def _video_download(op, out_path):
    resp = op.get("response") or {}
    samples = ((resp.get("generateVideoResponse") or {}).get("generatedSamples")
               or resp.get("generatedVideos") or resp.get("videos") or [])
    if not samples:
        filt = (resp.get("generateVideoResponse") or {}).get("raiMediaFilteredReasons")
        raise ApiError(0, "Video finished but no file came back.%s" % (
            (" Filtered: %s" % filt) if filt else ""))
    written = []
    base, ext = os.path.splitext(_abs(out_path))
    ext = ".mp4"
    for i, s in enumerate(samples):
        v = s.get("video") or s
        p = base + ext if len(samples) == 1 else "%s_%d%s" % (base, i + 1, ext)
        os.makedirs(os.path.dirname(p) or ".", exist_ok=True)
        if v.get("uri"):
            b = http("GET", v["uri"], timeout=600, raw=True)
        elif v.get("bytesBase64Encoded") or v.get("data"):
            b = base64.b64decode(v.get("bytesBase64Encoded") or v.get("data"))
        else:
            raise ApiError(0, "Video sample had neither a uri nor bytes")
        with open(p, "wb") as f:
            f.write(b)
        written.append({"path": p, "bytes": len(b)})
    return written


def generate_video(a):
    prompt = (a.get("prompt") or "").strip()
    if not prompt:
        raise ValueError("prompt is required")
    out_path = a.get("out_path") or ""
    if not out_path:
        raise ValueError("out_path is required - the .mp4 the video is saved to")
    model = a.get("model") or cfg("NANO_BANANA_VIDEO_MODEL", DEFAULT_VIDEO_MODEL)
    params = {
        "aspectRatio": a.get("aspect_ratio") or "16:9",
        "durationSeconds": str(a.get("duration_seconds") or "8"),
        "resolution": a.get("resolution") or "720p",
        # EU/UK/CH: allow_adult is the only value Veo accepts in every mode.
        "personGeneration": "allow_adult",
    }
    if a.get("negative_prompt"):
        params["negativePrompt"] = a["negative_prompt"]
    inst = {"prompt": prompt}
    if a.get("start_image"):
        mime, data = _load_image(a["start_image"])
        inst["image"] = {"inlineData": {"mimeType": mime, "data": data}}
    if a.get("last_frame"):
        mime, data = _load_image(a["last_frame"])
        inst["lastFrame"] = {"inlineData": {"mimeType": mime, "data": data}}

    op = http("POST", "%s/models/%s:predictLongRunning" % (API, model),
              {"instances": [inst], "parameters": params})
    name = op.get("name", "")
    wait = int(a.get("wait_seconds") if a.get("wait_seconds") is not None else 360)
    result = _poll_video(name, out_path, wait)
    result.update({"model": model, "parameters": params})
    return result


def _poll_video(name, out_path, wait):
    deadline = time.time() + max(0, wait)
    op = {"name": name}
    while True:
        op = http("GET", "%s/%s" % (API, name))
        if op.get("done"):
            if op.get("error"):
                raise ApiError(0, "Video failed: %s" % op["error"].get("message", op["error"]))
            return {"status": "done", "operation": name, "saved": _video_download(op, out_path),
                    "watermark": "SynthID (invisible) - this is an AI-generated video",
                    "note": "Google keeps the server copy for 2 days only; the local file is the copy.",
                    "next": "Extract a poster frame or use the start image as poster; check the motion teaches."}
        if time.time() >= deadline:
            return {"status": "running", "operation": name,
                    "next": "Call get_video with this operation and the same out_path to collect it."}
        time.sleep(10)


def get_video(a):
    name = a.get("operation") or ""
    if not name:
        raise ValueError("operation is required")
    return _poll_video(name, a.get("out_path") or "video.mp4",
                       int(a.get("wait_seconds") if a.get("wait_seconds") is not None else 300))


# ---------------------------------------------------------------- status

def status(_a=None):
    key, src = api_key()
    info = {"server": VERSION, "key_configured": bool(key),
            "key_source": ("env " + src) if src.isupper() else (src and "file " + src),
            "image_model": cfg("NANO_BANANA_IMAGE_MODEL", DEFAULT_IMAGE_MODEL),
            "video_model": cfg("NANO_BANANA_VIDEO_MODEL", DEFAULT_VIDEO_MODEL)}
    if not key:
        info["fix"] = NO_KEY
        return info
    try:
        models, token = [], ""
        for _ in range(10):
            r = http("GET", API + "/models?pageSize=200" + ("&pageToken=" + token if token else ""),
                     timeout=30)
            models += [m.get("name", "").replace("models/", "") for m in r.get("models", [])]
            token = r.get("nextPageToken", "")
            if not token:
                break
        info["key_works"] = True
        info["image_models_available"] = sorted(m for m in models if "image" in m)
        info["video_models_available"] = sorted(m for m in models if m.startswith("veo"))
    except ApiError as e:
        info["key_works"] = False
        info["error"] = str(e)
    return info


# ---------------------------------------------------------------- MCP

TOOLS = [
    {
        "name": "generate_image",
        "description": (
            "Generate a photorealistic, 3D-rendered or illustrated still image with Google Nano Banana "
            "(Gemini image models) and save it to disk. Use this - never hand-drawn SVG - whenever a "
            "slide, deck, handout or course screen needs a realistic photo-like picture, a 3D render, a "
            "cutaway render, a cinematic scene or a product-shot. Also edits or restyles existing images: "
            "pass them in reference_images and describe the change. Put NO text or labels in the pixels; "
            "add labels afterwards in HTML/SVG/PPTX. After it returns, open the saved file with Read and "
            "check it before use."),
        "inputSchema": {
            "type": "object",
            "properties": {
                "prompt": {"type": "string", "description": "Full scene description: subject, materials, camera position and lens, lighting, background, style (photographic / 3D render / technical illustration), and what must NOT appear."},
                "out_path": {"type": "string", "description": "Where to save, e.g. deck/assets/lng_carrier_render.png. Folders are created. Several results get _1, _2 suffixes."},
                "aspect_ratio": {"type": "string", "enum": IMAGE_ASPECTS, "description": "Default 16:9 (a slide)."},
                "image_size": {"type": "string", "enum": IMAGE_SIZES, "description": "Default 2K. 4K for full-bleed print; 1K for drafts."},
                "model": {"type": "string", "description": "Default gemini-3.1-flash-image (Nano Banana 2). Use gemini-3-pro-image (or 'pro') for complex scenes, fine detail or when Flash failed twice."},
                "reference_images": {"type": "array", "items": {"type": "string"}, "description": "Local image paths to edit, restyle, keep consistent with, or combine (max 14)."},
                "format": {"type": "string", "enum": ["png", "jpeg"], "description": "Default png."},
            },
            "required": ["prompt", "out_path"],
        },
    },
    {
        "name": "generate_video",
        "description": (
            "Generate a short realistic or 3D-animated video clip (4-8 s, mp4, with sound) with Google Veo 3.1 "
            "and save it to disk. Use for a realistic or 3D animation a slide or course screen needs - a "
            "camera move around equipment, a process in motion. Best practice: first make the key frame with "
            "generate_image, check it, then pass it as start_image so the clip starts from an approved picture. "
            "Waits up to wait_seconds (default 360); if still running, returns an operation for get_video."),
        "inputSchema": {
            "type": "object",
            "properties": {
                "prompt": {"type": "string", "description": "What happens over time: subject, action, camera movement, lighting, style, audio. One shot, one action."},
                "out_path": {"type": "string", "description": "Where to save the .mp4."},
                "start_image": {"type": "string", "description": "Optional local image used as the first frame (image-to-video)."},
                "last_frame": {"type": "string", "description": "Optional local image used as the last frame (interpolation)."},
                "aspect_ratio": {"type": "string", "enum": VIDEO_ASPECTS},
                "duration_seconds": {"type": "string", "enum": VIDEO_SECONDS, "description": "Default 8. Must be 8 for 1080p/4k."},
                "resolution": {"type": "string", "enum": VIDEO_RES, "description": "Default 720p."},
                "negative_prompt": {"type": "string"},
                "model": {"type": "string", "description": "Default veo-3.1-fast-generate-preview. veo-3.1-generate-preview for best quality, veo-3.1-lite-generate-preview for cheapest."},
                "wait_seconds": {"type": "integer", "description": "How long to wait before returning. Default 360."},
            },
            "required": ["prompt", "out_path"],
        },
    },
    {
        "name": "get_video",
        "description": "Collect a video that generate_video left running: polls the operation and downloads the mp4.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "operation": {"type": "string"},
                "out_path": {"type": "string"},
                "wait_seconds": {"type": "integer"},
            },
            "required": ["operation", "out_path"],
        },
    },
    {
        "name": "nano_banana_status",
        "description": "Check that the Gemini API key is configured and works, and list the image and video models this key can use. Run it first if a generation fails.",
        "inputSchema": {"type": "object", "properties": {}},
    },
]

HANDLERS = {"generate_image": generate_image, "generate_video": generate_video,
            "get_video": get_video, "nano_banana_status": status}


def send(msg):
    OUT.write(json.dumps(msg, ensure_ascii=False) + "\n")
    OUT.flush()


def handle(req):
    method = req.get("method", "")
    rid = req.get("id")
    if method == "initialize":
        pv = (req.get("params") or {}).get("protocolVersion") or "2025-06-18"
        return {"protocolVersion": pv, "capabilities": {"tools": {}},
                "serverInfo": {"name": "nano-banana", "version": VERSION}}
    if method == "ping":
        return {}
    if method == "tools/list":
        return {"tools": TOOLS}
    if method == "tools/call":
        p = req.get("params") or {}
        fn = HANDLERS.get(p.get("name"))
        if not fn:
            return {"content": [{"type": "text", "text": "unknown tool %s" % p.get("name")}],
                    "isError": True}
        try:
            result = fn(p.get("arguments") or {})
            return {"content": [{"type": "text", "text": json.dumps(result, indent=2, ensure_ascii=False)}]}
        except (ApiError, ValueError, OSError) as e:
            return {"content": [{"type": "text", "text": "ERROR: %s" % _redact(str(e))}], "isError": True}
    if rid is None:
        return None                     # a notification - no reply
    raise KeyError(method)


def serve():
    log("server %s ready" % VERSION)
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            req = json.loads(line)
        except ValueError:
            send({"jsonrpc": "2.0", "id": None, "error": {"code": -32700, "message": "parse error"}})
            continue
        rid = req.get("id")
        try:
            res = handle(req)
            if rid is not None and res is not None:
                send({"jsonrpc": "2.0", "id": rid, "result": res})
        except KeyError as e:
            if rid is not None:
                send({"jsonrpc": "2.0", "id": rid,
                      "error": {"code": -32601, "message": "method not found: %s" % e}})
        except Exception as e:          # never let one bad call kill the server
            log("internal error:", _redact(repr(e)))
            if rid is not None:
                send({"jsonrpc": "2.0", "id": rid,
                      "error": {"code": -32603, "message": _redact(str(e))}})


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        OUT.write(json.dumps(status(), indent=2) + "\n")
    else:
        serve()
