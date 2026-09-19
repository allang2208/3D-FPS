import bpy,math,json
from pathlib import Path
from mathutils import Matrix,Vector,Quaternion,Euler
O=Path(__file__).parent;bpy.ops.wm.open_mainfile(filepath=str(O.parent/'Revision5/M4_DrumFlow_Editable.blend'));r=bpy.data.objects['SK_M4_Infima'];s=bpy.context.scene;rest=r.data.bones
def smooth(t):
 t=max(0,min(1,t));return t*t*(3-2*t)
def mix(A,B,t):
 p,q,z=A.decompose();P,Q,Z=B.decompose();return Matrix.LocRotScale(p.lerp(P,t),q.slerp(Q,t),z.lerp(Z,t))
def track(keys,t):
 if t<=keys[0][0]:return keys[0][1].copy()
 if t>=keys[-1][0]:return keys[-1][1].copy()
 for (a,A),(b,B) in zip(keys,keys[1:]):
  if t<=b:return mix(A,B,smooth((t-a)/(b-a)))
def motion_curve(keys,t):
 if t<=keys[0][0]:return keys[0][1].copy()
 if t>=keys[-1][0]:return keys[-1][1].copy()
 for i,((a,A),(b,B)) in enumerate(zip(keys,keys[1:])):
  if t<=b:
   u=(t-a)/(b-a);dt=b-a
   m0=Vector((0,0,0)) if i==0 else (B.translation-keys[i-1][1].translation)/(b-keys[i-1][0])
   m1=Vector((0,0,0)) if i+2==len(keys) else (keys[i+2][1].translation-A.translation)/(keys[i+2][0]-a)
   pos=A.translation*(2*u**3-3*u*u+1)+m0*dt*(u**3-2*u*u+u)+B.translation*(-2*u**3+3*u*u)+m1*dt*(u**3-u*u)
   return Matrix.LocRotScale(pos,A.to_quaternion().slerp(B.to_quaternion(),smooth(u)),Vector((1,1,1)))

def update():bpy.context.view_layer.update()
report={}
for clip,end,release,pickup,lock in [('reload',126,18,44,50),('reload_empty',162,14,38,43)]:
 a=bpy.data.actions['A_M4_DrumFlow_'+clip];r.animation_data.action=a;r.animation_data.action_slot=a.slots[0];raw=[]
 for k in range(end*2+1):
  s.frame_set(k//2,subframe=(k%2)/2);update();raw.append({'P':{b.name:b.matrix.copy() for b in r.pose.bones},'B':{b.name:b.matrix_basis.copy() for b in r.pose.bones}})
 r.animation_data.action=None;reference=raw;W0=raw[0]['P']['WPN_root'];home=raw[0]['P']['hand_l'];hold=release+2;acquire=36 if clip=='reload' else 31
 # Author small, nonperiodic weight transfers rather than freezing the weapon.
 events=[(0,(0,0,0)),(hold,(0,0,0)),(hold+8,(1.0,-.65,-.9)),(lock,(-.7,.7,1.1)),(lock+17,(.8,-.8,-.7)),(76 if clip=='reload' else 65,(-.45,.5,.6)),(92 if clip=='reload' else 90,(.5,-.45,-.35)),(end-14,(-.25,.35,.25)),(end,(0,0,0))]
 events.sort(key=lambda x:x[0]);swaykeys=[(t,Matrix.Translation(Vector(v))) for t,v in events]
 # Rotation landmarks reference the ordinary-magazine cant, but keep the
 # right grip at one depth instead of moving the entire viewmodel forward/back.
 tiltkeys=[(0,Matrix.Translation(Vector((0,0,0)))),(release-7,Matrix.Translation(Vector((5,-3,1)))),(release,Matrix.Translation(Vector((8,10,12)))),(hold+8,Matrix.Translation(Vector((10,7,22)))),(end-20,Matrix.Translation(Vector((10,7,22)))),(end,Matrix.Translation(Vector((0,0,0))))]
 pivot=reference[0]['P']['hand_r'].translation.copy()
 def weapon(t,old):
  e=motion_curve(swaykeys,t).translation
  angles=motion_curve(tiltkeys,t).translation+e
  q=Euler(tuple(math.radians(v) for v in angles),'XYZ').to_quaternion()
  lift=.018*smooth(t/max(1,release-4))*smooth((end-t)/20)
  move=Vector((e.z*.0015,0,lift+e.x*.0015))
  return Matrix.Translation(pivot+move)@q.to_matrix().to_4x4()@Matrix.Translation(-pivot)@W0
 gun=[weapon(k/2,d['P']['WPN_root']) for k,d in enumerate(raw)]
 hand_hold=gun[hold*2]@W0.inverted()@home
 grasp=gun[lock*2]@raw[lock*2]['P']['WPN_root'].inverted()@raw[lock*2]['P']['hand_l']
 side=mix(hand_hold,grasp,.35);side.translation=Vector((-.30,.025,-.31))
 behind=grasp.copy();behind.translation=Vector((-.40,-.32,-.38))
 rest_dir=(rest['hand_l'].head_local-rest['lowerarm_l'].head_local).normalized()
 desired=(grasp.to_3x3()@rest['hand_l'].matrix_local.to_3x3().inverted()@rest_dir).normalized()
 behind_dir=Vector((.15,-.22,.07)).normalized()
 behind=Matrix.LocRotScale(behind.translation,desired.rotation_difference(behind_dir)@grasp.to_quaternion(),Vector((1,1,1)))
 fetch=Matrix.LocRotScale(grasp.translation+Vector((-.075,-.10,-.06)),behind.to_quaternion().slerp(grasp.to_quaternion(),.60),Vector((1,1,1)))
 handkeys=[(hold,hand_hold),(hold+7,side),(acquire-2,behind),(acquire,behind),(pickup,fetch),(lock,grasp)]
 trusted=[{n:gun[k]@src['P']['WPN_root'].inverted()@m for n,m in src['P'].items()} for k,src in enumerate(reference)]
 raw=[]
 for k,src in enumerate(reference):
  for n,m in src['B'].items():r.pose.bones[n].matrix_basis=m
  update();delta=gun[k]@src['P']['WPN_root'].inverted()
  for b in r.pose.bones:
   if b.name.startswith('WPN_'):b.matrix=delta@src['P'][b.name];update()
  # Both palms retain their exact grip relative to the weapon until the free-hand phase.
  for side in ['l','r']:r.pose.bones['hand_'+side].matrix=(delta@src['P']['hand_'+side] if side=='l' else gun[k]@W0.inverted()@reference[0]['P']['hand_r']);update()
  raw.append({'P':{b.name:b.matrix.copy() for b in r.pose.bones},'B':{b.name:b.matrix_basis.copy() for b in r.pose.bones}})
 poses=[];rows=[];pole_angles={side:[] for side in ['l','r']}
 for phase in [1]:
  twist_cache={};recovery_quats={};acquired_pose=None
  for k,src in enumerate(raw):
   t=k/2;s.frame_set(k//2,subframe=(k%2)/2)
   for n,m in src['B'].items():r.pose.bones[n].matrix_basis=m
   update();w=smooth((t-hold)/12)*smooth((end-t)/12)
   if t<lock:
    goal=gun[k]@W0.inverted()@home if t<=hold else motion_curve(handkeys,t);r.pose.bones['hand_l'].matrix=goal;update()
    for b in r.pose.bones:
     n=b.name
     if n.endswith('_l') and n.startswith(('thumb','index','middle','ring','pinky')):
      B=raw[0]['B'][n];C=raw[lock*2]['B'][n];openB=raw[(106 if clip=='reload' else 98)*2]['B'][n]
      b.matrix_basis=track([(0,B),(hold,B),(hold+5,openB),(acquire-5,openB),(acquire,C),(lock,C)],t)
    update()
   goals={side:r.pose.bones['hand_'+side].matrix.copy() for side in ['l','r']}
   # Keep the old drum mounted until release; the runtime creates its independent
   # physical actor then hides this socket mesh until the fresh drum is acquired.
   if t<=release:
    mounted=gun[k]@W0.inverted()@reference[0]['P']['WPN_SOCKET_Magazine']
    unseat=smooth((t-(release-5))/4)
    r.pose.bones['WPN_SOCKET_Magazine'].matrix=Matrix.Translation(gun[k].to_quaternion()@W0.to_quaternion().inverted()@Vector((0,0,-.06*unseat)))@mounted;update()
   elif t<lock:
    # Once acquired behind the left hip, carry the new drum rigidly with the palm.
    r.pose.bones['WPN_SOCKET_Magazine'].matrix=goals['l']@raw[lock*2]['P']['hand_l'].inverted()@raw[lock*2]['P']['WPN_SOCKET_Magazine'];update()
   row={'frame':t}
   # Reuse the accepted R5 limb, including all skin helpers and fingers.
   # Only the entire limb rotates at the shoulder for the behind-hip reach.
   # Installation is an exact rigid transform of R5, with no new IK solve.
   if t<=hold:
    si=0;reach=0.0
   elif t<acquire:
    progress=smooth((t-hold)/(acquire-hold));source_start=22 if clip=='reload' else 18
    si=round((source_start+(lock-source_start)*progress)*2);reach=progress
   elif t<lock:
    si=lock*2;reach=1-smooth((t-acquire)/(lock-acquire))
   else:si=k;reach=0.0
   delta=gun[k]@reference[si]['P']['WPN_root'].inverted()
   A=(delta@reference[si]['P']['upperarm_l']).translation
   palm=(delta@reference[si]['P']['hand_l']).translation
   back=Vector((-.40,-.32,-.38))
   backq=(palm-A).normalized().rotation_difference((back-A).normalized())
   q=Quaternion().slerp(backq,reach)
   reach_transform=Matrix.Translation(A)@q.to_matrix().to_4x4()@Matrix.Translation(-A)
   for b in r.pose.bones:
    if b.name.endswith('_l'):
     b.matrix=(delta@reference[si]['P'][b.name] if b.name.startswith('clavicle') else reach_transform@delta@reference[si]['P'][b.name]);update()
   if hold<t<acquire:
    # Unwind the free palm continuously toward the accepted grasp. The source
    # crosses the +/-180 degree boundary here; halving that wrapped angle made
    # the forearm skin helper jump by 180 degrees. Installation is untouched.
    lower=r.pose.bones['lowerarm_l'].matrix.copy();hand=r.pose.bones['hand_l'].matrix.copy();v=(hand.translation-lower.translation).normalized()
    def axial(pose):
     low=pose['lowerarm_l'];hnd=pose['hand_l'];axis=(hnd.translation-low.translation).normalized()
     neutral=low.to_quaternion()@rest['lowerarm_l'].matrix_local.to_quaternion().inverted()@rest['hand_l'].matrix_local.to_quaternion()
     dq=hnd.to_quaternion()@neutral.inverted();a=2*math.atan2(Vector((dq.x,dq.y,dq.z)).dot(axis),dq.w)
     return (a+math.pi)%(2*math.pi)-math.pi
    desired=axial(reference[0]['P'])*(1-progress)+axial(reference[lock*2]['P'])*progress
    correction=Quaternion(v,desired-axial({'lowerarm_l':lower,'hand_l':hand}))
    around=Matrix.Translation(hand.translation)@correction.to_matrix().to_4x4()@Matrix.Translation(-hand.translation)
    fingers={b.name:b.matrix.copy() for b in r.pose.bones if b.name.endswith('_l') and (b.name=='hand_l' or b.name.startswith(('thumb','index','middle','ring','pinky')))}
    for n,m in fingers.items():r.pose.bones[n].matrix=around@m;update()
    for n,f in [('lowerarm_twist_02_l',.5),('lowerarm_twist_01_l',.95)]:
     base=lower@rest['lowerarm_l'].matrix_local.inverted()@rest[n].matrix_local
     r.pose.bones[n].matrix=Matrix.LocRotScale(base.translation,Quaternion(v,desired*f)@base.to_quaternion(),Vector((1,1,1)));update()
    for n in ['upperarm_twist_01_l','upperarm_twist_02_l']:
     start_helper=r.pose.bones['upperarm_l'].matrix@reference[0]['P']['upperarm_l'].inverted()@reference[0]['P'][n]
     r.pose.bones[n].matrix=mix(start_helper,r.pose.bones[n].matrix,smooth((t-hold)/4));update()
   if True:
    for b in r.pose.bones:
     if b.name.endswith('_r'):b.matrix=trusted[k][b.name];update()
   if release<t<lock:
    r.pose.bones['WPN_SOCKET_Magazine'].matrix=r.pose.bones['hand_l'].matrix@raw[lock*2]['P']['hand_l'].inverted()@raw[lock*2]['P']['WPN_SOCKET_Magazine'];update()
   if phase:poses.append({b.name:b.matrix_basis.copy() for b in r.pose.bones});rows.append(row)
 a.name='BeforeThrow_'+clip;a=bpy.data.actions.new('A_M4_DrumThrow_'+clip);a.use_fake_user=True;r.animation_data.action=a;prev={}
 for k,p in enumerate(poses):
  for n,m in p.items():
   b=r.pose.bones[n];loc,q,z=m.decompose()
   if n in prev and prev[n].dot(q)<0:q.negate()
   prev[n]=q.copy();b.rotation_mode='QUATERNION';b.location=loc;b.rotation_quaternion=q;b.scale=z
   for prop in ['location','rotation_quaternion','scale']:b.keyframe_insert(prop,frame=k/2)
 for layer in a.layers:
  for strip in layer.strips:
   for bag in strip.channelbags:
    for curve in bag.fcurves:
     for key in curve.keyframe_points:key.interpolation='LINEAR'
 s.frame_start=0;s.frame_end=end;s.render.fps=60;bpy.ops.object.select_all(action='DESELECT');r.select_set(True);bpy.context.view_layer.objects.active=r
 bpy.ops.export_scene.fbx(filepath=str(O/(a.name+'.fbx')),use_selection=True,object_types={'ARMATURE'},axis_forward='-Y',axis_up='Z',add_leaf_bones=False,bake_anim=True,bake_anim_use_all_actions=False,bake_anim_use_nla_strips=False,bake_anim_force_startend_keying=True,bake_anim_step=.5,bake_anim_simplify_factor=0)
 report[clip]={'release_frame':release,'support_release_frame':hold,'new_drum_acquire_frame':acquire,'behind_hip_position':list(behind.translation),'pickup_frame':pickup,'grip_frame':lock,'rows':rows};r.animation_data.action=None
r.animation_data.action=bpy.data.actions['A_M4_DrumThrow_reload'];r.animation_data.action_slot=r.animation_data.action.slots[0];s.frame_start=0;s.frame_end=126;s.frame_set(0);bpy.ops.wm.save_as_mainfile(filepath=str(O/'M4_DrumThrow_Editable.blend'));(O/'motion_report.json').write_text(json.dumps(report,indent=2))


