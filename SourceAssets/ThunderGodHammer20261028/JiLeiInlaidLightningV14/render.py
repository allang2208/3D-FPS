"""User-requested actual mesh inspection views; no image generation or UE launch."""
import bpy,json,sys,math
from pathlib import Path
from mathutils import Vector
P=Path(__file__).resolve().parent
bpy.ops.wm.open_mainfile(filepath=str(P/'JiLei_V14_Editable.blend'))
manifest=json.loads((P/'model_manifest.json').read_text());parts=[bpy.data.objects[n] for n in manifest['objects']];context=[bpy.data.objects[n] for n in manifest['context']]
for o in bpy.data.objects:
 if o.type=='MESH':o.hide_render=o not in parts
for o in parts:o.hide_render=False;o.hide_set(False)
s=bpy.context.scene;s.render.engine='CYCLES';s.cycles.samples=80;s.cycles.use_denoising=True
try:
 pref=bpy.context.preferences.addons['cycles'].preferences;pref.compute_device_type='OPTIX';pref.get_devices()
 for d in pref.devices:d.use=d.type!='CPU'
 s.cycles.device='GPU'
except Exception:s.cycles.device='CPU'
s.render.resolution_percentage=100;s.render.image_settings.file_format='PNG';s.render.image_settings.color_mode='RGBA';s.render.film_transparent=False
s.world=bpy.data.worlds.new('JiLei V14 neutral studio');s.world.use_nodes=True
s.world.node_tree.nodes.clear();bg=s.world.node_tree.nodes.new('ShaderNodeBackground');out=s.world.node_tree.nodes.new('ShaderNodeOutputWorld');s.world.node_tree.links.new(bg.outputs[0],out.inputs['Surface']);bg.inputs[0].default_value=(.045,.055,.070,1);bg.inputs[1].default_value=.45
s.view_settings.view_transform='AgX';s.view_settings.look='AgX - Medium High Contrast';s.view_settings.exposure=-.45
target=Vector((-.000445,0,.915))
for loc,power,size in [((-.23,-.24,.24),6,.23),((.21,-.13,.08),3,.22),((.12,.20,.20),6,.20),((-.18,.10,-.07),1.8,.16)]:
 bpy.ops.object.light_add(type='AREA',location=target+Vector(loc));o=bpy.context.object;o.data.energy=power;o.data.shape='DISK';o.data.size=size;o.rotation_euler=(target-o.location).to_track_quat('-Z','Y').to_euler()
bpy.ops.object.camera_add();cam=bpy.context.object;cam.data.type='ORTHO';cam.data.lens=65;cam.data.clip_start=.001;cam.data.clip_end=10;s.camera=cam
views={
 '01_front':dict(at=(0,0,.922),offset=(0,-.6,0),scale=.195,size=(1200,1400)),
 '02_side':dict(at=(0,0,.922),offset=(.6,0,0),scale=.195,size=(1200,1400)),
 '03_back':dict(at=(0,0,.922),offset=(0,.6,0),scale=.195,size=(1200,1400)),
 '04_threequarter':dict(at=(0,0,.922),offset=(.27,-.52,.18),scale=.205,size=(1600,1500)),
 '05_assembly':dict(at=(0,0,.894),offset=(.16,-.75,.20),scale=.40,size=(1900,1300),assembly=True),
 '06_shoulder_detail':dict(at=(.044,-.035,.965),offset=(.18,-.52,.18),scale=.090,size=(1500,1200)),
 '07_neck_detail':dict(at=(0,-.005,.850),offset=(.17,-.60,.10),scale=.115,size=(1500,1000),assembly=True),
 '09_crown_detail':dict(at=(0,-.015,.978),offset=(.14,-.50,.24),scale=.145,size=(1700,1100)),
 '10_top':dict(at=(0,0,.980),offset=(0,0,.6),scale=.155,size=(1600,1200)),
 '11_lightning_joint':dict(at=(.043,-.032,.935),offset=(.13,-.60,.10),scale=.105,size=(1500,1300)),
 '12_rear_junction':dict(at=(0,.036,.924),offset=(.12,.60,.08),scale=.110,size=(1500,1300)),
 '08_geometry':dict(at=(0,0,.922),offset=(.27,-.52,.18),scale=.205,size=(1600,1500),clay=True),
}
clay=bpy.data.materials.new('Geometry inspection - neutral clay');clay.use_nodes=True
cb=next(n for n in clay.node_tree.nodes if n.type=='BSDF_PRINCIPLED');cb.inputs['Base Color'].default_value=(.22,.24,.26,1);cb.inputs['Roughness'].default_value=.62
args=sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else list(views)
for key in args:
 v=views[key];at=Vector(v['at']);cam.location=at+Vector(v['offset']);cam.rotation_euler=(at-cam.location).to_track_quat('-Z','Y').to_euler();cam.data.ortho_scale=v['scale']
 for o in context:o.hide_render=not v.get('assembly',False);o.hide_set(not v.get('assembly',False))
 s.view_layers[0].material_override=clay if v.get('clay',False) else None
 s.render.resolution_x,s.render.resolution_y=v['size'];s.render.filepath=str(P/'Previews'/(key+'.png'));bpy.ops.render.render(write_still=True)
 print('RENDERED',key,flush=True)
bpy.ops.wm.save_as_mainfile(filepath=str(P/'JiLei_V14_InspectionScene.blend'))
