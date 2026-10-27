"""usage: make_mac_port.py WIN2MAC LIQUIFY_REPO SPICETIFY_CSS_MAP OUT_DIR
Writes OUT_DIR/css-map-additions.json: the Windows css-map additions with keys translated to
Mac hashes, plus Mac twins of Spicetify's own Windows-only entries that have no Mac entry
(same readable name), and OUT_DIR/mac-map.json in patch_theme.py's MAP_JSON format."""
import json, sys, pathlib

w2m = json.load(open(sys.argv[1]))
repo, out = pathlib.Path(sys.argv[2]), pathlib.Path(sys.argv[4])
cm = json.load(open(sys.argv[3], encoding="utf8"))
add = json.load(open(repo / "tools/css-map-additions-1.3.5.3058.json", encoding="utf8"))
out.mkdir(parents=True, exist_ok=True)

result, stats = {}, {"additions": 0, "additions_untranslated": [], "twins": 0}
for k, v in add.items():
    mk = w2m.get(k)
    if not mk:
        stats["additions_untranslated"].append(k)
        continue
    result[mk] = v
    stats["additions"] += 1
for k, v in cm.items():
    mk = w2m.get(k)
    if mk and mk != k and mk not in cm and mk not in result:
        result[mk] = v
        stats["twins"] += 1

(out / "css-map-additions.json").write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", "utf8")
(out / "mac-map.json").write_text(json.dumps({k: {"new": v} for k, v in w2m.items()}, indent=0, sort_keys=True), "utf8")
print(json.dumps(stats), "total entries:", len(result))
