"""Replace only the three thumb rotation tracks after refining the release curve."""
import bpy,json,sys,shutil,math
from pathlib import Path
from mathutils import Quaternion,Vector
O=Path(__file__).parent;weapon,variant=sys.argv[sys.argv.index('--')+1:];D=O/weapon/variant;release=json.loads((O/'m4'/variant/'release_profile.json').read_text());buildfile=D/('animation_build.json' if weapon=='m4' else 'build.json');build=json.loads(buildfile.read_text());names=[f'thumb_{j:02}_l' for j in [1,2,3]]
def smooth(t):t=max(0,min(1,t));return t*t*(3-2*t)
akm_fit=json.loads((O/'akm/fits.json').read_text()).get(variant,{})
transition_file=D/'thumb_transition.json'
transitions=json.loads(transition_file.read_text()) if weapon=='akm' and transition_file.exists() else {}
for clip,info in build.items():
 if 'reload' not in clip and not (weapon=='akm' and variant=='vertical'):continue
 name=f'A_{weapon.upper()}_{variant.title() if weapon=="m4" else variant}_{clip}';backup=O/'BeforeReleaseFix'/weapon/variant;backup.mkdir(parents=True,exist_ok=True)
 for ext in ['.blend','.fbx']:
  if not (backup/(name+ext)).exists():shutil.copy2(D/(name+ext),backup/(name+ext))
 bpy.ops.wm.open_mainfile(filepath=info['source']);r=bpy.data.objects['SK_M4_Infima'];s=bpy.context.scene
 if weapon=='m4':a=bpy.data.actions[info['action']];r.animation_data.action=a;r.animation_data.action_slot=a.slots[0]
 elif 'reload' not in clip:a=bpy.data.actions['AKM_EquipCharge' if clip=='equip' else 'AKM_Native_'+clip];r.animation_data.action=a;r.animation_data.action_slot=a.slots[0]
 hz=info['sample_rate'];fps=60 if weapon=='m4' else 120;end=info['frames'];out=[];prev={}
 for k in range(round(end*hz/fps)+1):
  f=k*fps/hz;s.frame_set(int(f),subframe=f%1)
  if 'reload' not in clip:w=1;u=0
  elif weapon=='m4':w=1-smooth((f-(20 if clip.startswith('drum') else 9))/(8 if clip.startswith('drum') else 7))+smooth((f-(end-24))/8);u=max(0,min(1,f/9)) if f<end/2 else 1-max(0,min(1,(f-(end-12))/12))
  else:
   start=380 if 'empty' in clip else 270;finish=start+60;w=1-smooth((f-18)/24)+smooth((f-start)/40);u=max(0,min(1,f/18)) if f<end/2 else 1-max(0,min(1,(f-(finish-24))/24))
  i=min(len(release)-2,int(u*(len(release)-1)));lo,hi=release[i:i+2];t=max(0,min(1,(u-lo['u'])/(hi['u']-lo['u'])));row={}
  for n in names:
   original=r.pose.bones[n].matrix_basis.to_quaternion();target=Quaternion(lo['basis'][n]).slerp(Quaternion(hi['basis'][n]),t)
   if weapon=='akm' and n=='thumb_01_l':target=Quaternion(akm_fit.get('thumb_root_delta',[1,0,0,0]))@target
   q=original.slerp(target,w)
   if n=='thumb_01_l' and clip in transitions:
    correction=transitions[clip];start,peak,end_transition=[correction[k] for k in ['start','peak','end']]
    amount=smooth((f-start)/(peak-start)) if f<=peak else 1-smooth((f-peak)/(end_transition-peak))
    q=Quaternion(Vector(correction['axis']).normalized(),math.radians(correction['degrees'])*amount)@q
   if n in prev and q.dot(prev[n])<0:q.negate()
   row[n]=list(q);prev[n]=q.copy()
  out.append(row)
 bpy.ops.wm.open_mainfile(filepath=str(D/(name+'.blend')));r=bpy.data.objects['SK_M4_Infima'];s=bpy.context.scene;a=r.animation_data.action
 for layer in a.layers:
  for strip in layer.strips:
   for bag in strip.channelbags:
    for curve in bag.fcurves:
     n=next((n for n in names if curve.data_path==f'pose.bones["{n}"].rotation_quaternion'),None)
     if n:
      assert len(curve.keyframe_points)==len(out),(name,n,len(curve.keyframe_points),len(out))
      for k,point in enumerate(curve.keyframe_points):point.co.y=out[k][n][curve.array_index]
      curve.update()
 s.frame_set(0);bpy.ops.wm.save_as_mainfile(filepath=str(D/(name+'.blend')));bpy.ops.object.select_all(action='DESELECT');r.select_set(True);bpy.context.view_layer.objects.active=r
 bpy.ops.export_scene.fbx(filepath=str(D/(name+'.fbx')),use_selection=True,object_types={'ARMATURE'},axis_forward='-Y',axis_up='Z',add_leaf_bones=False,bake_anim=True,bake_anim_use_all_actions=False,bake_anim_use_nla_strips=False,bake_anim_force_startend_keying=True,bake_anim_step=fps/hz,bake_anim_simplify_factor=0)
 info['thumb_release_revision']='outward-before-unfold-with-akm-transition-clearance';print('THUMB_RELEASE_REFRESHED',weapon,variant,clip,flush=True)
buildfile.write_text(json.dumps(build,indent=2))
