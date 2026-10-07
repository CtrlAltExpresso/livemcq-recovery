#!/usr/bin/env python3
"""media_progress.tsv (status,url,size,sha256) -> committed media_manifest.tsv
Grouped by status; used to document exactly what media exists locally and what
could not be fetched.
"""
import os, json, io, sys, collections

PROG = '/home/sakib/offlineMCQ/media_progress.tsv'
OUT = '/home/sakib/offlineMCQ/api_data/media_manifest.tsv'
if not os.path.isfile(PROG):
    sys.exit('no progress file')

best = {}

for line in open(PROG, encoding='utf-8'):
    line = line.rstrip('\n')
    if not line: continue
    parts = line.split('\t')
    if len(parts) != 4:
        continue
    st, url, size, h = parts
    # later rows (latest run) win; prefer rows backed by a real file
    if url in best:
        cur = best[url]
        cur_ok = cur[0] in ('ok', 'skip') and int(cur[1] or 0) > 0
        new_ok = st in ('ok', 'skip') and int(size or 0) > 0
        if cur_ok or not new_ok:
            continue
    best[url] = (st.replace('skip', 'ok'), size or '0', h)

rows = []
for url, (st, size, h) in best.items():
    rows.append((st, url, size, h))

by = collections.Counter(r[0] for r in rows)
with open(OUT, 'w') as f:
    f.write('# status\tsize_bytes\tsha256\turl\n')
    for r in sorted(rows, key=lambda x: x[0]):
        f.write('\t'.join(r) + '\n')

print(f'{len(rows)} rows -> {OUT}')
print('status counts:', dict(by.most_common()))
ok = sum(int(sz) for st, url, sz, h in rows if st in ('ok', 'skip'))
print(f'total bytes on disk referenced: {ok:,}  ({ok/1e6:.1f} MB)')