"""usage: winmac_map.py WIN_DIR MAC_DIR OUT_JSON
Builds a Windows-hash -> Mac-hash class map for two extractions of the same Spotify version.
Each CSS file is turned into a token stream with every class name replaced by a placeholder;
files whose streams are identical are aligned class by class. Files are paired by name, and
leftover files by identical structure (chunk ids differ between builds)."""
import json, re, sys, pathlib
from collections import Counter, defaultdict

win, mac, out = map(pathlib.Path, sys.argv[1:4])
CLS = re.compile(r"\.(-?[_a-zA-Z][\w-]*)")


def strip(text):
    # Drop comments and sourcemap lines so only rules are compared.
    return re.sub(r"/\*.*?\*/", "", text, flags=re.S)


def tokens(text):
    text = strip(text)
    names = CLS.findall(text)
    skeleton = CLS.sub(".§", text)
    return skeleton, names


def load(d):
    return {p.name: tokens(p.read_text("utf8", "ignore")) for p in d.rglob("*.css")}


W, M = load(win), load(mac)
votes = defaultdict(Counter)
pairs, unpaired = [], []

def align(wn, mn):
    (ws, wl), (ms, ml) = W[wn], M[mn]
    if ws != ms or len(wl) != len(ml):
        return False
    for a, b in zip(wl, ml):
        votes[a][b] += 1
    pairs.append((wn, mn))
    return True

left_w = set(W)
left_m = set(M)
for name in sorted(set(W) & set(M)):
    if align(name, name):
        left_w.discard(name); left_m.discard(name)
by_skel = defaultdict(list)
for mn in left_m:
    by_skel[M[mn][0]].append(mn)
for wn in sorted(left_w):
    cands = by_skel.get(W[wn][0], [])
    if len(cands) == 1 and align(wn, cands[0]):
        left_m.discard(cands[0])
    else:
        unpaired.append(wn)

# Files whose structure differs (a byte or two): align rule by rule.
for wn in list(unpaired) + [n for n in sorted(set(W) & set(M)) if (n, n) not in pairs]:
    mn = wn if wn in M else None
    if not mn:
        continue
    wr = re.split(r"(?<=\})", strip((win / wn).read_text("utf8", "ignore")) if (win / wn).exists() else "")
    mr = re.split(r"(?<=\})", strip((mac / mn).read_text("utf8", "ignore")))
    import difflib
    wsk = [CLS.sub(".§", r) for r in wr]
    msk = [CLS.sub(".§", r) for r in mr]
    for tag, i1, i2, j1, j2 in difflib.SequenceMatcher(None, wsk, msk, autojunk=False).get_opcodes():
        if tag != "equal":
            continue
        for i, j in zip(range(i1, i2), range(j1, j2)):
            for a, b in zip(CLS.findall(wr[i]), CLS.findall(mr[j])):
                votes[a][b] += 1

mapping, conflicts = {}, {}
for a, c in votes.items():
    (b, n), *rest = c.most_common()
    if rest:
        conflicts[a] = dict(c)
    mapping[a] = b
rev = defaultdict(set)
for a, b in mapping.items():
    rev[b].add(a)
many_to_one = {b: sorted(s) for b, s in rev.items() if len(s) > 1}
json.dump(mapping, open(out, "w"), indent=0, sort_keys=True)
print(f"css files win={len(W)} mac={len(M)}; aligned exactly={len(pairs)}; unpaired win={unpaired}")
print(f"classes mapped={len(mapping)}; changed name={sum(a != b for a, b in mapping.items())}; "
      f"conflicting votes={len(conflicts)}; many-to-one={len(many_to_one)}")
for a, c in list(conflicts.items())[:5]:
    print("  conflict", a, c)
for b, s in list(many_to_one.items())[:5]:
    print("  many->one", b, s)
