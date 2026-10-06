#!/bin/bash
# LiveMCQ question bank dump (authorized LMCQ-DR-2026-1006) - question-by-tag global feed
TOK="YOUR_API_TOKEN"
B="https://livemcq.com/api/v1"
DIR=/home/sakib/offlineMCQ/api_data/questions
LOG=/tmp/opencode/dump_questions.log
mkdir -p "$DIR"
cd "$DIR" || exit 1

valid() { python3 -c "
import json,sys
try:
    d=json.load(open('$1')); qs=d.get('questions'); sys.exit(0 if isinstance(qs,list) and qs else 1)
except Exception: sys.exit(1)
" 2>/dev/null; }

for p in $(seq 1 1604); do
  f=$(printf "page_%04d.json" "$p")
  [ -s "$f" ] && valid "$f" && continue
  tries=0
  while [ $tries -lt 5 ]; do
    code=$(curl -sL -m 30 -o "$f.tmp" -w "%{http_code}" \
      -H "Authorization: Token $TOK" -H "accept: application/json" \
      "$B/question-by-tag/1/?page=$p")
    if [ "$code" = "200" ] && valid "$f.tmp"; then
      mv "$f.tmp" "$f"
      break
    fi
    rm -f "$f.tmp"
    tries=$((tries+1))
    [ $((p % 100)) -eq 0 ] && echo "  retry($tries) p$p code=$code" >> "$LOG"
    sleep $((tries * 45))
  done
  [ $((p % 50)) -eq 0 ] && echo "progress: p$p/1604 ok=$(ls page_*.json 2>/dev/null | wc -l)" >> "$LOG"
  sleep 1.2
done

miss=0
for p in $(seq 1 1604); do
  f=$(printf "page_%04d.json" "$p")
  valid "$f" || { miss=$((miss+1)); echo "MISS p$p" >> "$LOG"; }
done
echo "QUESTIONS DUMP COMPLETE: ok=$((1604-miss)) miss=$miss" >> "$LOG"
