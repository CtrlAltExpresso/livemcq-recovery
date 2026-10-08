#!/usr/bin/env bash
# Watchdog: keep download_media.py going until the download list is exhausted.
# Uses a pidfile (no pgrep self-match issues). Restarts when the process dies
# or the progress row-count stalls >5 min. Resume-aware.
set -u
LIST=/home/sakib/offlineMCQ/api_data/media_download_list.tsv
PROG=/home/sakib/offlineMCQ/media_progress.tsv
RUN=/home/sakib/offlineMCQ/scripts/download_media.py
PIDF=/home/sakib/offlineMCQ/.media_downloader.pid
WLOG=/home/sakib/offlineMCQ/.media_run.log
TOTAL=$(wc -l < "$LIST")
alive(){ [ -f "$PIDF" ] && kill -0 "$(cat "$PIDF")" 2>/dev/null; }
start(){ setsid nohup python3 "$RUN" --workers 24 > "$WLOG" 2>&1 < /dev/null & echo $! > "$PIDF"; }

log(){ echo "[$(date +%T)] $*"; }

while :; do
  done_rows=$(cut -f2 "$PROG" 2>/dev/null | sort -u | wc -l)
  if [ "$done_rows" -ge "$TOTAL" ]; then
    log "complete: $done_rows/$TOTAL unique URLs covered"; break
  fi
  if alive; then
    prev=$done_rows; sleep 300
    cur=$(cut -f2 "$PROG" 2>/dev/null | sort -u | wc -l)
    log "unique $prev -> $cur (target $TOTAL)"
    if [ "$cur" -le "$prev" ]; then
      log "stalled; killing and restarting"
      kill -9 "$(cat "$PIDF")" 2>/dev/null; rm -f "$PIDF"; sleep 2
      continue
    fi
    continue
  fi
  log "downloader not running; starting"
  start
  sleep 20
done
if alive; then log "watchdog exiting (downloader may still be retrying failures)"; fi
log "watchdog exiting"