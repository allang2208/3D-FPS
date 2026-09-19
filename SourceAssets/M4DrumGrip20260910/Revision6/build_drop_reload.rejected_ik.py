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
 tiltkeys=[(0,Matrix.Translation(Vector((0,0,0)))),(release-7,Matrix.Translation(Vector((5,-3,1)))),(release,Matrix.Translation(Vector((10,18,-4)))),(hold+8,Matrix.Translation(Vector((14,11,-3)))),(end-20,Matrix.Translation(Vector((14,11,-3)))),(end,Matrix.Translation(Vector((0,0,0))))]
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
 trusted=[]
 for k,src in enumerate(reference):
  for n,m in src['B'].items():r.pose.bones[n].matrix_basis=m
  update();delta=gun[k]@src['P']['WPN_root'].inverted()
  for b in r.pose.bones:b.matrix=delta@src['P'][b.name];update()
  trusted.append({b.name:b.matrix.copy() for b in r.pose.bones})
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
 for phase in [0,1]:
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
   for side in ['l','r']:
    un,fn,hn=['upperarm_'+side,'lowerarm_'+side,'hand_'+side];R=[rest[n].matrix_local.copy() for n in [un,fn,hn]];ru=R[1].translation-R[0].translation;rv=R[2].translation-R[1].translation;l1=ru.length;l2=rv.length;ru.normalize();rv.normalize();rh=ru.cross(rv).normalized()
    goal=goals[side];target=goal.translation;start=raw[0]['P'][un].translation
    anchor=Vector((-.24,-.25,-.22) if side=='l' else (.20,-.25,-.22));neutral_shoulder=(gun[k]@W0.inverted()@reference[0]['P'][un]).translation;A=neutral_shoulder.lerp(anchor,w)
    # A modest shoulder adjustment supports wrist alignment without changing bone lengths.
    desired=(goal.to_3x3()@R[2].to_3x3().inverted()@rv).normalized();ideal=target-desired*l2
    wanted=ideal+(A-ideal).normalized()*l1-A
    if wanted.length>.035:wanted=wanted.normalized()*.035
    A+=wanted*w
    recover=smooth((t-(lock-10))/10) if side=='l' else 0.0
    warped=gun[k]@reference[k]['P']['WPN_root'].inverted()
    if side=='l':A=A.lerp((warped@reference[k]['P'][un]).translation,recover)
    if side=='r':A=src['P'][un].translation.copy()
    dist=(target-A).length
    if dist>l1+l2-.015:A=target+(A-target).normalized()*(l1+l2-.015)
    axis=(target-A).normalized();dist=(target-A).length
    anatomical=Vector((-1,0,-.15) if side=='l' else (1,0,-.15));anatomical-=axis*anatomical.dot(axis);anatomical.normalize()
    ip=ideal-A;ip-=axis*ip.dot(axis);ip.normalize()
    old=((gun[k]@W0.inverted()@reference[0]['P'][fn]).translation if side=='l' else src['P'][fn].translation)-A;old-=axis*old.dot(axis);old.normalize()
    pole=old.lerp(ip.lerp(anatomical,.60).normalized(),w).normalized() if side=='l' else old
    if phase==0:
     angle=math.atan2(axis.dot(anatomical.cross(pole)),anatomical.dot(pole))
     if pole_angles[side]:
      previous=pole_angles[side][-1];angle=previous+(angle-previous+math.pi)%(2*math.pi)-math.pi
     pole_angles[side].append(angle)
    else:pole=Quaternion(axis,pole_angles[side][k])@anatomical
    if recover>0:
     final_pole=(warped@reference[k]['P'][fn]).translation-A;final_pole-=axis*final_pole.dot(axis);final_pole.normalize()
     turn=math.atan2(axis.dot(pole.cross(final_pole)),pole.dot(final_pole));pole=Quaternion(axis,turn*recover)@pole
    along=(l1*l1-l2*l2+dist*dist)/(2*dist);elbow=A+axis*along+pole*math.sqrt(max(0,l1*l1-along*along));u=(elbow-A).normalized();v=(target-elbow).normalized();h=u.cross(v).normalized()
    transforms=[]
    for i,(refvec,vec,p) in enumerate([(ru,u,A),(rv,v,elbow)]):
     ref=Matrix((refvec,rh.cross(refvec),rh)).transposed();tar=Matrix((vec,h.cross(vec),h)).transposed();transforms.append(Matrix.LocRotScale(p,(tar@ref.transposed()@R[i].to_3x3()).to_quaternion(),Vector((1,1,1))))
    upper,lower=transforms;clav=raw[0]['P']['clavicle_'+side].copy();clav.translation+=A-start;r.pose.bones['clavicle_'+side].matrix=clav;update()
    r.pose.bones[un].matrix=upper;update();r.pose.bones[fn].matrix=lower;update()
    # Both elbow segments share the same hinge frame. Do not blend a different
    # upper-arm roll into this frame: that introduced the previous sideways elbow.
    for n in ['upperarm_twist_01_'+side,'upperarm_twist_02_'+side]:r.pose.bones[n].matrix=upper@R[0].inverted()@rest[n].matrix_local;update()
    neutral=lower.to_quaternion()@R[1].to_quaternion().inverted()@R[2].to_quaternion();q=goal.to_quaternion()@neutral.inverted();twist=2*math.atan2(Vector((q.x,q.y,q.z)).dot(v),q.w);twist=(twist+math.pi)%(2*math.pi)-math.pi
    if side in twist_cache:twist=twist_cache[side]+(twist-twist_cache[side]+math.pi)%(2*math.pi)-math.pi
    twist_cache[side]=twist
    # The free reach must not wind the skin helpers through a full revolution.
    # The palm still follows its authored orientation; the forearm distributes
    # only a bounded pronation before recovering the proven installation pose.
    twist=max(-math.radians(110),min(math.radians(110),twist))
    for n,fraction in [('lowerarm_twist_02_'+side,.50),('lowerarm_twist_01_'+side,.95)]:
     base=lower@R[1].inverted()@rest[n].matrix_local;r.pose.bones[n].matrix=Matrix.LocRotScale(base.translation,Quaternion(v,twist*fraction)@base.to_quaternion(),Vector((1,1,1)));update()
    if recover>0:
     for name in ['upperarm_twist_01_'+side,'upperarm_twist_02_'+side,'lowerarm_twist_01_'+side,'lowerarm_twist_02_'+side]:
      B=r.pose.bones[name].matrix.copy();C=warped@reference[k]['P'][name];bq=B.to_quaternion();dq=bq.inverted()@C.to_quaternion()
      if (name in recovery_quats and recovery_quats[name].dot(dq)<0) or (name not in recovery_quats and dq.w<0):dq.negate()
      recovery_quats[name]=dq.copy();dv=Vector((dq.x,dq.y,dq.z));angle=2*math.atan2(dv.length,dq.w)
      rq=Quaternion(dv.normalized(),angle*recover) if dv.length>1e-7 else Quaternion()
      r.pose.bones[name].matrix=Matrix.LocRotScale(B.translation.lerp(C.translation,recover),bq@rq,Vector((1,1,1)));update()
    r.pose.bones[hn].matrix=goal;update();row[side]={'bend_deg':math.degrees(v.angle(desired)),'elbow_local_euler':list((upper.inverted()@lower).to_euler()),'shoulder':list(A)}
   # Preserve exact preexisting joint endpoints and fade into the anatomical FK setup.
   blendw=smooth(t/10)*smooth((end-t)/10)
   if blendw<1:
    for b in r.pose.bones:
     if 'twist' in b.name and b.name.startswith(('upperarm','lowerarm')):b.matrix_basis=mix(raw[0]['B'][b.name],b.matrix_basis,blendw)
    update()
   # Preserve the accepted R5 installation verbatim in weapon space. The new
   # reach ends here; no new IK, pole or skin-helper solve is allowed afterward.
   if t>=lock:
    for b in r.pose.bones:
     if b.name.endswith(('_l','_r')):b.matrix=trusted[k][b.name];update()
   elif t>=acquire:
    names=[b.name for b in r.pose.bones if b.name.endswith('_l')]
    if acquired_pose is None:acquired_pose={n:r.pose.bones[n].matrix.copy() for n in names}
    # Transition the complete accepted limb, retaining its FK relationships,
    # rather than twisting individual helpers to meet an unrelated wrist goal.
    for n in names:r.pose.bones[n].matrix=trusted[lock*2][n];update()
    target_local={n:r.pose.bones[n].matrix_basis.copy() for n in names}
    for n in names:r.pose.bones[n].matrix=acquired_pose[n];update()
    start_local={n:r.pose.bones[n].matrix_basis.copy() for n in names}
    amount=smooth((t-acquire)/(lock-acquire))
    for n in names:r.pose.bones[n].matrix_basis=mix(start_local[n],target_local[n],amount)
    update()
    # The new drum stays in the palm during this complete-limb return.
    r.pose.bones['WPN_SOCKET_Magazine'].matrix=r.pose.bones['hand_l'].matrix@raw[lock*2]['P']['hand_l'].inverted()@raw[lock*2]['P']['WPN_SOCKET_Magazine'];update()
   if phase:poses.append({b.name:b.matrix_basis.copy() for b in r.pose.bones});rows.append(row)
  if phase==0:
   for side,values in pole_angles.items():
    if not values or side=='r':continue
    # Smooth the unwrapped elbow-plane angle, preserving joint axes and hand contact.
    weights=[math.exp(-.5*(j/12)**2) for j in range(-36,37)];den=sum(weights)
    filtered=[sum(weights[j+36]*values[max(0,min(len(values)-1,i+j))] for j in range(-36,37))/den for i in range(len(values))]
    # Retain the authored idle endpoints so entering/exiting reload cannot pop.
    d0=values[0]-filtered[0];dn=values[-1]-filtered[-1]
    dh=values[hold*2]-filtered[hold*2]
    pole_angles[side]=[values[i] if i<=hold*2 else a+dh*(1-smooth((i-hold*2)/40))+dn*(1-smooth((len(values)-1-i)/40)) for i,a in enumerate(filtered)]
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


