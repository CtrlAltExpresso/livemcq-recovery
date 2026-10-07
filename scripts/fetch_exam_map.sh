#!/bin/bash
# fetch one exam's questions: exam-view first; if payment-gated/error -> archive-question-subject fallback.
# Validated + atomic write + retries. Output normalized: {"question_text": {...}, "_source": "...", "_exam_id": N}
TOK="YOUR_API_TOKEN"
B="https://livemcq.com/api/v1"
DIR=/home/sakib/offlineMCQ/api_data/exam_maps
mkdir -p "$DIR"
id="$1"
f="$DIR/exam_${id}.json"

valid() { python3 -c "
import json,sys
try:
    d=json.load(open('$1')); qt=d.get('question_text')
    sys.exit(0 if isinstance(qt,dict) and qt else 1)
except Exception: sys.exit(1)
" 2>/dev/null; }

[ -s "$f" ] && valid "$f" && { rm -f "$DIR/error_${id}"; exit 0; }

fetch() { # $1=url -> writes /tmp/opencode/em_$$.json, echoes http code
  curl -sL -m 30 -o "/tmp/opencode/em_$$.json" -w "%{http_code}" \
    -H "Authorization: Token $TOK" -H "accept: application/json" "$1"
}

save_primary() { # raw exam-view body already in /tmp/opencode/em_$$.json
  python3 - "$id" "/tmp/opencode/em_$$.json" "$f.tmp" <<'PY'
import json,sys
i,src,out=sys.argv[1],sys.argv[2],sys.argv[3]
d=json.load(open(src))
qt=d.get('question_text')
if not isinstance(qt,dict) or not qt: sys.exit(1)
d['_source']='exam-view'; d['_exam_id']=int(i)
json.dump(d,open(out,'w'),ensure_ascii=False)
PY
}

save_fallback() { # raw archive-question-subject body -> normalized
  python3 - "$id" "/tmp/opencode/em_$$.json" "$f.tmp" <<'PY'
import json,sys
i,src,out=sys.argv[1],sys.argv[2],sys.argv[3]
d=json.load(open(src))
q=d.get('question')
if not isinstance(q,dict) or not q: sys.exit(1)
out_d={'question_text':q,'_source':'archive-question-subject','_exam_id':int(i),
       'custom_field':d.get('custom_field',''),'exam_time':d.get('exam_time'),
       'is_omr':d.get('is_omr'),'omr_time':d.get('omr_time'),
       'examname':d.get('examname'),'type':d.get('type'),'payment':d.get('payment')}
json.dump(out_d,open(out,'w'),ensure_ascii=False)
PY
}

# permanent NO_CONTENT (already verified) -> skip within existing run? not needed; exit clean
# detect permanently-locked exam right after a validated no-content check below.
if grep -qs NO_CONTENT "$DIR/error_${id}" 2>/dev/null; then exit 0; fi

tries=0
while [ $tries -lt 3 ]; do
  code=$(fetch "$B/exam-view/$id")
  if [ "$code" = "200" ] && save_primary && valid "$f.tmp"; then
    mv "$f.tmp" "$f"; rm -f "$DIR/error_${id}"; exit 0
  fi
  # primary failed -> try fallback immediately (works for payment-gated)
  code2=$(fetch "$B/archive-question-subject/$id")
  if [ "$code2" = "200" ] && save_fallback && valid "$f.tmp"; then
    mv "$f.tmp" "$f"; rm -f "$DIR/error_${id}"; exit 0
  fi
  rm -f "$f.tmp"
  # both returned 200 but unusable -> no-paywall / empty-exam: permanent, don't retry
  if [ "$code" = "200" ] && [ "$code2" = "200" ]; then
    echo "NO_CONTENT (primary+fallback 200, no valid body)" > "$DIR/error_${id}"; exit 0
  fi
  tries=$((tries+1)); sleep $((tries * 30))
done
echo "FAIL:primary=$code,fallback=$code2" > "$DIR/error_${id}"
