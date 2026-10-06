# LiveMCQ API endpoint inventory

Discovered from `https://livemcq.com/api/v1` (authorization: LMCQ-DR-2026-1006).

_Primary content endpoints used for the dumps are listed below this table._

| Endpoint | Status | Bytes | Allowed methods |
|---|---|---|---|
| `quiz-master-custom-quiz` | 000 | 8948 | — |
| `search-question-filter-option` | 000 | 8948 | — |
| `verified-otp-for-fraud-detection` | 000 | 747 | — |
| `award-mania-home` | 200 | 222073 | `GET, HEAD, OPTIONS` |
| `central-favorite-list` | 200 | 5263 | `GET, HEAD, OPTIONS` |
| `confusion-series-list` | 200 | 20726 | `GET, HEAD, OPTIONS` |
| `customization-mysection-view` | 200 | 16811 | `GET, HEAD, OPTIONS` |
| `dynamic-panel-subject-list` | 200 | 8463 | `GET, HEAD, OPTIONS` |
| `faculty_service/get_faculty` | 200 | 4760 | `GET, HEAD, OPTIONS` |
| `lecture-sheet-subject-list-new-version` | 200 | 4703 | `GET, HEAD, OPTIONS` |
| `live-video-list` | 200 | 22 | `GET, HEAD, OPTIONS` |
| `live-video-routine` | 200 | 52681 | `GET, HEAD, OPTIONS` |
| `mysection-home` | 200 | 452 | `GET, HEAD, OPTIONS` |
| `omr-instruction-view` | 200 | 165 | `GET, HEAD, OPTIONS` |
| `profile-package-history` | 200 | 422 | `GET, HEAD, OPTIONS` |
| `profile-update` | 200 | 664 | `GET, PUT, HEAD, OPTIONS` |
| `quiz-master-custom-topic-list/0` | 200 | 3946 | `GET, HEAD, OPTIONS` |
| `quiz-master-regular-quiz` | 200 | 35503 | `GET, HEAD, OPTIONS` |
| `recent-lecture-sheet-list` | 200 | 16400 | `GET, HEAD, OPTIONS` |
| `referral-home` | 200 | 179 | `GET, HEAD, OPTIONS` |
| `subject-wise-package-info` | 200 | 15410 | `GET, HEAD, OPTIONS` |
| `suggest-question-v2` | 200 | 1170 | `GET, HEAD, OPTIONS` |
| `user-packages-with-discount` | 200 | 73720 | `GET, HEAD, OPTIONS` |
| `vedio-subject-mapping` | 200 | 747 | `GET, HEAD, OPTIONS` |
| `video-mentor-list` | 200 | 5786 | `GET, HEAD, OPTIONS` |
| `videoseries-subject-list` | 200 | 8882 | `GET, HEAD, OPTIONS` |
| `user-question-multiple-records` | 301 | 73720 | — |
| `add-or-remove-mysection-subject` | 405 | 40 | `POST, OPTIONS` |
| `apple-payment-create-view` | 405 | 40 | `POST, OPTIONS` |
| `bulk-subject-add-or-remove-mysection` | 405 | 40 | `POST, OPTIONS` |
| `create-bkash-payment` | 405 | 40 | `POST, OPTIONS` |
| `demo-package-enable` | 405 | 40 | `POST, OPTIONS` |
| `favourite-questions-bulk-create` | 405 | 40 | `POST, OPTIONS` |
| `favourite-questions-bulk-remove` | 405 | 40 | `DELETE, OPTIONS` |
| `multiple-to-single-user-phone` | 405 | 40 | `POST, OPTIONS` |
| `payment-create-view` | 405 | 40 | `POST, OPTIONS` |
| `pole-submit` | 405 | 40 | `POST, OPTIONS` |
| `profile-image-upload` | 405 | 40 | `POST, OPTIONS` |
| `question-read-bulk-update` | 405 | 40 | `POST, OPTIONS` |
| `referral-withdraw` | 405 | 40 | `POST, OPTIONS` |
| `send-otp-for-fraud-detection` | 405 | 40 | `POST, OPTIONS` |
| `send-otp-new` | 405 | 40 | `POST, OPTIONS` |
| `user-fav-question-count-by-tag` | 405 | 40 | `OPTIONS, POST` |
| `user-question-multiple-records/0` | 405 | 40 | `OPTIONS, DELETE` |
| `user-question-records-count-by-tag` | 405 | 40 | `POST, OPTIONS` |
| `validate-otp-new` | 405 | 40 | `POST, OPTIONS` |
| `multiple-tag-quiz` | 500 | 145 | — |
| `search-question-v2` | 500 | 145 | — |
| `user-question-records` | 502 | 150 | — |

## Core content endpoints (used for the dumps)

| Endpoint | Where used |
|---|---|
| `question/new_get_central_archive?page=N` | archive exam list (774 pages, 15,429 distinct exams) |
| `question/new_get_central_routine?page=N` | routine list (63 pages, 1,263 exams) |
| `question-by-tag/1/?page=N` | master question bank (1,604 pages, 80,162 questions) |
| `exam-view/<id>` | per-exam questions (payment-gated for some exams) |
| `archive-question-subject/<id>` | per-exam questions fallback (no payment check; same content verified) |

## Notes

- `500/502/504` endpoints exist server-side but error without the right parameters.
- `000` entries are unreliable connection captures (rate-limit/upstream); re-tried individually in `responses3/`.
