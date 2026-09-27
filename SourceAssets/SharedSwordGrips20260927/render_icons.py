"""Produce six shipped UI icons from the real fitted models, no acceptance renders."""
import bpy,json,sys
from pathlib import Path
from mathutils import Vector,Matrix
P=Path(__file__).resolve().parent;ROOT=P.parents[1]
sys.path.insert(0,str(ROOT/'skills/ue5-weapon-workflow/scripts'))
from apply_modification_icon_grayscale import apply_grayscale,neutral_output
out=P/'Icons';out.mkdir(exist_ok=True)
bpy.ops.wm.read_factory_settings(use_empty=True)
scene=bpy.context.scene;neutral_output(scene)
scene.render.engine='CYCLES';scene.cycles.samples=48;scene.cycles.use_denoising=True
try:
 prefs=bpy.context.preferences.addons['cycles'].preferences;prefs.compute_device_type='OPTIX';prefs.get_devices()
 for d in prefs.devices:d.use=d.type=='OPTIX'
 if any(d.type=='OPTIX' for d in prefs.devices):scene.cycles.device='GPU'
except Exception:pass
scene.render.resolution_x=scene.render.resolution_y=1024;scene.render.resolution_percentage=100
scene.render.film_transparent=True;scene.render.image_settings.file_format='PNG';scene.render.image_settings.color_mode='RGBA'
scene.view_settings.view_transform='AgX';scene.view_settings.look='AgX - Medium High Contrast'
world=bpy.data.worlds.new('Neutral icon studio');world.use_nodes=True;scene.world=world
bg=next(n for n in world.node_tree.nodes if n.type=='BACKGROUND');bg.inputs['Color'].default_value=(.22,.22,.22,1);bg.inputs['Strength'].default_value=.65
camera=bpy.data.objects.new('Level side - blade left',bpy.data.cameras.new('Orthographic'));scene.collection.objects.link(camera)
scene.camera=camera;camera.data.type='ORTHO';camera.data.clip_start=.0001
camera.rotation_euler=Matrix(((0,1,0),(0,0,-1),(-1,0,0))).to_euler()
lights=[]
for name,offset,power,size in [('Key',(1.8,-3,1.4),420,2.2),('Fill',(-1.8,-2.4,-1.8),150,2.8),('Rim',(.7,1.8,.5),320,1.6)]:
 lamp=bpy.data.objects.new(name,bpy.data.lights.new(name,'AREA'));scene.collection.objects.link(lamp);lights.append((lamp,Vector(offset),power,size))
receipt=[]
for row in json.loads((P/'models.json').read_text()):
 for ob in list(scene.objects):
  if ob.type=='MESH':bpy.data.objects.remove(ob,do_unlink=True)
 bpy.data.orphans_purge(do_local_ids=True,do_linked_ids=True,do_recursive=True)
 file=Path(row['folder'])/(row['mesh']+'_Editable.blend')
 with bpy.data.libraries.load(str(file),link=False) as (a,b):b.objects=[row['mesh']]
 obj=b.objects[0];scene.collection.objects.link(obj);obj.parent=None;obj.matrix_world=Matrix.Identity(4)
 apply_grayscale([obj]);scene.view_layers[0].update()
 points=[v.co for v in obj.data.vertices]
 low=Vector(tuple(min(v[i] for v in points) for i in range(3)));high=Vector(tuple(max(v[i] for v in points) for i in range(3)))
 center=(low+high)*.5;span=max(high.x-low.x,high.z-low.z)
 camera.location=center+Vector((0,-4*span,0));camera.data.ortho_scale=span/.83
 for lamp,offset,power,size in lights:
  lamp.location=center+offset*span;lamp.rotation_euler=(center-lamp.location).to_track_quat('-Z','Y').to_euler();lamp.data.energy=power*span*span;lamp.data.size=size*span
 key=row['weapon']+'_grip_'+row['id'];scene.render.filepath=str(out/(key+'.png'))
 bpy.ops.render.render(write_still=True)
 receipt.append({'key':key,'source':str(file),'png':scene.render.filepath,'palette':'shared neutral grayscale','size':[1024,1024],'fill':.83})
 print('GRIP_ICON_RENDERED '+key,flush=True)
(P/'icons.json').write_text(json.dumps(receipt,indent=2),encoding='utf-8')
