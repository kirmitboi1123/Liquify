"""usage: python patch_theme.py MAP_JSON SRC_DIR OUT_DIR [SPICETIFY_CSS_MAP] -- rewrites old Spotify class hashes to new ones.

With SPICETIFY_CSS_MAP (normally %LOCALAPPDATA%\\spicetify\\css-map.json), any raw hash that
Spicetify's css-map renames is also rewritten to its readable name: Spicetify renames those
classes inside Spotify, so a raw-hash selector would match nothing (2.46.3 renamed 30)."""
import json, re, sys, shutil, pathlib

m = {k: v["new"] for k, v in json.load(open(sys.argv[1])).items() if v["new"] and v["new"] != k}
src, out = pathlib.Path(sys.argv[2]), pathlib.Path(sys.argv[3])
out.mkdir(parents=True, exist_ok=True)
pat = re.compile(r"(?<![\w-])(" + "|".join(map(re.escape, sorted(m, key=len, reverse=True))) + r")(?![\w-])")
cssmap = json.load(open(sys.argv[4], encoding="utf8")) if len(sys.argv) > 4 else {}
renpat = re.compile(r"(?<![\w-])(" + "|".join(map(re.escape, sorted(cssmap, key=len, reverse=True))) + r")(?![\w-])") if cssmap else None
for name in ("user.css", "theme.js", "color.ini"):
    text = (src / name).read_text("utf8")
    n = len(pat.findall(text))
    text = pat.sub(lambda x: m[x.group(1)], text)
    compat = pathlib.Path(__file__).with_name("compat-1.3.5.css")
    if name == "user.css" and compat.exists():
        text += compat.read_text("utf8")
    r = 0
    if renpat and name != "color.ini":
        r = len(renpat.findall(text))
        text = renpat.sub(lambda x: cssmap[x.group(1)], text)
    (out / name).write_text(text, "utf8", newline="")
    print(f"{name}: {n} replacements, {r} renamed to Spicetify css-map names")
shutil.copy(src / "LICENSE.txt", out / "LICENSE.txt")
