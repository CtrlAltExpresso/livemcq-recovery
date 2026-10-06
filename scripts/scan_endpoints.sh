#!/bin/bash
# LiveMCQ endpoint scanner (authorized LMCQ-DR-2026-1006) - run AFTER dumps
TOK="YOUR_API_TOKEN"
B="https://livemcq.com/api/v1"
OUT=/home/sakib/offlineMCQ/api_data
REPORT="$OUT/endpoint_report3.tsv"
SAVEDIR="$OUT/responses3"
mkdir -p "$SAVEDIR"
: > "$REPORT"

valid_json() { python3 -c "
import json,sys
try:
    d=json.load(open('$1')); sys.exit(0 if isinstance(d,dict) else 1)
except Exception: sys.exit(1)
" 2>/dev/null; }

probe() {
  local ep="$1" code allow size
  # as-is (normalize: strip trailing slash first)
  local base="${ep%/}"
  code=$(curl -s -m 15 -D /tmp/opencode/h.txt -o /tmp/opencode/b.txt -w "%{http_code}" \
    -H "Authorization: Token $TOK" -H "accept: application/json" "$B/$base")
  if [ "$code" = "404" ]; then
    code=$(curl -s -m 15 -D /tmp/opencode/h.txt -o /tmp/opencode/b.txt -w "%{http_code}" \
      -H "Authorization: Token $TOK" -H "accept: application/json" "$B/$base/")
    [ "$code" != "404" ] && base="$base/"
  fi
  if [ "$code" != "404" ]; then
    size=$(wc -c < /tmp/opencode/b.txt)
    allow=$(grep -i "^allow:" /tmp/opencode/h.txt | tr -d '\r' | cut -d' ' -f2-)
    printf "%s\t%s\t%s\t%s\n" "$base" "$code" "$size" "${allow:-}" >> "$REPORT"
    if [ "$code" = "200" ] && valid_json /tmp/opencode/b.txt; then
      cp /tmp/opencode/b.txt "$SAVEDIR/$(echo "$base" | tr '/' '_').json"
      echo "200 $base ($size b)"
    elif [ "$code" != "200" ]; then
      echo "$code $base ${allow:+allow=$allow}"
    fi
  fi
  sleep 0.7
}

while IFS= read -r ep; do
  [ -z "$ep" ] && continue
  probe "$ep"
done < /tmp/opencode/scan_final.txt

echo "=== SCAN DONE ==="
sort -t$'\t' -k2,2 "$REPORT" | awk -F'\t' '{printf "%-50s %s %8s %s\n", $1, $2, $3, $4}'
