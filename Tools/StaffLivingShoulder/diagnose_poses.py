import bpy,numpy as np,json
from pathlib import Path
from mathutils import Matrix,Vector
ROOT=Path('D:/FPS3D/FPSGAME');OUT=ROOT/'SourceAssets/StaffLivingShoulder20261017';report={}
for role in ['FemaleA','FemaleB']:
 d=np.load(OUT/'Diagnosis'/f'{role}_binding.npz');names=list(d['names']);motions={}
 for clip in ['idle','attack']:
  bpy.ops.wm.read_factory_settings(use_empty=True)
  file=OUT/'Inputs'/f'{role}_{clip}.fbx'
  if not file.exists():file=ROOT/'SourceAssets'/(f'FacelessReceptionist20261007/V04/MotionSources/A_Receptionist_{clip}.fbx' if role=='FemaleA' else f'FacelessResearcher20261009/V04/Motion/A_Researcher_source_{clip}.fbx')
  bpy.ops.import_scene.fbx(filepath=str(file),use_anim=True)
  rig=next(o for o in bpy.context.scene.objects if o.type=='ARMATURE');first,last=map(int,rig.animation_data.action.frame_range)
  inv={n:(rig.matrix_world@rig.data.bones[n].matrix_local).inverted() for n in names}
  frames=[first] if clip=='idle' else [first+int((last-first)*.25),first+int((last-first)*.60)]
  for frame in frames:
   bpy.context.scene.frame_set(frame);bpy.context.view_layer.update()
   motions[clip+str(frame)]=np.array([np.array(rig.matrix_world@rig.pose.bones[n].matrix@inv[n]) for n in names])
 np.savez_compressed(OUT/'Diagnosis'/f'{role}_poses.npz',names=d['names'],**motions)
 for version in ['before','after']:
  p=d['current'];w=d['weights']
  if version=='after':fix=np.load(OUT/'Diagnosis'/f'{role}_repaired.npz');p=fix['current'];w=fix['weights']
  bpy.ops.wm.read_factory_settings(use_empty=True);scene=bpy.context.scene
  for idx,(label,mats) in enumerate(motions.items()):
   posed=np.zeros_like(p)
   for bi in range(len(names)):
    ids=np.where(w[:,bi]>0)[0]
    if len(ids):posed[ids]+=(p[ids]@mats[bi,:3,:3].T+mats[bi,:3,3])*w[ids,bi,None]
   mask=(d['source'][:,2]>1.3)&(d['source'][:,2]<1.6)&(abs(d['source'][:,0])<.2)
   center=posed[mask].mean(0);posed-=center;posed[:,2]+=.12
   me=bpy.data.meshes.new(label);me.from_pydata(posed,[],d['triangles'].tolist());me.update()
   for f in me.polygons:f.use_smooth=True
   for back in [False,True]:
    ob=bpy.data.objects.new(label+str(back),me);scene.collection.objects.link(ob);ob.location=(idx*1.05,0,-1.0*back);ob.rotation_euler.z=np.pi if back else 0
  scene.world=bpy.data.worlds.new('DiagnosticWorld');scene.world.color=(.035,.035,.035)
  scene.render.engine='BLENDER_WORKBENCH';scene.render.resolution_x=1800;scene.render.resolution_y=1200;scene.render.resolution_percentage=100
  sh=scene.display.shading;sh.light='STUDIO';sh.color_type='SINGLE';sh.single_color=(.65,.68,.72);sh.show_shadows=True;sh.show_cavity=True;sh.cavity_type='BOTH';sh.show_specular_highlight=False;sh.show_backface_culling=True;sh.background_type='WORLD'
  ca=bpy.data.cameras.new('ShoulderDiagnostic');cam=bpy.data.objects.new('ShoulderDiagnostic',ca);scene.collection.objects.link(cam);cam.location=(1.05,-5,-.25);target=Vector((1.05,0,-.25));cam.rotation_euler=(target-cam.location).to_track_quat('-Z','Y').to_euler();ca.type='ORTHO';ca.ortho_scale=3.2;scene.camera=cam
  scene.render.filepath=str(OUT/'Diagnosis'/f'{role}_{version}_poses.png');bpy.ops.render.render(write_still=True)
 print('POSE_DIAG',role,flush=True)
