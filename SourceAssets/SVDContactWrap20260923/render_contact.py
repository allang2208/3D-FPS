"""User-authorized local hand/magazine contact views from evaluated Blender skin."""
import bpy,ast,json,sys
from pathlib import Path
from mathutils import Vector,Matrix,Quaternion
O=Path(__file__).parent;S=O.parent
after='--after' in sys.argv;side='--side' in sys.argv;contact='--contact' in sys.argv;pulp='--pulp' in sys.argv;balanced='--balanced' in sys.argv;draft='--fit' in sys.argv or side or contact or pulp or balanced;label='after' if after else 'balanced' if balanced else 'pulp' if pulp else 'contact' if contact else 'side' if side else 'draft' if draft else 'before'
source=O/'SVD_base_Editable.blend' if after else S/'SVDNaturalGrasp20260923/SVD_base_Editable.blend'
t=ast.parse((S/'SVDCompletion20260923/author_svd.py').read_text())
exec(compile(ast.Module(body=[n for n in t.body if isinstance(n,ast.FunctionDef) and n.name=='sample'],type_ignores=[]),'<sample>','exec'))
bpy.ops.wm.open_mainfile(filepath=str(source));r=bpy.data.objects['SK_M4_Infima'];p=sample(r,bpy.data.actions['A_SVD_reload'],220)
if draft:
 fit=json.loads((O/('grasp_balanced.json' if balanced else 'grasp_pulp.json' if pulp else 'grasp_contact.json' if contact else 'grasp_side.json' if side else 'grasp_fit.json')).read_text());rest={b.name:b.matrix_local.copy() for b in r.data.bones}
 parent={b.name:b.parent.name if b.parent else None for b in r.data.bones};lr={n:rest[parent[n]].inverted()@m if parent[n] else m for n,m in rest.items()}
 original={n:m.copy() for n,m in p.items()};p['hand_l']=p['WPN_SOCKET_Magazine']@Matrix(fit['hand_in_mag'])
 for n,q in fit['finger_basis'].items():
  loc,_,scale=(lr[n].inverted()@original[parent[n]].inverted()@original[n]).decompose()
  p[n]=p[parent[n]]@lr[n]@Matrix.LocRotScale(loc,Quaternion(q),scale)
 r.animation_data.action=None
 for n,m in p.items():r.pose.bones[n].matrix_basis=lr[n].inverted()@(p[parent[n]].inverted()@m if parent[n] else m)
 bpy.context.view_layer.update()
inv=(r.matrix_world@p['WPN_SOCKET_Magazine']).inverted();dg=bpy.context.evaluated_depsgraph_get()
ids=json.loads((S/'SVDNaturalGrasp20260923/inputs.json').read_text())['indices'];lookup={v:i for i,v in enumerate(ids)}
parts=[]
for name,color,hand in [('SK_Manny_Arms_Export',(.48,.31,.18,1),True),('SM_SVD_Magazine',(.22,.25,.29,1),False),('SM_SVD_MagazineInterior',(.15,.18,.21,1),False)]:
 ob=bpy.data.objects.get(name)
 if not ob:continue
 ev=ob.evaluated_get(dg);m=ev.to_mesh();X=inv@ev.matrix_world
 used=ids if hand else list(range(len(m.vertices)));mp=lookup if hand else {i:i for i in used}
 vs=[list(X@m.vertices[i].co) for i in used];fs=[[mp[i] for i in f.vertices] for f in m.polygons if all(i in mp for i in f.vertices)]
 parts.append({'name':name,'vertices':vs,'faces':fs,'color':color});ev.to_mesh_clear()
joints={n:list(inv@r.matrix_world@m.translation) for n,m in p.items() if n.endswith('_l') and n.startswith(('hand','thumb','index','middle','ring','pinky'))}
(O/(label+'_surface.json')).write_text(json.dumps({'source':str(source),'parts':parts,'joints':joints}))
bpy.ops.wm.read_factory_settings(use_empty=True);scene=bpy.context.scene
for part in parts:
 mesh=bpy.data.meshes.new(part['name']);mesh.from_pydata(part['vertices'],[],part['faces']);mesh.update()
 ob=bpy.data.objects.new(part['name'],mesh);scene.collection.objects.link(ob);ob.color=part['color']
 for f in mesh.polygons:f.use_smooth=True
cam=bpy.data.objects.new('ContactCamera',bpy.data.cameras.new('ContactCamera'));scene.collection.objects.link(cam);scene.camera=cam
cam.data.type='ORTHO';cam.data.ortho_scale=.205
scene.render.engine='BLENDER_WORKBENCH';scene.display.shading.light='STUDIO';scene.display.shading.color_type='OBJECT'
scene.display.shading.show_cavity=True;scene.display.shading.cavity_type='BOTH';scene.display.shading.show_shadows=True
scene.display.shading.background_type='WORLD';scene.world=bpy.data.worlds.new('ContactWorld');scene.world.color=(.12,.12,.12)
scene.render.resolution_x=800;scene.render.resolution_y=800;scene.render.resolution_percentage=100
scene.render.image_settings.file_format='JPEG';scene.render.image_settings.quality=88
center=Vector((.01,.024,.002));out=O/'ContactViews';out.mkdir(exist_ok=True)
for view,offset in [('fingers',(.27,-.30,.05)),('palm',(-.30,-.22,.06)),('thumb',(.24,.30,.07)),('back',(.30,.03,.05))]:
 cam.location=center+Vector(offset);cam.rotation_euler=(center-cam.location).to_track_quat('-Z','Y').to_euler()
 scene.render.filepath=str(out/(label+'_'+view+'.jpg'));bpy.ops.render.render(write_still=True)
print('SVD_CONTACT_VIEWS',label,flush=True)
