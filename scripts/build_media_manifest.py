#!/usr/bin/env python3
"""Build api_data/media_manifest.tsv from disk truth:
walks api_data/media_download_list.tsv, resolves the local file (with the
same safe_rel used by download_media.py), re-hashes it, and records the
status of anything not on disk (from media_progress.tsv failure rows).

Output (tab-separated, git-committed): status  size  sha256  relpath  url
"""
import os, hashlib

ROOT = '/home/sakib/offlineMCQ'
LIST = f'{ROOT}/api_data/media_download_list.tsv'
PROG = f'{ROOT}/media_progress.tsv'
MEDIA = f'{ROOT}/media'
OUT = f'{ROOT}/api_data/media_manifest.tsv'

def safe_rel(rel):
    rel = rel.replace('\\n', '').replace('\n', '').replace('\r', '').replace('\t', '').replace('\x00', '')
    rel = rel.rstrip('/')
    base = os.path.basename(rel)
    if len(base.encode('utf-8')) > 180:
        stem, dot, ext = base.rpartition('.')
        keep = stem.encode('utf-8')[:120].decode('utf-8', 'ignore')
        base = keep + '_' + hashlib.md5(base.encode()).hexdigest()[:8] + (dot + ext if dot else '')
        rel = os.path.join(os.path.dirname(rel), base)
    return rel

last = {}
if os.path.isfile(PROG):
    for ln in open(PROG, encoding='utf-8'):
        p = ln.rstrip('\n').split('\t')
        if len(p) == 4:
            last[p[1]] = p[0]

ok = fail = 0
total = 0
with open(OUT, 'w') as out:
    out.write('# status\tsize_bytes\tsha256\trelpath\turl\n')
    for ln in open(LIST, encoding='utf-8'):
        if not ln.strip():
            continue
        url, rel = ln.rstrip('\n').split('\t')
        path = os.path.join(MEDIA, safe_rel(rel))
        if os.path.isfile(path) and os.path.getsize(path) > 0:
            with open(path, 'rb') as f:
                b = f.read()
            out.write(f'ok\t{len(b)}\t{hashlib.sha256(b).hexdigest()}\t{safe_rel(rel)}\t{url}\n')
            ok += 1
            total += len(b)
        else:
            status = last.get(url, 'unknown')
            out.write(f'{status}\t0\t\t{safe_rel(rel)}\t{url}\n')
            fail += 1
print(f'manifest rows: ok={ok} fail={fail} bytes={total:,} ({total/1e9:.2f} GB)')
if fail:
    for ln in open(LIST, encoding='utf-8'):
        if not ln.strip():
            continue
        url, rel = ln.rstrip('\n').split('\t')
        if not (os.path.isfile(os.path.join(MEDIA, safe_rel(rel))) and os.path.getsize(os.path.join(MEDIA, safe_rel(rel))) > 0):
            print('  FAIL', last.get(url, 'unknown'), url)