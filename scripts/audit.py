#!/usr/bin/env python3
"""Read-only audit: checksums + counts for every dumped file. Writes MANIFEST.tsv + INDEX.md. Never modifies data."""
import json, glob, os, hashlib, csv, sys, collections

ROOT = '/home/sakib/offlineMCQ'
API = os.path.join(ROOT, 'api_data')

def sha256(p):
    h = hashlib.sha256()
    with open(p, 'rb') as f:
        for chunk in iter(lambda: f.read(1 << 20), b''):
            h.update(chunk)
    return h.hexdigest()

def classify(path):
    n = os.path.basename(path)
    if '/pages/' in path:
        if 'archive' in n: return 'exam_list_archive'
        if 'routine' in n: return 'exam_list_routine'
        return 'exam_list_other'
    if '/questions/' in path: return 'question_page'
    if n == 'all_questions.jsonl': return 'question_merged'
    if '/responses' in path or '/one_shot' in path: return 'endpoint_sample'
    if n.startswith('endpoint_report'): return 'endpoint_report'
    return 'other'

def count_records(path, kind):
    try:
        if kind == 'question_page':
            d = json.load(open(path))
            return len(d.get('questions', []))
        if kind.startswith('exam_list'):
            d = json.load(open(path))
            data = d.get('data', d) if isinstance(d, dict) else d
            if isinstance(data, dict):
                pd = data.get('page_data')
                if isinstance(pd, list): return len(pd)
            return len(data) if isinstance(data, list) else ''
        if kind == 'question_merged':
            with open(path) as f: return sum(1 for _ in f)
        if kind == 'endpoint_sample':
            d = json.load(open(path))
            if isinstance(d, list): return len(d)
            if isinstance(d, dict):
                for v in d.values():
                    if isinstance(v, list): return len(v)
                return len(d)
        return ''
    except Exception:
        return 'ERR'

rows = []
for dirpath, dirnames, filenames in os.walk(API):
    dirnames.sort(); filenames.sort()
    for fn in filenames:
        p = os.path.join(dirpath, fn)
        rel = os.path.relpath(p, API)
        kind = classify(p)
        try:
            size = os.path.getsize(p)
            rows.append(dict(file=rel, kind=kind, bytes=size,
                             records=count_records(p, kind), sha256=sha256(p)))
        except Exception as e:
            rows.append(dict(file=rel, kind='UNREADABLE', bytes='', records=str(e), sha256=''))

with open(os.path.join(API, 'MANIFEST.tsv'), 'w', newline='') as f:
    w = csv.DictWriter(f, fieldnames=['file', 'kind', 'bytes', 'records', 'sha256'], delimiter='\t')
    w.writeheader(); w.writerows(rows)

# summary
by_kind = collections.defaultdict(lambda: [0, 0, 0])
for r in rows:
    b = by_kind[r['kind']]
    b[0] += 1
    b[1] += r['bytes'] if isinstance(r['bytes'], int) else 0
    if isinstance(r['records'], int): b[2] += r['records']

lines = ['# LiveMCQ API dump — INDEX\n', 'Read-only audit. MANIFEST.tsv = sha256 per file (verify integrity: `sha256sum -c` style via MANIFEST).\n',
         '| kind | files | MB | records |', '|---|---|---|---|']
for k in sorted(by_kind):
    c, s, r = by_kind[k]
    lines.append(f'| {k} | {c} | {s/1024/1024:.1f} | {r} |')
errs = [r for r in rows if r['kind'] == 'UNREADABLE' or r['records'] == 'ERR']
lines.append(f'\nUnreadable/corrupt: {len(errs)}')
for r in errs[:20]: lines.append(f'- {r["file"]}: {r["records"]}')
open(os.path.join(API, 'INDEX.md'), 'w').write('\n'.join(lines) + '\n')

print('\n'.join(lines))
print(f'\nManifest rows: {len(rows)}')
