"""Requested source-pose audit of the shared lower-body movement families."""
import json,gc,hashlib
from pathlib import Path
import unreal as u
P=Path('D:/FPS3D/FPSGAME');OUT=P/'SourceAssets/BlueMageSetAudit20261019';OUT.mkdir(parents=True,exist_ok=True)
cfg=json.loads((P/'Content/ColdSteelData/player_body.json').read_text(encoding='utf-8-sig'));mesh=u.load_asset(cfg['body_mesh'])
names=[str(n) for n in u.AnimPoseExtensions.get_bone_names(mesh.skeleton.get_reference_pose()) if str(n) in ('root','pelvis') or str(n).startswith(('thigh','calf','foot','ball','ankle','bigtoe','indextoe','middletoe','ringtoe','littletoe'))]
def pack(t):
    p,q,s=t.translation,t.rotation,t.scale3d
    return dict(p=[p.x,p.y,p.z],q=[q.x,q.y,q.z,q.w],s=[s.x,s.y,s.z])
def bones(pose):return {n:pack(u.AnimPoseExtensions.get_bone_pose(pose,n,u.AnimPoseSpaces.WORLD)) for n in names}
opts=u.AnimPoseEvaluationOptions();opts.optional_skeletal_mesh=mesh
report=dict(body=mesh.get_path_name(),reference=bones(mesh.skeleton.get_reference_pose()),clips={},runtime_tested=False)
for key,path in cfg['clips'].items():
    if not ('.Walk.' in key or '.Jog.' in key or key in ('Unarmed.Idle','Rifle.Idle','Pistol.Idle','Crouch.Idle','Warhammer.Idle','Warhammer.FullBody.Carry','Warhammer.FullBody.SprintCarry','Bow.Sparrow.Carry','Staff.NativeArm.Carry')):continue
    clip=u.load_asset(path)
    if not clip:raise RuntimeError('Missing routed movement clip '+key)
    length=clip.get_play_length();report['clips'][key]=dict(path=path,length=length,samples=[dict(t=length*i/16,bones=bones(u.AnimPoseExtensions.get_anim_pose_at_time(clip,length*i/16,opts))) for i in range(17)])
    disk=P/'Content'/(path[6:].split('.')[0]+'.uasset');report['clips'][key]['asset_sha256']=hashlib.sha256(disk.read_bytes()).hexdigest()
    print('ROBE_MOVEMENT_SOURCE',key,flush=True)
    gc.collect()
(OUT/'source-movement-poses.json').write_text(json.dumps(report,separators=(',',':')),encoding='utf-8')
print('ROBE_MOVEMENT_SOURCES_SAVED',len(report['clips']),flush=True)

import runpy
runpy.run_path(str(P/'Tools/BlueMageAudit/capture_lower.py'),run_name='__main__')
