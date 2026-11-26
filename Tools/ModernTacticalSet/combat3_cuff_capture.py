"""Capture current native sources, bounded to six new meshes per asset batch."""
import ast,json,hashlib,gc
from pathlib import Path
import unreal as u
P=Path('D:/FPS3D/FPSGAME');C=P/'SourceAssets/ModernTacticalSet20261113/CombatShirtR3/CuffRepairR1'
source=(P/'Tools/ST6SleeveRepair/capture.py').read_text(encoding='utf-8').split('inventory=[];cache={}')[0].replace("R=P/'SourceAssets/ST6SleeveRepair20261018'", "R=C")
exec(compile(source,'native_cuff_capture','exec'))
plan=json.loads((C/'capture-plan.json').read_text(encoding='utf-8'));state=json.loads((C/'captured.json').read_text(encoding='utf-8')) if (C/'captured.json').exists() else dict(completed=False,rows=[]);records={r['key']:r for r in state['rows']};count=0
for row in plan['rows']:
    disk=P/'Content'/(row['path'].split('.')[0].removeprefix('/Game/')+'.uasset');sha=hashlib.sha256(disk.read_bytes()).hexdigest()
    if records.get(row['key'],{}).get('sha256')==sha:continue
    file=read(row['path'],row['key']);records[row['key']]=dict(**row,file=file,sha256=sha);count+=1;(C/'captured.json').write_text(json.dumps(dict(completed=False,rows=list(records.values())),indent=2),encoding='utf-8');gc.collect();u.SystemLibrary.collect_garbage()
    if count>=6:break
(C/'captured.json').write_text(json.dumps(dict(completed=len(records)==len(plan['rows']),rows=list(records.values())),indent=2),encoding='utf-8');print('CUFF_NATIVE_CAPTURE_BATCH',len(records),len(plan['rows']),flush=True)
