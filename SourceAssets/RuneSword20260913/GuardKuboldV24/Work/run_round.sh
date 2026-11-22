#!/usr/bin/env bash
# Author round: bash Work/run_round.sh <tag> [extra author args]  -> Work/<tag>_{guard,hit,break}.jpg
set -u
cd "$(dirname "$0")/.."
TAG=$1; shift
B="/e/Program Files/Blender Foundation/Blender 5.1/blender.exe"
timeout 2400 "$B" -b --factory-startup --python author_guard_v24.py -- --no-export "$@" > "Work/author_$TAG.log" 2>&1
grep -E "Error|Traceback|SystemExit|unreachable|No reachable" "Work/author_$TAG.log" | head
JSON=authoring_v24.json; BLEND=Work/preview_Standard.blend
if [[ " $* " == *" --long-grip "* ]]; then JSON=authoring_v24_long_grip.json; BLEND=Work/preview_LongGrip.blend; fi
timeout 60 py -3.11 -c "
import json;d=json.load(open('$JSON'));print(d['hold'], d['grip_turn_hold_deg']); print('hit', d['hit_keys']); print('break', d['break_keys'])
for n,c in d['clips'].items(): print(n, {k:v for k,v in c.items() if k!='samples'})"
BL="$(cygpath -w "$PWD/$BLEND")"; OUTD="$(cygpath -w "$PWD/Work/$TAG")"
for A in "A_RuneSword_Guard 10,17,24,31,55,139" "A_RuneSword_GuardHit 7,19,27,43,55,67" "A_RuneSword_GuardBreak 8,20,32,54"; do
  set -- $A
  timeout 900 "$B" -b --factory-startup --python preview_v24.py -- "$BL" "$OUTD" $1 $2 2>&1 | grep -E "PREVIEW_V24|Error|Traceback"
done
timeout 200 py -3.11 compare_v24.py "Work/$TAG" "Work/${TAG}_guard.jpg" A_RuneSword_Guard 6662:10 6666:17 6670:24 6675:31 6684:55 6720:139
timeout 200 py -3.11 compare_v24.py "Work/$TAG" "Work/${TAG}_hit.jpg" A_RuneSword_GuardHit 7062:7 7068:19 7072:27 7080:43 7086:55 7092:67
timeout 200 py -3.11 compare_v24.py "Work/$TAG" "Work/${TAG}_break.jpg" A_RuneSword_GuardBreak 7186:8 7192:20 7198:32 7210:54
