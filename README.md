<div align="center">

# 📱 LiveMCQ Data Recovery

**The complete content of the LiveMCQ Android app — every exam, every question, every answer,
downloaded and rebuilt from its own live API into a clean, browsable structure.**

**15,429 archive exams** + **1,263 routine entries** + **80,162 questions with answers &
explanations**, organized as **115 courses → exams → questions**, verified with
checksums and cross-checked across independent dump passes.

[![Exams](https://img.shields.io/badge/exams-15%2C429%20%2B%201%2C263-16a34a?style=flat-square)](#-whats-inside)
[![Questions](https://img.shields.io/badge/questions-80%2C162-0f172a?style=flat-square)](#-whats-inside)
[![Courses](https://img.shields.io/badge/courses-115-3b82f6?style=flat-square)](#-course--exam--question)
[![Integrity](https://img.shields.io/badge/integrity-sha256%20verified-64748b?style=flat-square)](#-integrity)

</div>

---

## 🎯 What is this?

The LiveMCQ app (Bangladeshi BCS / Bank / Government-job MCQ test platform) was built behind a
growing collection of exams and questions that were at risk of being lost. With the app owner's
authorization (see [`authorization/`](authorization/)), everything the app serves was pulled
from its live API and re-organized into a structure that mirrors what the app shows:

```
app:   Course (subject)  →  Exam  →  Questions
repo:  courses/<name>.json → exam_maps/exam_<id>.json
```

This is a full job: every page, every exam, every question — nothing sampled, nothing skipped.
Paid/"payment-gated" exams are included too (fetched through the app's alternate endpoint).

## 📊 What's inside

| Asset | Count | Location |
|---|---|---|
| Courses (subjects) | 115 | [`api_data/courses/`](api_data/courses/) — one readable-named file each |
| Archive exams | 15,429 | [`api_data/exam_list_canonical.jsonl`](api_data/exam_list_canonical.jsonl) |
| Routine exams | 1,263 | [`api_data/routine_list_canonical.jsonl`](api_data/routine_list_canonical.jsonl) |
| Questions (master bank) | 80,162 | [`api_data/question_bank_chunks/`](api_data/question_bank_chunks/) |
| Per-exam question maps | 16,167 | [`api_data/exam_maps/`](api_data/exam_maps/) |
| App artifacts (APKs + original data) | — | [`extracted/`](extracted/) |
| Discovery/verification | — | [`docs/`](docs/), [`scripts/`](scripts/), `MANIFEST.tsv` |

## 🧭 Course → Exam → Question

All 115 courses are named files — [`api_data/courses/`](api_data/courses/). Example:

```
api_data/courses/১৪০_দিনে_৫২তম_বিসিএস_প্রস্তুতি.json
```

Each course file lists every exam in it (`exam_id`, date, question count). Click the exam's
`files` path to open `api_data/exam_maps/exam_<id>.json` — the full exam: every question,
its 4–5 options, the correct answer, and the explanation.

The master question bank is split into 3 line-safe JSONL chunks (each individually valid,
self-contained), because the merged file (106 MB) exceeds GitHub's 100 MB per-file limit:
`cat question_bank.aa question_bank.ab question_bank.ac > all_questions.jsonl`.

## 🔒 Integrity

- **`api_data/MANIFEST.tsv`** — sha256 + record count for every single dumped file (2,493 files)
- **`api_data/INDEX.md`** — human-readable inventory of the whole dump
- Exam lists were dumped **3 independent times** and union-verified — cross-pass agreement
  proved the set is complete (the API itself returns ~40 duplicate *rows* from an unstable
  join; true distinct count was established and canonicalized)
- Every exam map is validated (must parse as JSON with a non-empty question set) before it
  counts; corrupted/partial files are never kept

## 📂 Quick start

```bash
# browse courses (names in Bangla)
ls api_data/courses/

# open a course, see its exams
jq '.name, .exams_count' api_data/courses/ডেইলি_কুইজ_২০০_দিন.json

# read one exam's questions
jq '.question_text' api_data/exam_maps/exam_1.json | head -40

# reassemble the master question bank
cat api_data/question_bank_chunks/question_bank.* > /tmp/all_questions.jsonl

# verify a file against the manifest
cd api_data && sed -n '2p' MANIFEST.tsv
```

## 📦 Status

| Step | State |
|---|---|
| Authorization | ✅ 2026-10-06 (LMCQ-DR-2026-1006, valid through 2026-12-31) |
| App extraction (APK + original data) | ✅ |
| Exam lists (3-pass verified) | ✅ 15,429 + 1,263 |
| Question bank | ✅ 80,162 |
| Per-exam maps | ✅ 16,167 (525 exams are permanently empty/locked in the API) |
| Media (images / PDFs / videos) | ✅ images + study PDFs (local, manifest committed) |

**About the 525:** 16,692 `exam-view`/`archive-question-subject` fetches were attempted.
525 (3.1%) return an empty question set in the API itself (payment-locked at database
level) — the same view a non-owner account sees in the app. The remaining 16,167 all
fetch valid question sets. These 525 exams still appear in their course files
(`exam_maps` entry shows no `files`); a future owner-level account/server dump can
fill them in.

## 🛠 Background

- **App package:** `com.livemcq.livemcq` (Flutter). Data pulled from `https://livemcq.com/api/v1`.
- **Full methodology:** see [`docs/RETRIEVAL_PROCESS.md`](docs/RETRIEVAL_PROCESS.md).
- **Raw endpoint inventory:** see [`docs/API_ENDPOINTS.md`](docs/API_ENDPOINTS.md).
- **Scripts (documented):** see [`scripts/README.md`](scripts/README.md).
- **Authorization:** [`authorization/LiveMCQ_Data_Recovery_Authorization.pdf`](authorization/LiveMCQ_Data_Recovery_Authorization.pdf)

---

<div align="center">

*Recovered with the explicit, signed authorization of the LiveMCQ app owner (Ref: LMCQ-DR-2026-1006).*

</div>