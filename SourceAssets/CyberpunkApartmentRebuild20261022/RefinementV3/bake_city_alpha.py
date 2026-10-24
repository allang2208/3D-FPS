"""Retain the accepted city, remove only its baked sky for the hub-sky composition."""
from pathlib import Path
import json,sys
import bpy
from mathutils import Vector,Matrix
ROOT=Path(__file__).resolve().parent
SOURCE=ROOT.parents[1]/'CyberpunkBayLayered20261022/CyberpunkBay_Source.blend'
# ROOT parents: rebuild folder, SourceAssets, project.
bpy.ops.wm.open_mainfile(filepath=str(SOURCE))
scene=bpy.context.scene;cam=scene.camera
scene.render.film_transparent=True
scene.render.image_settings.file_format='PNG';scene.render.image_settings.color_mode='RGBA'
prefs=bpy.context.preferences.addons['cycles'].preferences
try:
 prefs.compute_device_type='OPTIX';prefs.get_devices()
 if any(d.type=='OPTIX' for d in prefs.devices):
  for d in prefs.devices:d.use=d.type=='OPTIX'
  scene.cycles.device='GPU'
except Exception:pass
report={'stage':'baking','captures':{}}
views=[('PX',(1,0,0),(0,0,1)),('NX',(-1,0,0),(0,0,1)),('PY',(0,0,1),(0,-1,0)),
 ('NY',(0,0,-1),(0,1,0)),('PZ',(0,1,0),(0,0,1)),('NZ',(0,-1,0),(0,0,1))]
for key,size,pos in [('Far',4096,(0,0,91.7)),('Reflection',1024,(0,200,1))]:
 folder=ROOT/'Sky'/key;folder.mkdir(parents=True,exist_ok=True)
 for ob in scene.objects:
  if ob.type=='MESH':ob.hide_render=(not ob.name.startswith('Far')) if key=='Far' else ob.name=='Water'
 scene.render.resolution_x=size;scene.render.resolution_y=size;cam.location=pos
 report['captures'][key]={'size':size,'faces':[]}
 for name,forward,up in views:
  f=Vector(forward);up=Vector(up);cam.rotation_euler=Matrix((f.cross(up),up,-f)).transposed().to_euler()
  scene.render.filepath=str(folder/(name+'.png'));bpy.ops.render.render(write_still=True)
  report['captures'][key]['faces'].append(name)
  (ROOT/'sky-bake.json').write_text(json.dumps(report,indent=2),encoding='utf8')
report['stage']='city_alpha_baked';(ROOT/'sky-bake.json').write_text(json.dumps(report,indent=2),encoding='utf8')
print('CITY_ALPHA_PRODUCTION_BAKE_COMPLETE')
