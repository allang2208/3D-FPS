"""Write the initialized-world evidence summary without running the engine."""
from pathlib import Path
import csv, json, hashlib, datetime
ROOT=Path(__file__).resolve().parent
PROJECT=ROOT.parents[1]
OUT=ROOT/'Receipts'
probe=json.loads((OUT/'initialized-game-directions.json').read_text('utf8'))
with (OUT/'per-light-game-directions.csv').open('w',newline='',encoding='utf-8-sig') as output:
    writer=csv.writer(output)
    writer.writerow(['module','index','type','room_yaw','actor_initialized','old_set_transform_accepted',
                     'previous_fix_actual','fixed_set_transform_accepted','corrected_actual','expected'])
    for row in probe['rows']:
        writer.writerow([row[key] for key in ('module','index','type','room_yaw','actor_initialized',
            'old_set_transform_accepted','previous_fix_actual','fixed_set_transform_accepted','corrected_actual','expected')])
files=[PROJECT/'Source/FPSGAME/Dungeons/AuthoredDungeonGenerator.cpp',
    PROJECT/'Intermediate/Build/Win64/x64/UnrealEditor/Development/FPSGAME/AuthoredDungeonGenerator.cpp.obj',
    PROJECT/'Binaries/Win64/UnrealEditor-FPSGAME.dll']
report={k:v for k,v in probe.items() if k!='rows'}
report.update(stage='mobility_order_fixed_and_compiled',build_log='native-build-2.log',files=[])
report.update(hall_render=dict(before='HallRender/before.png',after='HallRender/after.png',
    log='hall-render.log',native_hall_geometry=True,parts=149,lights=23,fixed_exposure=True,
    result='Ceiling direct-light patch reproduced before; absent after mobility-before-transform correction.',
    direct_light_only=True,full_gameplay_run=False))
for path in files:
    report['files'].append(dict(path=str(path.relative_to(PROJECT)),sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
        modified_utc=datetime.datetime.fromtimestamp(path.stat().st_mtime,datetime.timezone.utc).isoformat()))
(OUT/'completion.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf8')
print('SUMMARY_WRITTEN',probe['cases'],'cases; previous wrong',probe['previous_fix_wrong_cases'],'fixed wrong',probe['corrected_wrong_cases'])
