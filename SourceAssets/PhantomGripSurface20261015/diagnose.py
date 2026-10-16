import bpy,json,numpy as np
from pathlib import Path
from mathutils import Vector
O=Path(__file__).parent;D=json.loads((O/'capture.json').read_text());V=O/'Preview';V.mkdir(exist_ok=True);R={}
def setup(key):
 bpy.ops.wm.read_factory_settings(use_empty=True);bpy.context.preferences.filepaths.save_version=0;bpy.ops.import_scene.fbx(filepath=D['assets'][key]['export'])
 ob=next(o for o in bpy.context.scene.objects if o.type=='MESH');pts=[ob.matrix_world@v.co for v in ob.data.vertices];lo=Vector(tuple(min(v[i] for v in pts) for i in range(3)));hi=Vector(tuple(max(v[i] for v in pts) for i in range(3)));center=(lo+hi)/2;h=(hi-lo).z;scale=max(h*.82,(hi-lo).y)*1.28
 scene=bpy.context.scene;scene.render.engine='CYCLES';scene.cycles.samples=48;scene.cycles.use_denoising=True;scene.render.resolution_x=900;scene.render.resolution_y=1100;scene.render.resolution_percentage=100;scene.render.image_settings.file_format='PNG';scene.view_settings.view_transform='AgX';scene.view_settings.look='AgX - Medium High Contrast'
 world=bpy.data.worlds.new('DiagnosticWorld');world.use_nodes=True;bg=next(n for n in world.node_tree.nodes if n.type=='BACKGROUND');bg.inputs[0].default_value=(.2,.23,.27,1);bg.inputs[1].default_value=.6;scene.world=world
 def aim(a):a.rotation_euler=(center-a.location).to_track_quat('-Z','Y').to_euler()
 for name,offset,power,size in [('Key',(2,-1.3,2),5,2),('Fill',(2,2,.2),2,1.4),('Rim',(-1,.7,2),5,1.8)]:
  l=bpy.data.lights.new(name,'AREA');l.energy=power*(h/.1)**2;l.shape='DISK';l.size=size*h;a=bpy.data.objects.new(name,l);scene.collection.objects.link(a);a.location=center+Vector(offset)*h;aim(a)
 cam=bpy.data.objects.new('Camera',bpy.data.cameras.new('Camera'));scene.collection.objects.link(cam);cam.location=center+Vector((3,.6,.18))*h;cam.data.type='ORTHO';cam.data.ortho_scale=scale;cam.data.clip_start=.001;aim(cam);scene.camera=cam
 m=bpy.data.materials.new('ConstantDiagnosticMetal');m.use_nodes=True;bs=next(n for n in m.node_tree.nodes if n.type=='BSDF_PRINCIPLED');bs.inputs['Base Color'].default_value=(.16,.17,.18,1);bs.inputs['Metallic'].default_value=.8;bs.inputs['Roughness'].default_value=.32
 for i in range(len(ob.data.materials)):ob.data.materials[i]=m
 return ob,scene
for key in ['M4','M16','HK416','LMG201','Super90']:
 ob,scene=setup(key);me=ob.data;p=np.asarray([tuple(v.co) for v in me.vertices]);t=np.asarray([list(f.vertices) for f in me.polygons]);norm=np.asarray([tuple(n.vector) for n in me.corner_normals]);uvstats=[]
 for uv in me.uv_layers:
  a=np.asarray([tuple(v.uv) for v in uv.data]).reshape(-1,3,2);b=a[:,1]-a[:,0];c=a[:,2]-a[:,0];uvstats.append({'name':uv.name,'collapsed':int((abs(b[:,0]*c[:,1]-b[:,1]*c[:,0])<2e-14).sum())})
 R[key]={'triangles':len(t),'uv':uvstats,'zero_corner_normals':int((np.linalg.norm(norm,axis=1)<.9).sum()),'bounds':[list(min(v.co[i] for v in me.vertices) for i in range(3)),list(max(v.co[i] for v in me.vertices) for i in range(3))]}
 scene.render.filepath=str(V/(key+'_constant.png'));bpy.ops.render.render(write_still=True)
 if key=='M4':
  bpy.context.view_layer.objects.active=ob;ob.select_set(True)
  if me.has_custom_normals:bpy.ops.mesh.customdata_custom_splitnormals_clear()
  for f in me.polygons:f.use_smooth=True
  scene.render.filepath=str(V/'M4_recalculated.png');bpy.ops.render.render(write_still=True)
 print('PHANTOM_DIAGNOSED',key,flush=True)
(O/'geometry_diagnosis.json').write_text(json.dumps(R,indent=2),encoding='utf-8')
