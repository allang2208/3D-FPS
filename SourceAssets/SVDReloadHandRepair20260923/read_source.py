"""Read the current authored left arm and make the authorized local hand/arm views."""
import ast, json, math
from pathlib import Path
import bpy
from mathutils import Vector, Matrix
O=Path(__file__).parent;S=O.parent
tree=ast.parse((S/'SVDCompletion20260923/author_svd.py').read_text(encoding='utf-8-sig'))
exec(compile(ast.Module(body=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='sample'],type_ignores=[]),'<sample>','exec'))
bpy.ops.wm.open_mainfile(filepath=str(S/'SVDContactWrap20260923/SVD_base_Editable.blend'))
r=bpy.data.objects['SK_M4_Infima'];rest={b.name:b.matrix_local.copy() for b in r.data.bones}
parent={b.name:b.parent.name if b.parent else None for b in r.data.bones}
lr={n:rest[parent[n]].inverted()@m if parent[n] else m for n,m in rest.items()}
frames=[0,49,80,120,160,200,220,240,252,268,284,302]
out={'rest':{n:[list(row) for row in m] for n,m in rest.items()},'parent':parent,'poses':{}}
for f in frames:
 p=sample(r,bpy.data.actions['A_SVD_reload'],f)
 out['poses'][str(f)]={n:[list(row) for row in m] for n,m in p.items()}
(O/'source_before.json').write_text(json.dumps(out))
p=sample(r,bpy.data.actions['A_SVD_reload'],220)
inv=(r.matrix_world@p['WPN_SOCKET_Magazine']).inverted();dg=bpy.context.evaluated_depsgraph_get()
parts=[]
for name,color,hand in [('SK_Manny_Arms_Export',(.48,.31,.18,1),True),('SM_SVD_Magazine',(.22,.25,.29,1),False),('SM_SVD_MagazineInterior',(.15,.18,.21,1),False)]:
 ob=bpy.data.objects.get(name)
 if not ob:continue
 ev=ob.evaluated_get(dg);m=ev.to_mesh();X=inv@ev.matrix_world
 if hand:
  used=[v.index for v in ob.data.vertices if sum(g.weight for g in v.groups if ob.vertex_groups[g.group].name.endswith('_l'))>.9]
 else:used=list(range(len(m.vertices)))
 lookup={v:i for i,v in enumerate(used)}
 vs=[list(X@m.vertices[i].co) for i in used];fs=[[lookup[i] for i in f.vertices] for f in m.polygons if all(i in lookup for i in f.vertices)]
 parts.append({'name':name,'vertices':vs,'faces':fs,'color':color});ev.to_mesh_clear()
(O/'arm_surface_before.json').write_text(json.dumps({'parts':parts,'joints':{n:list(inv@r.matrix_world@m.translation) for n,m in p.items() if n.endswith('_l')}}))
bpy.ops.wm.read_factory_settings(use_empty=True);scene=bpy.context.scene
for part in parts:
 mesh=bpy.data.meshes.new(part['name']);mesh.from_pydata(part['vertices'],[],part['faces']);mesh.update()
 ob=bpy.data.objects.new(part['name'],mesh);scene.collection.objects.link(ob);ob.color=part['color']
 for f in mesh.polygons:f.use_smooth=True
cam=bpy.data.objects.new('LocalCamera',bpy.data.cameras.new('LocalCamera'));scene.collection.objects.link(cam);scene.camera=cam;cam.data.type='ORTHO';cam.data.ortho_scale=.7
scene.render.engine='BLENDER_WORKBENCH';scene.display.shading.light='STUDIO';scene.display.shading.color_type='OBJECT'
scene.display.shading.show_cavity=True;scene.display.shading.cavity_type='BOTH';scene.display.shading.show_shadows=True
scene.display.shading.background_type='WORLD';scene.world=bpy.data.worlds.new('LocalWorld');scene.world.color=(.12,.12,.12)
scene.render.resolution_x=1000;scene.render.resolution_y=800;scene.render.resolution_percentage=100
scene.render.image_settings.file_format='JPEG';scene.render.image_settings.quality=88
center=Vector((.06,.05,-.11))
for view,offset in [('outside',(.4,-.5,.08)),('inside',(.4,.5,.08))]:
 cam.location=center+Vector(offset);cam.rotation_euler=(center-cam.location).to_track_quat('-Z','Y').to_euler()
 scene.render.filepath=str(O/('before_'+view+'.jpg'));bpy.ops.render.render(write_still=True)
print('SVD_CURRENT_ARM_READ_COMPLETE',flush=True)
