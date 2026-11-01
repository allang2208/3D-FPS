"""M4-style separate release/retrieval phases on the current native M24 rig.

No rendering or runtime tests. Existing grasp, bolt and equip work is retained.
"""
from pathlib import Path
exec(compile((Path(__file__).parent/'library.py').read_text(),'lib','exec'))
C=Matrix(json.loads((O.parent/'M24Hold20261027/hip-calibration.json').read_text())['hip_transform'])@Matrix.Diagonal((100,-100,100,1))
source_frames=[0,8,18,21,24,27,30,34,38,40,44,50,54]
paced_frames=[0,8,24,34,43,54,64,77,90,96,104,116,120]
EXTRA=66
def paced_time(f):
 # Invert the same monotone Hermite map used by M24ReloadTiming.
 if f>=54:return (f+EXTRA)/30
 i=max(0,min(len(source_frames)-2,bisect.bisect_right(source_frames,f)-1))
 def slope(k):
  if k==0 or k==len(source_frames)-1:return 1.
  a=(source_frames[k]-source_frames[k-1])/(paced_frames[k]-paced_frames[k-1]);b=(source_frames[k+1]-source_frames[k])/(paced_frames[k+1]-paced_frames[k]);return 2*a*b/(a+b)
 span=paced_frames[i+1]-paced_frames[i];a=source_frames[i];b=source_frames[i+1];lo=0.;hi=1.
 for _ in range(30):
  t=(lo+hi)*.5;t2=t*t;t3=t2*t;v=(2*t3-3*t2+1)*a+(t3-2*t2+t)*span*slope(i)+(-2*t3+3*t2)*b+(t3-t2)*span*slope(i+1)
  if v<f:lo=t
  else:hi=t
 return (paced_frames[i]+span*(lo+hi)*.5)/30
def Q(x=0,y=0,z=0):return Quaternion((0,0,1),math.radians(z))@Quaternion((0,1,0),math.radians(y))@Quaternion((1,0,0),math.radians(x))
def mix(a,b,w):
 p,q,sc=a.decompose();pp,qq,ss=b.decompose();return Matrix.LocRotScale(p.lerp(pp,w),q.slerp(qq,w),sc.lerp(ss,w))
def pose(role,f,layer=True):
 data=ue['clips'][role];i=min(int(f),data['keys']-2);w=f-i;family='mag10' if role.endswith('_mag10') else 'base'
 tracks={t['bone']:t for t in next(c for c in ue['profiles'][family] if c['base']==data['path'])['tracks']};out={};local={}
 for j,n in enumerate(names):
  a=unpack(data['poses'][str(i)][j]);b=unpack(data['poses'][str(i+1)][j]);p=a[0].lerp(b[0],w);q=a[1].slerp(b[1],w);sc=a[2].lerp(b[2],w)
  if layer and n in tracks:
   dp,dq,ds=sample(tracks[n],f/30);p+=dp;q=dq@q;sc+=ds
  local[n]=K@Matrix.LocRotScale(p,q,sc)@K;out[n]=out[parents[n]]@local[n] if parents[n] else local[n]
 return out,local
ref=json.loads((O/'m4_reference.json').read_text());digits=[f'{d}_{j:02d}_l' for d in ('index','middle','ring','pinky','thumb') for j in (1,2,3)]
owned=['clavicle_l','upperarm_l','upperarm_twist_01_l','upperarm_twist_02_l','lowerarm_l','lowerarm_twist_01_l','lowerarm_twist_02_l','hand_l',*digits,'WPN_Magazine']
report={'clips':{},'reference':ref['path'],'reference_action':ref['action'],'clock':{'source':source_frames,'paced':paced_frames,'extra_source_frames':EXTRA},'release_source_frame':26.25,'new_grasp_source_frame':34,'runtime_tested':False,'rendered':False}
patch={};final={}
for role in ('reload','reload_empty','reload_mag10','reload_empty_mag10'):
 rows=clips[role];family='mag10' if role.endswith('_mag10') else 'base'
 anchor=rows[23];anchor_hand=anchor['WPN_root'].inverted()@anchor['hand_l'];anchor_mag=anchor['WPN_root'].inverted()@anchor['WPN_Magazine']
 retrieve_hand=rows[31]['WPN_root'].inverted()@rows[31]['hand_l'];open_q={}
 for n in digits:
  d,j,_=n.split('_');j=int(j);closed=(anchor[parents[n]].inverted()@anchor[n]).to_quaternion()
  if d=='thumb':
   target=local_rest[n].to_quaternion()@Q(*ref['frames']['24']['digits'][n]);angle=closed.rotation_difference(target).angle;angle=min(angle,2*math.pi-angle)
   open_q[n]=closed.slerp(target,min(1,math.radians(18 if j==1 else 10)/max(angle,1e-6)))
  else:
   flex=ref['frames']['24']['digits'][n][2]
   flex=max(0,min(20,flex)) if j==1 else max(10,min(30,flex)) if j==2 else max(5,min(20,flex))
   fan={'index':-4,'middle':0,'ring':3,'pinky':6}[d] if j==1 else 0
   open_q[n]=local_rest[n].to_quaternion()@Q(y=fan,z=flex)
 out=[];tracks={n:[] for n in owned};times=[];lastq={}
 for k in range((len(rows)-1)*4+1):
  f=k/4;old,locals=pose(role,f);row=clone(old)
  if 22<f<35:
   # Keep the freed magazine and palm in the lower visible corridor briefly.
   # The hand then travels empty to the existing off-screen retrieval point.
   if f<24:
    t=(f-22)/2;support_frame=22+2*t-t*t
   elif f<=27.5:support_frame=23
   elif f<31:
    t=(f-27.5)/3.5;support_frame=23+8*(3*t*t-2*t*t*t)+3.5*(t*t*t-t*t)
   else:support_frame=f
   support,support_locals=pose(role,support_frame);transport=old['WPN_root']@support['WPN_root'].inverted()
   # Retain the entire native shoulder/elbow/wrist chain at the release pose.
   # Re-timing only the wrist would overextend the still-retreating source arm.
   for n in names:
    if under(n,'clavicle_l'):row[n]=transport@support[n]
   for n in names:
    if n=='hand_l' or not under(n,'hand_l'):continue
    p,q,sc=support_locals[n].decompose()
    if n in open_q:
     d=n.split('_')[0];start={'index':24,'middle':24.1,'ring':24.2,'pinky':24.3,'thumb':24.1}[d]
     weight=ease((f-start)/2.5)*(1-ease((f-31)/3));q=q.slerp(open_q[n],weight)
    row[n]=row[parents[n]]@Matrix.LocRotScale(p,q,sc)
   heldmag=old['WPN_root']@anchor_mag
   if f<24:mag=transport@support['WPN_Magazine']
   elif f<=26.25:mag=heldmag
   elif f<30:
    drop=min(f,29);elapsed=paced_time(drop)-paced_time(26.25)
    camera_delta=Vector((0,-10*elapsed,-45*elapsed-490.5*elapsed*elapsed))
    mag=heldmag.copy();mag.translation+=C.inverted().to_3x3()@camera_delta
    # Switch props only below the screen; both endpoints are below the hand.
    if f>29:mag=mix(mag,old['WPN_Magazine'],ease(f-29))
   else:mag=old['WPN_Magazine']
   D=mag@old['WPN_Magazine'].inverted()
   for n in names:
    if under(n,'WPN_Magazine'):row[n]=D@old[n]
  out.append(row);times.append(f/30);_,raw=pose(role,f,False)
  for n in owned:
   local=row[parents[n]].inverted()@row[n];p,q,sc=(K@local@K).decompose();bp,bq,bs=(K@raw[n]@K).decompose();dq=q@bq.inverted()
   if n in lastq and dq.dot(lastq[n])<0:dq=-dq
   lastq[n]=dq.copy();tracks[n].extend([*(p-bp),dq.x,dq.y,dq.z,dq.w,*(sc-bs)])
 final[role]=out
 patch[family+'/'+role]={'base':ue['clips'][role]['path'],'window':[22/30,35/30],'tracks':[{'bone':n,'times':times,'values':values} for n,values in tracks.items()]}
(O/'release_patch.json').write_text(json.dumps(patch))
# Preserve quarter-frame source keys at the original 30 Hz authoring clock.
node=next(n for n in ast.parse((O.parent/'M24Hold20261027/author_hold.py').read_text()).body if isinstance(n,ast.FunctionDef) and n.name=='bake')
node.body=[n for n in node.body if not(isinstance(n,ast.Expr) and isinstance(n.value,ast.Call) and isinstance(n.value.func,ast.Name) and n.value.func.id=='twists')]
code=ast.unparse(node).replace('(f, row[k][axis])','(f / 4, row[k][axis])').replace('s.frame_end = len(rows) - 1','s.frame_end = (len(rows) - 1) // 4').replace('(len(rows) - 1) / 30','(len(rows) - 1) / 120')
exec(compile(code,'bake','exec'))
for role,rows in final.items():
 r.animation_data_clear();old=bpy.data.actions.get('A_M24_'+role)
 if old:bpy.data.actions.remove(old)
 bake(role,rows)
bpy.context.preferences.filepaths.save_version=0;bpy.ops.wm.save_as_mainfile(filepath=str(O/'M24_ReloadRelease_Editable.blend'))
(O/'authoring.json').write_text(json.dumps(report,indent=2));print('M24_RELEASE_AUTHORED',flush=True)
