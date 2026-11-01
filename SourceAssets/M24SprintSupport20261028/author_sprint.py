"""Two-handed M24 high carry, driven by the existing shared sprint phase."""
from pathlib import Path
exec(compile((Path(__file__).parent/'library.py').read_text(),'sprint_library','exec'))
idle=clips['idle'][0]
C=Matrix(json.loads((O.parent/'M24Hold20261027/hip-calibration.json').read_text())['hip_transform'])@Matrix.Diagonal((100,-100,100,1));Ci=C.inverted()
pivot=C@idle['hand_r'].translation
CarryOffset=Vector((-5,8,-12))
FPS=120
def R(axis,degrees):return Matrix.Rotation(math.radians(degrees),4,axis)
def signed_twist(q,axis):
 if q.w<0:q=-q
 return 2*math.atan2(Vector((q.x,q.y,q.z)).dot(axis),q.w)
def frames(side,hand,phi=0.):
 u,l,h=[x+'_'+side for x in ('upperarm','lowerarm','hand')]
 S=idle[u].translation.copy();T=hand.translation;E0=idle[l].translation;H0=idle[h].translation
 a=(E0-S).length;b=(H0-E0).length;direction=T-S;d=direction.length;axis=direction.normalized()
 # Keep original shoulder anchors and native segment lengths. The high carry
 # is fitted within the arm's reach; no hand/arm scaling or stretched bones.
 if d>=a+b-.0005:raise RuntimeError('Carry exceeds native arm reach: '+side)
 pole=E0-S;pole=(pole-axis*pole.dot(axis)).normalized();pole=Quaternion(axis,math.radians(phi))@pole
 along=(a*a-b*b+d*d)/(2*d);E=S+axis*along+pole*math.sqrt(max(0,a*a-along*along))
 uq=(E0-S).rotation_difference(E-S)@idle[u].to_quaternion()
 lq=(H0-E0).rotation_difference(T-E)@idle[l].to_quaternion()
 return S,E,uq,lq
def target_transform(progress,phase=None):
 # The transition is fully raised when the existing loop crossfade starts.
 # Reversing the same canonical track also handles a quick Shift release.
 w=ease(progress/.65)
 sway=Vector((0,0,0));yaw=roll=pitch=0.
 if phase is not None:
  sway=Vector((.24*math.sin(2*phase+.25),.65*math.sin(phase),.85*math.cos(2*phase)))
  pitch=.85*math.sin(2*phase-.35);yaw=1.15*math.sin(phase-.18);roll=1.35*math.sin(phase+.25)
 turn=R('X',(10+roll)*w)@R('Z',(6+yaw)*w)@R('Y',(-67+pitch)*w)
 dc=Matrix.Translation(CarryOffset*w+sway*w)@Matrix.Translation(pivot)@turn@Matrix.Translation(-pivot)
 return Ci@dc@C
def fit_cost(side,hand,phi):
 S,E,uq,lq=frames(side,hand,phi);u,l,h=[x+'_'+side for x in ('upperarm','lowerarm','hand')]
 axis=(rest[h].translation-rest[l].translation).normalized();axis=rest[l].to_quaternion().inverted()@axis
 rel=(lq.inverted()@hand.to_quaternion())@(rest[l].to_quaternion().inverted()@rest[h].to_quaternion()).inverted()
 roll=signed_twist(rel,axis);swing=(rel@Quaternion(axis,-roll)).angle
 if swing>math.pi:swing=2*math.pi-swing
 pc=C@E
 return (math.degrees(swing)/40)**2+(max(0,abs(math.degrees(roll))-75)/30)**2+(phi/40)**2*.7+max(0,(15-pc.length)/8)**2
# Fit one continuous elbow-plane trajectory, anchored to the existing idle.
# This is authoring, not an iterative solver in the game thread.
phis=np.arange(-45,46,3,dtype=float);progresses=np.linspace(0,1,61);paths={}
for side in ('l','r'):
 costs=np.array([[fit_cost(side,target_transform(p)@idle['hand_'+side],float(phi)) for phi in phis] for p in progresses])
 total=costs[0].copy();total[:]=1.e9;total[np.argmin(abs(phis))]=0;backs=[]
 for k in range(1,len(progresses)):
  transition=total[:,None]+((phis[:,None]-phis[None,:])/3)**2*4
  ix=transition.argmin(0);backs.append(ix);total=costs[k]+transition[ix,np.arange(len(phis))]
 index=int(total.argmin());path=[index]
 for back in reversed(backs):index=int(back[index]);path.append(index)
 values=phis[np.array(path[::-1])]
 # Retain the fit as a low-frequency continuous path; no discrete pole steps.
 smooth=np.convolve(np.pad(values,(5,5),mode='edge'),np.ones(11)/11,mode='valid')
 smooth*=np.array([ease(p/.25) for p in progresses]);paths[side]=smooth
def authored(progress,phase=None):
 if progress<=0:return clone(idle)
 D=target_transform(progress,phase);row=clone(idle)
 for n in names:
  if n.startswith('WPN_'):row[n]=D@idle[n]
 for side in ('l','r'):
  u,l,h=[x+'_'+side for x in ('upperarm','lowerarm','hand')];hand=D@idle[h]
  phi=float(np.interp(progress,progresses,paths[side]));S,E,uq,lq=frames(side,hand,phi)
  U=Matrix.LocRotScale(S,uq,Vector((1,1,1)));L=Matrix.LocRotScale(E,lq,Vector((1,1,1)))
  for n in names:
   if under(n,h):row[n]=D@idle[n]
   elif under(n,l):row[n]=L@idle[l].inverted()@idle[n]
   elif under(n,u):row[n]=U@idle[u].inverted()@idle[n]
  axis=rest[l].to_quaternion().inverted()@(rest[h].translation-rest[l].translation).normalized()
  ref=(rest[l].to_quaternion().inverted()@rest[h].to_quaternion()).inverted()
  oldrel=(idle[l].to_quaternion().inverted()@idle[h].to_quaternion())@ref
  rel=(lq.inverted()@hand.to_quaternion())@ref
  delta=signed_twist(rel,axis)-signed_twist(oldrel,axis)
  delta=(delta+math.pi)%(2*math.pi)-math.pi
  for j,share in ((1,1.),(2,.5)):
   n=f'lowerarm_twist_{j:02d}_{side}';loc=idle[l].inverted()@idle[n]
   row[n]=L@Matrix.LocRotScale(loc.translation,Quaternion(axis,delta*share)@loc.to_quaternion(),loc.to_scale())
 return row
roles=('sprint_enter','sprint_loop','sprint_exit');outputs={};patch={}
def reduced(track):
 ts=track['times'];keys=[unpack(track['values'][i:i+10]) for i in range(0,len(track['values']),10)]
 def error(a,b,w,key):
  p=a[0].lerp(b[0],w);q=a[1].slerp(b[1],w);sc=a[2].lerp(b[2],w)
  angle=(q.inverted()@key[1]).angle;angle=min(angle,2*math.pi-angle)
  return max((p-key[0]).length/.00005,angle/math.radians(.01),(sc-key[2]).length/.000001)
 zero=(Vector((0,0,0)),Quaternion(),Vector((0,0,0)))
 if all(error(zero,zero,0,k)<.05 for k in keys):return None
 if all(error(keys[0],keys[0],0,k)<.05 for k in keys):return {'bone':track['bone'],'times':[0.],'values':track['values'][:10]}
 keep={0,len(keys)-1};pending=[(0,len(keys)-1)]
 while pending:
  a,b=pending.pop()
  if b-a<2:continue
  err,k=max((error(keys[a],keys[b],(ts[i]-ts[a])/(ts[b]-ts[a]),keys[i]),i) for i in range(a+1,b))
  if err>1:keep.add(k);pending.extend(((a,k),(k,b)))
 ids=sorted(keep);return {'bone':track['bone'],'times':[ts[i] for i in ids],'values':[v for i in ids for v in track['values'][i*10:i*10+10]]}
for role in roles:
 data=ue['clips'][role];duration=(data['keys']-1)/data['fps'];rows=[];ts=[i/FPS for i in range(round(duration*FPS)+1)]
 for t in ts:
  p=t/duration if role=='sprint_enter' else 1-t/duration if role=='sprint_exit' else 1.
  rows.append(authored(p,2*math.pi*t/duration if role=='sprint_loop' else None))
 if role=='sprint_loop':rows[-1]=clone(rows[0])
 outputs[role]=rows;tracks=[]
 for n in names:
  values=[];last=None
  for t,row in zip(ts,rows):
   loc=K@(row[parents[n]].inverted()@row[n] if parents[n] else row[n])@K;p,q,sc=loc.decompose()
   pos=t*data['fps'];i=min(int(pos),data['keys']-2);w=pos-i
   a=unpack(data['poses'][str(i)][names.index(n)]);b=unpack(data['poses'][str(i+1)][names.index(n)])
   bp=a[0].lerp(b[0],w);bq=a[1].slerp(b[1],w);bs=a[2].lerp(b[2],w)
   dq=q@bq.inverted();dp=p-bp;ds=sc-bs
   if last is not None and last.dot(dq)<0:dq=-dq
   last=dq;values.extend([*dp,dq.x,dq.y,dq.z,dq.w,*ds])
  track=reduced({'bone':n,'times':ts,'values':values})
  if track:tracks.append(track)
 patch[role]={'base':data['path'],'duration':duration,'tracks':tracks}
(O/'sprint_patch.json').write_text(json.dumps(patch))
(O/'author_expected_profiles.json').write_text(json.dumps({family:[c for c in cs if c['base'] in {p['base'] for p in patch.values()}] for family,cs in ue['profiles'].items()}))
(O/'final_poses.json').write_text(json.dumps({role:[{n:[list(v) for v in m] for n,m in row.items()} for row in rows] for role,rows in outputs.items()}))
# Keep the editable actions at the same 120 Hz sampling as the exported deltas.
tree=ast.parse((O.parent/'M24Hold20261027/author_hold.py').read_text());node=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='bake')
node.body=[n for n in node.body if not(isinstance(n,ast.Expr) and isinstance(n.value,ast.Call) and isinstance(n.value.func,ast.Name) and n.value.func.id=='twists')]
report={'clips':{}}
exec(compile(ast.unparse(node).replace('/ 30','/ 120').replace('s.render.fps = 30','s.render.fps = 120'),'sprint_bake','exec'))
for role,rows in outputs.items():
 r.animation_data_clear();old=bpy.data.actions.get('A_M24_'+role)
 if old:bpy.data.actions.remove(old)
 bake(role,rows)
# This source document has one 120 Hz time base. Other roles remain editable
# in their original 30 Hz source files, rather than playing at the wrong speed.
for action in list(bpy.data.actions):
 if action.name.startswith('A_M24_') and action.name not in {'A_M24_'+role for role in roles}:bpy.data.actions.remove(action)
s.render.fps=120;r.animation_data.action=bpy.data.actions['A_M24_sprint_enter'];r.animation_data.action_slot=r.animation_data.action.slots[0];s.frame_set(60)
bpy.context.preferences.filepaths.save_version=0;bpy.ops.wm.save_as_mainfile(filepath=str(O/'M24_SupportedSprint_Editable.blend'))
(O/'authoring.json').write_text(json.dumps({'reference':'BV1Au9CYNEau 65-67 seconds','fps':120,'durations':{r:p['duration'] for r,p in patch.items()},'muzzle_lift_degrees':67,'camera_carry_delta_cm':list(CarryOffset),'hand_contact':'Both original idle grips locked in rifle space, including all native finger locals','elbow_poles_degrees':{k:list(v) for k,v in paths.items()},'runtime_tested':False,'rendered':False},indent=2))
print('M24_SUPPORTED_SPRINT_AUTHORED',flush=True)
