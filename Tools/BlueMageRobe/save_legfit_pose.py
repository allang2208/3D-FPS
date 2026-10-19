"""Keep the moving collision bones in the robe CopyPose required-bone set."""
import json,sys,gc
from pathlib import Path
import unreal as u
P=Path('D:/FPS3D/FPSGAME');F=P/'SourceAssets/BlueMageRobe20261018/LegFit20261019';sys.path.insert(0,str(P/'Tools/BlueMageRobe'))
import save_assets as io
file=F/'saved_assets.json';receipt=json.loads(file.read_text())
if not receipt.get('completed'):raise RuntimeError('Save the constructed robe assets first')
if '-run=' not in u.SystemLibrary.get_command_line().lower():
    level=u.get_editor_subsystem(u.LevelEditorSubsystem)
    if level and level.is_in_play_in_editor():raise RuntimeError('Preserve clothing during PIE')
for key,row in receipt['saved'].items():
    if not key.startswith('Body/'):continue
    mesh=io.load(row['asset']);io.cloth_pose_physics(mesh);io.save(mesh);row['collision_pose_physics']=mesh.get_editor_property('physics_asset').get_path_name();file.write_text(json.dumps(receipt,indent=2),encoding='utf-8');print('ROBE_COLLISION_POSE_BOUND',key,flush=True);del mesh;gc.collect();u.SystemLibrary.collect_garbage()
receipt['collision_pose_bound']=True;file.write_text(json.dumps(receipt,indent=2),encoding='utf-8');print('ROBE_COLLISION_POSE_SAVED',flush=True)
