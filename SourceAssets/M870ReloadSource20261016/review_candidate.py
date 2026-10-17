"""Compare native V7 result with the directly observed source hand poses."""
import bpy,json,gzip,math
from pathlib import Path
from mathutils import Matrix,Vector
from mathutils.bvhtree import BVHTree
O=Path(__file__).parent
bpy.ops.wm.open_mainfile(filepath=str(O/'M870_ReloadSource_Editable.blend'),use_scripts=False)
r=bpy.data.objects['SK_Super90'];s=bpy.context.scene;auth=json.loads((O/'authoring.json').read_text())
for ob in list(s.objects):
 if ob.type in ('CAMERA','LIGHT') or (ob.type=='MESH' and ('V7' in ob.name or 'BareArm' in ob.name)):bpy.data.objects.remove(ob,do_unlink=True)
with gzip.open(O.parent/'M870ReloadWrist20261016/native_arms.json.gz','rt',encoding='utf-8') as f:d=json.load(f)
faces=[f for f in d['faces'] if any(sum(w for n,w in d['weights'][i].items() if n.endswith('_r'))>.5 for i in f)]
me=bpy.data.meshes.new('Native right arm');me.from_pydata([(v[0]/100,-v[1]/100,v[2]/100) for v in d['vertices']],[],faces);me.update()
arm=bpy.data.objects.new('NativeRightArm',me);s.collection.objects.link(arm)
for p in me.polygons:p.use_smooth=True
for n in {n for w in d['weights'] for n in w}:arm.vertex_groups.new(name=n)
for i,w in enumerate(d['weights']):
 for n,v in w.items():arm.vertex_groups[n].add([i],v,'REPLACE')
arm.parent=r;arm.matrix_parent_inverse=Matrix.Identity(4);arm.matrix_basis=Matrix.Identity(4);arm.modifiers.new('Native skin','ARMATURE').object=r
for ob in s.objects:
 if ob.type=='MESH':ob.hide_render=False;ob.color=(.65,.35,.20,1) if ob==arm else (.8,.025,.01,1) if ob.name=='M870_ReloadShell' else (.1,.12,.14,1)
cam=bpy.data.objects.new('ReferenceMatchCamera',bpy.data.cameras.new('ReferenceMatchCamera'));s.collection.objects.link(cam);s.camera=cam
s.render.engine='BLENDER_WORKBENCH';s.render.resolution_x=1100;s.render.resolution_y=800;s.render.resolution_percentage=100
s.display.shading.light='STUDIO';s.display.shading.color_type='OBJECT';s.display.shading.show_shadows=True;s.display.shading.show_cavity=True;s.display.shading.background_type='WORLD'
if not s.world:s.world=bpy.data.worlds.new('ReviewWorld')
s.world.color=(.075,.075,.075);cam.data.type='ORTHO';cam.data.ortho_scale=.36
shots=[('reload_continuous',18,'side'),('reload_continuous',31,'side'),('reload_continuous',31,'palm'),('reload_continuous',44,'side'),('reload_continuous',53,'side'),('reload_full',390,'side')]
report=[]
for role,f,view in shots:
 a=bpy.data.actions[auth['clips'][role]['action']];r.animation_data.action=a;r.animation_data.action_slot=a.slots[0];s.frame_set(f);bpy.context.view_layer.update()
 center=r.pose.bones['hand_r'].matrix.translation
 cam.location=center+Vector((-.28,.20,.27) if view=='side' else (.25,-.30,-.15));cam.rotation_euler=(center-cam.location).to_track_quat('-Z','Y').to_euler()
 s.render.filepath=str(O/f'candidate_{role}_{f}_{view}.png');bpy.ops.render.render(write_still=True)
 if f in (18,31,44):
  dep=bpy.context.evaluated_depsgraph_get();ev=bpy.data.objects['M870_ReloadShell'].evaluated_get(dep);sm=ev.to_mesh()
  tree=BVHTree.FromPolygons([ev.matrix_world@v.co for v in sm.vertices],[list(p.vertices) for p in sm.polygons])
  av=arm.evaluated_get(dep);am=av.to_mesh();gaps={}
  for digit in ('thumb','index','middle'):
   ids=[i for i,w in enumerate(d['weights']) if sum(v for n,v in w.items() if n.startswith(digit+'_') and n.endswith('_r'))>.8]
   gaps[digit]=min(tree.find_nearest(av.matrix_world@am.vertices[i].co)[3] for i in ids)*1000
  report.append({'role':role,'frame':f,'gaps_mm':gaps});av.to_mesh_clear();ev.to_mesh_clear()
(O/'candidate_contact.json').write_text(json.dumps(report,indent=2))
print('M870_REFERENCE_CANDIDATE_RENDERED',flush=True)
