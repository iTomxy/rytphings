#!/usr/bin/env python3
"""
Minimal LevelDB SSTable (+ log) reader for a RIME userdb.

RIME stores each committed entry as:
    key   = "<spelling>\t<text>"     e.g.  "si \t詩"   (syllables space-joined,
                                            trailing space, TAB, then the hanzi)
    value = "c=<commits> d=<decay> t=<tick>"

We only need `c` (real commit count = usage frequency). This walks the .ldb
SSTable data blocks (varint prefix-compressed entries + restart array) and the
.log write-ahead records, and writes a merged frequency table to JSON:

    { "codes":  { "<spelling no spaces>": total_c, ... },   # per dict-style code
      "phrases":{ "<spelling with spaces>": total_c, ... },  # multi-syllable
      "entries":[ [spelling, text, c], ... ] }

Usage:
    python3 read_userdb.py --db "<...>/rytphings.userdb" --out freq.json
"""
import argparse, glob, json, os, re, struct, sys, collections


def uvarint(buf, i):
    shift = 0; result = 0
    while True:
        b = buf[i]; i += 1
        result |= (b & 0x7f) << shift
        if not (b & 0x80):
            return result, i
        shift += 7


def parse_block(content):
    """Yield (key_bytes, value_bytes) from one LevelDB data-block content."""
    n = len(content)
    num_restarts = struct.unpack('<I', content[n - 4:n])[0]
    restart_arr_start = n - 4 - num_restarts * 4
    i = 0; prev = b''
    while i < restart_arr_start:
        shared, i = uvarint(content, i)
        nonshared, i = uvarint(content, i)
        vlen, i = uvarint(content, i)
        key = prev[:shared] + content[i:i + nonshared]; i += nonshared
        val = content[i:i + vlen]; i += vlen
        prev = key
        yield key, val


def read_sstable(path):
    data = open(path, 'rb').read()
    # footer: last 48 bytes; index_handle is the 2nd BlockHandle
    footer = data[-48:]
    i = 0
    _moff, i = uvarint(footer, i); _msz, i = uvarint(footer, i)  # metaindex handle
    ioff, i = uvarint(footer, i); isz, i = uvarint(footer, i)    # index handle
    index_content = data[ioff:ioff + isz]
    out = []
    for _k, handle in parse_block(index_content):
        j = 0
        boff, j = uvarint(handle, j)
        bsz, j = uvarint(handle, j)
        block = data[boff:boff + bsz]     # content only (excludes 5-byte trailer)
        for key, val in parse_block(block):
            out.append((key, val))
    return out


def read_log(path):
    """Parse LevelDB write-ahead log; extract WriteBatch put records (type=1)."""
    data = open(path, 'rb').read()
    out = []
    off = 0
    BLOCK = 32768
    payload = bytearray()
    while off + 7 <= len(data):
        # record header: crc(4) len(2) type(1)
        length = struct.unpack('<H', data[off + 4:off + 6])[0]
        rtype = data[off + 6]
        chunk = data[off + 7:off + 7 + length]
        off += 7 + length
        if rtype in (1, 4):        # FULL or LAST -> could parse batch here
            payload.clear(); payload += chunk
            _parse_batch(bytes(payload), out)
        elif rtype == 2:           # FIRST
            payload.clear(); payload += chunk
        elif rtype == 3:           # MIDDLE
            payload += chunk
        # advance to next 32KB block boundary if remaining < 7
        if (off % BLOCK) > BLOCK - 7:
            off += BLOCK - (off % BLOCK)
    return out


def _parse_batch(rec, out):
    # WriteBatch: seq(8) count(4) then records: type(1) key(varstr) [val(varstr)]
    if len(rec) < 12:
        return
    i = 12
    try:
        while i < len(rec):
            t = rec[i]; i += 1
            klen, i = uvarint(rec, i); key = rec[i:i + klen]; i += klen
            if t == 1:  # put
                vlen, i = uvarint(rec, i); val = rec[i:i + vlen]; i += vlen
                out.append((key, val))
            elif t == 0:  # delete
                pass
            else:
                break
    except (IndexError, ValueError):
        return


C_RE = re.compile(rb'c=(\d+)')


def decode_entry(key, val):
    if not val.startswith(b'c='):
        return None
    m = C_RE.match(val)
    if not m:
        return None
    c = int(m.group(1))
    try:
        k = key.decode('utf-8')
    except UnicodeDecodeError:
        # strip internal-key trailer if present, retry
        try:
            k = key[:-8].decode('utf-8')
        except Exception:
            return None
    if '\t' in k:
        spelling, text = k.split('\t', 1)
    else:
        spelling, text = k, ''
    return spelling.strip(), text.strip(), c


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--db', required=True, help='path to *.userdb directory')
    ap.add_argument('--out', required=True)
    args = ap.parse_args()
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

    pairs = []
    for f in sorted(glob.glob(os.path.join(args.db, '*.ldb'))):
        try:
            pairs += read_sstable(f)
        except Exception as e:
            print(f'  warn: {os.path.basename(f)}: {e}', file=sys.stderr)
    for f in sorted(glob.glob(os.path.join(args.db, '*.log'))):
        try:
            pairs += read_log(f)
        except Exception as e:
            print(f'  warn: {os.path.basename(f)}: {e}', file=sys.stderr)

    entries = []
    codes = collections.Counter()
    phrases = collections.Counter()
    best = {}   # (spelling,text) -> max c (dedupe ldb vs log; keep highest)
    for key, val in pairs:
        d = decode_entry(key, val)
        if d is None:
            continue
        spelling, text, c = d
        if not spelling:
            continue
        prev = best.get((spelling, text), -1)
        if c > prev:
            best[(spelling, text)] = c
    for (spelling, text), c in best.items():
        entries.append([spelling, text, c])
        joined = spelling.replace(' ', '')
        if ' ' in spelling:
            phrases[spelling] += c
        codes[joined] += c

    entries.sort(key=lambda x: -x[2])
    result = {
        'codes': dict(codes.most_common()),
        'phrases': dict(phrases.most_common()),
        'entries': entries,
    }
    with open(args.out, 'w', encoding='utf-8') as fh:
        json.dump(result, fh, ensure_ascii=False, indent=0)

    tot = sum(codes.values())
    print(f'entries: {len(entries)}   distinct codes: {len(codes)}   '
          f'distinct phrases: {len(phrases)}   total commits: {tot}')
    print('top 20 codes by commit count:')
    for code, c in codes.most_common(20):
        print(f'  {code:12s} {c}')
    print(f'wrote {args.out}')


if __name__ == '__main__':
    main()
