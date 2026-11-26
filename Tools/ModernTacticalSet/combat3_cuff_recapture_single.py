"""Refresh blocked single-arm source reads into independent files."""
import json,gc
from pathlib import Path
import unreal as u
P=Path('D:/FPS3D/FPSGAME');C=P/'SourceAssets/ModernTacticalSet20261113/CombatShirtR3/CuffRepairR1'
source=(P/'Tools/ST6SleeveRepair/capture.py').read_text(encoding='utf-8').split('inventory=[];cache={}')[0].replace("R=P/'SourceAssets/ST6SleeveRepair20261018'", "R=C").replace("OUT=R/'Read'", "OUT=R/'ReadSingleRefresh'")
exec(compile(source,'current_single_glove_capture','exec'))
state=json.loads((C/'captured.json').read_text(encoding='utf-8'))
for rig in ['DW715_l','DW715_r','M1911_l','M1911_r']:
    row=next(r for r in state['rows'] if r['key']=='Glove_'+rig);file=read(row['path'],row['key']);data=json.loads(Path(file).read_text(encoding='utf-8'));row['file']=file;row['sha256']=data['asset_sha256'];(C/'captured.json').write_text(json.dumps(state,indent=2),encoding='utf-8');print('SINGLE_NATIVE_GLOVE_REFRESHED',rig,flush=True);gc.collect();u.SystemLibrary.collect_garbage()
