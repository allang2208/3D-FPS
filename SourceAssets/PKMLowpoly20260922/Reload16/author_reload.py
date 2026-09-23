"""PKM reload correction: empty bypass, coherent elbows, charge contact and weight."""
import bpy,json,math
from pathlib import Path
from mathutils import Matrix,Vector,Quaternion,Euler
O=Path(__file__).parent;R=O.parent;FPS=120;CUT=.9
source=json.loads((O/'sources.json').read_text());fit=Matrix(json.loads((R/'Animation03/animation_manifest.json').read_text())['fit_matrix'])
bpy.context.preferences.filepaths.save_version=0
def smooth(x):x=max(0,min(1,x));return x*x*(3-2*x)
def ramp(t,a,b):return smooth((t-a)/(b-a))
def mix(a,b,x):
 p,q,s=a.decompose();p2,q2,s2=b.decompose();return Matrix.LocRotScale(p.lerp(p2,x),q.slerp(q2,x),s.lerp(s2,x))
def frame(axis,width):
 x=axis.normalized();y=width-x*width.dot(x)
 if y.length<1e-7:y=x.orthogonal()
 y.normalize();z=x.cross(y).normalized();return Matrix((x,y,z)).transposed()
def source_time(t,empty):
 if not empty or t<=1.10:return t
 if t>=1.40:return t+CUT
 # Only mechanics use this accelerated source bridge. The left hand below
 # explicitly returns from cover release to support, bypassing all belt poses.
 return 1.10+1.20*ramp(t,1.10,1.40)
def event(t,empty):return t-CUT if empty and t>=2.30 else t
def pulse(t,at,frequency=8,decay=17):
 d=t-at
 return math.sin(d*frequency*2*math.pi)*math.exp(-decay*d) if 0<=d<.42 else 0
def assembly_motion(t,empty,duration,W):
 # Broad weight shifts plus short contact impulses. Both hands and every
 # moving part receive one rigid transform, preserving mechanical contact.
 work=ramp(t,.25,.75)*(1-ramp(t,duration-.48,duration))
 box=ramp(t,event(2.35,empty),event(2.8,empty))*(1-ramp(t,event(4.35,empty),event(4.70,empty)))
 cover=ramp(t,.50,.85)*(1-ramp(t,1.08,1.40))
 charge=ramp(t,event(5.90,empty),event(6.13,empty))*(1-ramp(t,event(6.43,empty),event(6.7,empty))) if empty else 0
 impact=sum(a*pulse(t,event(at,empty)) for at,a in [(.65,.45),(2.6,.60),(4.35,1.),(5.1,.35),(5.72,1.15)])
 if empty:impact+=.70*pulse(t,event(6.45,True),10,21)
 loc=Vector((.0028*math.sin(t*2.0)*work-.002*box,.003*box-.004*charge,-.0035*box-.002*cover-.0018*impact))
 angles=(math.radians(.55)*work*math.sin(t*2.4)+math.radians(.7)*impact,
         math.radians(1.65)*box-math.radians(.7)*cover+math.radians(.5)*impact,
         math.radians(.75)*math.sin(t*1.7)*work+math.radians(.65)*charge)
 local=Matrix.Translation(loc)@Euler(angles,'XYZ').to_matrix().to_4x4()
 return W@local@W.inverted()

records={};params={'empty_cut_seconds':CUT,'empty_duration':6.6,'normal_duration':6.5,'fps':FPS,'charge_donor':source['donor']['file'],'source_frame':75}
for family in ['base','vertical','canted','prism','angled']:
 path=R/'Feed13/PKM_FiringFeed_Editable.blend' if family=='base' else R/'GripContact15'/f'PKM_{family}_Editable.blend'
 bpy.ops.wm.open_mainfile(filepath=str(path));r=bpy.data.objects['PKM_Manny_Rig'];s=bpy.context.scene
 rest={b.name:b.matrix_local.copy() for b in r.data.bones};parents={b.name:b.parent.name if b.parent else None for b in r.data.bones}
 localrest={n:rest[parents[n]].inverted()@m if parents[n] else m.copy() for n,m in rest.items()};B=rest['WPN_root']@fit
 def action(a):r.animation_data.action=a;r.animation_data.action_slot=a.slots[0]
 def sample(a,t):
  action(a);f=t*60;s.frame_set(int(f),subframe=f%1);bpy.context.view_layer.update();return {b.name:b.matrix.copy() for b in r.pose.bones}
 fingers={side:[n for n in rest if n.endswith('_'+side) and n.startswith(('thumb_','index_','middle_','ring_','pinky_'))] for side in ['l','r']}
 arms={side:[n for n in rest if n.endswith('_'+side) and n.startswith(('clavicle_','upperarm_','lowerarm_','hand_','thumb_','index_','middle_','ring_','pinky_'))] for side in ['l','r']}
 donor=source['donor'];dr={n:Matrix(m) for n,m in donor['rest'].items()};dp={n:Matrix(m) for n,m in donor['poses']['75'].items()};dopen={n:Matrix(m) for n,m in donor['poses']['54'].items()}
 donor_q={};open_q={}
 for n in fingers['r']:
  p=parents[n];lr=dr[p].inverted()@dr[n]
  donor_q[n]=(lr.inverted()@dp[p].inverted()@dp[n]).to_quaternion();open_q[n]=(lr.inverted()@dopen[p].inverted()@dopen[n]).to_quaternion()
 # Hand rotation from an existing right-hand AKM charging action; the
 # gripping anchor is rebuilt on this rig and this PKM's actual handle.
 charge_rotation=(dp['WPN_root'].inverted()@dp['hand_r']).to_quaternion()
 fk={'hand_r':Matrix.Identity(4)}
 for n in fingers['r']:fk[n]=fk[parents[n]]@localrest[n]@donor_q[n].to_matrix().to_4x4()
 anchor=sum((fk[n+'_02_r'].translation.lerp(fk[n+'_03_r'].translation,.6) for n in ['index','middle']),Vector())*.5
 handle=Vector((-.0595,.115,.0205))
 def solve_arm(row,side,H,amount,contact=False):
  if amount<=1e-7:return row
  d={n:m.copy() for n,m in row.items()};u='upperarm_'+side;lo='lowerarm_'+side;ha='hand_'+side;cl='clavicle_'+side
  S0=row[u].translation;E0=row[lo].translation;P0=row[ha].translation;P=H.translation
  L1=(E0-S0).length;L2=(P0-E0).length;S=S0.copy();v=P-S;distance=v.length
  if distance>(L1+L2)*.96:S+=v.normalized()*(distance-(L1+L2)*.96)
  v=P-S;distance=v.length;n=v.normalized();along=(L1*L1-L2*L2+distance*distance)/(2*distance);radius=math.sqrt(max(0,L1*L1-along*along));C=S+n*along
  restaxis=rest[ha].translation-rest[lo].translation
  Dh=H.to_3x3()@rest[ha].to_3x3().inverted();ideal=P-(Dh@restaxis).normalized()*L2
  a=E0-C;a-=n*a.dot(n);a.normalize();b=ideal-C;b-=n*b.dot(n)
  if b.length<1e-7:b=a.copy()
  b.normalize();angle=math.atan2(n.dot(a.cross(b)),a.dot(b))
  # Preserve the elbow's side and move smoothly toward a supported wrist.
  swivel=max(-math.radians(55),min(math.radians(55),angle))*(.78 if side=='l' else .72)*amount
  E=C+Quaternion(n,swivel)@a*radius
  oldU=E0-S0;oldL=P0-E0;newU=E-S;newL=P-E
  oldPlane=oldU.cross(oldL);newPlane=newU.cross(newL)
  Ru=frame(newU,newPlane)@frame(oldU,oldPlane).transposed()@row[u].to_3x3()
  width=rest['index_metacarpal_'+side].translation-rest['pinky_metacarpal_'+side].translation
  targetR=frame(newL,Dh@width)@frame(restaxis,width).transposed()@rest[lo].to_3x3()
  carryR=oldL.rotation_difference(newL).to_matrix()@row[lo].to_3x3()
  Rl=carryR.to_quaternion().slerp(targetR.to_quaternion(),amount).to_matrix()
  # Let the upper arm share a modest part of the axial turn at the elbow.
  relative=targetR.to_quaternion()@carryR.to_quaternion().inverted();axis=newL.normalized();proj=Vector((relative.x,relative.y,relative.z)).dot(axis)
  axial=2*math.atan2(proj,relative.w)
  axial=(axial+math.pi)%(2*math.pi)-math.pi
  Ru=Quaternion(newU.normalized(),max(-.20,min(.20,axial*.20))*amount).to_matrix()@Ru
  d[u]=Ru.to_4x4();d[u].translation=S;d[lo]=Rl.to_4x4();d[lo].translation=E;d[cl].translation+=S-S0;d[ha]=H
  for seg in ['upperarm','lowerarm']:
   p=seg+'_'+side
   for suffix in ['01','02']:
    k=seg+'_twist_'+suffix+'_'+side
    original=row[p].inverted()@row[k];coherent=rest[p].inverted()@rest[k]
    d[k]=d[p]@mix(original,coherent,amount)
  return d
 for clip in ['reload','reload_empty']:
  empty=clip=='reload_empty';duration=6.6 if empty else 6.5
  name=('PKM_Reload_Empty_HandReload10_Wrist12' if empty else 'PKM_Reload_Normal_HandReload10_Wrist12') if family=='base' else f'A_PKM_{family}_{clip}_Contact15'
  src=bpy.data.actions[name];s.render.fps=60
  release=sample(src,1.10);support=sample(src,2.30);WR=release['WPN_root'];WS=support['WPN_root']
  frames=[sample(src,source_time(f/FPS,empty)) for f in range(round(duration*FPS)+1)]
  out=bpy.data.actions.new(f'PKM16_{family}_{clip}');out.use_fake_user=True;r.animation_data.action=out;previous={};s.render.fps=FPS
  for f,old in enumerate(frames):
   t=f/FPS;st=source_time(t,empty);row={n:m.copy() for n,m in old.items()};W=row['WPN_root']@fit
   if empty and 1.10<t<1.40:
    a=ramp(t,1.10,1.40);X=row['WPN_root']@WR.inverted();Y=row['WPN_root']@WS.inverted()
    H=mix(X@release['hand_l'],Y@support['hand_l'],a)
    # Curve out of the open cover, then move straight back to support.
    H.translation+=W.to_3x3()@Vector((.014,0,.016))*math.sin(math.pi*a)**2
    row=solve_arm(row,'l',H,1.)
    for n in fingers['l']:
     p=parents[n];local=mix(release[p].inverted()@release[n],support[p].inverted()@support[n],a)
     row[n]=row[p]@local
   elif not empty:
    amount=ramp(st,1.04,1.30)*(1-ramp(st,2.05,2.30))
    row=solve_arm(row,'l',row['hand_l'],amount)
   if empty:
    amount=ramp(st,5.84,6.03)*(1-ramp(st,6.48,6.78))
    if amount>0:
     # Follow the animated handle bone through the pull and the positive stop.
     delta=row['PKM_Charge']@rest['PKM_Charge'].inverted()@B
     orientation=W.to_quaternion()@charge_rotation
     goal=orientation.to_matrix().to_4x4();goal.translation=delta@handle-orientation@anchor
     away=ramp(st,6.42,6.65);goal.translation+=W.to_3x3()@Vector((-.035,0,.026))*away
     H=mix(row['hand_r'],goal,amount);row=solve_arm(row,'r',H,amount,True)
     close=ramp(st,5.90,6.03)*(1-ramp(st,6.42,6.60))
     for n in fingers['r']:
      p=parents[n];oldlocal=old[p].inverted()@old[n]
      shape=localrest[n]@open_q[n].slerp(donor_q[n],close).to_matrix().to_4x4()
      row[n]=row[p]@mix(oldlocal,shape,amount)
   D=assembly_motion(t,empty,duration,W)
   for n in row:
    if parents[n]:row[n]=D@row[n]
   for n,m in row.items():
    p=parents[n];basis=localrest[n].inverted()@(row[p].inverted()@m if p else m);loc,q,scale=basis.decompose()
    if n in previous and previous[n].dot(q)<0:q.negate()
    previous[n]=q.copy();b=r.pose.bones[n];b.location=loc;b.rotation_mode='QUATERNION';b.rotation_quaternion=q;b.scale=scale
    for prop in ['location','rotation_quaternion','scale']:b.keyframe_insert(prop,frame=f,group=n)
  for layer in out.layers:
   for strip in layer.strips:
    for bag in strip.channelbags:
     for curve in bag.fcurves:
      for p in curve.keyframe_points:p.interpolation='LINEAR'
  s.frame_start=0;s.frame_end=round(duration*FPS);s.frame_set(0);bpy.ops.object.select_all(action='DESELECT');r.hide_set(False);r.select_set(True);bpy.context.view_layer.objects.active=r
  dest=O/'Animations'/family;dest.mkdir(parents=True,exist_ok=True);asset='A_PKM_'+('' if family=='base' else family+'_')+clip
  bpy.ops.export_scene.fbx(filepath=str(dest/(asset+'.fbx')),use_selection=True,object_types={'ARMATURE'},axis_forward='-Y',axis_up='Z',add_leaf_bones=False,bake_anim=True,bake_anim_use_all_actions=False,bake_anim_use_nla_strips=False,bake_anim_step=1,bake_anim_simplify_factor=0)
  records[family+'/'+clip]={'name':asset,'action':out.name,'seconds':duration,'fps':FPS,'source':str(path),'empty_belt_bypassed':empty}
  print('PKM16_RELOAD_EXPORTED',family,clip,flush=True)
 action(bpy.data.actions[f'PKM16_{family}_reload_empty']);s.frame_start=0;s.frame_end=round(6.6*FPS);s.frame_set(0)
 bpy.ops.wm.save_as_mainfile(filepath=str(O/f'PKM_{family}_Reload_Editable.blend'));(O/'animations.json').write_text(json.dumps(records,indent=2))
(O/'authoring.json').write_text(json.dumps(params,indent=2));print('PKM16_AUTHOR_COMPLETE',flush=True)
