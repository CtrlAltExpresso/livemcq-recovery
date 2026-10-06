#!/usr/bin/env python3
"""Cross-verify exam list dumps v1 vs v2. Read-only. Pass criteria:
- v2 internally consistent (page alignment, no dups)
- union(v1,v2) distinct == API total_items
- zero dups inside union
"""
import json, glob, re, sys, collections

API = '/home/sakib/offlineMCQ/api_data'
fail = []

def load(pattern, dirn):
    recs = {}          # id -> record
    pages = {}         # id -> set of pages
    bad_align = []
    files = sorted(glob.glob(f'{API}/{dirn}/{pattern}'))
    for f in files:
        m = re.search(r'_p(\d+)\.json', f)
        p = int(m.group(1))
        d = json.load(open(f))
        data = d.get('data', d)
        if data.get('current_page') != p:
            bad_align.append(p)
        for r in data['page_data']:
            pages.setdefault(r['id'], set()).add(p)
            recs[r['id']] = json.dumps(r, sort_keys=True)   # last copy wins
    dups = {i: sorted(ps) for i, ps in pages.items() if len(ps) > 1}
    return files, recs, dups, bad_align

for kind, pat1, pat2, expect in (
    ('archive', '*archive*.json', 'archive_p*.json', 15469),
    ('routine', '*routine*.json', 'routine_p*.json', 1248),
):
    f1, r1, d1, a1 = load(pat1, 'pages')
    f2, r2, d2, a2 = load(pat2, 'pages_v2')
    union = set(r1) | set(r2)
    inter = set(r1) & set(r2)
    only1 = set(r1) - set(r2)
    only2 = set(r2) - set(r1)
    # content agreement on intersection
    disagree = sum(1 for i in inter if r1[i] != r2[i])
    print(f'== {kind} ==')
    print(f'  v1: {len(f1)} pages, {len(r1)} distinct, {len(d1)} boundary-dups, {len(a1)} misaligned')
    print(f'  v2: {len(f2)} pages, {len(r2)} distinct, {len(d2)} boundary-dups, {len(a2)} misaligned')
    print(f'  union: {len(union)} | overlap: {len(inter)} | only-v1: {len(only1)} | only-v2: {len(only2)} | content-disagree: {disagree}')
    if d2: fail.append(f'{kind} v2 internal dups: {list(d2.items())[:5]}')
    if a1 or a2: fail.append(f'{kind} misaligned pages v1={a1[:5]} v2={a2[:5]}')
    if len(union) != expect: fail.append(f'{kind} union {len(union)} != API total {expect}')
    if len(set(r2)) != len(r2): fail.append(f'{kind} v2 distinct anomaly')
    if disagree: fail.append(f'{kind} {disagree} records differ between passes')

print()
if fail:
    print('FAILURES:')
    for x in fail: print(' -', x)
    sys.exit(1)
print('ALL LIST CHECKS PASSED')
