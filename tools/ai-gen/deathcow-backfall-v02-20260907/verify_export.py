import bpy,json
from pathlib import Path
P=Path(__file__).resolve().parent
def load(path):
 bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
 for a in list(bpy.data.actions):bpy.data.actions.remove(a)
 bpy.context.scene.render.fps=84
 bpy.ops.import_scene.gltf(filepath=str(path))
 return next(o for o in bpy.context.scene.objects if o.type=='ARMATURE'),next(o for o in bpy.context.scene.objects if o.type=='MESH')
def select(arm,body,name):
 for ob in [arm,body.data.shape_keys]:
  if ob is None:continue
  if ob.animation_data:
   for tr in ob.animation_data.nla_tracks:tr.mute=True
  # glTF importer packs object-specific channels into slots of each named clip.
  a=next(a for a in bpy.data.actions if a.name==name)
  ob.animation_data_create();ob.animation_data.action=a
  suitable=[sl for sl in a.slots if sl.target_id_type==ob.id_type]
  if suitable:ob.animation_data.action_slot=suitable[0]
def sample(arm,body,name,t):
 select(arm,body,name);f=t*84;bpy.context.scene.frame_set(int(f),subframe=f-int(f));bpy.context.view_layer.update()
 ev=body.evaluated_get(bpy.context.evaluated_depsgraph_get());m=ev.to_mesh();pts=[ev.matrix_world@v.co for v in m.vertices];ev.to_mesh_clear();return pts
arm,body=load(P.parent/'deathcow-motion-v01-20260907/fat-zombie-motion-v01.glb')
before={(n,t):sample(arm,body,n,t) for n in ['Idle','Run','Attack'] for t in [0,.2,.5,.7]}
arm,body=load(P/'fat-zombie-backfall-v02.glb')
report={'preserved_clips':{},'Death_samples':{}}
for (n,t),pts in before.items():
 after=sample(arm,body,n,t);assert len(pts)==len(after)
 err=max((x-y).length for x,y in zip(pts,after));report['preserved_clips'][n]=max(err,report['preserved_clips'].get(n,0))
assert max(report['preserved_clips'].values())<.0001
for t in [i/84 for i in range(127)]:
 pts=sample(arm,body,'Death',t);report['Death_samples'][str(t)]={'min_z':min(p.z for p in pts),'max_z':max(p.z for p in pts)}
assert all(v['min_z'] > -.002 for v in report['Death_samples'].values())
report['resting_feet']={}
pts=sample(arm,body,'Death',1.5)
for side in ['Left','Right']:
 ids={g.index for g in body.vertex_groups if side+'Foot' in g.name or side+'ToeBase' in g.name}
 indices=[v.index for v in body.data.vertices if sum(g.weight for g in v.groups if g.group in ids)>.65]
 low=min(pts[i].z for i in indices);report['resting_feet'][side]=low
 assert .003<low<.015,(side,low)
report['actions']=[{'name':a.name,'seconds':(a.frame_range[1]-a.frame_range[0])/84} for a in bpy.data.actions]
assert abs(next(a['seconds'] for a in report['actions'] if a['name']=='Death')-1.5)<.001
(P/'export-validation.json').write_text(json.dumps(report,indent=2))
print('EXPORT_VALIDATION_COMPLETE',json.dumps(report))
