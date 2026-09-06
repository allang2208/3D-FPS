import bpy,json,math
from pathlib import Path
R=Path(__file__).resolve().parent
bpy.ops.wm.read_factory_settings(use_empty=True);s=bpy.context.scene;s.render.fps=30
bpy.ops.import_scene.gltf(filepath=str(R/'modern-zombie-v02.glb'))
a=next(o for o in s.objects if o.type=='ARMATURE')
meshes=[o for o in s.objects if o.type=='MESH' and any(m.type=='ARMATURE' for m in o.modifiers)]
for tr in a.animation_data.nla_tracks:tr.mute=True
report={};total=0
for action in bpy.data.actions:
 if action.name not in ['Idle','Walk','Attack','AttackRight','Death','HitReact']:continue
 a.animation_data.action=action
 if action.slots:a.animation_data.action_slot=action.slots[0]
 lo=1e9;hi=-1e9;ends=[];duration=action.frame_range[1]/30
 for i in range(round(duration*60)+1):
  frame=i*.5;s.frame_set(int(frame),subframe=frame%1);bpy.context.view_layer.update()
  floor=1e9
  for m in meshes:
   ev=m.evaluated_get(bpy.context.evaluated_depsgraph_get());mesh=ev.to_mesh()
   for v in mesh.vertices:
    co=ev.matrix_world@v.co
    assert all(math.isfinite(x) and abs(x)<5 for x in co),(action.name,i,list(co))
    floor=min(floor,co.z);hi=max(hi,co.z)
   ev.to_mesh_clear()
  lo=min(lo,floor)
  if i in [0,round(duration*60)]:ends.append(floor)
  total+=1
 report[action.name]={'duration':duration,'min_z':lo,'max_z':hi,'start_end_ground_z':ends}
for m in meshes:
 assert m.data.uv_layers.active is not None
 for v in m.data.vertices:
  assert 0<len(v.groups)<=4
  assert abs(sum(g.weight for g in v.groups)-1)<1e-5
report['pose_samples']=total;report['bone_count']=len(a.data.bones)
(R/'asset-validation.json').write_text(json.dumps(report,indent=2));print('MODERN_ZOMBIE_VALIDATION_COMPLETE',json.dumps(report))
