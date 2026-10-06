#!/bin/bash
# LiveMCQ API dump v2 - resume-aware, rate-limit safe (auth: LMCQ-DR-2026-1006)
TOK="YOUR_API_TOKEN"
B="https://livemcq.com/api/v1"
OUT=/home/sakib/offlineMCQ/api_data
mkdir -p "$OUT/pages" "$OUT/one_shot"

valid() {
  [ -s "$1" ] && python3 -c "
import json,sys
try:
    d=json.load(open('$1')); sys.exit(0 if isinstance(d,dict) and 'data' in d else 1)
except Exception: sys.exit(1)
"
}

fetch_retry() {  # $1=url $2=dest ; retries on 403 with backoff
  local url="$1" dest="$2" attempt=1 code
  while [ "$attempt" -le 4 ]; do
    code=$(curl -s -m 30 -o "$dest" -w "%{http_code}" -H "Authorization: Token $TOK" -H "accept: application/json" "$url")
    if [ "$code" = "200" ] && valid "$dest"; then return 0; fi
    echo "  retry($attempt) $code -> sleep 60 ($url)"
    sleep 60
    attempt=$((attempt+1))
  done
  return 1
}

dump_paginated() {
  local ep="$1" name="${1//\//_}"
  # page 1 for metadata
  if ! valid "$OUT/pages/${name}_p1.json"; then
    fetch_retry "$B/$ep" "$OUT/pages/${name}_p1.json" || { echo "FAIL $ep p1"; return 1; }
  fi
  local npages
  npages=$(python3 -c "import json; print(json.load(open('$OUT/pages/${name}_p1.json'))['data']['num_pages'])")
  echo "=== $ep : $npages pages ==="
  local p=1 ok=0 miss=0
  while [ "$p" -le "$npages" ]; do
    local f="$OUT/pages/${name}_p${p}.json"
    if valid "$f"; then ok=$((ok+1)); else
      if fetch_retry "$B/$ep?page=$p" "$f"; then ok=$((ok+1)); else miss=$((miss+1)); echo "MISS p$p"; fi
      sleep 1.2
    fi
    [ $((p % 100)) -eq 0 ] && echo "  progress: p$p/$npages (cached+new ok=$ok miss=$miss)"
    p=$((p+1))
  done
  echo "DONE $ep: ok=$ok miss=$miss"
}

dump_paginated "question/new_get_central_archive"
dump_paginated "question/new_get_central_routine"

# one-shot endpoints (follow redirects for 301s)
for ep in "question/get_archive_filters" "question/get_result_filters" "question/get_routine_filters" \
          "question/get_central_result" "search-question-filter-option/" "faculty_service/get_faculty" \
          "profile/" "quiz-master-custom-topic-list/0/" "quiz_game/leaderboard" "smart-tutor/get_dashboard/" \
          "smart-tutor/welcome_to_athena/" "bookstore/book-list-new/"; do
  safe=$(echo "$ep" | tr '/' '_')
  dest="$OUT/one_shot/${safe}.json"
  if ! valid "$dest"; then
    code=$(curl -sL -m 20 -o "$dest" -w "%{http_code}" -H "Authorization: Token $TOK" -H "accept: application/json" "$B/$ep")
    echo "[one-shot] $ep -> $code ($(wc -c < "$dest") b)"
    sleep 1.2
  fi
done

echo "ALL DUMPS COMPLETE"
