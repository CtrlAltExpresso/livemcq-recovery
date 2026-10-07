#!/usr/bin/env python3
"""Download every unique media URL referenced by the app's own content.
- resume-aware: existing, size-validated files are skipped and re-merged
- validates magic bytes of downloaded images; reports HTTP failures per URL
- writes results incrementally to media_progress.tsv (interrupted runs lose nothing)
- out dir: $MEDIA_ROOT (default ./media under repo root)
"""
import os, hashlib, time, argparse, concurrent.futures
import requests
from requests.adapters import HTTPAdapter
import urllib3
urllib3.disable_warnings()

a = argparse.ArgumentParser()
a.add_argument('--manifest', default='/tmp/opencode/media_download_list.tsv')
a.add_argument('--out', default=os.environ.get('MEDIA_ROOT', '/home/sakib/offlineMCQ/media'))
a.add_argument('--workers', type=int, default=16)
a.add_argument('--resume', default=os.environ.get('MEDIA_PROGRESS', '/home/sakib/offlineMCQ/media_progress.tsv'))
a.add_argument('--limit', type=int, default=0)
opt = a.parse_args()

SESSION = requests.Session()
SESSION.headers['User-Agent'] = 'Mozilla/5.0 (offlineMCQ)'
ad = HTTPAdapter(pool_connections=32, pool_maxsize=32, max_retries=0)
SESSION.mount('https://', ad)

def sniff(b):
    if b.startswith(b'\x89PNG\r\n\x1a\n'): return 'png'
    if b.startswith(b'\xff\xd8\xff'): return 'jpg'
    if b[:6] in (b'GIF87a', b'GIF89a'): return 'gif'
    if b[:4] == b'RIFF' and b[8:12] == b'WEBP': return 'webp'
    if b.startswith(b'%PDF-'): return 'pdf'
    return None

lines = [l for l in open(opt.manifest, encoding='utf-8') if l.strip()]
if opt.limit: lines = lines[:opt.limit]
print(f'{len(lines)} URLs to consider', flush=True)

prog = open(opt.resume, 'a', buffering=1)
failf = open(os.environ.get('MEDIA_FAILS', '/tmp/opencode/media_failures.tsv'), 'a')

def safe_rel(rel):
    """Sanitize a media-relative path: drop control chars, shorten basename."""
    rel = rel.replace('\\n', '').replace('\n', '').replace('\r', '').replace('\t', '').replace('\x00', '')
    if rel.endswith('/'):
        rel = rel.rstrip('/')
    base = os.path.basename(rel)
    if len(base.encode('utf-8')) > 180:
        stem, dot, ext = base.rpartition('.')
        keep = stem.encode('utf-8')[:120].decode('utf-8', 'ignore')
        base = keep + '_' + hashlib.md5(base.encode()).hexdigest()[:8] + (dot + ext if dot else '')
        rel = os.path.join(os.path.dirname(rel), base)
    return rel

def fetch(item):
    url, rel = item.split('\t')
    rel = safe_rel(rel)
    dest = os.path.join(opt.out, rel)
    if os.path.isfile(dest) and os.path.getsize(dest) > 0:
        h = hashlib.sha256(open(dest, 'rb').read()).hexdigest()
        return ('skip', url, rel, os.path.getsize(dest), h)
    fetched = None
    for attempt in range(3):
        try:
            with SESSION.get(url, timeout=(10, 90), stream=False) as r:
                if r.status_code in (404, 410):
                    return (f'HTTP_{r.status_code}', url, rel, 0, '')
                if r.status_code >= 400 and attempt < 2:
                    time.sleep(4 * (attempt + 1)); continue
                if r.status_code >= 400:
                    return (f'HTTP_{r.status_code}', url, rel, 0, '')
                fetched = r.content
                break
        except requests.RequestException:
            if attempt < 2:
                time.sleep(2); continue
            return ('ERR_req', url, rel, 0, '')
    if fetched is None:
        return ('ERR_req', url, rel, 0, '')
    if len(fetched) == 0:
        return ('empty', url, rel, 0, '')
    ext = os.path.splitext(rel)[1].lower().lstrip('.')
    if ext in ('png', 'jpg', 'jpeg', 'gif', 'webp', 'jfif', 'jpe'):
        if not sniff(fetched[:12]):
            return ('badmagic', url, rel, len(fetched), '')
    return ('ok', url, rel, len(fetched), hashlib.sha256(fetched).hexdigest()) if write_file(dest, fetched) else ('badwrite', url, rel, len(fetched), '')

def write_file(dest, fetched):
    try:
        os.makedirs(os.path.dirname(dest), exist_ok=True)
        with open(dest, 'wb') as f:
            f.write(fetched)
        return True
    except OSError as e:
        failf.write(f'ERR_write\t{dest}\t{str(e)[:80]}\n')
        return False

def run(items):
    stats = {'ok': 0, 'skip': 0}
    t0 = time.time(); n = 0
    with concurrent.futures.ThreadPoolExecutor(max_workers=opt.workers) as ex:
        for item in items:
            try:
                res = fetch(item)
            except Exception as e:
                url = item.split('\t')[0]
                failf.write(f'ERR_unhandled\t{url}\t{type(e).__name__}\n')
                res = ('ERR_unhandled', url, item.split('\t')[1], 0, '')
            st, url, rel, size, h = res
            prog.write(f'{st}\t{url}\t{size}\t{h}\n')
            n += 1
            stats[st] = stats.get(st, 0) + 1
            if st in ('ok', 'skip'):
                if stats.get('ok', 0) and stats['ok'] % 1000 == 0:
                    print(f'{n}/{len(lines)} ok={stats["ok"]} skip={stats.get("skip")} {n/(time.time()-t0):.1f}/s', flush=True)
            else:
                failf.write(f'{st}\t{url}\t{rel}\n')
    return stats, time.time() - t0

stats, el = run(lines)
print(f'DONE ok={stats.get("ok")} skip={stats.get("skip")} other={sum(v for k,v in stats.items() if k not in ("ok","skip"))} in {el:.0f}s', flush=True)