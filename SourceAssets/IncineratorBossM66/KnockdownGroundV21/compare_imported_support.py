"""Skin the current source surface using saved UE compressed poses; no game run."""
from pathlib import Path
import bpy,json,numpy as np
from mathutils import Quaternion
ROOT=Path(__file__).resolve().parent;BASE=ROOT.parent
old=json.loads((ROOT/'Records/active-assets.json').read_text('utf-8'))
new=json.loads((ROOT/'Records/import.json').read_text('utf-8'))
bpy.ops.wm.open_mainfile(filepath=str(BASE/'FurnaceBreathV17/Authoring/M66_furnace_breath_v17.blend'))
rig=bpy.data.objects['M66_Rig'];mesh=bpy.data.objects['M66_Body']
reference=old['clips']['land_clip']['samples'][0]['bones']
names=[b.name for b in rig.data.bones if b.name in reference]
source=np.array([list(rig.matrix_world@rig.data.bones[n].matrix_local.translation)+[1] for n in names])
target=np.array([reference[n]['reference']['p'] for n in names])
affine=np.linalg.lstsq(source,target,rcond=None)[0]
residual=float(np.max(np.abs(source@affine-target)))
if residual>.01:raise RuntimeError('Reference coordinate mapping changed: '+str(residual))
points=np.array([list(mesh.matrix_world@v.co)+[1] for v in mesh.data.vertices])@affine
reference_floor=float(points[:,2].min())
groups={g.index:g.name for g in mesh.vertex_groups};weights={}
for v in mesh.data.vertices:
 for g in v.groups:
  if g.weight>0:weights.setdefault(groups[g.group],[]).append((v.index,g.weight))
body_ids=[v.index for v in mesh.data.vertices if sum(g.weight for g in v.groups if groups[g.group] in ('Bone_000','Bone_001','Bone_005','Bone_006','Bone_007') or groups[g.group].startswith('M66_Sac'))>.6]
feet={side:[v.index for v in mesh.data.vertices if sum(g.weight for g in v.groups if groups[g.group]==bone)>.7] for side,bone in [('left','Bone_010'),('right','Bone_015')]}
def matrix(t):
 x,y,z,w=t['q'];m=np.eye(4);m[:3,:3]=np.array(Quaternion((w,x,y,z)).to_matrix())@np.diag(t['s']);m[:3,3]=t['p'];return m
inverses={n:np.linalg.inv(matrix(v['reference'])) for n,v in reference.items()}
rows=[]
for version in ('V03','V21'):
 for role,prop in [('Landing','land_clip'),('GetUp','get_up_clip')]:
  poses=old['clips'][prop]['runtime_samples'] if version=='V03' else new['runtime_poses'][role]
  for pose in poses:
   out=np.zeros_like(points);total=np.zeros(len(points))
   for name,pairs in weights.items():
    if name not in pose['bones']:raise RuntimeError('Missing compressed bone '+name)
    indices=np.array([p[0] for p in pairs]);values=np.array([p[1] for p in pairs])
    t=matrix(pose['bones'][name]['component'])@inverses[name]
    out[indices]+=(points[indices]@t[:3,:3].T+t[:3,3])*values[:,None];total[indices]+=values
   out/=total[:,None]
   rows.append(dict(version=version,role=role,seconds=pose['time'],surface_gap_cm=float(out[:,2].min()-reference_floor),body_gap_cm=float(out[body_ids,2].min()-reference_floor),feet_gap_cm={side:float(out[ids,2].min()-reference_floor) for side,ids in feet.items()}))
report=dict(method='Current source skin driven by actual UE compressed/retargeted bone transforms',reference_affine_error_cm=residual,poses=rows,game_run=False,multiplayer_tested=False)
(ROOT/'Records/compressed-support.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
for row in rows:print('M66_COMPRESSED_SUPPORT',row,flush=True)
