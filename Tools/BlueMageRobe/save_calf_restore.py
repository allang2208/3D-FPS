"""Save restored calves in new packages; retain the existing robe cloth assets."""
import json,sys,gc
from pathlib import Path
import unreal as u
P=Path('D:/FPS3D/FPSGAME');R=P/'SourceAssets/BlueMageRobe20261018';F=R/'LegFit20261019';OUT=F/'CalfRestore';OUT.mkdir(exist_ok=True);sys.path.insert(0,str(P/'Tools/BlueMageRobe'))
import save_assets as io
previous=json.loads((F/'saved_assets.json').read_text());io.receipt_path=OUT/'saved_assets.json';io.receipt=json.loads(io.receipt_path.read_text()) if io.receipt_path.exists() else dict(saved={k:v for k,v in previous['saved'].items() if k.startswith('Body/')},underlayers={},collision_pose_bound=previous['collision_pose_bound'],runtime_tested=False)
if '-run=' not in u.SystemLibrary.get_command_line().lower():
    level=u.get_editor_subsystem(u.LevelEditorSubsystem)
    if level and level.is_in_play_in_editor():raise RuntimeError('Finish the current PIE session before saving restored calves')
io.receipt['completed']=False;io.record()
for row in json.loads((F/'authored.json').read_text())['rows']:
    if not row.get('geometry_changed',True):path=row['source']
    elif row['remaining_triangles']:
        io.skeletal(Path(row['authored']),[io.load(p) for p in row['materials']],group='Underlayers');path=io.receipt['saved']['Underlayers/'+row['key']]['asset']
    else:path=''
    io.receipt['underlayers'][row['source']]=path;io.record();gc.collect();u.SystemLibrary.collect_garbage()
io.receipt['completed']=True;io.receipt['leg_fit_revision']='20261019-v3-calves';io.record();print('BLUE_ROBE_CALVES_SAVED',len(io.receipt['underlayers']),'sources',flush=True)
