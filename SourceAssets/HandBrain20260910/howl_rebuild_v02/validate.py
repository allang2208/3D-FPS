import bpy,json,numpy as np
from pathlib import Path
R=Path(__file__).resolve().parent
names=['HandBrain_Body','HandBrain_AttackArm','HandBrain_CrownHands']
tests=[(name,f) for name,end in [('Idle',61),('Move',31),('Attack_Slam',61)] for f in [1,(end+1)//2,end]]
def activate(rig,name,f):
 a=bpy.data.actions[name];rig.animation_data.action=a
 if a.slots:rig.animation_data.action_slot=a.slots[0]
 bpy.context.scene.frame_set(f);bpy.context.view_layer.update()
def verts(ob):
 e=ob.evaluated_get(bpy.context.evaluated_depsgraph_get());m=e.to_mesh()
 arr=np.array([e.matrix_world@v.co for v in m.vertices]);e.to_mesh_clear();return arr
bpy.ops.wm.open_mainfile(filepath=str(R.parent/'hunyuan_v01/delivery/HandBrain_Animated.blend'))
rig=bpy.data.objects['SK_HandBrain'];oldbones=list(rig.pose.bones.keys())
original_rest=np.array([v.co for v in bpy.data.objects['HandBrain_Body'].data.vertices]);old={};mats={}
for name,f in tests:
 activate(rig,name,f);old[(name,f)]={n:verts(bpy.data.objects[n]) for n in names}
 mats[(name,f)]={n:np.array(rig.pose.bones[n].matrix) for n in oldbones}
bpy.ops.wm.open_mainfile(filepath=str(R/'delivery/HandBrain_SingleFace.blend'))
rig=bpy.data.objects['SK_HandBrain'];body=bpy.data.objects['HandBrain_Body']
mapping=np.array(json.loads((R/'source_vertex_map.json').read_text()))
rest=np.array([v.co for v in body.data.vertices]);valid=mapping>=0
unchanged=valid.copy();unchanged[valid]=np.linalg.norm(rest[valid]-original_rest[mapping[valid]],axis=1)<1e-6
result={'original_bone_matrices_max_error':0,'retained_body_vertices_unchanged':int(sum(unchanged)),'retained_body_vertices_repositioned':int(sum(valid&~unchanged)),'new_body_vertices':int(sum(~valid)),'legacy_deformation_max_error':{},'geometry':{}}
for name,f in tests:
 activate(rig,name,f)
 for n in oldbones:result['original_bone_matrices_max_error']=max(result['original_bone_matrices_max_error'],float(np.max(np.abs(np.array(rig.pose.bones[n].matrix)-mats[(name,f)][n]))))
 for n in names:
  now=verts(bpy.data.objects[n]);before=old[(name,f)][n]
  delta=np.max(np.linalg.norm(now[unchanged]-before[mapping[unchanged]],axis=1)) if n==names[0] else np.max(np.linalg.norm(now-before,axis=1))
  result['legacy_deformation_max_error'][n]=max(result['legacy_deformation_max_error'].get(n,0),float(delta))
assert result['original_bone_matrices_max_error']<1e-5
assert max(result['legacy_deformation_max_error'].values())<1e-5
for o in bpy.context.scene.objects:
 if o.type!='MESH':continue
 weights=[sum(g.weight>1e-7 for g in v.groups) for v in o.data.vertices]
 sums=[sum(g.weight for g in v.groups) for v in o.data.vertices]
 result['geometry'][o.name]={'vertices':len(o.data.vertices),'triangles':sum(len(p.vertices)-2 for p in o.data.polygons),'unweighted':sum(w==0 for w in weights),'max_influences':max(weights),'max_weight_sum_error':max(abs(s-1) for s in sums)}
 assert min(weights)>0 and max(weights)<=8 and max(abs(s-1) for s in sums)<1e-5
for f in range(1,92,3):
 activate(rig,'Attack_Howl',f)
 for o in bpy.context.scene.objects:
  if o.type=='MESH':assert np.isfinite(verts(o)).all()
activate(rig,'Attack_Howl',1);first={n:verts(bpy.data.objects[n]) for n in names+['HandBrain_OralTeeth']}
activate(rig,'Attack_Howl',91)
result['howl_closure_error']=max(float(np.max(np.abs(verts(bpy.data.objects[n])-v))) for n,v in first.items());assert result['howl_closure_error']<1e-5
result['ue_runtime_verified']=False
(R/'delivery/validation.json').write_text(json.dumps(result,indent=2))
print('SINGLE_FACE_VALIDATION_COMPLETE',json.dumps(result))
