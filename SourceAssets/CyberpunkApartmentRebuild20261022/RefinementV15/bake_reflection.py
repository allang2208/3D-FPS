"""Production city-only TextureCube source; never an acceptance screenshot."""
import bpy,json,math
from pathlib import Path
from mathutils import Vector,Matrix
R=Path(__file__).resolve().parent;bpy.ops.wm.open_mainfile(filepath=str(R/'CloserBay_Source.blend'));scene=bpy.context.scene
families=['Corporate','Financial'];materials=bpy.data.materials
if 'Terraces' not in materials:
 m=materials['Housing'].copy();m.name='Terraces'
 for node in m.node_tree.nodes:
  if node.type=='TEX_IMAGE' and node.image:
   source=node.image;filename=Path(source.filepath).name.replace('T_AP7_Housing_','T_AP7_Terraces_')
   node.image=bpy.data.images.load(str(R.parent/'RefinementV7/Textures'/filename));node.image.colorspace_settings.name=source.colorspace_settings.name;node.image.pack()
for ob in scene.objects:
 if ob.type=='MESH':
  ob.hide_render=ob.name=='Water' or 'SkySphere' in ob.name
  for slot in ob.material_slots:
   if not slot.material:continue
   role=slot.material.name
   family='Data' if role=='Tech' else ('Terraces' if ob.name.endswith(('1','3')) else 'Housing') if role=='Residential' else families[sum(ord(ch) for ch in 'BAY_'+ob.name)%2] if role=='Office' else None
   if family:slot.material=materials[family]
scene.render.engine='CYCLES';scene.cycles.samples=32;scene.cycles.use_denoising=True;scene.cycles.max_bounces=2
scene.cycles.diffuse_bounces=1;scene.cycles.glossy_bounces=1;scene.cycles.sample_clamp_indirect=2.
prefs=bpy.context.preferences.addons['cycles'].preferences
try:
 prefs.compute_device_type='OPTIX';prefs.get_devices()
 for device in prefs.devices:device.use=device.type=='OPTIX'
 if any(d.type=='OPTIX' for d in prefs.devices):scene.cycles.device='GPU'
except Exception:scene.cycles.device='CPU'
scene.render.threads_mode='FIXED';scene.render.threads=2;scene.render.use_persistent_data=True
scene.render.film_transparent=True;scene.render.image_settings.file_format='PNG';scene.render.image_settings.color_mode='RGBA'
scene.render.resolution_x=2048;scene.render.resolution_y=2048;scene.render.resolution_percentage=100
camera=scene.camera;camera.data.type='PERSP';camera.data.lens=18;camera.data.sensor_width=36;camera.data.sensor_fit='HORIZONTAL';camera.data.clip_start=.2;camera.data.clip_end=50000;camera.location=(0,200,1)
out=R/'ReflectionFaces';out.mkdir(exist_ok=True)
views=[('PX',(1,0,0),(0,0,1)),('NX',(-1,0,0),(0,0,1)),('PY',(0,0,1),(0,-1,0)),('NY',(0,0,-1),(0,1,0)),('PZ',(0,1,0),(0,0,1)),('NZ',(0,-1,0),(0,0,1))]
record=dict(stage='baking_production_texture',faces=[],size=2048,city_only=True,game_run=False,acceptance_rendered=False)
for name,forward,up in views:
 f=Vector(forward);up=Vector(up);camera.rotation_euler=Matrix((f.cross(up),up,-f)).transposed().to_euler();scene.render.filepath=str(out/(name+'.png'))
 bpy.ops.render.render(write_still=True);record['faces'].append(name);(R/'reflection-bake.json').write_text(json.dumps(record,indent=2),encoding='utf8')
 print('AP15_REFLECTION_FACE',name,flush=True)
record['stage']='production_faces_baked';(R/'reflection-bake.json').write_text(json.dumps(record,indent=2),encoding='utf8')
