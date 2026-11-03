"""The nineteen engine task prototypes (engines/demo/tasks) in the brandbook's colours, as a Navy theme and a white theme -
a layer over the originals, which stay as they are. Reads every colour with the property it paints and maps it; signal
colours (good, bad, warning, the simulator's pipe colours) keep their meaning. In the white theme the picture boxes - the
simulator screens (gb_hmi), the 3D stages, an instrument's own display - stay Navy, as on the slides.
Usage: themes.py <out dir>   -> <out>/dark/... and <out>/light/... (open <theme>/design/task-templates/engines/demo/tasks/*.html)"""
import colorsys, io, os, re, shutil, sys

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, "engines")
REPO = os.path.dirname(os.path.dirname(HERE))
NAVY = (10, 36, 99)
HEX = re.compile(r"#([0-9a-fA-F]{3}|[0-9a-fA-F]{6})\b")
RGBA = re.compile(r"rgba?\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*(?:,\s*([\d.]+)\s*)?\)")

def to_rgb(h):
    h = h if len(h) == 6 else "".join(c * 2 for c in h)
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))

def hexs(c):
    return "#%02X%02X%02X" % tuple(max(0, min(255, round(v))) for v in c)

def hls(c):
    return colorsys.rgb_to_hls(*(v / 255 for v in c))

def from_hls(h, l, s):
    return tuple(v * 255 for v in colorsys.hls_to_rgb(h, l, s))

NAVY_H = hls(NAVY)[0]

def is_signal(c):
    """greens, reds, ambers, purples and teal pipes: meanings, kept"""
    h, l, s = hls(c)
    deg = h * 360
    return s > .35 and l > .18 and not (185 <= deg <= 235)

def cyan_to_brand(c):
    """the prototypes' cyan-teal accent family becomes the brand's Novikontas Blue family"""
    h, l, s = hls(c)
    deg = h * 360
    if s > .45 and 165 <= deg <= 215 and .3 < l < .9:
        bh, bl, bs = hls((83, 167, 219))
        return from_hls(bh, max(.28, min(.86, bl + (l - .58))), bs)
    return c

def dark_theme(c, prop):
    """Navy instead of near-black, brand blue instead of cyan"""
    c = cyan_to_brand(c)
    h, l, s = hls(c)
    if l < .32 and not is_signal(c):          # a dark ground or panel: the navy family, never near-black
        return from_hls(NAVY_H, max(.1, min(.32, .13 + (l - .06) * 1.1)), .82)
    return c

def light_theme(c, prop, a=None):
    c = cyan_to_brand(c)
    h, l, s = hls(c)
    text = prop in ("color", "fill") or prop.endswith("-color") and prop not in ("background-color", "border-color")
    if is_signal(c):
        if text and l > .5:                   # a signal colour as text on white: deeper, same hue
            return from_hls(h, .36, min(1, s))
        return c
    if l < .38:                               # a dark ground or panel: white and the brand's light greys
        return (255, 255, 255) if l < .1 else from_hls(NAVY_H, min(.985, .96 + (.2 - l) * .1), .45)
    if l > .62:                               # light text: Navy, the dimmer the more steel
        if text:
            return NAVY if l > .86 else (65, 92, 143) if l > .7 else (106, 127, 160)
        return from_hls(NAVY_H, .9, .35)      # a light line or border
    return from_hls(h, l * .8, s)             # a mid tone: a little deeper on white

def rgba_light(r, g, b, a, prop):
    c = (r, g, b); h, l, s = hls(c)
    if prop.startswith("box-shadow") or prop in ("filter", "text-shadow"):
        return "rgba(10,36,99,%.2f)" % min(.3, a * .45)
    if l > .9:                                # a white wash on dark: a navy wash on white
        return "rgba(10,36,99,%.3f)" % min(.5, a * .9)
    if l < .2 and not is_signal(c):           # a dark glass: white glass
        return "rgba(255,255,255,%.2f)" % max(.82, a)
    nc = light_theme(c, prop)
    return "rgba(%d,%d,%d,%s)" % (round(nc[0]), round(nc[1]), round(nc[2]), ("%g" % a))

def rgba_dark(r, g, b, a, prop):
    nc = dark_theme((r, g, b), prop)
    return "rgba(%d,%d,%d,%s)" % (round(nc[0]), round(nc[1]), round(nc[2]), ("%g" % a))

DECL = re.compile(r"([a-zA-Z0-9-]+)(\s*:\s*)([^;{}]+)")

def convert_css(css, theme):
    def fix_decl(m):
        prop, sep, val = m.group(1).lower(), m.group(2), m.group(3)
        if prop.startswith("--"):
            prop = "color" if re.search(r"text|ink|dim|faint", prop) else "background"
        def hx(mm):
            c = to_rgb(mm.group(1))
            return hexs(dark_theme(c, prop) if theme == "dark" else light_theme(c, prop))
        def rg(mm):
            r, g, b = int(mm.group(1)), int(mm.group(2)), int(mm.group(3)); a = float(mm.group(4)) if mm.group(4) else 1.0
            return rgba_dark(r, g, b, a, prop) if theme == "dark" else rgba_light(r, g, b, a, prop)
        return m.group(1) + sep + RGBA.sub(rg, HEX.sub(hx, val))
    return re.sub(r"\{([^{}]*)\}", lambda b: "{" + DECL.sub(fix_decl, b.group(1)) + "}", css)

# the big button: one solid brand colour, never a gradient
GO = {"dark": ".tl-eye{color:#53A7DB!important}.tl-go{background:#53A7DB!important;color:#0A2463!important;box-shadow:0 14px 30px -14px rgba(83,167,219,.6)!important}"
              ".tl-go::after{display:none}",
      "light": ".tl-eye{color:#415C8F!important}.tl-go{background:#0A2463!important;color:#fff!important;box-shadow:0 14px 30px -14px rgba(10,36,99,.55)!important}"
               ".tl-go::after{display:none}"}
# white theme: the picture boxes stay Navy - the simulator screen, the 3D stage and whatever is drawn on them
KEEP_DARK = (".hm,.tl-stage,.tl-stage *,canvas{color-scheme:dark}"
             ".tl-stage{background:linear-gradient(160deg,#0C2B78,#071A48)!important}"
             ".tl-stage::after{background:radial-gradient(ellipse at center,rgba(0,0,0,0) 55%,rgba(6,23,61,.45) 100%)!important}")
PAT = {"dark": "html body{background:radial-gradient(ellipse 80% 70% at 78% -5%,#16408f 0%,rgba(22,64,143,0) 100%),#0A2463!important}",
       "light": "html body{background:#F7F8FA!important;color:#0A2463}"
                ":root{--tl-line:rgba(10,36,99,.18)}.dw-step:disabled{opacity:.7}"}

# what stays Navy in the white theme: the picture boxes, the simulator screen, an instrument's own display
SCREENS = (".tl-stage", ".hm", ".sv-lcd")


def light_page(css):
    """a page's own rules in the white theme: light for the page, and again in Navy for whatever sits in a picture box
    (.tl-stage, the simulator screen .hm) - those keep the screen's dark look"""
    light = convert_css(css, "light")
    dark = convert_css(css, "dark")
    scoped = []
    for m in re.finditer(r"([^{}]+)\{([^{}]*)\}", re.sub(r"/\*.*?\*/", "", dark, flags=re.S)):
        sel, body = m.group(1).strip(), m.group(2)
        if not (HEX.search(body) or RGBA.search(body)) or sel.startswith("@") or sel.startswith("from") or sel.startswith("to") or "%" in sel[:5]:
            continue
        # only the colours: a layout line copied here would outrank the page's own, more particular layout rules
        body = ";".join(d for d in body.split(";") if HEX.search(d) or RGBA.search(d))
        parts = [x.strip() for x in sel.split(",") if x.strip()]
        if any(x.startswith((":root", "html", "body")) for x in parts):
            continue
        scoped.append(",".join(sum(([k + " " + x] + ([x] if x.startswith(k) and k != ".tl-stage" else []) for k in SCREENS for x in parts), []))
                      + "{" + body + "}")
    return light + "\n" + "\n".join(scoped)


# 3D where a task had no real picture; the photo tasks and the simulator screens stay as they are. Static 3D renders in
# engines/demo/img3d
INJECT = {
    "17_radio_call.html": ('<div class="rc">', '<div class="rc"><img class="x3d-radio" src="../img3d/s3d_radio.jpg" alt="The ship-shore VHF, channel 14">',
        ".rc{padding-left:31%!important}.x3d-radio{position:absolute;left:0;top:0;width:29%;height:100%;object-fit:cover;"
        "border-radius:16px;box-shadow:0 18px 34px -16px rgba(0,0,0,.6)}"),
    "03_predict_curve.html": ('<div class="tl-card pc-case">', '<div class="tl-card x3d-card"><img src="../img3d/s3d_tankcard.jpg" alt="The cargo tank in 3D"></div><div class="tl-card pc-case">',
        ".x3d-card{flex:none!important;min-height:170px;padding:0!important;overflow:hidden;background:radial-gradient(ellipse at 50% 45%,#16408f,#0A2463 75%)!important}.x3d-card img{display:block;width:100%;height:170px;object-fit:contain}"),
    "10_build_procedure.html": ('<div class="bp-cases" id="cases"></div>', '<div class="bp-cases" id="cases"></div>',
        ".bp-cases{height:44%!important}#cases>*::before{content:'';display:block;flex:none;height:64px;margin:-4px -6px 4px;border-radius:10px;background:url(../img3d/s3d_tankcard.jpg) center 45%/cover}"
        "#cases>*:nth-child(2)::before{background-image:url(../img3d/s3d_voidspace.jpg)}"),
}


def dark_tokens():
    """the engine's own colour tokens as the Navy theme has them - set again inside every picture box of the white theme,
    so a word drawn with var(--tl-text) on a Navy screen stays light"""
    css = io.open(os.path.join(SRC, "gb_lab.css"), encoding="utf-8").read()
    m = re.search(r":root\s*\{([^}]*)\}", convert_css(css, "dark"))
    return ",".join(SCREENS) + "{" + (m.group(1) if m else "") + ";color:var(--tl-text)}"


def write(out):
    for theme in ("dark", "light"):
        top = os.path.join(out, theme)
        if os.path.isdir(top):
            shutil.rmtree(top)
        root = os.path.join(top, "design", "task-templates", "engines")
        img = os.path.join("demo", "img")
        for dp, dn, fn in os.walk(SRC):
            rel = os.path.relpath(dp, SRC)
            if rel == img or rel.startswith(img + os.sep) or "__pycache__" in rel:
                continue
            os.makedirs(os.path.join(root, rel), exist_ok=True)
            for f in fn:
                sp, dp2 = os.path.join(dp, f), os.path.join(root, rel, f)
                if f.endswith(".css") and not (theme == "light" and f in ("gb_hmi.css", "gb_3d.css")):
                    src_css = io.open(sp, encoding="utf-8").read()
                    out_css = light_page(src_css) if theme == "light" and f == "gb_lab.css" else convert_css(src_css, theme)
                    # a bold word inside a start-screen step is a word, not the step's number bubble
                    io.open(dp2, "w", encoding="utf-8").write(out_css.replace(".tl-how li b", ".tl-how li > b"))
                elif f.endswith(".html"):
                    s = io.open(sp, encoding="utf-8").read()
                    s = re.sub(r"<style>(.*?)</style>", lambda m: "<style>" + (convert_css(m.group(1), theme) if theme == "dark" else light_page(m.group(1))) + "</style>", s, flags=re.S)
                    extra = "<style>" + PAT[theme] + GO[theme] + (KEEP_DARK + dark_tokens() if theme == "light" else "") + "</style>"
                    if f in INJECT:
                        old, new, css = INJECT[f]
                        assert old in s, f
                        s = s.replace(old, new, 1)
                        extra += "<style>" + css + "</style>"
                    io.open(dp2, "w", encoding="utf-8").write(s.replace("</head>", extra + "</head>", 1))
                else:
                    shutil.copy(sp, dp2)
        shutil.copytree(os.path.join(SRC, img), os.path.join(root, img))       # the photographs, as they are
        tok = os.path.join(REPO, "plugin", "skills", "course-module-ui", "templates")      # the tokens file the pages read
        td = os.path.join(top, "plugin", "skills", "course-module-ui", "templates")
        os.makedirs(td, exist_ok=True)
        for f in os.listdir(tok):
            if f.endswith(".css"):
                shutil.copy(os.path.join(tok, f), td)
        print(theme, "written")


if __name__ == "__main__":
    write(sys.argv[1])
