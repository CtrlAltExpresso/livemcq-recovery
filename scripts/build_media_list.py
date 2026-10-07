#!/usr/bin/env python3
"""Build the media download list from every saved response.
Parses raw bytes (not JSON) so URLs inside escaped JSON strings are caught too.
- host: one of the app's own hosts below
- strips HTML/JSON punctuation artifacts around URLs
- dedupes by normalized URL
Writes /tmp/opencode/media_download_list.tsv  (url \t relative_path)
"""
import json, re, os

HOSTS = {
    'elasticbeanstalk-ap-southeast-1-051040323559.s3.amazonaws.com',
    'assets.livemcq.com',
    'files.livemcq.app',
}
API = '/home/sakib/offlineMCQ/api_data'
url_re = re.compile(r'https?://([^"<>\s\\]+)', re.I)

seen = {}
files = []
for root, dirs, fs in os.walk(API):
    if '/pages_v2' in root or '/pages_v3' in root:
        continue
    for fn in fs:
        p = os.path.join(root, fn)
        if os.path.getsize(p) == 0:
            continue
        files.append(p)

for p in files:
    try:
        data = open(p, 'rb').read()
    except Exception:
        continue
    for m in url_re.findall(data.decode('utf-8', 'ignore')):
        scheme_rest = m
        host = scheme_rest.split('/', 1)[0].lower()
        if host not in HOSTS:
            continue
        path = scheme_rest.split('/', 1)[1] if '/' in scheme_rest else ''
        # HTML/JSON artifacts: URL may be followed by '</span>', "\", "'", ';' etc.
        # strip trailing slash FIRST (so an embedded quote then shows up), then
        # punctuation, then any remaining trailing slash.
        clean = path.rstrip('/')
        clean = clean.rstrip('\'"`,;).:')
        clean = clean.rstrip('/') or 'index/'
        key = f'{host}/{clean}'
        if key not in seen:
            seen[key] = f'https://{host}/{clean}'

with open('/tmp/opencode/media_download_list.tsv', 'w') as f:
    for key, url in sorted(seen.items()):
        f.write(f'{url}\t{key}\n')

print(f'unique media URLs: {len(seen)}')
from collections import Counter
ext = Counter(k.rsplit('.', 1)[-1].lower() if '.' in k.split('/')[-1] else '(none)' for k in seen)
for e, n in ext.most_common(15):
    print(f'  {e:>12} {n}')