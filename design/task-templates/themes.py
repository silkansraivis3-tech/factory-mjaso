"""The nineteen engine task prototypes (engines/demo/tasks) in the brandbook's colours, as a Navy theme and a white theme -
a layer over the originals, which stay as they are. Reads every colour with the property it paints and maps it; signal
colours (good, bad, warning, the simulator's pipe colours) keep their meaning. In the white theme the picture boxes - the
simulator screens (gb_hmi), the 3D stages, an instrument's own display - stay Navy, as on the slides.
Usage: themes.py <out dir>   -> <out>/dark/... and <out>/light/... (open <theme>/design/task-templates/engines/demo/tasks/*.html)"""
import io, os, re, shutil, sys

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, "engines")
REPO = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.join(REPO, "plugin", "skills", "course-task-ux", "scripts"))
from engine_theme import convert_css, light_page, PAT, GO, KEEP_DARK, SCREENS, dark_tokens as _dark_tokens  # noqa: E402  - the one colour code
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
    return _dark_tokens(io.open(os.path.join(SRC, "gb_lab.css"), encoding="utf-8").read())


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
