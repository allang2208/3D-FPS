"""Produce the three real part thumbnails required by the modification catalog."""
import bpy,json
from pathlib import Path
from mathutils import Vector,Matrix
P=Path(__file__).parent;OUT=P/'Icons';OUT.mkdir(exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=str(P/'Bow_ThreeBodies.blend'))
bpy.context.preferences.filepaths.save_version=0;scene=bpy.context.scene
objects=list(scene.objects)
for o in objects:o.data.transform(Matrix.Scale(.01,4));o.hide_render=True
scene.unit_settings.scale_length=1
d=bpy.data.cameras.new('PartIconCamera');d.type='ORTHO';d.clip_start=.001;d.clip_end=10
cam=bpy.data.objects.new('PartIconCamera',d);scene.collection.objects.link(cam);scene.camera=cam
cam.rotation_euler=Vector((0,-1,0)).to_track_quat('-Z','Y').to_euler()
lights=[]
for name,offset,power,size in [('Key',(-1,1.4,1.5),55,2),('Fill',(1,1.3,.2),30,1.5),('Edge',(0,-1,1.2),45,1)]:
 data=bpy.data.lights.new(name,'AREA');data.energy=power;data.shape='DISK';data.size=size
 o=bpy.data.objects.new(name,data);scene.collection.objects.link(o);lights.append((o,Vector(offset)))
w=bpy.data.worlds.new('NeutralStudio');w.use_nodes=True;scene.world=w
bg=next(n for n in w.node_tree.nodes if n.type=='BACKGROUND');bg.inputs['Color'].default_value=(.3,.3,.3,1);bg.inputs['Strength'].default_value=.12
scene.render.engine='CYCLES';scene.cycles.device='CPU';scene.cycles.samples=48;scene.cycles.use_denoising=True
scene.render.film_transparent=True;scene.render.image_settings.file_format='PNG';scene.render.image_settings.color_mode='RGBA';scene.render.image_settings.color_depth='8'
scene.render.resolution_x=1024;scene.render.resolution_y=1024;scene.render.resolution_percentage=100
scene.render.use_compositing=False;scene.render.use_sequencer=False
scene.view_settings.view_transform='AgX';scene.view_settings.look='None';scene.view_settings.exposure=0
records=[]
for row in json.loads((P/'authoring.json').read_text())['assets']:
 o=bpy.data.objects[row['mesh']];o.hide_render=False
 lo=Vector([min(v.co[j] for v in o.data.vertices) for j in range(3)]);hi=Vector([max(v.co[j] for v in o.data.vertices) for j in range(3)])
 center=(lo+hi)*.5;cam.location=center+Vector((0,3,0));d.ortho_scale=max(hi.z-lo.z,hi.x-lo.x)/.84
 for light,offset in lights:light.location=center+offset;light.rotation_euler=(center-light.location).to_track_quat('-Z','Y').to_euler()
 name='bow_dark_riser_'+row['id'];scene.render.filepath=str(OUT/(name+'.png'))
 bpy.ops.render.render(write_still=True);o.hide_render=True
 records.append(dict(name=name,part=row['id'],mesh=row['mesh'],size=[1024,1024],fill=.84))
 print('BOW_BODY_ICON_SAVED',name,flush=True)
bpy.ops.wm.save_as_mainfile(filepath=str(P/'Bow_ThreeBodyIcons.blend'))
(P/'icon-authoring.json').write_text(json.dumps(dict(records=records,orientation='installed forward UE+X screen left; +Z up; camera UE-Y',purpose='production attachment PNGs, no gameplay acceptance rendering'),indent=2),encoding='utf8')
