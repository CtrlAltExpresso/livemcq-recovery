# LiveMCQ Data Recovery

Recovered data for the LiveMCQ Android app, authorized by owner Nabil Rahman
(authorization: `authorization/LiveMCQ_Data_Recovery_Authorization.pdf`, LMCQ-DR-2026-1006).

## What's here

| Folder | Contents |
|---|---|
| `authorization/` | Signed authorization letter (txt/html/pdf) |
| `docs/` | Progress reports |
| `scripts/` | Dump + verification scripts |
| `extracted/` | Original app artifacts: APKs, extracted app data (Isar DB, prefs) from Waydroid |
| `api_data/exams/` | Canonical exam lists (archive 15,429; routine 1,263) |
| `api_data/exam_maps/` | One JSON file per exam: full questions + answers + explanations |
| `api_data/questions/pages/` | Raw question-bank pages (source of truth) |
| `api_data/question_bank_chunks/` | Merged question bank, 80,162 Q&A, split into 3 valid JSONL chunks |
| `api_data/endpoint_*.tsv` | Endpoint discovery results |
| `passes/` → (renamed dirs) | Dump passes used for cross-verification |

## Integrity

- `api_data/MANIFEST.tsv` — sha256 + record counts for every dumped file
- `api_data/INDEX.md` — human-readable inventory
- Question bank reassembly: `cat question_bank.aa question_bank.ab question_bank.ac > all_questions.jsonl`

## Notes

- One global token (`Token 590c6d...`) is embedded in the scripts; enabled by the
  authorization above.
- `all_questions.jsonl` (106 MB, > GitHub 100 MB limit) lives locally only; the
  three chunk files above are its git-hosted equivalent.
- Media (PDFs/images/videos) not yet downloaded — planned next.