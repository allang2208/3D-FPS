"""Summarize the requested component-direction diagnosis; no engine execution."""
from pathlib import Path
import csv, json, hashlib, collections, datetime

ROOT = Path(__file__).resolve().parent
PROJECT = ROOT.parents[1]
OUT = ROOT/'Receipts'
probe = json.loads((OUT/'native-spawn-directions.json').read_text('utf8'))
with (OUT/'per-light-directions.csv').open('w', newline='', encoding='utf-8-sig') as output:
    writer = csv.writer(output)
    writer.writerow(['module', 'index', 'id', 'type', 'room_yaw', 'expected_XYZ', 'legacy_component_XYZ', 'corrected_component_XYZ', 'legacy_error_degrees'])
    for row in probe['rows']:
        writer.writerow([row['module'], row['index'], row['id'], row['type'], row['room_yaw'],
            json.dumps(row['expected']), json.dumps(row['before']), json.dumps(row['after']), row['angle_error_before_deg']])
affected = collections.Counter(r['module'] for r in probe['legacy_bad'] if r['room_yaw'] == 0)
files = [PROJECT/'Source/FPSGAME/Dungeons/AuthoredDungeonGenerator.cpp',
    PROJECT/'Intermediate/Build/Win64/x64/UnrealEditor/Development/FPSGAME/AuthoredDungeonGenerator.cpp.obj',
    PROJECT/'Binaries/Win64/UnrealEditor-FPSGAME.dll']
receipt = dict(stage='direction_fix_compiled', affected_modules=dict(affected), affected_lights=probe['actual_legacy_bad_lights'],
    catalog_lights=probe['light_count'], actual_spawn_cases=len(probe['rows']), engine_version=probe['engine_version'],
    build_log='preview-native-build.log', game_run=False, production_maps_modified_this_fix=False, files=[])
for path in files:
    receipt['files'].append(dict(path=str(path.relative_to(PROJECT)), sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
        modified_utc=datetime.datetime.fromtimestamp(path.stat().st_mtime, datetime.timezone.utc).isoformat()))
(OUT/'build-and-direction-summary.json').write_text(json.dumps(receipt, ensure_ascii=False, indent=2), encoding='utf8')
(OUT/'Render/invalid-export.json').write_text(json.dumps(dict(valid_visual_evidence=False,
    reason='Python render-target export returned identical black images. Use NativeRender with render-thread GPU staging readback.',
    replacement='Receipts/NativeRender/before.png and after.png'), indent=2), encoding='utf8')
print(json.dumps({k:v for k,v in receipt.items() if k!='files'}, ensure_ascii=False))
