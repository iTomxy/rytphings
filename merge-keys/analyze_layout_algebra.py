#!/usr/bin/env python3
"""
Algebra-aware collision analyzer for the rytphings reduced-key fold.

The sibling `analyze_layout.py` measures collisions on the RAW dict codes only.
The deployed schema, however, runs a chain of `derive` rules (yang-ru coda
voicing, oi/ui->oy/uy, aa->a, glottal q-, kwh->khw) BEFORE the reduced-key fold
is applied. Those derives create extra accepted spellings, and the fold can
merge two of them that were distinct before -- most notably tone minimal pairs
via  derive/aa(q|s|$)/a$1/  +  xform/s/a/ .

This script replays the real speller/algebra from rytphings.schema.yaml, then
applies a candidate fold, and reports how much EXTRA collision the fold causes
once the derives are present. It also enumerates concrete newly-merged
(char, code) pairs so you can eyeball the tone damage.

abbrev/^([a-z]).+$/$1/ (first-letter shortcut) is intentional, orthogonal, and
swamps everything, so it is EXCLUDED by default (use --with-abbrev to include).

Usage:
    python3 analyze_layout_algebra.py --dir . --fold 18
    python3 analyze_layout_algebra.py --dir . --fold 18 --show 40
    python3 analyze_layout_algebra.py --dir . --fold none   # baseline, no fold
"""
import argparse, collections, glob, json, os, re, sys


def apply_freq(codes, freq_path, floor):
    """Replace entry-count load with REAL commit counts from a userdb freq.json
    (single-syllable spellings only). Untyped codes get `floor` weight."""
    data = json.load(open(freq_path, encoding='utf-8'))
    single = collections.Counter()
    for spelling, text, c in data['entries']:
        s = spelling.strip()
        if s and ' ' not in s:
            single[s] += c
    new = collections.Counter()
    for code in codes:
        new[code] = single.get(code, 0) + floor
    return new

# ---- the real speller/algebra derive chain (order matters), abbrev excluded ----
# Each entry: (kind, pattern, repl). kind in {derive, xform}.
# Translated from rytphings.schema.yaml. $1 -> \1 for Python.
ALGEBRA = [
    ('derive', r'^([aeo])', r'q\1'),
    ('derive', r'^u(k|ng)', r'qu\1'),
    ('derive', r'^(b|v|d|g|x|ng|j|z|r|w)(.+)p$', r'\1\2b'),
    ('derive', r'^(b|v|d|g|x|ng|j|z|r|w)(.+)t$', r'\1\2d'),
    ('derive', r'^(b|v|d|g|x|ng|j|z|r|w)(.+)k$', r'\1\2g'),
    ('derive', r'^([mnl])(?!h)(.+)p$', r'\1\2b'),
    ('derive', r'^([mnl])(?!h)(.+)t$', r'\1\2d'),
    ('derive', r'^([mnl])(?!h)(.+)k$', r'\1\2g'),
    ('derive', r'oi(q|s|$)', r'oy\1'),
    ('derive', r'ui(q|s|$)', r'uy\1'),
    ('derive', r'aa(q|s|$)', r'a\1'),
    ('derive', r'^(k|g)wh', r'\1hw'),
]
ABBREV = ('abbrev', r'^([a-z]).+$', r'\1')

# ---- fold definitions (representative = LEFT letter of each merged key) ----
FOLDS = {
    '18': [('w', 'q'), ('r', 'e'), ('y', 't'), ('p', 'o'),
           ('s', 'a'), ('g', 'f'), ('x', 'z'), ('b', 'v')],
    # 17 = 18 plus h+j -> hj (represent as h)
    '17': [('w', 'q'), ('r', 'e'), ('y', 't'), ('p', 'o'),
           ('s', 'a'), ('g', 'f'), ('x', 'z'), ('b', 'v'), ('j', 'h')],
    # 18opt = algebra-aware optimum: a/s stay SPLIT, h/j merged instead
    '18opt': [('w', 'q'), ('r', 'e'), ('y', 't'), ('p', 'o'),
              ('g', 'f'), ('j', 'h'), ('x', 'z'), ('b', 'v')],
    # 19noS = HANDOFF fold minus s->a : keeps departing-tone -s on its own key
    '19noS': [('w', 'q'), ('r', 'e'), ('y', 't'), ('p', 'o'),
              ('g', 'f'), ('x', 'z'), ('b', 'v')],
    # 18freq = freq-weighted algebra-aware optimum (a/s split; d+f, g+h merged)
    '18freq': [('w', 'q'), ('r', 'e'), ('y', 't'), ('p', 'o'),
               ('f', 'd'), ('h', 'g'), ('x', 'z'), ('b', 'v')],
    'none': [],
}


def load_codes(dirpath, tables=('chars',)):
    codes = collections.Counter()   # primary code -> entry count (load proxy)
    code_chars = collections.defaultdict(set)  # primary code -> {chars}
    files = []
    for kind in tables:
        files += [h for h in glob.glob(os.path.join(dirpath, f'*{kind}*.yaml'))
                  if 'schema' not in os.path.basename(h)]
    if not files:
        sys.exit(f'no dict found in {dirpath} for tables {tables}')
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
            char = parts[0].strip()
            code = parts[1].split('#')[0].strip()
            if code:
                codes[code] += 1
                code_chars[code].add(char)
    return codes, code_chars, [os.path.basename(f) for f in files]


def spell(code, use_abbrev):
    """Replay the derive chain: return the set of accepted spellings for a code.
    Mirrors RIME: derive APPENDS an alternate (original kept); each rule scans
    the spellings accumulated so far (snapshot per rule)."""
    forms = [code]
    seen = {code}
    rules = ALGEBRA + ([ABBREV] if use_abbrev else [])
    for kind, pat, repl in rules:
        rx = re.compile(pat)
        for f in list(forms):            # snapshot at rule start
            if rx.search(f):
                nf = rx.sub(repl, f)
                if nf not in seen:
                    seen.add(nf)
                    forms.append(nf)      # derive/abbrev both append
    return seen


def fold_map(pairs):
    tbl = {}
    for src, dst in pairs:
        tbl[ord(src)] = dst
    return tbl


def accepted(codes, use_abbrev, tbl):
    """spelling(after fold) -> set of primary codes that produce it."""
    m = collections.defaultdict(set)
    for code in codes:
        for s in spell(code, use_abbrev):
            m[s.translate(tbl)].add(code)
    return m


def analyze(codes, code_chars, pairs, use_abbrev):
    total = sum(codes.values())
    tbl_fold = fold_map(pairs)
    tbl_id = {}
    base = accepted(codes, use_abbrev, tbl_id)   # derives, no fold
    fold = accepted(codes, use_abbrev, tbl_fold)  # derives + fold

    def collisions(m):
        # set of unordered code-pairs that share at least one accepted spelling
        pairset = set()
        for s, cs in m.items():
            if len(cs) > 1:
                cl = sorted(cs)
                for i in range(len(cl)):
                    for j in range(i + 1, len(cl)):
                        pairset.add((cl[i], cl[j]))
        return pairset

    base_pairs = collisions(base)
    fold_pairs = collisions(fold)
    new_pairs = fold_pairs - base_pairs

    # load-clean%: a code's typing mass is "dirty" if its PRIMARY spelling,
    # after fold, lands in a bucket shared with another primary code.
    def dirty_load(m):
        dirty = 0
        types = 0
        for code, load in codes.items():
            img = code.translate(tbl_fold if m is fold else tbl_id)
            if len(m.get(img, ())) > 1:
                dirty += load
                types += 1
        return dirty, types

    fold_dirty, fold_types = dirty_load(fold)
    base_dirty, base_types = dirty_load(base)

    # heaviest-wins accounting (matches raw analyze_layout.py's 98.23% metric):
    # a code's load is "lost" only if a HEAVIER code shares its primary bucket
    # (i.e. a more frequent char steals the top candidate slot). This is the
    # real "did my intended char get buried?" UX number.
    def buried_load(m, tbl):
        buried = 0
        for code, load in codes.items():
            comp = m.get(code.translate(tbl), ())
            if any(codes[c] > load or (codes[c] == load and c < code)
                   for c in comp if c != code):
                buried += load
        return buried

    fold_buried = buried_load(fold, tbl_fold)
    base_buried = buried_load(base, tbl_id)

    return {
        'total': total,
        'base_pairs': len(base_pairs),
        'fold_pairs': len(fold_pairs),
        'new_pairs': new_pairs,
        'base_clean': 100 * (total - base_dirty) / total,
        'fold_clean': 100 * (total - fold_dirty) / total,
        'base_types': base_types,
        'fold_types': fold_types,
        'fold_buried_clean': 100 * (total - fold_buried) / total,
        'base_buried_clean': 100 * (total - base_buried) / total,
    }


ROWS = ['qwertyuiop', 'asdfghjkl', 'zxcvbnm']


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


def optimize(codes, use_abbrev, target, maxsize=2):
    """Exhaustive QWERTY-order search scored by the ALGEBRA-AWARE dirty-load
    metric (a code is dirty if its primary folded spelling shares a candidate
    bucket with any other code). Returns best fold as list of (src,dst) pairs."""
    total = sum(codes.values())
    # precompute each code's accepted-spelling set ONCE (derives don't depend on fold)
    spellsets = {c: spell(c, use_abbrev) for c in codes}
    primaries = list(codes)

    def score(pairs):
        tbl = fold_map(pairs)
        bucket = collections.defaultdict(set)
        for c in primaries:
            for s in spellsets[c]:
                bucket[s.translate(tbl)].add(c)
        dirty = 0
        for c, load in codes.items():
            if len(bucket[c.translate(tbl)]) > 1:
                dirty += load
        return dirty

    def key_letter_pairs(tiling):
        # each multi-letter group -> (secondary->primary) folds onto LEFT letter
        pairs = []
        for g in tiling:
            for ch in g[1:]:
                pairs.append((ch, g[0]))
        return pairs

    T = [ [row_tilings(r, maxsize) for r in ROWS] ]
    tilings = [row_tilings(r, maxsize) for r in ROWS]
    best = None; searched = 0
    for a in tilings[0]:
        for b in tilings[1]:
            for c in tilings[2]:
                groups = a + b + c
                if len(groups) != target:
                    continue
                searched += 1
                pairs = key_letter_pairs(groups)
                d = score(pairs)
                if best is None or d < best[0]:
                    best = (d, groups, pairs)
    return best, searched, total


def score_groups(codes, spellsets, groups):
    """dirty load for an arbitrary letter grouping (each group -> one sentinel).
    A code is dirty if its primary folded spelling shares a bucket."""
    rep = {}
    for i, g in enumerate(groups):
        sym = chr(0x100 + i)
        for ch in g:
            rep[ch] = sym
    tbl = {ord(ch): rep[ch] for ch in rep}
    bucket = collections.defaultdict(set)
    for c in codes:
        for s in spellsets[c]:
            bucket[s.translate(tbl)].add(c)
    dirty = 0
    for c, load in codes.items():
        if len(bucket[c.translate(tbl)]) > 1:
            dirty += load
    return dirty


def greedy_unconstrained(codes, use_abbrev, stop_at, letters=None):
    """Greedy pairwise merge (no QWERTY constraint), scored algebra-aware.
    Returns {k: (groups, dirty)} snapshots for every k from 26 down to stop_at."""
    spellsets = {c: spell(c, use_abbrev) for c in codes}
    if letters is None:
        letters = sorted({ch for c in codes for ch in c if ch.isalpha()})
    groups = [{c} for c in letters]
    snaps = {len(groups): ([set(g) for g in groups],
                           score_groups(codes, spellsets, groups))}
    while len(groups) > stop_at:
        best = None
        for i in range(len(groups)):
            for j in range(i + 1, len(groups)):
                trial = ([groups[k] for k in range(len(groups)) if k not in (i, j)]
                         + [groups[i] | groups[j]])
                d = score_groups(codes, spellsets, trial)
                if best is None or d < best[0]:
                    best = (d, i, j)
        _, i, j = best
        merged = groups[i] | groups[j]
        groups = ([groups[k] for k in range(len(groups)) if k not in (i, j)]
                  + [merged])
        snaps[len(groups)] = ([set(g) for g in groups],
                              score_groups(codes, spellsets, groups))
    return snaps


def main():
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass
    ap = argparse.ArgumentParser()
    ap.add_argument('--dir', default='.')
    ap.add_argument('--fold', default='18', choices=sorted(FOLDS))
    ap.add_argument('--with-abbrev', action='store_true')
    ap.add_argument('--show', type=int, default=25,
                    help='how many newly-merged code pairs to print')
    ap.add_argument('--attribute', action='store_true',
                    help='report each single xform fold\'s marginal cost')
    ap.add_argument('--optimize', type=int, metavar='KEYS',
                    help='exhaustive QWERTY-order search at KEYS, algebra-aware')
    ap.add_argument('--freq', metavar='JSON',
                    help='weight by REAL userdb commit counts (read_userdb.py out)')
    ap.add_argument('--floor', type=float, default=0.0,
                    help='weight for codes with no commits (default 0)')
    ap.add_argument('--tables', nargs='+', default=['chars'],
                    help='dict tables to include, e.g. chars mod greek kana symbol')
    ap.add_argument('--compare', nargs='+', type=int, metavar='K',
                    help='compare QWERTY-order vs unconstrained across key counts')
    args = ap.parse_args()

    if args.compare:
        codes, code_chars, files = load_codes(args.dir, args.tables)
        if args.freq:
            codes = apply_freq(codes, args.freq, args.floor)
        total = sum(codes.values())
        print(f'tables: {args.tables}   codes: {len(codes)}   load: {total:.0f}'
              f'   [{"userdb freq" if args.freq else "entry count"}]')
        ks = sorted(args.compare, reverse=True)
        snaps = greedy_unconstrained(codes, args.with_abbrev, min(ks))
        print(f'\n  keys | QWERTY-order clean | unconstrained clean | QWERTY cost')
        print(f'  -----|--------------------|---------------------|------------')
        for k in sorted(args.compare, reverse=True):
            best, n, _ = optimize(codes, args.with_abbrev, k)
            qclean = 100 * (total - best[0]) / total if best else float('nan')
            uclean = 100 * (total - snaps[k][1]) / total
            qtxt = f'{qclean:6.2f}%' if best else '  n/a  '
            print(f'   {k:3d} |      {qtxt}       |       {uclean:6.2f}%       '
                  f'|   {(uclean-qclean):+5.2f} pt' if best
                  else f'   {k:3d} |       n/a          |       {uclean:6.2f}%       |    n/a')
        # print the unconstrained groupings
        print(f'\n  unconstrained (greedy) groupings:')
        for k in sorted(args.compare, reverse=True):
            groups, d = snaps[k]
            layout = ' '.join(''.join(sorted(g)) for g in
                              sorted(groups, key=lambda s: sorted(s)))
            print(f'   {k:3d}: {layout}')
        return

    if args.optimize:
        codes, code_chars, files = load_codes(args.dir, args.tables)
        if args.freq:
            codes = apply_freq(codes, args.freq, args.floor)
        print(f'files: {files}   codes: {len(codes)}   load: {sum(codes.values())}'
              f'   [{"userdb freq" if args.freq else "entry count"}]')
        best, n, total = optimize(codes, args.with_abbrev, args.optimize)
        d, groups, pairs = best
        layout = ' '.join(''.join(g) for g in groups)
        emit = ' '.join(g[0] for g in groups if len(g) > 1)
        print(f'\nBEST QWERTY-order {args.optimize}-key (algebra-aware, searched {n}):')
        print(f'  layout : {layout}')
        print(f'  folds  : ' + ' '.join(f'{s}->{dd}' for s, dd in pairs))
        print(f'  clean  : {100*(total-d)/total:.2f}%  (dirty load {d}/{total})')
        return

    if args.attribute:
        codes, code_chars, files = load_codes(args.dir, args.tables)
        if args.freq:
            codes = apply_freq(codes, args.freq, args.floor)
        print(f'files: {files}   codes: {len(codes)}   load: {sum(codes.values())}'
              f'   [{"userdb freq" if args.freq else "entry count"}]')
        print(f'per-fold marginal cost (each xform applied ALONE, over derives):')
        base = analyze(codes, code_chars, [], args.with_abbrev)['base_clean']
        print(f'  baseline (no fold): {base:.2f}% clean')
        for pair in FOLDS['18']:
            r = analyze(codes, code_chars, [pair], args.with_abbrev)
            print(f'  xform/{pair[0]}/{pair[1]}/ : {r["fold_clean"]:6.2f}% clean  '
                  f'(cost {base - r["fold_clean"]:5.2f} pt, '
                  f'{len(r["new_pairs"])} new pairs)')
        return

    codes, code_chars, files = load_codes(args.dir, args.tables)
    if args.freq:
        codes = apply_freq(codes, args.freq, args.floor)
    print(f'files: {files}')
    print(f'distinct primary codes: {len(codes)}   total load: {sum(codes.values())}'
          f'   [{"userdb freq" if args.freq else "entry count"}]')
    print(f'fold: {args.fold}   abbrev: {args.with_abbrev}')

    r = analyze(codes, code_chars, FOLDS[args.fold], args.with_abbrev)
    print(f'\n-- with real derive chain applied --')
    print(f'  baseline (derives, NO fold): clean={r["base_clean"]:.2f}%  '
          f'colliding code-pairs={r["base_pairs"]}  dirty codes={r["base_types"]}')
    print(f'  folded   (derives + fold)  : clean={r["fold_clean"]:.2f}%  '
          f'colliding code-pairs={r["fold_pairs"]}  dirty codes={r["fold_types"]}')
    print(f'  >>> fold cost: {r["base_clean"]-r["fold_clean"]:.2f} pt of typing mass, '
          f'{len(r["new_pairs"])} NEW colliding code-pairs')
    print(f'\n  heaviest-wins view (does a MORE FREQUENT char steal the top slot?):')
    print(f'    baseline: {r["base_buried_clean"]:.2f}% keep top slot  |  '
          f'folded: {r["fold_buried_clean"]:.2f}%  '
          f'(cost {r["base_buried_clean"]-r["fold_buried_clean"]:.2f} pt)')

    if r['new_pairs']:
        print(f'\n-- {min(args.show, len(r["new_pairs"]))} of {len(r["new_pairs"])} '
              f'newly-merged code pairs (char lists) --')
        # sort by combined load, heaviest first
        scored = sorted(r['new_pairs'],
                        key=lambda p: -(codes[p[0]] + codes[p[1]]))
        for a, b in scored[:args.show]:
            ca = ''.join(sorted(code_chars[a]))
            cb = ''.join(sorted(code_chars[b]))
            print(f'    {a:10s} [{ca}]   <->   {b:10s} [{cb}]')


if __name__ == '__main__':
    main()
