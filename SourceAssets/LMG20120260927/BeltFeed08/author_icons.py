"""Produce the magazine-slot UI art from the final authoring surfaces."""
import bpy,bmesh,json,importlib.util,shutil
from pathlib import Path
from mathutils import Vector
O=Path(__file__).parent;OUT=O/'Icons';OUT.mkdir(exist_ok=True)
spec=importlib.util.spec_from_file_location('gray','C:/Users/allan/.codex/skills/ue5-weapon-workflow/scripts/apply_modification_icon_grayscale.py')
gray=importlib.util.module_from_spec(spec);spec.loader.exec_module(gray)
report=[]
for part,source in [('false','LMG201_Magazine'),('lmg201_ammo_box','LMG201_BoxAndBelt')]:
 bpy.ops.wm.open_mainfile(filepath=str(O/'LMG201_BeltFeed_Animated.blend'),use_scripts=False)
 sc=bpy.context.scene;r=bpy.data.objects['SK_M4_Infima']
 r.animation_data.action=bpy.data.actions['A_LMG201_idle_BeltFeed08'];sc.frame_set(0);bpy.context.view_layer.update()
 ob=bpy.data.objects[source];dg=bpy.context.evaluated_depsgraph_get()
 me=bpy.data.meshes.new_from_object(ob.evaluated_get(dg),preserve_all_data_layers=True,depsgraph=dg)
 if part!='false':
  bm=bmesh.new();bm.from_mesh(me)
  bmesh.ops.delete(bm,geom=[f for f in bm.faces if '__OldBox' not in me.materials[f.material_index].name],context='FACES')
  bmesh.ops.delete(bm,geom=[v for v in bm.verts if not v.link_faces],context='VERTS')
  bm.to_mesh(me);bm.free();me.update()
 xf=(r.matrix_world@r.pose.bones['WPN_root'].matrix).inverted();me.transform(xf@ob.matrix_world)
 cp=bpy.data.objects.new('Icon_'+part,me)
 # A compact independent author scene retains only the one real component.
 ns=bpy.data.scenes.new('201_Magazine_Icon');bpy.context.window.scene=ns;ns.collection.objects.link(cp);sc=ns
 gray.apply_grayscale([cp]);gray.neutral_output(sc)
 points=[v.co for v in me.vertices];center=Vector(tuple((min(v[i] for v in points)+max(v[i] for v in points))*.5 for i in range(3)))
 cd=bpy.data.cameras.new('IconCamera');cam=bpy.data.objects.new('IconCamera',cd);sc.collection.objects.link(cam)
 cam.location=center+Vector((2,0,0));cam.rotation_euler=Vector((-1,0,0)).to_track_quat('-Z','Y').to_euler();sc.camera=cam;cd.type='ORTHO'
 width=max(v.y for v in points)-min(v.y for v in points);height=max(v.z for v in points)-min(v.z for v in points);size=max(width,height)/.82;cd.ortho_scale=size
 for name,xyz,power in [('Key',(1,-.3,1.4),130),('Fill',(1,.9,.45),60),('Rim',(-.8,.4,1.),100)]:
  ld=bpy.data.lights.new(name,'AREA');ld.energy=power*size*size;ld.shape='DISK';ld.size=size*1.8
  lamp=bpy.data.objects.new(name,ld);sc.collection.objects.link(lamp);lamp.location=center+Vector(xyz)*size*2;lamp.rotation_euler=(center-lamp.location).to_track_quat('-Z','Y').to_euler()
 sc.world=bpy.data.worlds.new('NeutralStudio');sc.world.use_nodes=True;next(n for n in sc.world.node_tree.nodes if n.type=='BACKGROUND').inputs['Color'].default_value=(.25,.25,.25,1)
 sc.render.engine='CYCLES';sc.cycles.device='CPU';sc.cycles.samples=32;sc.cycles.use_denoising=True;sc.render.film_transparent=True
 sc.render.resolution_x=sc.render.resolution_y=1024;sc.render.resolution_percentage=100;sc.render.image_settings.file_format='PNG';sc.render.image_settings.color_mode='RGBA';sc.view_settings.view_transform='AgX'
 key='ue_lmg201_magazine_'+part;sc.render.filepath=str(OUT/(key+'.png'));bpy.ops.render.render(write_still=True)
 for old in list(bpy.data.scenes):
  if old!=sc:bpy.data.scenes.remove(old)
 bpy.data.orphans_purge(do_local_ids=True,do_linked_ids=True,do_recursive=True)
 bpy.context.preferences.filepaths.save_version=0;bpy.ops.wm.save_as_mainfile(filepath=str(OUT/(key+'.blend')))
 report.append({'key':key,'file':str(OUT/(key+'.png')),'source_object':source,'material_faces':'__OldBox' if part!='false' else 'all','source_mesh':'/Game/Weapons/LMG201/BeltFeed08/SK_LMG201_BeltFeed','source_scene':str(O/'LMG201_BeltFeed_Animated.blend'),'forward':'-Y','up':'+Z','camera':'level orthographic +X','palette':'neutral grayscale','resolution':[1024,1024]})
category='ue_lmg201_category_magazine';shutil.copy2(OUT/'ue_lmg201_magazine_false.png',OUT/(category+'.png'))
report.append({'key':category,'file':str(OUT/(category+'.png')),'same_as':'ue_lmg201_magazine_false'})
(O/'icon_authoring.json').write_text(json.dumps(report,indent=2),encoding='utf8')
print('201_FEED_ICONS_AUTHORED',len(report),flush=True)
