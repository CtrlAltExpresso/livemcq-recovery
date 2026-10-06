#!/usr/bin/env python3
"""Build course -> exams -> questions structure from canonical lists + filters.
Outputs: api_data/courses/courses.json (master) and api_data/courses/course_<id>.json (per course).
Writes only; never modifies existing data files."""
import json, glob, collections, os, re, unicodedata

API = '/home/sakib/offlineMCQ/api_data'
OUT = f'{API}/courses'
os.makedirs(OUT, exist_ok=True)

def slugify(name):
    """keep everything except ASCII control/space/punctuation; collapse runs to single _, trim to 80 chars."""
    name = (name or '').strip()
    name = re.sub(r'[\x00-\x20\x7f-\xa0\[\](){}<>"\'`!@#$%^&*+=|:;,./?\\~-]+', ' ', name)
    name = re.sub(r'\s+', '_', name)
    name = re.sub(r'_+', '_', name).strip('_')
    return name[:80]

# subject metadata from filters
filters = {}
for fn in ('question_get_archive_filters.json', 'question_get_result_filters.json',
           'question_get_routine_filters.json', 'endpoint_sample_*', 'responses*/*subject*.json'):
    for f in glob.glob(f'{API}/' + fn):
        try:
            d = json.load(open(f))
            subs = d.get('data', {}).get('subjects', [])
            for s in subs:
                filters[s['id']] = {'type': s.get('type'), 'name': s.get('textfield') or s.get('subjects')}
        except Exception:
            pass

exams = collections.defaultdict(list)
def append(exams, r):
    sid = r.get('subject_id')
    if sid is not None:
        exams[sid].append(r)

for line in open(f'{API}/exam_list_canonical.jsonl'):
    append(exams, json.loads(line))
for line in open(f'{API}/routine_list_canonical.jsonl'):
    append(exams, json.loads(line))

def qcount(r):
    return r.get('question_number') or 0

master = []
for sid, rows in sorted(exams.items(), key=lambda kv: -sum(qcount(x) for x in kv[1])):
    meta = filters.get(sid, {})
    rows_sorted = sorted(rows, key=lambda x: x['id'])
    nq = sum(qcount(r) for r in rows_sorted)
    exam_entries = []
    for r in rows_sorted:
        eid = r['id']
        exam_entries.append({
            'exam_id': eid,
            'date': r.get('date_str') or r.get('date'),
            'question_number': qcount(r),
            'is_omr': r.get('is_omr'),
            'slug': r.get('slug'),
            'files': [f'exam_maps/exam_{eid}.json'],   # will exist once per-exam dump completes
        })
    course = {
        'subject_id': sid,
        'name': meta.get('name') or rows_sorted[0].get('subject_name') or sid,
        'slug_or_type': meta.get('type', ''),
        'exams_count': len(rows_sorted),
        'questions_total': nq,
        'exams': exam_entries,
    }
    with open(f'{OUT}/course_{sid}.json', 'w') as f:
        json.dump(course, f, ensure_ascii=False, indent=1)
    course['filename'] = f'course_{sid}_{slugify(course["name"])}.json'
    with open(f'{OUT}/{course["filename"]}', 'w') as f:
        json.dump(course, f, ensure_ascii=False, indent=1)
    os.remove(f'{OUT}/course_{sid}.json')
    master.append({k: course[k] for k in ('subject_id', 'name', 'slug_or_type', 'exams_count', 'questions_total', 'filename')})

with open(f'{OUT}/courses.json', 'w') as f:
    json.dump(master, f, ensure_ascii=False, indent=1)

with open(f'{OUT}/README.md', 'w') as f:
    f.write('# Courses structure\n\n')
    f.write('`courses.json` = master list of all subject/courses.\n')
    f.write('`course_<subject_id>.json` = one course: its exams, and for each exam the questions are at the path in `files[]` (under `api_data/`).\n\n')
    f.write('| subject_id | name | exams | questions |\n|---|---|---|---|\n')
    for c in master:
        f.write(f"| {c['subject_id']} | {c['name']} | {c['exams_count']} | {c['questions_total']} |\n")

print(f'courses written: {len(master)}')
print(f'files: courses.json, README.md, course_*.json x {len(master)}')