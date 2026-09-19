import bpy, math, json, sys
from pathlib import Path
from mathutils import Matrix, Vector, Quaternion
O=Path(__file__).parent
BASE=O.parents[1]
fit=json.loads((O/'fit_final.json').read_text())
release=json.loads((O/'release_profile.json').read_text())
def release_angles(t):
 t=max(0,min(11,t))*2;i=min(int(t),len(release)-2);a=t-i
 return [x+(y-x)*a for x,y in zip(release[i]['parameters'],release[i+1]['parameters'])]
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
    phase=f if f<end/2 else end-f
    finger_angles=release_angles(phase);retreat=smooth((phase-4)/5)
    grip=old['WPN_root']@Matrix(fit['grip_in_root'])
    # Withdraw out of the side of the opening before following the magazine.
    H.translation+=grip.to_3x3().col[1].normalized()*(.11*retreat)
   if w<1:
    loc,q,z=old[hn].decompose();L,Q,Z=H.decompose();H=Matrix.LocRotScale(loc.lerp(L,w),q.slerp(Q,w),z)
    if 'reload' in clip:H.translation+=grip.to_3x3().col[1].normalized()*(.08*math.sin(math.pi*w))
   # Translate the shoulder girdle as a unit for the forward support reach.
   # Both arm segments and the wrist contact retain their original lengths/position.
   support_offset=Vector((-.015,.13,-.025))*w
   p['clavicle_l']=old['clavicle_l'].copy();p['clavicle_l'].translation+=support_offset
   A=old[un].translation+support_offset;target=H.translation;l1=(rest[fn].translation-rest[un].translation).length;l2=(rest[hn].translation-rest[fn].translation).length
   axis=(target-A).normalized();shift=axis*max(0,(target-A).length-(l1+l2-.015));A+=shift;maxshift=max(maxshift,shift.length)
   p['clavicle_l'].translation+=shift
   dist=(target-A).length;axis=(target-A).normalized();pole=old[fn].translation-A;pole-=axis*pole.dot(axis)
   desired=H.to_3x3()@rest[hn].to_3x3().inverted()@(rest[hn].translation-rest[fn].translation).normalized()
   natural=target-desired*l2-A;natural-=axis*natural.dot(axis);pole=pole.normalized().lerp(natural.normalized(),w).normalized()
   along=(l1*l1-l2*l2+dist*dist)/(2*dist);E=A+axis*along+pole*math.sqrt(max(0,l1*l1-along*along))
   u=(E-A).normalized();v=(target-E).normalized();ou=(old[fn].translation-old[un].translation).normalized();ov=(old[hn].translation-old[fn].translation).normalized()
   p[un]=Matrix.LocRotScale(A,ou.rotation_difference(u)@old[un].to_quaternion(),Vector((1,1,1)))
   p[fn]=Matrix.LocRotScale(E,ov.rotation_difference(v)@old[fn].to_quaternion(),Vector((1,1,1)))
   for n in ['upperarm_twist_01_l','upperarm_twist_02_l']:p[n]=p[un]@old[un].inverted()@old[n]
   neutral=p[fn].to_quaternion()@rest[fn].to_quaternion().inverted()@rest[hn].to_quaternion();q=H.to_quaternion()@neutral.inverted();twist=2*math.atan2(Vector((q.x,q.y,q.z)).dot(v),q.w);twist=(twist+math.pi)%(2*math.pi)-math.pi
   for n,t in [('lowerarm_twist_02_l',.55),('lowerarm_twist_01_l',.95)]:
    m=p[fn]@rest[fn].inverted()@rest[n];p[n]=Matrix.LocRotScale(m.translation,Quaternion(v,twist*t)@m.to_quaternion(),Vector((1,1,1)))
   p[hn]=H
   for n in left:
    if any(n.startswith(d) for d in ['index','middle','ring','pinky','thumb']):
     digitbasis=Matrix(fit['basis'][n])
     if 'reload' in clip and n.startswith(('index_0','middle_0','ring_0')):
      digit=n.split('_')[0];joint=int(n.split('_')[1]);offset={'index':0,'middle':1,'ring':2}[digit]
      angle=finger_angles[12+offset] if joint==1 else finger_angles[6+offset*2+joint-2]
      digitbasis=Quaternion((0,0,1),math.radians(angle)).to_matrix().to_4x4()
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
 a=bpy.data.actions.new('A_M4_Foregrip_'+clip);a.use_fake_user=True;r.animation_data.action=a;previous={}
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
 with bpy.data.libraries.load(str(O/'M4_Foregrip_Fitted.blend'),link=False) as (src,dst):dst.objects=[n for n in src.objects if n.startswith('FG_')]
 for ob in dst.objects:
  local=Matrix(fit['grip_matrix']).inverted()@ob.matrix_basis.copy();s.collection.objects.link(ob);ob.matrix_world=r.matrix_world@r.pose.bones['WPN_root'].matrix@Matrix(fit['grip_in_root'])@local
  world=ob.matrix_world.copy();ob.parent=r;ob.parent_type='BONE';ob.parent_bone='WPN_root';bpy.context.view_layer.update();ob.matrix_world=world
 bpy.ops.wm.save_as_mainfile(filepath=str(O/(a.name+'.blend')))
 bpy.ops.object.select_all(action='DESELECT');r.select_set(True);bpy.context.view_layer.objects.active=r
 bpy.ops.export_scene.fbx(filepath=str(O/(a.name+'.fbx')),use_selection=True,object_types={'ARMATURE'},axis_forward='-Y',axis_up='Z',add_leaf_bones=False,bake_anim=True,bake_anim_use_all_actions=False,bake_anim_use_nla_strips=False,bake_anim_force_startend_keying=True,bake_anim_step=60/hz,bake_anim_simplify_factor=0)
 report[clip]={'source':str(source),'action':action,'frames':end,'duration':end/60,'sample_rate':hz,'max_additional_reach_shift_m':maxshift,'support_shoulder_offset_m':[-.015,.13,-.025],'unchanged_contact_interval_frames':[28 if clip.startswith('drum') else 16,end-24] if 'reload' in clip else None}
 (O/'animation_build.json').write_text(json.dumps(report,indent=2));print('FOREGRIP_CLIP_DONE',clip,flush=True)
print('FOREGRIP_ANIMATIONS_DONE',flush=True)
