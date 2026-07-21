#!/usr/bin/env python3
"""
Finalize the unconstrained N-key layout for rytphings (default N=16).

    python merge-keys/finalize.py --keys 18

Seeds from the greedy unconstrained partition at N keys, polishes it with local
search (move / swap letters between keys to cut algebra-aware, frequency-weighted
collision) plus random multi-starts, then emits everything needed to deploy:
  * the letter->key partition and per-key representative (emitted letter)
  * the destructive xform fold lines for speller/algebra
  * a QWERTY-grid placement (each key near its representative's home)
  * verification numbers (list-clean %, top-slot %) and top collision pairs
"""
import argparse, collections, importlib.util, json, random, sys

sys.stdout.reconfigure(encoding='utf-8')
spec = importlib.util.spec_from_file_location("alg", "merge-keys/analyze_layout_algebra.py")
alg = importlib.util.module_from_spec(spec); spec.loader.exec_module(alg)

ap = argparse.ArgumentParser()
ap.add_argument('--keys', type=int, default=16)
ap.add_argument('--restarts', type=int, default=12)
ap.add_argument('--seed', type=int, default=20260721)
args = ap.parse_args()
KEYS = args.keys

TABLES = ['chars', 'mod', 'greek', 'kana', 'symbol']
codes_raw, code_chars, _ = alg.load_codes('.', TABLES)
codes = alg.apply_freq(codes_raw, 'merge-keys/freq.json', 0.0)
total = sum(codes.values())
spellsets = {c: alg.spell(c, False) for c in codes}
letters = sorted({ch for c in codes for ch in c if ch.isalpha()})
assert KEYS <= len(letters), f"{KEYS} keys but only {len(letters)} letters"

# per-letter frequency (for choosing representatives)
lf = collections.Counter()
for code, w in codes.items():
    for ch in set(code):
        if ch.isalpha():
            lf[ch] += w

def score(groups):
    return alg.score_groups(codes, spellsets, groups)

def valid(gs):
    allletters = set().union(*gs) if gs else set()
    return (len(gs) == KEYS and allletters == set(letters)
            and sum(len(g) for g in gs) == len(letters))

def local_search(groups):
    """First-improvement hill climb; RESTART the scan after any accepted change
    so we never iterate a stale snapshot. Moves a letter to another key, or
    swaps two letters between keys."""
    best = score(groups)
    changed = True
    while changed:
        changed = False
        for gi in range(len(groups)):
            if len(groups[gi]) == 1:
                continue
            for ch in list(groups[gi]):
                for gj in range(len(groups)):
                    if gj == gi:
                        continue
                    groups[gi].discard(ch); groups[gj].add(ch)
                    s = score(groups)
                    if s < best and valid(groups):
                        best = s; changed = True; break
                    groups[gj].discard(ch); groups[gi].add(ch)
                if changed:
                    break
            if changed:
                break
        if changed:
            continue
        for gi in range(len(groups)):
            for gj in range(gi + 1, len(groups)):
                for a in list(groups[gi]):
                    for b in list(groups[gj]):
                        groups[gi].discard(a); groups[gi].add(b)
                        groups[gj].discard(b); groups[gj].add(a)
                        s = score(groups)
                        if s < best and valid(groups):
                            best = s; changed = True; break
                        groups[gi].discard(b); groups[gi].add(a)
                        groups[gj].discard(a); groups[gj].add(b)
                    if changed:
                        break
                if changed:
                    break
            if changed:
                break
    return best

# ---- seed from greedy unconstrained partition at KEYS ----
snaps = alg.greedy_unconstrained(codes, False, KEYS)
groups = [set(g) for g in snaps[KEYS][0]]
assert valid(groups), "greedy seed invalid"
best = local_search(groups)
best_groups = [set(g) for g in groups]

# ---- multi-start: random KEYS-partitions + polish ----
random.seed(args.seed)
for _ in range(args.restarts):
    shuffled = letters[:]
    random.shuffle(shuffled)
    cut = sorted(random.sample(range(1, len(shuffled)), KEYS - 1))
    idx = [0] + cut + [len(shuffled)]
    trial = [set(shuffled[idx[i]:idx[i+1]]) for i in range(KEYS)]
    if not valid(trial):
        continue
    groups = trial
    s = local_search(groups)
    if s < best:
        best = s; best_groups = [set(g) for g in groups]
groups = [g for g in best_groups if g]
assert valid(groups), "partition corrupted"
print(f"tables={TABLES}  codes={len(codes)}  load={total:.0f}")
print(f"final {KEYS}-key partition (dirty={best:.0f}  list-clean={100*(total-best)/total:.2f}%)")

# ---- choose representative = highest-freq letter in each group ----
reps = {frozenset(g): max(g, key=lambda c: lf[c]) for g in groups}

# ---- verification via a real fold spec (both metrics) ----
pairs = []
for g in groups:
    r = reps[frozenset(g)]
    for ch in g:
        if ch != r:
            pairs.append((ch, r))
r = alg.analyze(codes, code_chars, pairs, False)
print(f"  verify: list-clean={r['fold_clean']:.2f}%  top-slot={r['fold_buried_clean']:.2f}%")

# ---- render placement on QWERTY grid ----
QROWS = ['qwertyuiop', 'asdfghjkl', 'zxcvbnm']
QPOS = {c: (ri, i) for ri, row in enumerate(QROWS) for i, c in enumerate(row)}
grid = {}
for g in groups:
    rp = reps[frozenset(g)]
    grid[QPOS[rp]] = (rp, g)
print("\n  keyboard (CAPS = emitted letter, placed at its QWERTY home):")
for ri, row in enumerate(QROWS):
    cells = []
    for i, _c in enumerate(row):
        if (ri, i) in grid:
            rp, g = grid[(ri, i)]
            lab = ''.join(ch.upper() if ch == rp else ch
                          for ch in sorted(g, key=lambda c: -lf[c]))
            cells.append(lab)
    print("    " + "   ".join(cells))

# ---- emit fold lines and JSON ----
print("\n  xform fold lines (append to END of speller/algebra):")
for src, dst in sorted(pairs):
    print(f"    - xform/{src}/{dst}/")

out = {
    'keys': KEYS,
    'partition': [sorted(g) for g in groups],
    'representatives': {reps[frozenset(g)]: sorted(g) for g in groups},
    'folds': [[s, d] for s, d in sorted(pairs)],
    'list_clean_pct': round(100 * (total - best) / total, 2),
    'top_slot_pct': round(r['fold_buried_clean'], 2),
    'grid': {f'{ri},{i}': (grid[(ri, i)][0], sorted(grid[(ri, i)][1]))
             for (ri, i) in grid},
}
json.dump(out, open(f'merge-keys/layout{KEYS}.json', 'w', encoding='utf-8'),
          ensure_ascii=False, indent=2)
print(f"\n  wrote merge-keys/layout{KEYS}.json")

# ---- top collision pairs the fold introduces (freq-weighted) ----
print("\n  heaviest newly-merged code pairs (real-typing weighted):")
tbl = alg.fold_map(pairs)
base = alg.accepted(codes, False, {})
fold = alg.accepted(codes, False, tbl)
def cps(m):
    s = set()
    for _k, cs in m.items():
        if len(cs) > 1:
            cl = sorted(cs)
            for i in range(len(cl)):
                for j in range(i+1, len(cl)):
                    s.add((cl[i], cl[j]))
    return s
new = cps(fold) - cps(base)
for a, b in sorted(new, key=lambda p: -(codes[p[0]] + codes[p[1]]))[:15]:
    ca = ''.join(sorted(code_chars[a]))[:8]
    cb = ''.join(sorted(code_chars[b]))[:8]
    print(f"    {a:9s} f={codes[a]:<5.0f}[{ca}]  <->  {b:9s} f={codes[b]:<5.0f}[{cb}]")
