"""Author dual pistol actions on the existing left/right Manny pistol meshes.

Blender --background --python author_dual.py -- M1911|DW715 [--sprint-smooth|--revolver-reload-flick]
Reference: BV1PExtzNEBS, holding/fire 7-10 and 30-35 s, reload 9-12/35-37 s.
Writes current NaturalAimV3, SprintSmoothV5 or RevolverReloadFlickV6 sources.
The accepted skeletal mesh FBXs are reused. This script does not render or test.
"""
import json, math, sys
from pathlib import Path
import bpy, bmesh
from mathutils import Matrix, Vector, Euler, Quaternion

O=Path(__file__).parent; S=O.parent
smooth_sprint='--sprint-smooth' in sys.argv
if '--sprint-reference' in sys.argv:raise ValueError('SprintReferenceV4 is archived; use --sprint-smooth')
sprint_update=smooth_sprint
revolver_flick='--revolver-reload-flick' in sys.argv
revision='RevolverReloadFlickV6' if revolver_flick else 'SprintSmoothV5' if smooth_sprint else 'NaturalAimV3'
P=O/revision
profile=json.loads((O/'NaturalAimV3'/'pose_profile.json').read_text(encoding='utf-8'))
sprint_profile=json.loads((P/'sprint_profile.json').read_text(encoding='utf-8')) if sprint_update else None
weapon=sys.argv[sys.argv.index('--')+1]
if revolver_flick and (weapon!='DW715' or sprint_update):
 raise ValueError('--revolver-reload-flick is a DW715 reload-only export')
flick_profile=json.loads((P/'reload_profile.json').read_text(encoding='utf-8')) if revolver_flick else None
spec={
 'M1911':('M1911Contact20260913/M1911_Contact_Editable.blend','SK_M1911_Manny','M1911_LOW','M1911_Contact_'),
 'DW715':('DanWesson715Upgrade20260914/DanWesson715_Upgrade_Editable.blend','SK_DW715_Manny','DW715_LOW','DW715V2_')
}[weapon]
bpy.context.preferences.filepaths.save_version=0
try:bpy.ops.wm.open_mainfile(filepath=str(S/spec[0]))
except RuntimeError as e:
 if 'Missing library override hierarchy root data' not in str(e):raise
scene=bpy.context.scene; scene.render.fps=60
rig=bpy.data.objects[spec[1]];rig.data.pose_position='POSE'
rest={b.name:b.matrix_local.copy() for b in rig.data.bones}
parent={b.name:b.parent.name if b.parent else None for b in rig.data.bones};names=list(rest)
lr={n:rest[parent[n]].inverted()@rest[n] if parent[n] else rest[n] for n in names}
reload_file='M1911ReloadTiming20260913/M1911_ReloadReady_Editable.blend' if weapon=='M1911' else 'DanWesson715LeftRecovery20260914/DanWesson715_LeftRecovery_Editable.blend'
reload_prefix='M1911_ReloadReady_' if weapon=='M1911' else 'DW715_LeftRecovery_'
with bpy.data.libraries.load(str(S/reload_file),link=False) as (src,dst):
 dst.actions=[n for n in src.actions if n.startswith(reload_prefix)]

def sample(action,t):
 rig.animation_data_create();rig.animation_data.action=action;rig.animation_data.action_slot=action.slots[0]
 frame=t*60;scene.frame_set(int(frame),subframe=frame%1);bpy.context.view_layer.update()
 return {b.name:b.matrix.copy() for b in rig.pose.bones}

idle=sample(bpy.data.actions[spec[3]+'idle'],0)
Sx=Matrix.Diagonal((-1.,1.,1.,1.))
mirrored={n:(Sx@idle[n[:-2]+'_r']@rest[n[:-2]+'_r'].inverted()@Sx@rest[n])
          if n.endswith('_l') and n[:-2]+'_r' in rest else m.copy() for n,m in idle.items()}
def cv(x,y,z):return Vector((-y,-x,z))
# cv reflects camera right into Blender -X: positive roll leans the gun's top
# toward screen right, so mirrored outward wrist throws use r:+ / l:-.
def turn(p,y,r):return Euler(tuple(math.radians(v) for v in (-p,-r,-y)),'XYZ').to_quaternion()
def smooth(x):x=max(0.,min(1.,x));return x*x*(3-2*x)
def keys(rows,t):
 if t<=rows[0][0]:return rows[0][1]
 for (a,x),(b,y) in zip(rows,rows[1:]):
  if t<=b:return x+(y-x)*smooth((t-a)/(b-a))
 return rows[-1][1]

def ease(x):
 x=max(0.,min(1.,x));return x*x*x*(x*(6*x-15)+10)

def flick_keys(rows,t):
 if t<=rows[0][0]:return rows[0][1]
 for (a,x),(b,y) in zip(rows,rows[1:]):
  if t<=b:return x+(y-x)*ease((t-a)/(b-a))
 return rows[-1][1]

def periodic_stroke(t,settings):
 # Low harmonics retain the asymmetric swing without stopping at every key.
 # Value, velocity and acceleration remain continuous through the loop seam.
 return settings['offset']+sum(c*math.cos(2*math.pi*n*t)+s*math.sin(2*math.pi*n*t)
                               for n,c,s in settings['harmonics'])

def hand_at(p,old,side,H,shoulder,pole_target):
 # The donor is a two-handed stance. Its shoulder and elbow plane cannot serve
 # as the pole for two independent arms entering from the lower screen corners.
 hn='hand_'+side;un='upperarm_'+side;fn='lowerarm_'+side
 old_s=old[un].translation;old_e=old[fn].translation;old_h=old[hn].translation
 target=H.translation;upper_length=(old_e-old_s).length;lower_length=(old_h-old_e).length
 axis=(target-shoulder).normalized();distance=(target-shoulder).length
 reach=(upper_length+lower_length)*.985
 if distance>reach:shoulder=shoulder+axis*(distance-reach);distance=reach
 distance=max(abs(upper_length-lower_length)+.0001,distance)
 pole=pole_target-shoulder;pole-=axis*pole.dot(axis);pole.normalize()
 along=(upper_length**2-lower_length**2+distance**2)/(2*distance)
 elbow=shoulder+axis*along+pole*math.sqrt(max(0.,upper_length**2-along**2))
 old_normal=(old_e-old_s).cross(old_h-old_e).normalized()
 normal=(elbow-shoulder).cross(target-elbow).normalized()
 # Preserve the elbow hinge plane for the upper arm. The forearm inherits palm
 # roll and swings onto its solved segment, as in the accepted casting arm.
 for n,pos,direction,was in [(un,shoulder,elbow-shoulder,old_e-old_s),(fn,elbow,target-elbow,old_h-old_e)]:
  swing=was.rotation_difference(direction)
  hinge=(swing@old_normal).rotation_difference(normal)
  p[n]=Matrix.LocRotScale(pos,hinge@swing@old[n].to_quaternion(),old[n].to_scale())
 ref_lower=rest[hn].translation-rest[fn].translation
 hand_deform=H.to_quaternion()@rest[hn].to_quaternion().inverted()
 aligned_lower=hand_deform@ref_lower.normalized()
 lower_deform=aligned_lower.rotation_difference((target-elbow).normalized())@hand_deform
 p[fn]=Matrix.LocRotScale(elbow,lower_deform@rest[fn].to_quaternion(),old[fn].to_scale())
 p['clavicle_'+side]=old['clavicle_'+side].copy()
 p['clavicle_'+side].translation+=shoulder-old_s
 hand_delta=H@old[hn].inverted()
 for n in names:
  if n==hn or n.endswith('_'+side) and n.startswith(('thumb','index','middle','ring','pinky')):p[n]=hand_delta@old[n]
 for n in names:
  if n.endswith('_'+side) and n.startswith(('upperarm_twist','lowerarm_twist')):
   segment=un if n.startswith('upperarm') else fn
   # Keep the complete helper-to-segment bind transform; fractional roll against
   # an already rolled parent can pinch the Manny sleeve/forearm volume.
   p[n]=p[segment]@rest[segment].inverted()@rest[n]
 if 'ik_hand_'+side in p:p['ik_hand_'+side]=H.copy()

clips={'idle':(1.,spec[3]+'idle',0.),'sprint':(1.,spec[3]+'idle',0.),
       'fire':(.4 if weapon=='DW715' else .34,spec[3]+'fire',.4 if weapon=='DW715' else .733333333),
       'equip':(.65,spec[3]+'idle',0.)}
if weapon=='M1911':
 clips.update({'idle_empty':(1.,spec[3]+'idle_empty',0.),'sprint_empty':(1.,spec[3]+'idle_empty',0.),
 'fire_last':(.34,spec[3]+'fire_last',.733333333),
 'reload':(2.3,reload_prefix+'reload',1.75),'reload_empty':(2.8,reload_prefix+'reload_empty',2.25)})
else:
 for a in range(6):
  for n in range(1,7-a):
   duration=(1.5 if a==0 else .6)+1.1*n+.7
   clips[f'single_{a}_{n}']=(duration,reload_prefix+f'single_{a}_{n}',duration)
 clips['speed_0']=(3.85,reload_prefix+'speed_0',3.85)
if sprint_update:clips={kind:data for kind,data in clips.items() if kind.startswith('sprint')}
if revolver_flick:clips={kind:data for kind,data in clips.items() if kind.startswith(('single_','speed_'))}
if not sprint_update and not revolver_flick:
 clips={kind:data for kind,data in clips.items() if not kind.startswith('sprint') and not (weapon=='DW715' and kind.startswith(('single_','speed_')))}

# Cache source mechanical poses once for both hands; custom gun framing and arm
# solves replace the donor's two-handed gross motion, while preserving mechanics.
mechanics={}
for kind,(duration,action_name,source_duration) in clips.items():
 action=bpy.data.actions[action_name]; rows=[]
 for i in range(round(duration*120)+1):
  t=i/120; source=sample(action,min(source_duration,t/duration*source_duration))
  inv=source['WPN_root'].inverted()
  rows.append({n:inv@source[n] for n in names if n.startswith('WPN_')})
 mechanics[kind]=rows

original_hands=bpy.data.objects['SK_Manny_Arms_Export']
receipt={'reference':'https://www.bilibili.com/video/BV1PExtzNEBS/', 'source':spec[0],
         'mechanical_source':reload_file,'pose_profile':profile,'revision':revision,
         'fps':60,'sample_rate':120,'sides':{}}
if sprint_update:receipt['sprint_profile']=sprint_profile
if revolver_flick:receipt['reload_profile']=flick_profile
for side in ('r','l'):
 dest=P/weapon/side;(dest/'Animations').mkdir(parents=True,exist_ok=True)
 base=idle if side=='r' else mirrored
 sign=1 if side=='r' else -1
 # Separate the guns around the view centre; the 715 has a slightly deeper hold.
 grip=base['hand_'+side].copy()
 target_grip=grip.copy();target_grip.translation=cv(profile['grip_forward'][weapon],sign*profile['grip_side'],profile['grip_height'])
 offset=target_grip.translation-grip.translation
 if side=='r':G=Matrix.Translation(offset)@idle['WPN_root']
 else:
  G=idle['WPN_root'].copy();G.translation=Sx@G.translation+offset
 H=target_grip.copy()
 pivot=H.translation.copy()
 # Keep the physical pistol unmirrored, including lettering and its ejection side.
 right_contact=idle['WPN_root'].inverted()@idle['hand_r']
 left_contact=G.inverted()@H
 contact=right_contact if side=='r' else left_contact
 bore_local=(idle['WPN_root'].inverted().to_3x3()@(idle['WPN_FrontSight'].translation-idle['WPN_RearSight'].translation)).normalized()
 muzzle_local=idle['WPN_root'].inverted()@idle['WPN_SOCKET_Muzzle'].translation
 bore=(G.to_3x3()@bore_local).normalized()
 cant=Quaternion(bore,math.radians(sign*profile['grip_roll']))
 G=Matrix.Translation(pivot)@cant.to_matrix().to_4x4()@Matrix.Translation(-pivot)@G
 aim_target=cv(profile['zero_distance'],0,0)
 # Rotation about the fixed grip also moves the muzzle, so solve the barrel ray
 # iteratively. The bore comes from each weapon's own calibrated sight line.
 for _ in range(5):
  bore=(G.to_3x3()@bore_local).normalized()
  correction=bore.rotation_difference((aim_target-G@muzzle_local).normalized())
  G=Matrix.Translation(pivot)@correction.to_matrix().to_4x4()@Matrix.Translation(-pivot)@G
 H=G@contact
 # Start at the fitted wrist and build its support backwards. A fixed outer
 # elbow pole would force the wrist sideways again when the gun faces forward.
 ref_forearm=(rest['hand_'+side].translation-rest['lowerarm_'+side].translation).normalized()
 forearm=H.to_quaternion()@rest['hand_'+side].to_quaternion().inverted()@ref_forearm
 forearm=Quaternion(cv(0,1,0),math.radians(profile['neutral_wrist_bend']))@forearm
 upper_length=(base['lowerarm_'+side].translation-base['upperarm_'+side].translation).length
 lower_length=(base['hand_'+side].translation-base['lowerarm_'+side].translation).length
 pole_home=H.translation-forearm.normalized()*lower_length
 preferred_shoulder=cv(profile['shoulder'][0],sign*profile['shoulder'][1],profile['shoulder'][2])
 shoulder_home=pole_home+(preferred_shoulder-pole_home).normalized()*upper_length
 actions={};records={}
 for kind,(duration,source_name,source_duration) in clips.items():
  rows=[];frames=[];previous={}
  reload=kind.startswith(('reload','single_','speed_'))
  for i,mech in enumerate(mechanics[kind]):
   t=i/120;u=t/duration;phase=2*math.pi*u+(math.pi if side=='l' else 0.)
   pos=cv(0,0,0);pitch=yaw=roll=0.
   shoulder=shoulder_home.copy();pole=pole_home.copy()
   if sprint_update:
    # A raised carry with opposite arm strokes, not opposing high/low gun flips.
    # The elbow leads the stroke; gun/palm/forearm rotate as a rigid assembly.
    sp=sprint_profile;cycle=(u+(.5 if side=='l' else 0.))%1.
    family=sp['weapons'][weapon];carry=sp['hands'][side]
    stroke=periodic_stroke(cycle,sp['stroke_wave']) if smooth_sprint else keys(sp['stroke_keys'],cycle)
    delayed=(cycle-family['follow_lag_cycles'])%1.
    follow=periodic_stroke(delayed,sp['stroke_wave']) if smooth_sprint else keys(sp['stroke_keys'],delayed)
    cross=math.cos(2*math.pi*cycle)
    # A broad landing arc replaces V4's 0.05-source-second impact pulse.
    contact_drop=-math.cos(2*math.pi*(2*u-sp['footfall_phase'])) if smooth_sprint else keys(sp['footfall_keys'],(2*u)%1.)
    pitch=carry['pitch']+family['pitch_bias']+sp['pitch_stroke']*family['stroke_scale']*follow+sp['pitch_footfall']*contact_drop
    yaw=-sign*(sp['yaw_carry']+sp['yaw_stroke']*cross)
    roll=-sign*(sp['roll_carry']+sp['roll_stroke']*cross)
    pos=cv(carry['elbow_forward']+family['forward_bias']+sp['elbow_forward_stroke']*stroke,
           sign*(sp['elbow_outward']+sp['elbow_side_stroke']*cross),
           carry['elbow_height']+sp['elbow_height_stroke']*stroke+sp['elbow_footfall']*contact_drop)
   elif kind.startswith('sprint'):
    pitch=profile['sprint_pitch']+profile['sprint_pitch_amplitude']*math.sin(phase-.15)
    yaw=-sign*(2+3*math.cos(phase-.2));roll=-sign*(7+3*math.cos(phase))
    pos=cv(-.045+.022*math.sin(phase),sign*(.013+.009*math.cos(phase)),-.025+.018*math.sin(phase-.3))
    shoulder+=cv(.008*math.sin(phase),sign*.002*math.cos(phase),.004*math.sin(phase))
    pole+=cv(.020*math.sin(phase-.25),sign*.012*math.cos(phase),.018*math.sin(phase-.15))
   elif kind.startswith('fire'):
    kick=keys([(0,0),(.018,1),(.065,.75),(.16,.20),(duration,0)],t)
    pitch=(14 if weapon=='DW715' else 11)*kick;roll=-sign*3*kick;pos=cv(-.038*kick,sign*.004*kick,.008*kick)
    shoulder+=cv(-.004*kick,0,0);pole+=cv(-.008*kick,0,.004*kick)
   elif reload:
    pitch=keys([(0,0),(.15,48),(.30,20),(.67,20),(.82,32),(1,0)],u)
    roll=sign*keys([(0,0),(.16,12),(.30,5),(.72,5),(1,0)],u)
    # Mechanical removal stays visible; loading is a belt-level, off-screen action.
    if kind.startswith('single_'):
     start,count=map(int,kind.split('_')[1:]);begin=1.5 if start==0 else .6
     # Every insertion stays below frame; the last cylinder-close brings it up.
     hold=(begin+(count-1)*1.1+.64+.12)/duration
     low=keys([(0,0),(.12,0),(.27,1),(hold,1),(min(.97,hold+.07),.3),(1,0)],u)
    elif kind=='speed_0':low=keys([(0,0),(.18,0),(.32,1),(.82,1),(.94,.25),(1,0)],u)
    else:low=keys([(0,0),(.18,0),(.32,1),(.69,1),(.88,.18),(1,0)],u)
    opening_pos=cv(0,0,0)
    if revolver_flick:
     # Use the cylinder's source clock, never total reload duration. A six-round
     # reload must open with the same wrist throw as a one-round reload.
     fp=flick_profile;clock=t*(3.6/3.85 if kind=='speed_0' else 1.)
     empty=kind=='speed_0' or start==0
     lowering=fp['empty_lowering' if empty else 'tactical_lowering']
     return_start=(.82 if kind=='speed_0' else hold)*duration
     if t<return_start:low=ease((clock-lowering[0])/(lowering[1]-lowering[0]))
     intro=1-ease((clock-lowering[1])/fp['join_below_frame'])
     direction=fp['hands'][side]
     pitch=pitch*(1-intro)+flick_keys(fp['pitch_empty' if empty else 'pitch_tactical'],clock)*intro
     roll=roll*(1-intro)+direction['roll']*flick_keys(fp['roll'],clock)*intro
     yaw=direction['outward']*flick_keys(fp['yaw'],clock)*intro
     carry=1-low
     opening_pos=cv(flick_keys(fp['forward'],clock),direction['outward']*flick_keys(fp['outward'],clock),flick_keys(fp['height'],clock))*carry
     # The fitted palm stays locked to the grip; let the elbow/shoulder support
     # the brief throw instead of twisting a stationary forearm at the wrist.
     follow=flick_keys(fp['arm_follow'],clock)*carry
     shoulder+=cv(0,direction['outward']*.006*follow,.004*follow)
     pole+=cv(.008*follow,direction['outward']*.026*follow,.010*follow)
    pos=cv(-.11*low,sign*.025*low,-.43*low)
    pos+=opening_pos
    shoulder+=cv(-.03*low,sign*.015*low,-.16*low)
    pole+=cv(-.06*low,sign*.06*low,-.14*low)
   elif kind=='equip':
    w=1-smooth(u);pitch=36*w;roll=-sign*10*w;pos=cv(-.06*w,sign*.035*w,-.30*w)
    shoulder+=cv(-.015*w,sign*.010*w,-.085*w);pole+=cv(-.04*w,sign*.04*w,-.15*w)
   else:
    pos=cv(0,sign*.001*math.sin(phase),.0015*math.sin(phase))
   pivot=H.translation
   D=Matrix.Translation(pivot+pos)@turn(pitch,yaw,roll).to_matrix().to_4x4()@Matrix.Translation(-pivot)
   if sprint_update:
    # Carry the already fitted forearm about its elbow. Moving the same elbow
    # with the assembly keeps the NaturalAimV3 wrist bend and finger contact.
    pivot=pole_home
    D=Matrix.Translation(pivot+pos)@turn(pitch,yaw,roll).to_matrix().to_4x4()@Matrix.Translation(-pivot)
    pole=D@pole_home
    preferred=shoulder_home+cv(-.015,sign*.012,-.10+sp['shoulder_footfall']*contact_drop)
    shoulder=pole+(preferred-pole).normalized()*upper_length
   root=D@G
   p={n:m.copy() for n,m in base.items()}
   for n,m in mech.items():p[n]=root@m
   hand_at(p,base,side,root@contact,shoulder,pole)
   # Mirror the trigger-finger movement onto the real left finger chain, using
   # the current fitted grip as the reference rather than negative mesh scaling.
   if kind.startswith('fire'):
    pulse=smooth(t/.018)*(1-smooth((t-.08)/.08))
    for n in [f'index_{j:02}_{side}' for j in (1,2,3)]:
     if n in p:
      local=p[parent[n]].inverted()@p[n];loc,q,scale=local.decompose()
      q=q@Euler((.06*pulse,0,0)).to_quaternion();p[n]=p[parent[n]]@Matrix.LocRotScale(loc,q,scale)
   row={}
   for n in names:
    b=lr[n].inverted()@(p[parent[n]].inverted()@p[n] if parent[n] else p[n]);loc,q,scale=b.decompose()
    if n in previous and previous[n].dot(q)<0:q.negate()
    previous[n]=q.copy();row[n]=(loc,q,scale)
   rows.append(row);frames.append(t*60)
  a=bpy.data.actions.new(f'Dual_{weapon}_{side}_{kind}');a.use_fake_user=True;rig.animation_data.action=a
  for n in names:
   b=rig.pose.bones[n];b.rotation_mode='QUATERNION'
   for prop in ('location','rotation_quaternion','scale'):b.keyframe_insert(prop,frame=0)
  curves={(c.data_path,c.array_index):c for c in a.layers[0].strips[0].channelbag(a.slots[0]).fcurves}
  for n in names:
   for prop,field,count in [('location',0,3),('rotation_quaternion',1,4),('scale',2,3)]:
    for axis in range(count):
     c=curves[(f'pose.bones["{n}"].{prop}',axis)];c.keyframe_points.clear();c.keyframe_points.add(len(frames))
     c.keyframe_points.foreach_set('co',[v for f,row in zip(frames,rows) for v in (f,row[n][field][axis])])
     for k in c.keyframe_points:k.interpolation='LINEAR'
     c.update()
  rig.animation_data.action_slot=a.slots[0];scene.frame_start=0;scene.frame_end=round(duration*60);scene.frame_set(0)
  bpy.ops.object.select_all(action='DESELECT');rig.hide_set(False);rig.select_set(True);bpy.context.view_layer.objects.active=rig
  fbx=dest/'Animations'/f'A_Dual_{weapon}_{side}_{kind}.fbx'
  bpy.ops.export_scene.fbx(filepath=str(fbx),use_selection=True,object_types={'ARMATURE'},axis_forward='-Y',axis_up='Z',add_leaf_bones=False,
                          bake_anim=True,bake_anim_use_all_actions=False,bake_anim_use_nla_strips=False,bake_anim_step=.5,bake_anim_simplify_factor=0)
  actions[kind]=a;records[kind]={'duration':duration,'source_duration':source_duration,'source_action':source_name,'fbx':str(fbx)}
  print('DUAL_ACTION_EXPORTED',weapon,side,kind,flush=True)
 # Export only the actual anatomical arm for this side, plus the unmirrored gun.
 rig.animation_data_clear()
 for b in rig.pose.bones:b.matrix_basis=Matrix.Identity(4)
 bpy.context.view_layer.update()
 hands=original_hands.copy();hands.data=original_hands.data.copy();scene.collection.objects.link(hands);hands.name=f'Manny_Dual_{side}'
 bm=bmesh.new();bm.from_mesh(hands.data);weights=bm.verts.layers.deform.active
 remove=[]
 for v in bm.verts:
  data=v[weights];right=left=0.
  for index,weight in data.items():
   name=hands.vertex_groups[index].name
   if name.endswith('_r'):right+=weight
   if name.endswith('_l'):left+=weight
  if (side=='r' and left>right) or (side=='l' and right>=left):remove.append(v)
 bmesh.ops.delete(bm,geom=remove,context='VERTS');bm.to_mesh(hands.data);bm.free()
 bpy.ops.object.select_all(action='DESELECT')
 export_objects=[rig,hands]+[ob for ob in bpy.data.collections[spec[2]].objects if ob.type=='MESH']
 for ob in export_objects:ob.hide_set(False);ob.select_set(True)
 bpy.context.view_layer.objects.active=rig
 # The fitted meshes and bind pose are unchanged; retain the accepted FBX/SK.
 meshfile=O/weapon/side/f'SK_Dual_{weapon}_{side}.fbx'
 preview_kind='single_0_6' if revolver_flick else 'sprint' if sprint_update else 'idle'
 preview_action=actions[preview_kind]
 rig.animation_data_create();rig.animation_data.action=preview_action;rig.animation_data.action_slot=preview_action.slots[0];scene.frame_start=0;scene.frame_end=round(clips[preview_kind][0]*60);scene.frame_set(0)
 original_hands.hide_render=True;original_hands.hide_set(True);hands.hide_render=False
 bpy.ops.file.pack_all();bpy.ops.wm.save_as_mainfile(filepath=str(dest/f'{weapon}_{side}_Dual_Editable.blend'))
 receipt['sides'][side]={'mesh':str(meshfile),'clips':records,
  'neutral_blender_metres':{'muzzle':list(G@muzzle_local),'bore':list((G.to_3x3()@bore_local).normalized()),
   'shoulder':list(shoulder_home),'elbow':list(pole_home),'wrist':list(H.translation)}}
 bpy.data.objects.remove(hands,do_unlink=True)
(P/f'{weapon}-authoring.json').write_text(json.dumps(receipt,indent=2),encoding='utf-8')
print('DUAL_AUTHOR_COMPLETE',weapon,flush=True)
