"""Continuous M24 extraction, release and empty-hand retrieval in the paced clock."""
from pathlib import Path
exec(compile((Path(__file__).parent/'library.py').read_text(),'library','exec'))
C=Matrix(json.loads((O.parent/'M24Hold20261027/hip-calibration.json').read_text())['hip_transform'])@Matrix.Diagonal((100,-100,100,1))
Ci=C.inverted();Cr=C.to_3x3().normalized();Cri=Cr.inverted()
old_ue=json.loads((O.parent/'M24ReloadRelease20261028/ue_before.json').read_text())
source=ast.parse((O.parent/'M24ReloadRelease20261028/author_release.py').read_text())
for name in ('paced_time','Q','mix'):
 exec(compile(ast.unparse(next(n for n in source.body if isinstance(n,ast.FunctionDef) and n.name==name)),name,'exec'))
source_frames=[0,8,18,21,24,27,30,34,38,40,44,50,54]
paced_frames=[0,8,24,34,43,54,64,77,90,96,104,116,120];EXTRA=66
def frame(f,r):
 f=f.normalized();r=(r-f*r.dot(f)).normalized();return Matrix((f,r,f.cross(r))).transposed()
node=next(n for n in ast.parse((O.parent/'M24MagazineGraspEquip20261028/contact_pose.py').read_text()).body if isinstance(n,ast.FunctionDef) and n.name=='arm_to_hand')
exec(compile(ast.unparse(node),'native_arm','exec'))
def pose(role,f,layer=True,data=None):
 data=ue if data is None else data;desc=data['clips'][role];f=max(0,min(desc['keys']-1,f));i=min(int(f),desc['keys']-2);w=f-i;family='mag10' if role.endswith('_mag10') else 'base'
 ts={t['bone']:t for t in next(c for c in data['profiles'][family] if c['base']==desc['path'])['tracks']};out={};local={}
 for j,n in enumerate(names):
  a=unpack(desc['poses'][str(i)][j]);b=unpack(desc['poses'][str(i+1)][j]);p=a[0].lerp(b[0],w);q=a[1].slerp(b[1],w);sc=a[2].lerp(b[2],w)
  if layer and n in ts:
   dp,dq,ds=sample(ts[n],f/30);p+=dp;q=dq@q;sc+=ds
  local[n]=K@Matrix.LocRotScale(p,q,sc)@K;out[n]=out[parents[n]]@local[n] if parents[n] else local[n]
 return out,local
def hermite(p0,p1,v0,v1,t,d):
 t=max(0,min(1,t));return p0*(2*t**3-3*t*t+1)+v0*d*(t**3-2*t*t+t)+p1*(-2*t**3+3*t*t)+v1*d*(t**3-t*t)
def camera_spin(m,degrees):
 p,q,sc=m.decompose();rot=Quaternion(Vector((.2,.8,.4)).normalized(),math.radians(degrees));return Matrix.LocRotScale(p,(Cri@rot.to_matrix()@Cr).to_quaternion()@q,sc)
digits=[f'{d}_{j:02d}_l' for d in ('index','middle','ring','pinky','thumb') for j in (1,2,3)]
owned=['clavicle_l','upperarm_l','upperarm_twist_01_l','upperarm_twist_02_l','lowerarm_l','lowerarm_twist_01_l','lowerarm_twist_02_l','hand_l',*digits,'WPN_Magazine']
ref=json.loads((O.parent/'M24ReloadRelease20261028/m4_reference.json').read_text())
START=20.;RELEASE=25.25;RESET0=29.;RESET1=30.;RETRIEVE=31.;END=50.
final={};patch={};report={'clips':{},'release_source_frame':RELEASE,'release_paced_seconds':paced_time(RELEASE),'window':[START,END],'clock_unchanged':True,'runtime_tested':False,'reference':ref['path'],'mesh':'Existing M24 V9/115 morphs; no mesh changes'}
for role in ('reload','reload_empty','reload_mag10','reload_empty_mag10'):
 family='mag10' if role.endswith('_mag10') else 'base';baseline,base_locals=pose(role,START);anchor,_=pose(role,22,data=old_ue)
 G=anchor['WPN_Magazine'].inverted()@anchor['hand_l'];M0=pose(role,22)[0]['WPN_Magazine'];P0=C@M0.translation
 P1=Vector((44.,-1.,-22.5));V1=Vector((-6.,-52.,4.))
 eps=.02;ta=paced_time(22-eps);tb=paced_time(22+eps)
 V0=C.to_3x3()@(pose(role,22+eps)[0]['WPN_Magazine'].translation-pose(role,22-eps)[0]['WPN_Magazine'].translation)/(tb-ta)
 t0=paced_time(22);tr=paced_time(RELEASE);tt=paced_time(RETRIEVE)
 release_ref,_=pose(role,23,data=old_ue);MR=release_ref['WPN_Magazine'];M1=camera_spin(MR,-18)
 M1.translation=Ci@P1
 def held_mag(f):
  if f<=22:return pose(role,f)[0]['WPN_Magazine']
  t=(paced_time(f)-t0)/(tr-t0);angle=hermite(0.,-18.,0.,-100.,t,tr-t0)
  m=camera_spin(mix(M0,MR,ease(t)),angle);m.translation=Ci@hermite(P0,P1,V0,V1,t,tr-t0);return m
 # Preserve the shell-relative grasp; orient a short flick without forcing a wrist roll.
 H0=M1@G;H1,ret_local=pose(role,RETRIEVE);H1=H1['hand_l'];HP0=C@H0.translation;HP1=C@H1.translation
 a=pose(role,RETRIEVE-eps)[0]['hand_l'].translation;b=pose(role,RETRIEVE+eps)[0]['hand_l'].translation
 HV1=C.to_3x3()@(b-a)/(paced_time(RETRIEVE+eps)-paced_time(RETRIEVE-eps))
 def departing_hand(f):
  t=(paced_time(f)-tr)/(tt-tr);h=mix(H0,H1,ease(t));h.translation=Ci@hermite(HP0,HP1,V1,HV1,t,tt-tr);return h
 def dropped_mag(f):
  dt=paced_time(f)-tr;m=camera_spin(M1,-100*dt)
  m.translation=Ci@(P1+V1*dt+Vector((0,0,-490.5*dt*dt)));return m
 open_q={};closed_q={}
 for n in digits:
  d,j,_=n.split('_');j=int(j);closed=(anchor[parents[n]].inverted()@anchor[n]).to_quaternion();closed_q[n]=closed
  if d=='thumb':
   target=local_rest[n].to_quaternion()@Q(*ref['frames']['24']['digits'][n]);angle=closed.rotation_difference(target).angle;angle=min(angle,2*math.pi-angle)
   open_q[n]=closed.slerp(target,min(1,math.radians(24 if j==1 else 13)/max(angle,1e-6)))
  else:
   flex={1:12,2:22,3:12}[j];fan={'index':-4,'middle':0,'ring':3,'pinky':6}[d] if j==1 else 0
   open_q[n]=local_rest[n].to_quaternion()@Q(y=fan,z=flex)
 out=[];tracks={n:[] for n in owned};times=[];lastq={}
 for k in range((ue['clips'][role]['keys']-1)*4+1):
  f=k/4;original,locals=pose(role,f);row=clone(original)
  if START<f<END:
   # Recover the native elbow trajectory at the saved shoulder anchor.
   # The old source retracts its shoulder too early for a visible toss.
   native,native_local=pose(role,f,data=old_ue) if f<35 else (original,locals)
   if f<35:
    shoulder=original['clavicle_l']@native['clavicle_l'].inverted()
    for n in names:
     if under(n,'clavicle_l'):row[n]=shoulder@native[n]
   h=row['hand_l'].copy()
   if f<=RELEASE:
    mag=held_mag(f);h=mag@G
    h=mix(row['hand_l'],h,ease((f-START)/1.0))
   elif f<RETRIEVE:h=departing_hand(f)
   elif f<35:h=mix(h,original['hand_l'],ease((f-RETRIEVE)/4))
   # Seat first, then slide the open hand around the magazine rather than dwelling under it.
   if 40<f<50:
    w=ease((f-40)/3)*(1-ease((f-44)/6));h.translation+=Ci.to_3x3()@Vector((-.8*w,-3.3*w,-.6*w))
   try:row=arm_to_hand(row,h)
   except ValueError:
    print('REACH',role,f,list(C@row['upperarm_l'].translation),list(C@h.translation),(h.translation-row['upperarm_l'].translation).length,flush=True);raise
   for n in names:
    if n=='hand_l' or not under(n,'hand_l'):continue
    p,q,sc=locals[n].decompose()
    if n in digits and f<35:
     digit=n.split('_')[0];begin={'thumb':24.25,'index':24.3,'middle':24.45,'ring':24.55,'pinky':24.6}[digit]
     w=ease((f-begin)/1.0);cq=closed_q[n]
     if f<21:q=q.slerp(cq,ease(f-START))
     else:q=cq.slerp(open_q[n],w)
     if f>RETRIEVE:q=q.slerp(locals[n].to_quaternion(),ease((f-RETRIEVE)/3))
    row[n]=row[parents[n]]@Matrix.LocRotScale(p,q,sc)
   if f<=RELEASE:mag=held_mag(f)
   elif f<RESET0:mag=dropped_mag(f)
   elif f<RESET1:
    # Both endpoints lie below the view frustum; the same prop changes role out of view.
    mag=mix(dropped_mag(f),original['WPN_Magazine'],ease((f-RESET0)/(RESET1-RESET0)))
   else:mag=original['WPN_Magazine']
   D=mag@original['WPN_Magazine'].inverted()
   for n in names:
    if under(n,'WPN_Magazine'):row[n]=D@original[n]
  out.append(row);times.append(f/30);_,raw=pose(role,f,False)
  for n in owned:
   local=row[parents[n]].inverted()@row[n];p,q,sc=(K@local@K).decompose();bp,bq,bs=(K@raw[n]@K).decompose();dq=q@bq.inverted()
   if n in lastq and dq.dot(lastq[n])<0:dq=-dq
   lastq[n]=dq.copy();tracks[n].extend([*(p-bp),dq.x,dq.y,dq.z,dq.w,*(sc-bs)])
 final[role]=out;patch[family+'/'+role]={'base':ue['clips'][role]['path'],'window':[START/30,END/30],'tracks':[{'bone':n,'times':times,'values':values} for n,values in tracks.items()]}
(O/'flow_patch.json').write_text(json.dumps(patch))
(O/'final_poses.json').write_text(json.dumps({role:[{n:[list(v) for v in m] for n,m in row.items()} for row in rows] for role,rows in final.items()}))
node=next(n for n in ast.parse((O.parent/'M24Hold20261027/author_hold.py').read_text()).body if isinstance(n,ast.FunctionDef) and n.name=='bake')
node.body=[n for n in node.body if not(isinstance(n,ast.Expr) and isinstance(n.value,ast.Call) and isinstance(n.value.func,ast.Name) and n.value.func.id=='twists')]
code=ast.unparse(node).replace('(f, row[k][axis])','(f / 4, row[k][axis])').replace('s.frame_end = len(rows) - 1','s.frame_end = (len(rows) - 1) // 4').replace('(len(rows) - 1) / 30','(len(rows) - 1) / 120')
exec(compile(code,'bake','exec'))
for role,rows in final.items():
 r.animation_data_clear();old=bpy.data.actions.get('A_M24_'+role)
 if old:bpy.data.actions.remove(old)
 bake(role,rows)
bpy.context.preferences.filepaths.save_version=0;bpy.ops.wm.save_as_mainfile(filepath=str(O/'M24_ReloadFlow_Editable.blend'))
(O/'authoring.json').write_text(json.dumps(report,indent=2));print('M24_RELOAD_FLOW_AUTHORED',flush=True)
