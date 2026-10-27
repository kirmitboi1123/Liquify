"""usage: python3 merge_cssmap.py ADDITIONS_JSON CSS_MAP_JSON
Adds the entries from ADDITIONS_JSON that CSS_MAP_JSON lacks (Spicetify's entry wins on a
conflict) and writes the result as UTF-8 without a BOM. Before the first change to a given
css-map it saves the original next to it as css-map.<sha256 prefix>.json.bak.
Prints how many entries were added; exit code 0 = unchanged, 10 = changed, 1 = error."""
import hashlib, json, pathlib, sys

additions, target = pathlib.Path(sys.argv[1]), pathlib.Path(sys.argv[2])
raw = target.read_bytes()
cssmap = json.loads(raw.decode("utf-8-sig"))
extra = json.loads(additions.read_text("utf-8-sig"))
missing = {k: v for k, v in extra.items() if k not in cssmap}
if not missing:
    print(f"css-map: 0 added ({len(cssmap)} entries)")
    sys.exit(0)

backup = target.with_name(f"css-map.{hashlib.sha256(raw).hexdigest()[:12]}.json.bak")
if not backup.exists():
    backup.write_bytes(raw)
cssmap.update(missing)
target.write_bytes((json.dumps(cssmap, indent=2, ensure_ascii=False) + "\n").encode("utf-8"))
print(f"css-map: {len(missing)} added ({len(cssmap)} entries), original saved as {backup.name}")
sys.exit(10)
