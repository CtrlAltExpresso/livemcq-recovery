#!/bin/bash
# Orchestrator: feeds all exam ids to fetch_exam_map.sh with 3 workers.
LOG=/tmp/opencode/dump_exammap.log
API=/home/sakib/offlineMCQ/api_data
SCRIPT=/home/sakib/offlineMCQ/scripts/fetch_exam_map.sh

{
  python3 -c "
import json
ids=set()
for f in ('$API/exam_list_canonical.jsonl','$API/routine_list_canonical.jsonl'):
    for line in open(f): ids.add(json.loads(line)['id'])
print('\n'.join(str(i) for i in sorted(ids)))
"
} > /tmp/opencode/all_exam_ids.txt

total=$(wc -l < /tmp/opencode/all_exam_ids.txt)
echo "START $(date) total=$total" >> "$LOG"

xargs -a /tmp/opencode/all_exam_ids.txt -n1 -P3 -I{} bash "$SCRIPT" {} 2>>"$LOG"

done_n=$(ls "$API"/exam_maps/exam_*.json 2>/dev/null | wc -l)
err_n=$(ls "$API"/exam_maps/error_* 2>/dev/null | wc -l)
echo "EXAMMAP COMPLETE $(date) ok=$done_n err=$err_n total=$total" >> "$LOG"
