import bpy, math, json, sys
from pathlib import Path
from mathutils import Matrix, Vector, Quaternion
O=Path(__file__).parent
BASE=O.parents[1]
fit=json.loads((O/'fit_final.json').read_text())
profile=json.loads((O/'profile.json').read_text())
sys.path.insert(0,str(O.parent))
from fit_pose import solve_arm
specs=[
 ('idle','M4ContactImpact20260910','M4_idle',180,120),
 ('aim','M4ContactImpact20260910','M4_aim',2,120),
 ('fire','M4ContactImpact20260910','M4_fire',46,120),
 ('aim_fire','M4ContactImpact20260910','M4_aim_fire',46,120),
 ('equip','M4WrapGrip20260910','M4_MAT_equip_charge',38,120),
 ('reload','M4TacticalToss20260910','M4_MAT_reload',126,480),
 ('reload_empty','M4SlapImpact20260910','M4_MAT_reload_empty',162,480),
 ('drum_reload','M4DrumContact20260910','A_M4_DrumContact_reload',126,240),
 ('drum_reload_empty','M4DrumContact20260910','A_M4_DrumContact_reload_empty',148,240)]
def smooth(x):
 x=max(0,min(1,x));return x*x*(3-2*x)
def weight(clip,f,end):
 if 'reload' in clip:return 1-smooth((f-(20 if clip.startswith('drum') else 9))/(8 if clip.startswith('drum') else 7)) + smooth((f-(end-24))/8)
 # Existing equip uses the right hand for charging; the left supports throughout.
 return 1
release=json.loads((O/'release_profile.json').read_text()) if (O/'release_profile.json').exists() else []
report=json.loads((O/'animation_build.json').read_text()) if (O/'animation_build.json').exists() else {}
for clip,folder,action,end,hz in specs:
 if '--' in sys.argv and clip not in sys.argv[sys.argv.index('--')+1:]:continue
 source=BASE/folder/('M4_DrumContact_Editable.blend' if clip.startswith('drum') else 'M4_Hand_MAT_Editable.blend')
 bpy.ops.wm.open_mainfile(filepath=str(source));r=bpy.data.objects['SK_M4_Infima'];s=bpy.context.scene
 names=[b.name for b in r.pose.bones];left=[n for n in names if n.endswith('_l')];parents={b.name:b.parent.name if b.parent else None for b in r.pose.bones}
 rest={b.name:b.matrix_local.copy() for b in r.data.bones};lr={n:rest[parents[n]].inverted()@rest[n] if parents[n] else rest[n] for n in names}
 a=bpy.data.actions[action];r.animation_data.action=a;r.animation_data.action_slot=a.slots[0]
 samples=[]
 for k in range(round(end*hz/60)+1):
  f=k*60/hz;s.frame_set(int(f),subframe=f%1);bpy.context.view_layer.update();samples.append({b.name:b.matrix.copy() for b in r.pose.bones})
 r.animation_data.action=None
 output=[];maxshift=0;maxscale=0
 for k,old in enumerate(samples):
  f=k*60/hz;w=weight(clip,f,end);p={n:m.copy() for n,m in old.items()}
  if w>0:
   H=old['WPN_root']@Matrix(fit['hand_in_root']);un,fn,hn='upperarm_l','lowerarm_l','hand_l'
   opening=0
   if 'reload' in clip:
    if f<end/2:u=max(0,min(1,f/9))
    else:u=1-max(0,min(1,(f-(end-12))/12))
    retreat=smooth((u-fit.get('retreat_start',0))/(1-fit.get('retreat_start',0)));opening=smooth(u*fit.get('release_open_speed',1))
    grip=old['WPN_root']@Matrix(fit['grip_in_root'])
    # Withdraw out of the side of the opening before following the magazine.
    H.translation+=grip.to_3x3()@Vector(fit['release_vector'])*retreat
   if w<1:
    loc,q,z=old[hn].decompose();L,Q,Z=H.decompose();H=Matrix.LocRotScale(loc.lerp(L,w),q.slerp(Q,w),z)
    if 'reload' in clip:H.translation+=(grip.to_3x3()@Vector((fit['release_vector'][0]*.8,fit['release_vector'][1]*.8,-.14 if clip=='reload_empty' else -.10)))*math.sin(math.pi*w)
   grip=old['WPN_root']@Matrix(fit['grip_in_root'])
   solve_arm(p,rest,H,grip,w)
   for n in left:
    if any(n.startswith(d) for d in ['index','middle','ring','pinky','thumb']):
     digitbasis=Matrix(fit['basis'][n])
     if 'reload' in clip and release:
      t=max(0,min(1,f/9)) if f<end/2 else 1-max(0,min(1,(f-(end-12))/12));index=min(len(release)-2,int(t*(len(release)-1)));lo,hi=release[index],release[index+1]
      blend=max(0,min(1,(t-lo['u'])/(hi['u']-lo['u'])))
      digitbasis=Quaternion(lo['basis'][n]).slerp(Quaternion(hi['basis'][n]),blend).to_matrix().to_4x4()
     p[n]=p[parents[n]]@lr[n]@digitbasis
  # Blend local rotations and clavicle reach only. Never translate finger joints.
  basis={}
  for n in names:
   original=lr[n].inverted()@(old[parents[n]].inverted()@old[n] if parents[n] else old[n])
   if n in left and w>0:
    targetlocal=lr[n].inverted()@(p[parents[n]].inverted()@p[n] if parents[n] else p[n]);loc,q,z=original.decompose();L,Q,Z=targetlocal.decompose()
    # Wrist follows the explicit side-entry path. Local-only arm blending would cut its corner through the frame.
    digit=n.startswith(('index','middle','ring','pinky','thumb'));blend=w if digit or 'twist' in n else 1
    basis[n]=Matrix.LocRotScale(L if n=='clavicle_l' else loc,q.slerp(Q,blend),z)
   else:basis[n]=original
  output.append(basis)
 a=bpy.data.actions.new(profile['animation_prefix']+clip);a.use_fake_user=True;r.animation_data.action=a;previous={}
 for k,pose in enumerate(output):
  for n,m in pose.items():
   loc,q,z=m.decompose()
   if n in previous and previous[n].dot(q)<0:q.negate()
   previous[n]=q.copy();b=r.pose.bones[n];b.rotation_mode='QUATERNION';b.location=loc;b.rotation_quaternion=q;b.scale=z
   for prop in ['location','rotation_quaternion','scale']:b.keyframe_insert(prop,frame=k*60/hz)
 for layer in a.layers:
  for strip in layer.strips:
   for bag in strip.channelbags:
    for curve in bag.fcurves:
     for key in curve.keyframe_points:key.interpolation='LINEAR'
 s.render.fps=60;s.frame_start=0;s.frame_end=end;s.frame_set(end)
 # Keep an editable source for each clip, with the actual attachment parented to the weapon bone.
 with bpy.data.libraries.load(str(O/profile['fitted_mesh']),link=False) as (src,dst):dst.objects=[n for n in src.objects if n.startswith(profile['mesh_prefix'])]
 for ob in dst.objects:
  local=Matrix(fit['attachment_local'][ob.name]);s.collection.objects.link(ob);ob.matrix_world=r.matrix_world@r.pose.bones['WPN_root'].matrix@Matrix(fit['grip_in_root'])@local
  world=ob.matrix_world.copy();ob.parent=r;ob.parent_type='BONE';ob.parent_bone='WPN_root';bpy.context.view_layer.update();ob.matrix_world=world
 bpy.ops.wm.save_as_mainfile(filepath=str(O/(a.name+'.blend')))
 bpy.ops.object.select_all(action='DESELECT');r.select_set(True);bpy.context.view_layer.objects.active=r
 bpy.ops.export_scene.fbx(filepath=str(O/(a.name+'.fbx')),use_selection=True,object_types={'ARMATURE'},axis_forward='-Y',axis_up='Z',add_leaf_bones=False,bake_anim=True,bake_anim_use_all_actions=False,bake_anim_use_nla_strips=False,bake_anim_force_startend_keying=True,bake_anim_step=60/hz,bake_anim_simplify_factor=0)
 report[clip]={'source':str(source),'action':action,'frames':end,'duration':end/60,'sample_rate':hz,'max_shoulder_shift_m':maxshift,'unchanged_contact_interval_frames':[28 if clip.startswith('drum') else 16,end-24] if 'reload' in clip else None}
 (O/'animation_build.json').write_text(json.dumps(report,indent=2));print('VERTICAL_CLIP_DONE',clip,flush=True)
print('VERTICAL_ANIMATIONS_DONE',flush=True)
