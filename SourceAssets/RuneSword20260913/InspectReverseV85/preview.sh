#!/usr/bin/env bash
# Author a preview (no FBX) and render review sheets: ./preview.sh <tag> [--long-grip]
set -e
cd "$(dirname "$0")"
B="/e/Program Files/Blender Foundation/Blender 5.1/blender.exe"
TAG=$1; shift || true
VAR=Standard; [ "$1" = "--long-grip" ] && VAR=LongGrip
"$B" -b --factory-startup --python author_inspect_v85.py -- --no-export "$@" > "Work/author_$TAG.log" 2>&1
grep -E "INSPECT_REVERSE_V85_AUTHORED|Error|Traceback" "Work/author_$TAG.log" | cut -c1-1800
cp authoring_v85$([ "$VAR" = LongGrip ] && echo _long_grip).json "Work/authoring_$TAG.json"
BL="$(cygpath -w "$PWD/Work/preview_$VAR.blend")"
FR=$(py -c "import json;print(','.join(sorted({str(round(k['t']*120)) for k in json.load(open('keys_v85.json',encoding='utf-8'))['keys']}|{'44','48','88','96','110'},key=int)))")
"$B" -b --factory-startup --python render_review.py -- "$BL" "$(cygpath -w "$PWD/Work/$TAG")" 4 --frames=$FR > /dev/null 2>&1
"$B" -b --factory-startup --python render_review.py -- "$BL" "$(cygpath -w "$PWD/Work/${TAG}_hand")" 4 --frames=$FR --hand > /dev/null 2>&1
py sheet.py "Work/$TAG" 6 400 "${TAG}_sheet.jpg" 380 0 960 540
py sheet.py "Work/${TAG}_hand" 6 400 "${TAG}_hand_sheet.jpg"
py compare_v85.py "Work/$TAG" "Work/${TAG}_hand" "Work/${TAG}_keys.jpg"
