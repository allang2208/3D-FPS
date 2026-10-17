"""Native skin/outfit key-frame review. These are offline author renders."""
import bpy,json,gzip,math
from pathlib import Path
from mathutils import Matrix,Vector
O=Path(__file__).parent;(O/'Review').mkdir(exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=str(O/'M870_SurfaceFit_Editable.blend'),use_scripts=False)
r=bpy.data.objects['SK_Super90'];s=bpy.context.scene;auth=json.loads((O/'authoring.json').read_text())
def action(role,frame):
 a=bpy.data.actions[auth['clips'][role]['action']];r.animation_data.action=a;r.animation_data.action_slot=a.slots[0];s.frame_set(frame);bpy.context.view_layer.update()
action('idle',0);canon=r.data.bones['WPN_root'].matrix_local@r.pose.bones['WPN_root'].matrix.inverted()
def material(name,c):
 m=bpy.data.materials.new(name);m.diffuse_color=(*c,1);return m
skin=material('Native skin review',(.64,.39,.27));cloth=material('Chainmail silhouette review',(.25,.30,.36));gun=material('Gun review',(.065,.07,.08))
for ob in s.objects:
 if ob.type!='MESH':continue
 ob.data.materials.clear();ob.data.materials.append(gun)
 for p in ob.data.polygons:p.material_index=0
bpy.data.objects.remove(bpy.data.objects['M870_V7'],do_unlink=True)
native=[]
for key in ('native_arms','shirt'):
 d=json.loads(gzip.decompress((O/(key+'.json.gz')).read_bytes()))
 for part in (('arms','hands') if key=='native_arms' else ('shirt',)):
  faces=[f for i,f in enumerate(d['faces']) if key=='shirt' or (d['materials'][i]==2)==(part=='hands')]
  mesh=bpy.data.meshes.new(part);mesh.from_pydata([(v[0]/100,-v[1]/100,v[2]/100) for v in d['vertices']],[],faces);mesh.update();mesh.materials.append(cloth if part=='shirt' else skin)
  ob=bpy.data.objects.new('Review_'+part,mesh);s.collection.objects.link(ob)
  for p in mesh.polygons:p.use_smooth=True
  for n in {n for w in d['weights'] for n in w}:ob.vertex_groups.new(name=n)
  for i,w in enumerate(d['weights']):
   for n,weight in w.items():ob.vertex_groups[n].add([i],weight,'REPLACE')
  ob.parent=r;ob.matrix_parent_inverse=Matrix.Identity(4);ob.matrix_basis=Matrix.Identity(4);ob.modifiers.new('Saved native skin','ARMATURE').object=r;native.append(ob)
ca=bpy.data.cameras.new('ReviewCamera');co=bpy.data.objects.new('ReviewCamera',ca);s.collection.objects.link(co);s.camera=co;ca.clip_start=.005;ca.lens=25
s.render.engine='BLENDER_WORKBENCH';s.display.shading.light='STUDIO';s.display.shading.color_type='MATERIAL';s.display.shading.show_shadows=True;s.display.shading.show_cavity=True
s.render.resolution_x=1280;s.render.resolution_y=720;s.render.resolution_percentage=100;s.view_settings.view_transform='Standard'
if not s.world:s.world=bpy.data.worlds.new('ReviewWorld')
s.world.color=(.14,.16,.18)
def camera(ads):
 eye=Vector((0,-.262,-.7014)) if ads else Vector((-.105,-.30,-.665))
 direction=Vector((0,1,-.00272)) if ads else Vector((0,1,0))
 transform=canon.inverted();co.location=transform@eye;co.rotation_euler=(transform.to_3x3()@direction).to_track_quat('-Z','Y').to_euler();ca.lens=32 if ads else 25
shots=[('hip','idle',0,False),('ads','idle',0,True),('fire_back','fire',21,False),('fire_closed','fire',44,False)]
for role in ('reload_continuous','reload_full'):
 for frame in (0,22,44,94,194,294,344,360,380,391,399):shots.append((role+'_%03d'%frame,role,frame,False))
 if role=='reload_full':shots.append((role+'_424',role,424,False))
report=[]
for dressed in (False,True):
 for ob in native:ob.hide_render=(ob.name=='Review_arms' and dressed) or (ob.name=='Review_shirt' and not dressed)
 for label,role,frame,ads in shots:
  action(role,frame);camera(ads);name=('chain_' if dressed else 'bare_')+label+'.png';s.render.filepath=str(O/'Review'/name);bpy.ops.render.render(write_still=True)
  report.append({'file':name,'role':role,'frame':frame,'outfit':dressed})
(O/'Review/shots.json').write_text(json.dumps(report,indent=2));print('NATIVE_REVIEW_RENDERED',len(report))
