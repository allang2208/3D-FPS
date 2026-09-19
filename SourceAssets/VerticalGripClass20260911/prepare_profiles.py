import bpy,json,math
from pathlib import Path
from mathutils import Matrix,Vector,Quaternion
O=Path(__file__).parent;common=json.loads((O/'common_hand_pose.json').read_text());vp=json.loads((O/'vertical/profile.json').read_text());vf=json.loads((O/'vertical/fit_final.json').read_text());VH=Matrix(vf['grip_in_root']).inverted()@Matrix(vf['hand_in_root']);axis=VH.to_3x3().inverted()@Vector(vp['forearm_direction']);(O/'arm_standard.json').write_text(json.dumps({'forearm_direction_in_hand':list(axis),'pole_reference':'PrismHandstop20260910/GripAnimation','twist_weights':[.55,.95]},indent=2))
p=O/'prism';profile=json.loads((p/'profile.json').read_text());fit=json.loads((p/'fit_final.json').read_text());bpy.ops.wm.open_mainfile(filepath=str(Path(profile['source'])/'A_M4_Prism_idle.blend'));r=bpy.data.objects['SK_M4_Infima'];s=bpy.context.scene;s.frame_set(0);bpy.context.view_layer.update();ref={n:r.pose.bones[n].matrix.translation.copy() for n in ['upperarm_l','lowerarm_l','hand_l']};upper=(ref['lowerarm_l']-ref['upperarm_l']).normalized();G=r.pose.bones['WPN_root'].matrix@Matrix(fit['grip_in_root']);H=r.pose.bones['WPN_root'].matrix@Matrix(fit['hand_in_root']);fore=H.to_3x3()@axis;l1=(r.data.bones['lowerarm_l'].head_local-r.data.bones['upperarm_l'].head_local).length;l2=(r.data.bones['hand_l'].head_local-r.data.bones['lowerarm_l'].head_local).length;A=H.translation-fore*l2-upper*l1
r.animation_data.action=bpy.data.actions['M4_idle'];r.animation_data.action_slot=r.animation_data.action.slots[0];s.frame_set(0);bpy.context.view_layer.update();profile['shoulder_offset']=list(A-r.pose.bones['upperarm_l'].matrix.translation);profile['forearm_direction']=list(G.to_3x3().inverted()@fore)
# The short stop keeps the two contact fingers fitted; lower fingers use the common closed hand.
for n,m in common.items():
 if n.startswith(('ring_','pinky_')):fit['basis'][n]=m
(p/'profile.json').write_text(json.dumps(profile,indent=2));(p/'fit_final.json').write_text(json.dumps(fit,indent=2));(p/'contact_overrides.json').write_text(json.dumps({n:m for n,m in fit['basis'].items() if m!=common.get(n)},indent=2))
release=[]
for k in range(37):
 u=k/36;t=u*u*(3-2*u);basis={}
 for n,m in fit['basis'].items():
  q=Matrix(m).to_quaternion();target=q.copy()
  if not n.startswith('thumb') and ('_02_' in n or '_03_' in n or '_01_' in n):target=Quaternion((0,0,1),math.radians(15 if n.startswith('pinky') and '_02_' in n else 10 if n.startswith('pinky') and '_03_' in n else 0))
  basis[n]=list(q.slerp(target,t))
 release.append({'u':u,'basis':basis})
(p/'release_profile.json').write_text(json.dumps(release,indent=2));print('FAMILY_PROFILE_READY',profile)
