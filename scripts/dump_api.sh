#!/bin/bash
# LiveMCQ API bulk dump - authorized under LMCQ-DR-2026-1006
TOK="YOUR_API_TOKEN"
B="https://livemcq.com/api/v1"
OUT=/home/sakib/offlineMCQ/api_data
mkdir -p "$OUT/pages"

fetch() {
  local ep="$1" qs="$2" dest="$3"
  curl -s -m 30 -H "Authorization: Token $TOK" -H "accept: application/json" "$B/$ep${qs:+?$qs}" -o "$dest"
}

# --- small one-shot endpoints ---
mkdir -p "$OUT/one_shot"
for ep in "question/get_archive_filters" "question/get_result_filters" "question/get_routine_filters" \
          "question/get_central_result" "search-question-filter-option" "faculty_service/get_faculty" \
          "profile" "quiz-master-custom-topic-list/0"; do
  safe=$(echo "$ep" | tr '/' '_')
  fetch "$ep" "" "$OUT/one_shot/$safe.json"
  echo "[one-shot] $ep -> $(wc -c < "$OUT/one_shot/$safe.json") bytes"
  sleep 0.3
done

# --- test page_size support ---
curl -s -m 20 -H "Authorization: Token $TOK" -H "accept: application/json" \
  "$B/question/new_get_central_archive?page_size=200&page=1" -o "$OUT/ps_test.json"
PSIZE=$(python3 -c "
import json
try:
    d=json.load(open('$OUT/ps_test.json')); print(len(d['data']['page_data']))
except Exception: print(0)
")
if [ "$PSIZE" -gt 20 ]; then PAGE_SIZE=$PSIZE; else PAGE_SIZE=20; fi
echo "[config] page_size=$PAGE_SIZE"
rm -f "$OUT/ps_test.json"

# --- paginated dumps ---
dump_paginated() {
  local ep="$1"
  local psq=""
  [ "$PAGE_SIZE" -gt 20 ] && psq="page_size=$PAGE_SIZE"
  echo "=== dumping $ep (page_size=$PAGE_SIZE) ==="
  fetch "$ep" "$psq" "$OUT/pages/${ep//\//_}_p1.json"
  local meta
  meta=$(python3 -c "
import json
d=json.load(open('$OUT/pages/${ep//\//_}_p1.json'))['data']
print(d['num_pages'], d['total_items'])
" 2>/dev/null)
  local npages total
  npages=$(echo "$meta" | cut -d' ' -f1); total=$(echo "$meta" | cut -d' ' -f2)
  echo "$ep: $npages pages, $total items"
  if [ -z "$npages" ] || [ "$npages" -lt 1 ]; then echo "SKIP $ep"; return; fi
  local p=2
  while [ "$p" -le "$npages" ]; do
    local qs="page=$p"
    [ -n "$psq" ] && qs="$qs&$psq"
    fetch "$ep" "$qs" "$OUT/pages/${ep//\//_}_p${p}.json"
    if [ $((p % 50)) -eq 0 ]; then echo "  $ep: page $p/$npages"; fi
    p=$((p+1))
    sleep 0.25
  done
  echo "DONE $ep"
}

dump_paginated "question/new_get_central_archive"
dump_paginated "question/new_get_central_routine"

echo "ALL DUMPS COMPLETE"
