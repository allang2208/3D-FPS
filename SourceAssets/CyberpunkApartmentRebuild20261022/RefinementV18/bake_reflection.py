"""Production city-only TextureCube source; never an acceptance screenshot."""
import bpy,json,math
from pathlib import Path
from mathutils import Vector,Matrix
R=Path(__file__).resolve().parent;bpy.ops.wm.open_mainfile(filepath=str(R/'WaterfrontLife_Source.blend'));scene=bpy.context.scene
# Bring the four existing static V16 road batches into the texture production scene.
# Their file uses reflected final-world coordinates; return to the author-space
# cube convention. Cars are deliberately excluded from this static supplement.
with bpy.data.libraries.load(str(R.parent/'RefinementV16/HarborStreets_Source.blend'),link=False) as (source,dest):
 dest.objects=[name for name in source.objects if name in ['SM_AP16_Roads','SM_AP16_Trees','SM_AP16_StreetFurniture','SM_AP16_Junctions']]
street_colors={'Asphalt':((.035,.045,.055),.85,0,0),'Concrete':((.24,.28,.3),.8,0,0),'Paint':((.65,.63,.49),.7,0,0),'Bark':((.11,.075,.05),.95,0,0),'Leaves':((.08,.19,.12),.85,0,0),'Metal':((.12,.16,.2),.4,.65,0),'Cyan':((.05,.6,.85),.4,.1,2),'Warm':((.9,.62,.28),.45,0,2)}
for ob in dest.objects:
 if not ob:continue
 scene.collection.objects.link(ob)
 for v in ob.data.vertices:v.co=(-v.co.x/1.25+10,-v.co.y/1.25,v.co.z/1.25+90)
 for slot in ob.material_slots:
  role=slot.material.name.split('.')[0];rgb,rough,metal,glow=street_colors[role]
  m=bpy.data.materials.get('AP18_BakeStreet_'+role)
  if not m:
   m=bpy.data.materials.new('AP18_BakeStreet_'+role);m.use_nodes=True;p=next(n for n in m.node_tree.nodes if n.type=='BSDF_PRINCIPLED')
   for pin,value in [('Base Color',(*rgb,1)),('Roughness',rough),('Metallic',metal),('Emission Color',(*rgb,1)),('Emission Strength',glow)]:p.inputs[pin].default_value=value
  slot.material=m
for ob in scene.objects:
 if ob.type!='MESH':continue
 ob.hide_render=ob.name=='Water' or 'SkySphere' in ob.name
 if ob.name.startswith('Far'):
  for slot in ob.material_slots:
   if not slot.material or not slot.material.use_nodes:continue
   key='Far18_'+slot.material.name
   mat=bpy.data.materials.get(key)
   if not mat:
    mat=slot.material.copy();mat.name=key
    p=next((n for n in mat.node_tree.nodes if n.type=='BSDF_PRINCIPLED'),None)
    if p:p.inputs['Emission Strength'].default_value*=.32
   slot.material=mat
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
 print('AP18_REFLECTION_FACE',name,flush=True)
record['stage']='production_faces_baked';(R/'reflection-bake.json').write_text(json.dumps(record,indent=2),encoding='utf8')
