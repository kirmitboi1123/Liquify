"""Map Spotify's hashed CSS class names from an old xpui build to a new one.

usage: python mapclasses.py OLD_DIR NEW_DIR WANTED_LIST OUT_JSON
Pass 1: CSS rules whose (at-rule context, selector with hashes masked, body) match.
Pass 2: re-match remaining rules by selector with already-mapped names substituted.
Pass 3: JS context (masked surrounding text) for classes only referenced from JS.
"""
import json, re, sys, collections, pathlib

HASH = r"[A-Za-z0-9_]{16}(?:[A-Za-z0-9_]{4})?"
HASH_RE = re.compile(r"(?<![\w-])(" + HASH + r")(?![\w-])")
# READABLE=<file>: Spicetify's readable names (css-map values) are also treated as
# mappable tokens, so a Spicetify-patched old build can be mapped onto a clean new one.
import os
READABLE = set(open(os.environ["READABLE"]).read().split()) if os.environ.get("READABLE") else set()
CLS_RE = re.compile(r"\.([A-Za-z_][\w-]*)(?![\w-])")
if READABLE:
    HASH_RE = re.compile(r"(?<![\w-])(" + HASH + "|" + "|".join(map(re.escape, sorted(READABLE, key=len, reverse=True))) + r")(?![\w-])")


def is_hash(tok):
    if tok in READABLE:
        return True
    return re.fullmatch(HASH, tok) and re.search(r"[A-Z]", tok) and re.search(r"[a-z]", tok) and not tok.startswith("main")


def read(d, ext):
    return "\n".join(p.read_text("utf8", "ignore") for p in sorted(pathlib.Path(d).glob("*." + ext)))


def rules(css):
    css = re.sub(r"/\*.*?\*/", "", css, flags=re.S)
    out, stack, buf = [], [], ""
    i = 0
    while i < len(css):
        c = css[i]
        if c == "{":
            head = buf.strip()
            buf = ""
            if head.startswith("@"):
                stack.append(head)
            else:
                j = css.index("}", i)
                out.append(("|".join(stack), head, css[i + 1:j].strip()))
                i = j
        elif c == "}":
            if stack:
                stack.pop()
            buf = ""
        else:
            buf += c
        i += 1
    return out


def classes_in(sel):
    return [m for m in CLS_RE.findall(sel) if is_hash(m)]


def mask(sel, known=None):
    def r(m):
        t = m.group(1)
        if not is_hash(t):
            return "." + t
        if known and t in known:
            return "." + known[t]
        return ".#"
    return CLS_RE.sub(r, sel)


def vote(old_rules, new_rules, keyf, votes, known_old=None):
    idx = collections.defaultdict(list)
    for r in new_rules:
        idx[keyf(r, None)].append(r)
    for r in old_rules:
        k = keyf(r, known_old)
        cands = idx.get(k)
        if not cands or len(cands) > 3:
            continue
        oc = classes_in(r[1])
        for nr in cands:
            nc = classes_in(nr[1])
            if len(oc) != len(nc):
                continue
            for a, b in zip(oc, nc):
                votes[a][b] += 1.0 / len(cands)


def settle(votes, mapping):
    used = set(mapping.values())
    for a, c in sorted(votes.items(), key=lambda kv: -max(kv[1].values())):
        if a in mapping:
            continue
        b, n = c.most_common(1)[0]
        total = sum(c.values())
        if n / total >= 0.6 and b not in used:
            mapping[a] = b
            used.add(b)


def main():
    old_dir, new_dir, wanted_path, out = sys.argv[1:5]
    wanted = {l.strip().lstrip(".") for l in open(wanted_path) if l.strip()}
    old_css, new_css = read(old_dir, "css"), read(new_dir, "css")
    ro, rn = rules(old_css), rules(new_css)
    mapping, how = {}, {}

    votes = collections.defaultdict(collections.Counter)
    vote(ro, rn, lambda r, k: (r[0], mask(r[1]), r[2]), votes)
    settle(votes, mapping)
    for a in mapping:
        how[a] = "css-exact"

    # pass 2: selector structure only, with known names filled in; body ignored
    for rnd in range(3):
        votes = collections.defaultdict(collections.Counter)
        inv = {v: v for v in mapping.values()}
        vote(ro, rn, lambda r, k: (r[0], mask(r[1], mapping if k is not None else inv)), votes, known_old=True)
        before = set(mapping)
        settle(votes, mapping)
        for a in set(mapping) - before:
            how[a] = "css-structure"

    # pass 2b: fuzzy - same selector shape, most similar declaration set
    def decls(body):
        return set(d.strip() for d in body.split(";") if d.strip())
    new_by_shape = collections.defaultdict(list)
    inv = {v: v for v in mapping.values()}
    for r in rn:
        new_by_shape[(r[0], mask(r[1], inv))].append(r)
    for rnd in range(3):
        votes = collections.defaultdict(collections.Counter)
        inv = {v: v for v in mapping.values()}
        new_by_shape = collections.defaultdict(list)
        for r in rn:
            new_by_shape[(r[0], mask(r[1], inv))].append(r)
        for r in ro:
            oc = [c for c in classes_in(r[1]) if c not in mapping]
            if not oc or not any(c in wanted for c in oc):
                continue
            cands = new_by_shape.get((r[0], mask(r[1], mapping)), [])
            od = decls(r[2])
            scored = []
            for nr in cands:
                nd = decls(nr[2])
                j = len(od & nd) / max(1, len(od | nd))
                scored.append((j, nr))
            scored.sort(key=lambda x: -x[0])
            if not scored or scored[0][0] < 0.34 or (len(scored) > 1 and scored[1][0] >= scored[0][0] - 0.05):
                continue
            nr = scored[0][1]
            full_o, full_n = classes_in(r[1]), classes_in(nr[1])
            if len(full_o) == len(full_n):
                for a, b in zip(full_o, full_n):
                    if a not in mapping:
                        votes[a][b] += scored[0][0]
        before = set(mapping)
        settle(votes, mapping)
        for a in set(mapping) - before:
            how[a] = "css-fuzzy"

    # pass 3: JS context for wanted classes still unmapped
    old_js, new_js = read(old_dir, "js"), read(new_dir, "js")
    new_js_masked = HASH_RE.sub("#", new_js)
    for a, (m, w) in ((a, mw) for a in sorted(wanted - set(mapping)) for mw in
                      ((m, w) for w in (60, 35, 22) for m in re.finditer(r"(?<![\w-])" + a + r"(?![\w-])", old_js))):
        if a in mapping:
            continue
        if True:
            s, e = m.start(), m.end()
            left = HASH_RE.sub("#", old_js[max(0, s - w):s])
            right = HASH_RE.sub("#", old_js[e:e + w])
            pat = re.escape(left) + r"#" + re.escape(right)
            hits = [h.start() + len(left) for h in re.finditer(pat, new_js_masked)]
            if len(hits) != 1:
                continue
            # recover the real token at that position in unmasked new_js
            masked_prefix = new_js_masked[:hits[0]]
            # walk unmasked text to align positions
            pos = align(new_js, masked_prefix)
            tok = re.match(HASH, new_js[pos:])
            if tok and tok.group(0) not in mapping.values():
                mapping[a] = tok.group(0)
                how[a] = "js-context"
                continue

    res = {a: {"new": mapping.get(a), "how": how.get(a)} for a in sorted(wanted)}
    json.dump(res, open(out, "w"), indent=1)
    got = sum(1 for v in res.values() if v["new"])
    print(f"wanted {len(wanted)}  mapped {got}  ({collections.Counter(v['how'] for v in res.values())})")


def align(text, masked_prefix):
    # masked text replaced each hash with '#'; rebuild offset in original
    pos = mpos = 0
    for m in HASH_RE.finditer(text):
        seg = m.start() - pos
        if mpos + seg >= len(masked_prefix):
            return pos + (len(masked_prefix) - mpos)
        mpos += seg + 1
        pos = m.end()
        if mpos >= len(masked_prefix):
            return pos
    return pos + (len(masked_prefix) - mpos)


main()
