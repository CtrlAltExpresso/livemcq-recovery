#!/bin/bash
# Archive+routine list re-dump v2 (read-only, writes to *_v2 dirs; original pages/ untouched)
TOK="YOUR_API_TOKEN"
B="https://livemcq.com/api/v1"
API=/home/sakib/offlineMCQ/api_data
LOG=/tmp/opencode/dump_v2.log
mkdir -p "$API/pages_v2"

valid_exam() { python3 -c "
import json,sys
try:
    d=json.load(open('$1')); pd=d.get('data',{}).get('page_data'); sys.exit(0 if isinstance(pd,list) and pd else 1)
except Exception: sys.exit(1)
" 2>/dev/null; }

dump() {  # $1=endpoint $2=maxpages $3=prefix
  local ep="$1" max="$2" prefix="$3"
  for p in $(seq 1 "$max"); do
    local f="$API/pages_v2/${prefix}_p${p}.json"
    [ -s "$f" ] && valid_exam "$f" && continue
    local tries=0
    while [ $tries -lt 5 ]; do
      local code
      code=$(curl -sL -m 30 -o "$f.tmp" -w "%{http_code}" -H "Authorization: Token $TOK" -H "accept: application/json" "$B/$ep?page=$p")
      if [ "$code" = "200" ] && valid_exam "$f.tmp"; then mv "$f.tmp" "$f"; break; fi
      rm -f "$f.tmp"; tries=$((tries+1)); sleep $((tries*40))
    done
    [ $((p % 100)) -eq 0 ] && echo "progress: $prefix p$p/$max" >> "$LOG"
    sleep 1.2
  done
}

echo "v2 start $(date)" >> "$LOG"
dump "question/new_get_central_archive" 774 "archive"
echo "archive v2 done $(date)" >> "$LOG"
dump "question/new_get_central_routine" 63 "routine"
echo "V2 DUMPS COMPLETE $(date)" >> "$LOG"
