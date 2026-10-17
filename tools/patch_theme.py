"""usage: python patch_theme.py MAP_JSON SRC_DIR OUT_DIR -- rewrites old Spotify class hashes to new ones."""
import json, re, sys, shutil, pathlib

m = {k: v["new"] for k, v in json.load(open(sys.argv[1])).items() if v["new"] and v["new"] != k}
src, out = pathlib.Path(sys.argv[2]), pathlib.Path(sys.argv[3])
out.mkdir(parents=True, exist_ok=True)
pat = re.compile(r"(?<![\w-])(" + "|".join(map(re.escape, sorted(m, key=len, reverse=True))) + r")(?![\w-])")
for name in ("user.css", "theme.js", "color.ini"):
    text = (src / name).read_text("utf8")
    n = len(pat.findall(text))
    text = pat.sub(lambda x: m[x.group(1)], text)
    compat = pathlib.Path(__file__).with_name("compat-1.3.5.css")
    if name == "user.css" and compat.exists():
        text += compat.read_text("utf8")
    (out / name).write_text(text, "utf8", newline="")
    print(f"{name}: {n} replacements")
shutil.copy(src / "LICENSE.txt", out / "LICENSE.txt")
