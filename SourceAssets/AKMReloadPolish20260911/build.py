import bpy,json,math,runpy
from pathlib import Path
from mathutils import Quaternion
O=Path(__file__).parent;B=O.parent/'AKMAttachments20260911';report={}
def smooth(x):
 x=max(0,min(1,x));return x*x*(3-2*x)
def source_frame(f):
 xs=[0,44,56,86,106,120];ys=[0,44,60,72,100,120];ds=[(ys[i+1]-ys[i])/(xs[i+1]-xs[i]) for i in range(5)];ms=[1]+[2*ds[i-1]*ds[i]/(ds[i-1]+ds[i]) for i in range(1,5)]+[1]
 if f>=120:return f
 for i in range(5):
  if f<=xs[i+1]:
   h=xs[i+1]-xs[i];t=(f-xs[i])/h
   return (2*t**3-3*t*t+1)*ys[i]+(t**3-2*t*t+t)*h*ms[i]+(-2*t**3+3*t*t)*ys[i+1]+(t**3-t*t)*h*ms[i+1]
for variant in ['base','prism','angled']:
 for clip in ['reload','reload_empty','drum_reload','drum_reload_empty']:
  src=B/'AKM_Attachments_Editable.blend' if variant=='base' else B/variant/f'A_AKM_{variant}_{clip}.blend'
  bpy.ops.wm.open_mainfile(filepath=str(src));r=bpy.data.objects['SK_M4_Infima'];s=bpy.context.scene
  old=bpy.data.actions['AKM_Native_'+clip.replace('drum_','')] if variant=='base' else bpy.data.actions[f'A_AKM_{variant}_{clip}']
  idle=bpy.data.actions['AKM_Native_idle'];r.animation_data.action=idle;r.animation_data.action_slot=idle.slots[0];s.frame_set(0)
  index={n:r.pose.bones[n].rotation_quaternion.copy() if r.pose.bones[n].rotation_mode=='QUATERNION' else r.pose.bones[n].matrix_basis.to_quaternion() for n in ['index_01_r','index_02_r','index_03_r']}
  r.animation_data.action=old;r.animation_data.action_slot=old.slots[0];end=515 if clip.endswith('empty') else 400;poses=[]
  for f in range(end+1):
   t=source_frame(f) if clip.startswith('drum') else f;s.frame_set(int(t),subframe=t%1)
   poses.append({b.name:b.matrix_basis.copy() for b in r.pose.bones})
  name='A_AKM_'+('' if variant=='base' else variant+'_')+clip;a=bpy.data.actions.new(name+'_Polished');a.use_fake_user=True;r.animation_data.action=a;prev={}
  for f,pose in enumerate(poses):
   opening=(smooth((f-78)/12)*(1-smooth((f-98)/14))) if clip.startswith('drum') else 0
   for n,m in pose.items():
    loc,q,z=m.decompose()
    if n in index:q=index[n].copy()
    if opening and n.endswith('_l') and n.startswith(('index_02','index_03','middle_02','middle_03','ring_02','ring_03','pinky_02','pinky_03')):q=q.slerp(Quaternion(),opening*.85)
    if n in prev and prev[n].dot(q)<0:q.negate()
    prev[n]=q.copy();b=r.pose.bones[n];b.rotation_mode='QUATERNION';b.location=loc;b.rotation_quaternion=q;b.scale=z
    for prop in ['location','rotation_quaternion','scale']:b.keyframe_insert(prop,frame=f)
  for layer in a.layers:
   for strip in layer.strips:
    for bag in strip.channelbags:
     for curve in bag.fcurves:
      for key in curve.keyframe_points:key.interpolation='LINEAR'
  s.render.fps=120;s.frame_start=0;s.frame_end=end;s.frame_set(0);D=O/variant;D.mkdir(exist_ok=True)
  for ob in s.objects:
   if ob.name.startswith('SM_AKM_'):ob.hide_render=not (ob.name=='SM_AKM_'+variant or (clip.startswith('drum') and ob.name=='SM_AKM_drum'))
  runpy.run_path(str(B/'preview_visibility.py'))['configure_preview'](clip.startswith('drum'),variant)
  bpy.ops.wm.save_as_mainfile(filepath=str(D/(name+'.blend')))
  bpy.ops.object.select_all(action='DESELECT');r.select_set(True);bpy.context.view_layer.objects.active=r
  bpy.ops.export_scene.fbx(filepath=str(D/(name+'.fbx')),use_selection=True,object_types={'ARMATURE'},axis_forward='-Y',axis_up='Z',add_leaf_bones=False,bake_anim=True,bake_anim_use_all_actions=False,bake_anim_use_nla_strips=False,bake_anim_force_startend_keying=True,bake_anim_step=1,bake_anim_simplify_factor=0)
  report[name]={'source':str(src),'duration':end/120,'index_pose':'accepted AKM idle','drum_release_frame120':86 if clip.startswith('drum') else None};print('POLISH_CLIP_PASS',name,flush=True)
(O/'build.json').write_text(json.dumps(report,indent=2));print('AKM_RELOAD_POLISH_BUILD_PASS')
