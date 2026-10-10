#!/bin/bash
# Retry the exams that previously returned NO_CONTENT (empty question_text).
# These are exams the site has NOT published yet (future dates, is_exam_enable=false
# at scrape time). When the site enables them, this script picks them up.
#
# Usage: scripts/retry_exam_maps.sh            # retry every error_* once
#        scripts/retry_exam_maps.sh 17261 5507 # retry specific ids
#
# Run it periodically (e.g. weekly cron) to absorb newly-enabled exams.
LOG=/tmp/opencode/retry_exam_maps.log
API=/home/sakib/offlineMCQ/api_data
DIR="$API/exam_maps"
SCRIPT=/home/sakib/offlineMCQ/scripts/fetch_exam_map.sh

ids=("$@")
if [ ${#ids[@]} -eq 0 ]; then
  ids=($(ls "$DIR"/error_* 2>/dev/null | sed -E 's#.*/error_([0-9]+)#\1#'))
fi
echo "RETRY START $(date) n=${#ids[@]}" >> "$LOG"

for id in "${ids[@]}"; do
  # drop the NO_CONTENT marker so fetch_exam_map.sh re-attempts the API
  rm -f "$DIR/error_${id}"
  bash "$SCRIPT" "$id" 2>>"$LOG"
done

ok=$(ls "$DIR"/exam_*.json 2>/dev/null | wc -l)
err=$(ls "$DIR"/error_* 2>/dev/null | wc -l)
echo "RETRY DONE $(date) ok=$ok err=$err" >> "$LOG"