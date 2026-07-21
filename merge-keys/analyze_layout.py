#!/usr/bin/env python3
"""
rytphings reduced-key layout analyzer.

Computes, against the ACTUAL dictionary files in a rytphings repo:
  - the collision-optimal (unconstrained) letter->key grouping, and
  - the collision-optimal grouping that PRESERVES QWERTY row order,
for any target key count.

Collision metric: for a given letter->key map, encode every dictionary code;
two originally-distinct codes that map to the same image "collide" (their
candidate lists merge). We report:
    types_lost  = number of codes that lost their unique encoding
    load_lost   = sum of entry-counts of those codes (frequency proxy)
    load-clean% = share of typing mass still uniquely coded
Higher load-clean% = fewer candidate-list growths = better.

Caveats (read before trusting the number):
  * Single-code collisions only. Multi-syllable segmentation is NOT modelled.
  * "load" = entry count per code, a proxy for real corpus frequency.
  * Operates on the DICT codes as written; it does NOT expand the scheme's
    speller/algebra alternates (yang-ru -b/-d/-g, oi->oy, aa->a, q- glottal,
    abbrev first-letter). Those add their own intentional ambiguity, and the
    fold interacts with the tone letters q/s -- test tone minimal pairs after.

Usage:
    python3 analyze_layout.py --dir . --keys 18 17 14
    python3 analyze_layout.py --dir . --keys 18 --all-tables
"""
import argparse, collections, itertools, glob, os, sys

ROWS = ['qwertyuiop', 'asdfghjkl', 'zxcvbnm']

def find(dirpath, kind):
    # matches both rytphings.chars.dict.yaml and rytphings_chars_dict.yaml
    hits = glob.glob(os.path.join(dirpath, f'*{kind}*.yaml'))
    return [h for h in hits if 'schema' not in os.path.basename(h)]

def load(files):
    codes = collections.Counter()
    for path in files:
        started = False
        for ln in open(path, encoding='utf-8'):
            ln = ln.replace('\r', '')
            if ln.startswith('#'):
                continue
            if not started:
                if ln.strip() == '...':
                    started = True
                continue
            parts = ln.rstrip('\n').split('\t')
            if len(parts) < 2 or not parts[1].strip():
                continue
            code = parts[1].split('#')[0].strip()
            if code:
                codes[code] += 1
    return codes

def letters_of(codes):
    s = set()
    for c in codes:
        s |= {ch for ch in c if ch.isalpha()}
    return sorted(s)

def cost(codes, groups):
    rep = {}
    for i, g in enumerate(groups):
        sym = chr(0x100 + i)
        for ch in g:
            rep[ch] = sym
    tbl = {ord(ch): rep[ch] for ch in rep}
    clusters = collections.defaultdict(list)
    for code, load in codes.items():
        clusters[code.translate(tbl)].append((code, load))
    types_lost = load_lost = 0
    for lst in clusters.values():
        if len(lst) > 1:
            lst.sort(key=lambda x: -x[1])
            types_lost += len(lst) - 1
            load_lost += sum(l for _, l in lst[1:])
    return types_lost, load_lost

def greedy(codes, letters, target):
    groups = [{c} for c in letters]
    while len(groups) > target:
        best = None
        for i, j in itertools.combinations(range(len(groups)), 2):
            trial = [groups[k] for k in range(len(groups)) if k not in (i, j)] + [groups[i] | groups[j]]
            c = cost(codes, trial)
            key = (c[1], c[0])
            if best is None or key < best[0]:
                best = (key, i, j)
        _, i, j = best
        m = groups[i] | groups[j]
        groups = [groups[k] for k in range(len(groups)) if k not in (i, j)] + [m]
    return groups

def row_tilings(row, maxsize=2):
    n = len(row); res = []
    def rec(i, acc):
        if i == n:
            res.append(list(acc)); return
        for size in range(1, maxsize + 1):
            if i + size <= n:
                acc.append(row[i:i + size]); rec(i + size, acc); acc.pop()
    rec(0, [])
    return res

def qwerty_best(codes, letters, target, maxsize=2):
    lset = set(letters)
    def clean(t):
        return [set(g) & lset for g in t if set(g) & lset]
    T = [[clean(t) for t in row_tilings(r, maxsize)] for r in ROWS]
    best = None; searched = 0
    for a in T[0]:
        for b in T[1]:
            for c in T[2]:
                groups = a + b + c
                if len(groups) != target:
                    continue
                searched += 1
                co = cost(codes, groups)
                key = (co[1], co[0])
                if best is None or key < best[0]:
                    best = (key, groups, co)
    return best, searched

def fmt(groups, keep_order=False):
    if keep_order:
        return ' '.join(''.join(sorted(g)) for g in groups)
    return ' '.join(''.join(sorted(g)) for g in sorted(groups, key=lambda s: sorted(s)))

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--dir', default='.')
    ap.add_argument('--keys', type=int, nargs='+', default=[18, 17, 14])
    ap.add_argument('--all-tables', action='store_true',
                    help='include greek/kana/mod/symbol, not just chars')
    ap.add_argument('--maxsize', type=int, default=2,
                    help='max letters per key in the QWERTY-order search')
    args = ap.parse_args()

    files = find(args.dir, 'chars')
    if not files:
        sys.exit(f'no chars dict found in {args.dir}')
    if args.all_tables:
        for k in ('greek', 'kana', 'mod', 'symbol'):
            files += find(args.dir, k)
    codes = load(files)
    letters = letters_of(codes)
    tot = sum(codes.values())
    print(f'files: {[os.path.basename(f) for f in files]}')
    print(f'distinct codes: {len(codes)}   total load: {tot}   letters: {"".join(letters)}')

    for T in args.keys:
        g = greedy(codes, letters, T)
        tl, ll = cost(codes, g)
        print(f'\n== {T} keys ==')
        print(f'  UNCONSTRAINED : {fmt(g)}')
        print(f'                  types_lost={tl} load_lost={ll} clean={100*(tot-ll)/tot:.2f}%')
        best, n = qwerty_best(codes, letters, T, args.maxsize)
        if best is None:
            print(f'  QWERTY-order  : no size<={args.maxsize} tiling reaches {T} keys')
        else:
            _, qg, (qtl, qll) = best
            print(f'  QWERTY-order  : {fmt(qg, keep_order=True)}   (searched {n})')
            print(f'                  types_lost={qtl} load_lost={qll} clean={100*(tot-qll)/tot:.2f}%'
                  f'  (QWERTY penalty {(100*(tot-qll)/tot)-(100*(tot-ll)/tot):+.2f} pt)')

if __name__ == '__main__':
    main()
