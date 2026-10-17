"""Recover hash equivalences from Liquify's own git history.

Every "fixes for new Spotify version" commit swaps old Spotify class hashes for new
ones on otherwise identical lines. Pair them up across all of history (union-find),
then chain through classmap JSON from mapclasses.py to resolve hashes it could not see.

usage: python history_equiv.py REPO CLASSMAP_JSON NEW_CSS_CLASSES_TXT OUT_JSON
"""
import difflib, json, re, subprocess, sys

HASH = r"[A-Za-z0-9_]{16}(?:[A-Za-z0-9_]{4})?"
TOK = re.compile(r"(?<![\w-])(" + HASH + r")(?![\w-])")
CLS = re.compile(r"\.([A-Za-z_][\w-]{3,})")


def is_hash(t):
    return re.search(r"[A-Z]", t) and re.search(r"[a-z]", t) and re.search(r"\d", t)


def git(repo, *a):
    return subprocess.run(["git", "-C", repo, *a], capture_output=True, text=True, encoding="utf8", errors="ignore").stdout


parent = {}


def find(x):
    parent.setdefault(x, x)
    while parent[x] != x:
        parent[x] = parent[parent[x]]
        x = parent[x]
    return x


def union(a, b):
    parent[find(a)] = find(b)


def masked(line):
    return CLS.sub(".#", TOK.sub(lambda m: "#" if is_hash(m.group(1)) else m.group(1), line))


def pair_versions(a, b):
    al, bl = a.splitlines(), b.splitlines()
    sm = difflib.SequenceMatcher(None, al, bl, autojunk=False)
    for op, i1, i2, j1, j2 in sm.get_opcodes():
        if op != "replace":
            continue
        bm = {}
        for j in range(j1, j2):
            bm.setdefault(masked(bl[j]), []).append(bl[j])
        for i in range(i1, i2):
            cands = bm.get(masked(al[i]))
            if not cands or len(cands) != 1:
                continue
            ta = CLS.findall(al[i]) or [t for t in TOK.findall(al[i]) if is_hash(t)]
            tb = CLS.findall(cands[0]) or [t for t in TOK.findall(cands[0]) if is_hash(t)]
            if len(ta) == len(tb):
                for x, y in zip(ta, tb):
                    if x != y:
                        union(x, y)


def main():
    repo, cmap_path, newcls_path, out = sys.argv[1:5]
    for f in ("user.css", "theme.js"):
        revs = git(repo, "log", "--reverse", "--format=%H", "--", f).split()
        prev = None
        for r in revs:
            cur = git(repo, "show", f"{r}:{f}")
            if not cur:
                continue
            if prev:
                pair_versions(prev, cur)
            prev = cur
    cmap = {k: v["new"] for k, v in json.load(open(cmap_path)).items() if v["new"]}
    newcls = {l.strip().lstrip(".") for l in open(newcls_path)}
    groups = {}
    for x in list(parent):
        groups.setdefault(find(x), set()).add(x)
    # every hash already mapped resolves its whole group
    res = {}
    for g in groups.values():
        targets = {cmap[x] for x in g if x in cmap}
        targets |= {x for x in g if x in newcls}
        if len(targets) == 1:
            t = targets.pop()
            for x in g:
                if x not in cmap:
                    res[x] = t
    json.dump({"resolved": res, "groups": [sorted(g) for g in groups.values() if len(g) > 1]}, open(out, "w"), indent=1)
    print(f"groups {len(groups)}  extra resolved {len(res)}")


main()
