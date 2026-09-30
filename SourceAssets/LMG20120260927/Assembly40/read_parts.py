import bpy,numpy as np,json
from pathlib import Path
from mathutils import Matrix
O=Path(__file__).parent;out={}
bpy.ops.wm.open_mainfile(filepath=str(O.parent/'HardSurface39/LMG201_HardSurface39.blend'),use_scripts=False)
rig=bpy.data.objects['SK_M4_Infima'];root=rig.matrix_world@rig.data.bones['WPN_root'].matrix_local
for ob in bpy.data.objects:
 if ob.type!='MESH':continue
 v=np.array([(root.inverted()@ob.matrix_world@q.co)[:] for q in ob.data.vertices]);out[ob.name]={'bounds':[v.min(0).tolist(),v.max(0).tolist()],'mats':[m.name for m in ob.data.materials],'bones':[g.name for g in ob.vertex_groups]}
(O/'source_parts.json').write_text(json.dumps(out,indent=2))
bpy.ops.wm.read_factory_settings(use_empty=True);bpy.ops.import_scene.fbx(filepath=str(O/'Exports/Before_Body.fbx'),use_anim=False)
rig=next(ob for ob in bpy.data.objects if ob.type=='ARMATURE');root=rig.matrix_world@rig.data.bones['WPN_root'].matrix_local
out={'bones':{b.name:(root.inverted()@rig.matrix_world@b.matrix_local).to_translation()[:] for b in rig.data.bones if b.name.startswith(('WPN_','LMG201_'))},'groups':{}}
for ob in bpy.data.objects:
 if ob.type!='MESH':continue
 me=ob.data;xf=root.inverted()@ob.matrix_world;v=np.array([(xf@q.co)[:] for q in me.vertices]);me.calc_loop_triangles()
 for slot,mat in enumerate(me.materials):
  ts=[t for t in me.loop_triangles if t.material_index==slot]
  if not ts:continue
  f=np.array([t.vertices[:] for t in ts]);vi=np.unique(f);groups={}
  for i in vi:
   for g in me.vertices[int(i)].groups:
    if g.weight>.5:groups.setdefault(ob.vertex_groups[g.group].name,[]).append(int(i))
  out['groups'][mat.name]={'triangles':len(f),'bounds':[v[vi].min(0).tolist(),v[vi].max(0).tolist()],'bones':{k:{'vertices':len(ids),'bounds':[v[ids].min(0).tolist(),v[ids].max(0).tolist()]} for k,ids in groups.items()}}
  if any(s in mat.name for s in ['Charging','Trigger','Magazine']):np.savez_compressed(O/(mat.name+'.npz'),v=v,f=f)
(O/'current_parts.json').write_text(json.dumps(out,indent=2));print('A40_PARTS_RECORDED',flush=True)
