import bpy,bmesh,json,collections
from pathlib import Path
from mathutils import Matrix
O=Path(__file__).parent
bpy.ops.wm.read_factory_settings(use_empty=True);bpy.ops.import_scene.fbx(filepath=str(O/'Inputs/m870.fbx'),use_anim=False)
r=next(o for o in bpy.context.scene.objects if o.type=='ARMATURE')
print('RIG',r.name,[(b.name,list(b.matrix_local.translation)) for b in r.data.bones if b.name.startswith('WPN')])
report=[]
for o in bpy.context.scene.objects:
 if o.type!='MESH':continue
 o.data.transform(o.matrix_world);o.parent=None;o.matrix_world=Matrix.Identity(4);o.modifiers.clear()
 bm=bmesh.new();bm.from_mesh(o.data);bmesh.ops.remove_doubles(bm,verts=list(bm.verts),dist=1e-6);bm.faces.ensure_lookup_table();todo=set(bm.faces)
 while todo:
  f=todo.pop();group={f};stack=[f]
  while stack:
   for v in stack.pop().verts:
    for ff in v.link_faces:
     if ff in todo:todo.remove(ff);group.add(ff);stack.append(ff)
  vs={v for f in group for v in f.verts};bounds=[[min(v.co[j] for v in vs),max(v.co[j] for v in vs)] for j in range(3)]
  if len(group)>12:
   row={'object':o.name,'faces':len(group),'bounds':bounds,'slots':list({o.data.materials[f.material_index].name for f in group})};report.append(row)
 bm.free()
(O/'regions.json').write_text(json.dumps(report,indent=2))
for x in report:print('REGION',json.dumps(x))
bpy.ops.wm.save_as_mainfile(filepath=str(O/'Inputs/Native_Edit.blend'))
