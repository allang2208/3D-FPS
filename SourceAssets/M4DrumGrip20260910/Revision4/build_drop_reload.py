import bpy,math,json
from pathlib import Path
from mathutils import Matrix,Vector,Quaternion
O=Path(__file__).parent;bpy.ops.wm.open_mainfile(filepath=str(O.parent/'Revision3/M4_DrumGrip_Rebuilt.blend'));r=bpy.data.objects['SK_M4_Infima'];s=bpy.context.scene;rest=r.data.bones
def smooth(t):
 t=max(0,min(1,t));return t*t*(3-2*t)
def mix(A,B,t):
 p,q,z=A.decompose();P,Q,Z=B.decompose();return Matrix.LocRotScale(p.lerp(P,t),q.slerp(Q,t),z.lerp(Z,t))
def track(keys,t):
 if t<=keys[0][0]:return keys[0][1].copy()
 if t>=keys[-1][0]:return keys[-1][1].copy()
 for (a,A),(b,B) in zip(keys,keys[1:]):
  if t<=b:return mix(A,B,smooth((t-a)/(b-a)))
def update():bpy.context.view_layer.update()
report={}
for clip,end,release,pickup,lock in [('reload',126,18,42,50),('reload_empty',162,14,29,35)]:
 a=bpy.data.actions['A_M4_DrumGrip_'+clip];r.animation_data.action=a;r.animation_data.action_slot=a.slots[0];raw=[]
 for k in range(end*2+1):
  s.frame_set(k//2,subframe=(k%2)/2);update();raw.append({'P':{b.name:b.matrix.copy() for b in r.pose.bones},'B':{b.name:b.matrix_basis.copy() for b in r.pose.bones}})
 r.animation_data.action=None;home=raw[0]['P']['hand_l'];grasp=raw[lock*2]['P']['hand_l'];away=home.copy();away.translation+=Vector((-.075,-.015,-.16));fetch=grasp.copy();fetch.translation+=Vector((-.025,0,-.06))
 handkeys=[(0,home),(5,home),(release+3,away),(pickup,fetch),(lock,grasp)]
 poses=[];rows=[];pole_angles={side:[] for side in ['l','r']}
 for phase in [0,1]:
  for k,src in enumerate(raw):
   t=k/2;s.frame_set(k//2,subframe=(k%2)/2)
   for n,m in src['B'].items():r.pose.bones[n].matrix_basis=m
   update();w=smooth(t/12)*smooth((end-t)/12)
   if t<lock:
    goal=track(handkeys,t);r.pose.bones['hand_l'].matrix=goal;update()
    for b in r.pose.bones:
     n=b.name
     if n.endswith('_l') and n.startswith(('thumb','index','middle','ring','pinky')):
      B=raw[0]['B'][n];C=raw[lock*2]['B'][n];openB=raw[(106 if clip=='reload' else 98)*2]['B'][n]
      b.matrix_basis=track([(0,B),(8,B),(release+3,openB),(pickup,openB),(lock,C)],t)
    update()
   goals={side:r.pose.bones['hand_'+side].matrix.copy() for side in ['l','r']}
   # Keep the old drum mounted until release; the runtime creates its independent
   # physical actor then hides this socket mesh until the fresh drum is acquired.
   if t<=release:r.pose.bones['WPN_SOCKET_Magazine'].matrix=src['P']['WPN_root']@raw[0]['P']['WPN_root'].inverted()@raw[0]['P']['WPN_SOCKET_Magazine'];update()
   row={'frame':t}
   for side in ['l','r']:
    un,fn,hn=['upperarm_'+side,'lowerarm_'+side,'hand_'+side];R=[rest[n].matrix_local.copy() for n in [un,fn,hn]];ru=R[1].translation-R[0].translation;rv=R[2].translation-R[1].translation;l1=ru.length;l2=rv.length;ru.normalize();rv.normalize();rh=ru.cross(rv).normalized()
    goal=goals[side];target=goal.translation;start=raw[0]['P'][un].translation
    anchor=Vector((-.24,-.25,-.22) if side=='l' else (.20,-.25,-.22));A=start.lerp(anchor,w)
    # A modest shoulder adjustment supports wrist alignment without changing bone lengths.
    desired=(goal.to_3x3()@R[2].to_3x3().inverted()@rv).normalized();ideal=target-desired*l2
    wanted=ideal+(A-ideal).normalized()*l1-A
    if wanted.length>.035:wanted=wanted.normalized()*.035
    A+=wanted*w
    if side=='r':A=src['P'][un].translation.copy()
    dist=(target-A).length
    if dist>l1+l2-.015:A=target+(A-target).normalized()*(l1+l2-.015)
    axis=(target-A).normalized();dist=(target-A).length
    anatomical=Vector((-.7,-.1,-.8) if side=='l' else (.7,-.1,-.8));anatomical-=axis*anatomical.dot(axis);anatomical.normalize()
    ip=ideal-A;ip-=axis*ip.dot(axis);ip.normalize()
    old=src['P'][fn].translation-A;old-=axis*old.dot(axis);old.normalize()
    pole=old.lerp(ip.lerp(anatomical,.12).normalized(),w).normalized() if side=='l' else old
    if phase==0:
     angle=math.atan2(axis.dot(anatomical.cross(pole)),anatomical.dot(pole))
     if pole_angles[side]:
      previous=pole_angles[side][-1];angle=previous+(angle-previous+math.pi)%(2*math.pi)-math.pi
     pole_angles[side].append(angle)
    else:pole=Quaternion(axis,pole_angles[side][k])@anatomical
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
    for n,fraction in [('lowerarm_twist_02_'+side,.50),('lowerarm_twist_01_'+side,.95)]:
     base=lower@R[1].inverted()@rest[n].matrix_local;r.pose.bones[n].matrix=Matrix.LocRotScale(base.translation,Quaternion(v,twist*fraction)@base.to_quaternion(),Vector((1,1,1)));update()
    r.pose.bones[hn].matrix=goal;update();row[side]={'bend_deg':math.degrees(v.angle(desired)),'elbow_local_euler':list((upper.inverted()@lower).to_euler()),'shoulder':list(A)}
   # Preserve exact preexisting joint endpoints and fade into the anatomical FK setup.
   blendw=smooth(t/10)*smooth((end-t)/10)
   if blendw<1:
    for b in r.pose.bones:
     if 'twist' in b.name and b.name.startswith(('upperarm','lowerarm')):b.matrix_basis=mix(raw[0]['B'][b.name],b.matrix_basis,blendw)
    update()
   if phase:poses.append({b.name:b.matrix_basis.copy() for b in r.pose.bones});rows.append(row)
  if phase==0:
   for side,values in pole_angles.items():
    if not values or side=='r':continue
    # Smooth the unwrapped elbow-plane angle, preserving joint axes and hand contact.
    weights=[math.exp(-.5*(j/12)**2) for j in range(-36,37)];den=sum(weights)
    filtered=[sum(weights[j+36]*values[max(0,min(len(values)-1,i+j))] for j in range(-36,37))/den for i in range(len(values))]
    # Retain the authored idle endpoints so entering/exiting reload cannot pop.
    d0=values[0]-filtered[0];dn=values[-1]-filtered[-1]
    pole_angles[side]=[a+d0*(1-smooth(i/40))+dn*(1-smooth((len(values)-1-i)/40)) for i,a in enumerate(filtered)]
 a.name='BeforeDrop_'+clip;a=bpy.data.actions.new('A_M4_DrumDrop_'+clip);a.use_fake_user=True;r.animation_data.action=a;prev={}
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
 report[clip]={'release_frame':release,'pickup_frame':pickup,'grip_frame':lock,'rows':rows};r.animation_data.action=None
r.animation_data.action=bpy.data.actions['A_M4_DrumDrop_reload'];r.animation_data.action_slot=r.animation_data.action.slots[0];s.frame_start=0;s.frame_end=126;s.frame_set(0);bpy.ops.wm.save_as_mainfile(filepath=str(O/'M4_DrumDrop_Editable.blend'));(O/'motion_report.json').write_text(json.dumps(report,indent=2))


