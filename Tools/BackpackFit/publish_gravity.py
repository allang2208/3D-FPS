"""Attach cargo-only support bounds and calibrated gravity to the saved current fits."""
import json,os,runpy
from pathlib import Path
import numpy as np
from scipy.spatial.transform import Rotation
P=Path('D:/FPS3D/FPSGAME');R=Path(os.environ['BACKPACK_FIT_RUN_DIR'])
read=lambda p:json.loads(p.read_text(encoding='utf-8-sig'))
authored=read(R/'authored.json');saved=read(R/'saved_assets.json');captured=read(R/'captured.json')
if not saved.get('completed'):raise RuntimeError('Complete asset save before gravity publication')
path=P/'Content/ColdSteelData/player_body.json';raw=path.read_bytes();body=json.loads(raw.decode('utf-8-sig'));owned=[]
calibration={'ue_portable_backpack':.4,'ue_mountain_backpack':.45,'ue_expedition_backpack':.6,'ue_pathfinder_backpack':.55,'ue_farreach_backpack':.5,'ue_special_duty_backpack':.45}
for row in authored['rows']:
    if row['item'] not in calibration:continue
    prefix=() if row['rig']=='Jason' else ('body_variants','kaitlin')
    config=body if not prefix else body['body_variants']['kaitlin'];outfit=config['outfits'][row['item']]
    actual=outfit.get('world_mesh_by_shirt',{}).get(row['shirt']) if row['shirt'] else outfit['world_mesh']
    if actual!=saved['meshes'][row['asset']]['asset']:raise RuntimeError('Preserve newer harness recipe '+actual)
    if row.get('rigid_mesh'):
        static=next(s for s in authored['statics'] if row['rigid_mesh'].split('.')[0]==s['asset'])
        v=np.fromfile(static['positions'],dtype='<f4').reshape(-1,3).astype(float)
        v=v@Rotation.from_quat(row['rigid_rotation_quat']).as_matrix().T+row['rigid_location']
    else:
        v=np.fromfile(row['positions'],dtype='<f4').reshape(-1,3)
        cargo=np.fromfile(captured[row['source']]['cargo_vertices'],dtype='u1');v=v[cargo>0]
    support={'pivot':row['motion_pivot'],'bounds_min':v.min(0).tolist(),'bounds_max':v.max(0).tolist()};row['support']=support
    root=prefix+('outfits',row['item'],'backpack_motion');motion=outfit['backpack_motion']
    if row['shirt']:motion.setdefault('support_by_shirt',{})[row['shirt']]=support;owned.append(root+('support_by_shirt',row['shirt']))
    else:motion['support']=support;owned.append(root+('support',))
    motion['gravity_sag_cm']=calibration[row['item']];motion['max_separation_cm']=.75 if row['item'] in ['ue_portable_backpack','ue_mountain_backpack'] else .65
    owned.extend([root+('gravity_sag_cm',),root+('max_separation_cm',)])
writer=runpy.run_path(str(P/'Tools/PlayerBody/config_transaction.py'));receipt=writer['commit'](path,raw,body,owned_paths=owned,producer=__file__)
(R/'authored.json').write_text(json.dumps(authored,indent=2));(R/'gravity_published.json').write_text(json.dumps({'config_receipt':receipt,'double_shoulder_profiles':len(authored['rows']),'slings_preserved':True},indent=2))
print('BACKPACK_GRAVITY_PUBLISHED',len(authored['rows']))
