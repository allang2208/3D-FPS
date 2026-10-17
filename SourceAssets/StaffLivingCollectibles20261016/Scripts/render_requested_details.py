"""User-requested close views of the actual editable models. Never save altered source assets."""
from pathlib import Path
from datetime import datetime
import bpy,json,math
from mathutils import Vector,Matrix
ROOT=Path(__file__).resolve().parents[1]
SPEC=json.loads((ROOT/'model_manifest.json').read_text('utf-8'))
OUT=ROOT/'Previews'/'DetailReview20261016';OUT.mkdir(parents=True,exist_ok=True)
report={'stage':'rendering','requested_by_user':True,'source':'Actual saved Blender models and their production PBR','engine':'Blender Cycles','ue_gameplay_capture':False,'production_assets_modified':False,'views':[]}
def record():(OUT/'render-receipt.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
def aim(o,target):o.rotation_euler=(Vector(target)-o.location).to_track_quat('-Z','Y').to_euler()
def light(name,pos,power,size,target=(0,0,0),shape='DISK',size_y=None):
 d=bpy.data.lights.new(name,'AREA');d.energy=power;d.shape=shape;d.size=size
 if size_y is not None:d.size_y=size_y
 o=bpy.data.objects.new(name,d);bpy.context.scene.collection.objects.link(o);o.location=pos;aim(o,target)
def fit(cam,points,aspect,margin=1.12):
 bpy.context.view_layer.update();inv=cam.matrix_world.inverted();ps=[inv@p for p in points]
 left=min(p.x for p in ps);right=max(p.x for p in ps);low=min(p.y for p in ps);high=max(p.y for p in ps)
 cam.location+=cam.matrix_world.to_3x3()@Vector(((left+right)/2,(low+high)/2,0))
 extent=max(right-left,(high-low)*aspect)*margin
 cam.data.ortho_scale=extent if aspect>=1 else extent/aspect
def save_render(scene,key,view,path,res,detail_note=''):
 scene.render.resolution_x,scene.render.resolution_y=res;scene.render.filepath=str(path)
 bpy.ops.render.render(write_still=True)
 report['views'].append({'model':key,'view':view,'file':str(path),'resolution':list(res),'note':detail_note,'source':SPEC['assets'][key]['source']});record()
 print('DETAIL_RENDER_SAVED',key,view,str(path),flush=True)
for key in ('Perfume','MusicPlayer','Camera'):
 spec=SPEC['assets'][key];bpy.ops.wm.open_mainfile(filepath=spec['source']);scene=bpy.context.scene
 parts=[o for o in scene.objects if o.type=='MESH' and not o.name.startswith('UCX_')]
 transforms=[(o,o.matrix_world.copy()) for o in parts]
 for o,m in transforms:o.parent=None;o.matrix_world=m
 bpy.context.view_layer.update()
 pts=[o.matrix_world@Vector(v) for o in parts for v in o.bound_box]
 lo=Vector([min(p[i] for p in pts) for i in range(3)]);hi=Vector([max(p[i] for p in pts) for i in range(3)])
 factor=2.8/max(hi-lo);scale=Matrix.Scale(factor,4)
 for o in parts:o.matrix_world=scale@o.matrix_world
 bpy.context.view_layer.update();pts=[o.matrix_world@Vector(v) for o in parts for v in o.bound_box]
 lo=Vector([min(p[i] for p in pts) for i in range(3)]);hi=Vector([max(p[i] for p in pts) for i in range(3)]);offset=-(lo+hi)*.5
 for o in parts:o.matrix_world.translation+=offset
 bpy.context.view_layer.update();pts=[o.matrix_world@Vector(v) for o in parts for v in o.bound_box]
 floor=min(p.z for p in pts)-.025
 bpy.ops.mesh.primitive_plane_add(size=200,location=(0,0,floor));ground=bpy.context.object;ground.name='Preview studio floor'
 material=bpy.data.materials.new('Preview neutral grey');material.use_nodes=True
 bs=next(n for n in material.node_tree.nodes if n.bl_idname=='ShaderNodeBsdfPrincipled');bs.inputs['Base Color'].default_value=(.075,.085,.095,1);bs.inputs['Roughness'].default_value=.85;ground.data.materials.append(material)
 scene.unit_settings.scale_length=1;scene.render.engine='CYCLES';scene.cycles.samples=384;scene.cycles.adaptive_threshold=.006;scene.cycles.use_denoising=True
 scene.cycles.max_bounces=20;scene.cycles.transmission_bounces=16;scene.cycles.transparent_max_bounces=16;scene.cycles.device='CPU'
 try:
  prefs=bpy.context.preferences.addons['cycles'].preferences;prefs.compute_device_type='OPTIX';prefs.get_devices()
  if any(d.type=='OPTIX' for d in prefs.devices):
   for d in prefs.devices:d.use=d.type=='OPTIX'
   scene.cycles.device='GPU'
 except Exception as e:print('CPU_RENDER',str(e),flush=True)
 scene.render.resolution_percentage=100;scene.render.image_settings.file_format='PNG';scene.render.image_settings.color_mode='RGB';scene.render.film_transparent=False
 scene.view_settings.view_transform='AgX';scene.view_settings.look='AgX - Medium High Contrast';scene.view_settings.exposure=.15
 scene.world=bpy.data.worlds.new('Neutral preview studio');scene.world.use_nodes=True
 bg=next(n for n in scene.world.node_tree.nodes if n.bl_idname=='ShaderNodeBackground');bg.inputs['Color'].default_value=(.20,.23,.26,1);bg.inputs['Strength'].default_value=.38
 light('Wide key',(-3.5,-4,5),650,4)
 light('Front fill',(4,-3,3.2),350,3)
 light('Narrow reflection strip',(-2,3.0,4),850,1.1,shape='RECTANGLE',size_y=4)
 light('Rear fill',(4,3.2,2),350,3)
 camera=bpy.data.cameras.new('Requested asset detail');camera.type='ORTHO';cam=bpy.data.objects.new(camera.name,camera);scene.collection.objects.link(cam);scene.camera=cam
 views=[('front',(5,-9,4.3 if key!='Camera' else 6.5)),('rear',(-5,9,4.5 if key!='Camera' else 6.5))]
 for view,direction in views:
  cam.location=Vector(direction).normalized()*10;aim(cam,(0,0,0));fit(cam,pts,1600/1500)
  save_render(scene,key,view,OUT/(key+'_'+view+'.png'),(1600,1500))
 if key=='Perfume':
  for o in parts:
   if o.name.startswith(('Faceted hollow smoked cap','Cap satin metal bottom trim')):o.hide_render=True
  target=Vector((0,0,10.15))*factor+offset;direction=Vector((4,-9,4.3));width=1.33
  note='Bottle cap hidden only for this inspection render to show atomizer and spray bore; saved model untouched.'
 elif key=='MusicPlayer':
  target=Vector((.05,0,10.7))*factor+offset;direction=Vector((4,-9,7));width=1.7
  note='Close view of audio sockets, machined encoder and top shell.'
 else:
  target=Vector((.55,-2.7,3.5))*factor+offset;direction=Vector((2,-10,2.8));width=1.9
  note='Close view of lens stack, coated optical element, barrel grooves and engravings.'
 cam.location=target+direction.normalized()*10;aim(cam,target);cam.data.ortho_scale=width
 save_render(scene,key,'detail',OUT/(key+'_detail.png'),(1600,1200),note)
report['stage']='requested_previews_saved';record();print('REQUESTED_DETAILS_COMPLETE',len(report['views']),flush=True)
