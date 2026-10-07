#!/usr/bin/env bash
# Dump get-video-list/<subject_id> for every subject, paced to stay under the API rate limit.
TOKEN="Token YOUR_API_TOKEN"
B="https://livemcq.com/api/v1"
OUT=/home/sakib/offlineMCQ/api_data/video_catalog
mkdir -p "$OUT"
FAIL=0; OK=0
while read -r id title; do
  [ -z "$id" ] && continue
  code=$(curl -sL -o "$OUT/video_$id.json" -w "%{http_code}" -H "Authorization: $TOKEN" "$B/get-video-list/$id")
  if [ "$code" = "200" ]; then
    # validate it's JSON & non-empty
    if python3 -c "import json,sys; d=json.load(open('$OUT/video_$id.json')); sys.exit(0 if isinstance(d,dict) else 1)"; then
      OK=$((OK+1))
    else
      rm -f "$OUT/video_$id.json"; FAIL=$((FAIL+1)); echo "bad-200 $id"
    fi
  else
    rm -f "$OUT/video_$id.json"; FAIL=$((FAIL+1)); echo "FAIL $id $code"
  fi
  sleep 2.2
done < <(python3 -c "
import json
d=json.load(open('/home/sakib/offlineMCQ/api_data/endpoints/videoseries-subject-list.json'))
for v in d['videos']: print(v['id'], v['type'])
")
echo "video catalog done: ok=$OK fail=$FAIL"