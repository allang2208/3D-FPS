"""Retarget the original UC Blend's evaluated right arm, hand and twist rig."""
import bpy,ast,json,gzip,math,sys,numpy as np
from pathlib import Path
from mathutils import Matrix,Vector,Quaternion
O=Path(__file__).parent;S=O.parent;BASE=S/'M870Tactical20261015';PREV=S/'M870ReloadWrist20261016'
X=O/'Exports';(X/'Animations').mkdir(parents=True,exist_ok=True)
D=json.loads((O/'reference_poses.json').read_text());surface=json.loads((O/'reference_surfaces.json').read_text())
def meters(m):
 m=Matrix(m);m.translation*=.0254;return m
sr={n:meters(m) for n,m in D['rest'].items()};sp={k:[{n:meters(m) for n,m in row.items()} for row in v['rows']] for k,v in D['clips'].items()}
prefix='ValveBiped.Bip01_R_'
bpy.ops.wm.open_mainfile(filepath=str(S/'M870Super90Sprint20261016/M870_Super90Sprint_Editable.blend'),use_scripts=False)
r=bpy.data.objects['SK_Super90'];s=bpy.context.scene;I=Matrix.Identity(4)
rest={b.name:b.matrix_local.copy() for b in r.data.bones};parents={b.name:b.parent.name if b.parent else None for b in r.data.bones}
local_rest={n:rest[parents[n]].inverted()@m if parents[n] else m for n,m in rest.items()}
inputs=json.loads((S/'M870ReloadContact20261016/authoring.json').read_text())['clips']
idle_name=json.loads((S/'M870AKMArmSupport20261016/authoring.json').read_text())['clips']['idle']['action']
a=bpy.data.actions[idle_name];r.animation_data.action=a;r.animation_data.action_slot=a.slots[0];s.frame_set(0)
idle={b.name:b.matrix.copy() for b in r.pose.bones}
def unit(v):return v.normalized()
def frame(axis,normal):
 y=unit(axis);z=unit(normal-y*normal.dot(y));return Matrix((y.cross(z),y,z)).transposed()
def palm(p,source=False):
 ns=[prefix+n for n in ('Hand','Finger2','Finger1','Finger4')] if source else ['hand_r','middle_01_r','index_01_r','pinky_01_r']
 h,m,i,k=[p[n].translation for n in ns];return frame(m-h,(i-k).cross(m-h))
def mix(a,b,w):
 p,q,sc=a.decompose();v,t,ss=b.decompose()
 if q.dot(t)<0:t=-t
 return Matrix.LocRotScale(p.lerp(v,w),q.slerp(t,w),sc.lerp(ss,w))
def ease(t):
 t=max(0,min(1,t));return t*t*(3-2*t)
def sample(name,f):
 rows=sp[name];f=max(0,min(len(rows)-1,f));i=int(f)
 return {n:mix(m,rows[min(i+1,len(rows)-1)][n],f-i) for n,m in rows[i].items()}
def under(n,root):
 while n:
  if n==root:return True
  n=parents.get(n)
 return False
sf=frame(sp['Idle'][0]['870_flash'].translation-sp['Idle'][0]['870_bolt'].translation,sp['Idle'][0]['870_bolt'].translation-sp['Idle'][0]['870_loadingport'].translation)
tf=frame(idle['WPN_FrontSight'].translation-idle['WPN_RearSight'].translation,idle['WPN_RearSight'].translation-idle['WPN_SOCKET_Magazine'].translation)
C=(tf@sf.inverted()).to_4x4();C.translation=idle['WPN_SOCKET_Magazine'].translation-C.to_3x3()@sp['Idle'][0]['870_loadingport'].translation
BP=palm(sr,True);TP=palm(rest);hand_map=BP@TP.inverted()
with gzip.open(PREV/'native_arms.json.gz','rt',encoding='utf-8') as f:skin=json.load(f)
native_vertices=[Vector((v[0]/100,-v[1]/100,v[2]/100)) for v in skin['vertices']]
def tip_axis(data,n,points,origin):
 ids=[i for i,w in enumerate(data['weights']) if w.get(n,0)>.5]
 center=sum((points[i] for i in ids),Vector())/len(ids)
 return center-origin
source_vertices=[Vector(v)*.0254 for v in surface['c_arms_combine']['positions']]
maps={};donor_names={};axes={}
for digit,word in enumerate(('thumb','index','middle','ring','pinky')):
 for j in range(3):
  n=f'{word}_{j+1:02d}_r';dn=prefix+'Finger'+str(digit)+('' if j==0 else str(j));donor_names[n]=dn
  if j<2:
   sa=sr[prefix+'Finger'+str(digit)+str(j+1)].translation-sr[dn].translation
   ta=rest[f'{word}_{j+2:02d}_r'].translation-rest[n].translation
  else:
   sa=tip_axis(surface['c_arms_combine'],dn,source_vertices,sr[dn].translation)
   ta=tip_axis(skin,n,native_vertices,rest[n].translation)
  # Valve and V7 have different reference finger directions. Register these
  # once in their palm planes, then preserve the entire source rotation track.
  # Unlike the rejected layer there is no frame-wise hinge/roll rewrite.
  maps[n]=frame(sa,BP.col[2])@frame(ta,TP.col[2]).inverted();axes[n]=(sa,ta)
rf=rest['hand_r'].translation-rest['lowerarm_r'].translation;ru=rest['lowerarm_r'].translation-rest['upperarm_r'].translation
srf=sr[prefix+'Hand'].translation-sr[prefix+'Forearm'].translation;sru=sr[prefix+'Forearm'].translation-sr[prefix+'UpperArm'].translation
fore_map=frame(srf,BP.col[2])@frame(rf,TP.col[2]).inverted()
upper_map=frame(sru,BP.col[2])@frame(ru,TP.col[2]).inverted()
source_shell_points=[sr['870_shell2'].inverted()@(Vector(p)*.0254) for p,w in zip(surface['shell for animating ']['positions'],surface['shell for animating ']['weights']) if w.get('870_shell2',0)>.5]
source_shell_center=sum(source_shell_points,Vector())/len(source_shell_points)
shell=bpy.data.objects['M870_ReloadShell'];shell_points=[rest['WPN_Shell'].inverted()@shell.matrix_world@v.co for v in shell.data.vertices]
target_shell_center=sum(shell_points,Vector())/len(shell_points)
handbones=[n for n in rest if under(n,'hand_r')]
fit_path=O/'contact_registration.json'
contact_fit=Matrix(json.loads(fit_path.read_text())['hand_local_matrix']) if fit_path.exists() and '--without-contact-fit' not in sys.argv else I
curve_path=O/'contact_curve.json'
contact_keys=json.loads(curve_path.read_text())['keys'] if curve_path.exists() and '--without-contact-fit' not in sys.argv else []
def contact_at(name,phase):
 if not contact_keys:return contact_fit
 # Both source end clips begin at reloadinsert frame 26, which is the same
 # grab pose as frame 0. Reuse that calibration at the clip boundary.
 if name!='reloadinsert':return Matrix(contact_keys[0]['matrix'])
 if phase>12:return mix(Matrix(contact_keys[-1]['matrix']),Matrix(contact_keys[0]['matrix']),ease((phase-12)/14))
 for left,right in zip(contact_keys,contact_keys[1:]):
  if phase<=right['source_phase']:
   return mix(Matrix(left['matrix']),Matrix(right['matrix']),ease((phase-left['source_phase'])/(right['source_phase']-left['source_phase'])))
 return Matrix(contact_keys[-1]['matrix'])
def mapped_hand(p,M):
 """One per-bone anatomical bind registration, then the full source rotation."""
 mq=M.to_quaternion();hn=prefix+'Hand'
 q=mq@p[hn].to_quaternion()@sr[hn].to_quaternion().inverted()@hand_map.to_quaternion()@rest['hand_r'].to_quaternion()
 row={'hand_r':Matrix.LocRotScale(M@p[hn].translation,q,Vector((1,1,1)))}
 for n in handbones:
  if n=='hand_r':continue
  parent=parents[n];base=row[parent]@local_rest[n]
  if n in donor_names:
   dn=donor_names[n];q=mq@p[dn].to_quaternion()@sr[dn].to_quaternion().inverted()@maps[n].to_quaternion()@rest[n].to_quaternion()
   base=Matrix.LocRotScale(base.translation,q,Vector((1,1,1)))
  row[n]=base
 return row
def registration(row,p):return row['WPN_root']@idle['WPN_root'].inverted()@C@sp['Idle'][0]['870_parent']@p['870_parent'].inverted()
# Reuse the source retreat path. Its last fast fetch keys cannot be squeezed
# into two target frames; mix source phase and travelled distance to distribute
# that same path across the existing sixteen-frame post-insertion interval.
release_phases=np.arange(12.,26.001,.25)
release_points=[]
for phase in release_phases:
 p=sample('reloadinsert',float(phase));release_points.append(list(p['870_parent'].inverted()@p[prefix+'Hand'].translation))
release_lengths=np.r_[0.,np.cumsum(np.linalg.norm(np.diff(release_points,axis=0),axis=1))]
release_clock=.25*(release_phases-12)/14+.75*release_lengths/release_lengths[-1]
def source_clock(f,role):
 if f<18:return 'reloadstart',20*f/18
 if f<360:
  idx=0 if f<60 else min(6,1+(f-60)//50);start=18 if idx==0 else 60+(idx-1)*50;contact=44+idx*50;end=60+idx*50
  return 'reloadinsert',12*(f-start)/(contact-start) if f<=contact else float(np.interp((f-contact)/(end-contact),release_clock,release_phases))
 name='reloadendCycle' if role=='reload_full' else 'reloadend';last=424 if role=='reload_full' else 399
 if role!='reload_full':return name,(f-360)/(last-360)*22
 # Keep the current pump event clock. Reference frame 26 is the lock point.
 knots=[(360,0),(378,15),(386,20),(389,20),(397.2,26),(424,39)]
 for (a,x),(b,y) in zip(knots,knots[1:]):
  if f<=b:return name,x+(y-x)*(f-a)/(b-a)
 return name,39
def correction(row,p,M):
 return row['WPN_Shell']@target_shell_center-M@(p['870_shell2']@source_shell_center)
def support(row,p,M,hand):
 mq=M.to_quaternion();fore=mq@(p[prefix+'Hand'].translation-p[prefix+'Forearm'].translation).normalized()
 upper=mq@(p[prefix+'Forearm'].translation-p[prefix+'UpperArm'].translation).normalized()
 h=hand.translation;e=h-fore*rf.length;a=e-upper*ru.length
 def deform(source):return p[source].to_quaternion()@sr[source].to_quaternion().inverted()
 du=deform(prefix+'UpperArm');df=deform(prefix+'Forearm');dn=deform(prefix+'Ulna');dw=deform(prefix+'Wrist')
 uq=mq@du@upper_map.to_quaternion()@rest['upperarm_r'].to_quaternion()
 row['upperarm_r']=Matrix.LocRotScale(a,uq,Vector((1,1,1)))
 delta=row['upperarm_r']@rest['upperarm_r'].inverted()
 for n in rest:
  if n!='upperarm_r' and under(n,'upperarm_r') and not under(n,'lowerarm_r'):row[n]=delta@rest[n]
 for n in ('lowerarm_r','lowerarm_aux_r','lowerarm_twist_02_r','lowerarm_twist_01_r'):
  off=rest[n].translation-rest['lowerarm_r'].translation;t=off.dot(rf)/rf.length_squared
  a0,a1,fraction=(df,dn,t*2) if t<=.5 else (dn,dw,(t-.5)*2)
  if a0.dot(a1)<0:a1=-a1
  dq=a0.slerp(a1,fraction)
  if n=='lowerarm_aux_r':dq=du.slerp(df,.5)
  driver=mq@dq@fore_map.to_quaternion()
  # Native forearm stations carry pronation, not the source elbow's swing.
  # Keep every skin station on the same shaft; bending its deformation axis
  # pulls mid-forearm vertices outward and produces the rejected bulge.
  driver=(driver@rf).rotation_difference(fore)@driver
  pos=e+t*fore*rf.length+driver@(off-t*rf)
  row[n]=Matrix.LocRotScale(pos,driver@rest[n].to_quaternion(),Vector((1,1,1)))
 row['clavicle_r'].translation+=a-(row['clavicle_r']@local_rest['upperarm_r']).translation
 return row
tree=ast.parse((BASE/'author_m870.py').read_text());authored={}
exec(compile(ast.Module(body=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in ('select','bake')],type_ignores=[]),str(BASE/'author_m870.py'),'exec'))
recipes={};report={'source':'Original UC Blend evaluated rig; source SMD bind is not used','reference_bind_registration':{n:[list(v) for v in m] for n,m in maps.items()},'clips':{}}
for role,entry in inputs.items():
 a=bpy.data.actions[entry['action']];r.animation_data.action=a;r.animation_data.action_slot=a.slots[0];count=round(entry['duration']*60)+1
 old=[]
 for f in range(count):s.frame_set(f);old.append({b.name:b.matrix.copy() for b in r.pose.bones})
 stages=[source_clock(f,role) for f in range(count)];poses=[sample(k,t) for k,t in stages];regs=[registration(row,p) for row,p in zip(old,poses)]
 corrections=[correction(old[f],poses[f],regs[f]) for f in range(count)]
 out=[]
 for f,(original,p,M,(name,phase)) in enumerate(zip(old,poses,regs,stages)):
  row={n:m.copy() for n,m in original.items()};hp=mapped_hand(p,M)
  # Register MCP landmarks as a complete palm, retaining native finger lengths.
  source_knuckles=sum((M@p[prefix+'Finger'+str(i)].translation for i in (1,2,3,4)),Vector())/4
  native_knuckles=sum((hp[n+'_01_r'].translation for n in ('index','middle','ring','pinky')),Vector())/4
  shift=source_knuckles-native_knuckles
  if name=='reloadinsert':
   if phase<=12:shift+=corrections[f]
   else:
    idx=0 if f<60 else min(6,1+(f-60)//50);contact=44+idx*50;end=min(60+idx*50,359)
    next_correction=corrections[end] if end<359 else corrections[18]
    shift+=corrections[contact].lerp(next_correction,ease((phase-12)/14))
  elif name=='reloadstart':shift+=corrections[18]*ease(f/18)
  else:shift+=corrections[18]*(1-ease(phase/9))
  for m in hp.values():m.translation+=shift
  fit_world=hp['hand_r']@contact_at(name,phase)@hp['hand_r'].inverted()
  for n in hp:hp[n]=fit_world@hp[n]
  # Preserve current stock contact at entry/exit while source owns the full
  # exposed loading interval. No held-pose freeze or synthetic finger opening.
  weight=ease(f/18) if f<18 else 1 if f<360 else 1-ease(phase/9)
  hand=mix(original['hand_r'],hp['hand_r'],weight)
  carry=hand@hp['hand_r'].inverted()
  for n in handbones:hp[n]=carry@hp[n]
  candidate=support({n:m.copy() for n,m in original.items()},p,carry@fit_world@M,hand)
  # Blend arm segment directions at the same ownership boundary, with native
  # lengths throughout; the source helper rotations remain authoritative inside.
  if weight<1:
   e=hand.translation-(original['hand_r'].translation-original['lowerarm_r'].translation).normalized().lerp((hand.translation-candidate['lowerarm_r'].translation).normalized(),weight).normalized()*rf.length
   a=e-(original['lowerarm_r'].translation-original['upperarm_r'].translation).normalized().lerp((candidate['lowerarm_r'].translation-candidate['upperarm_r'].translation).normalized(),weight).normalized()*ru.length
   candidate['clavicle_r']=mix(original['clavicle_r'],candidate['clavicle_r'],weight)
   candidate['upperarm_r']=mix(original['upperarm_r'],candidate['upperarm_r'],weight);candidate['upperarm_r'].translation=a
   for n in ('lowerarm_r','lowerarm_aux_r','lowerarm_twist_02_r','lowerarm_twist_01_r'):
    t=(rest[n].translation-rest['lowerarm_r'].translation).dot(rf)/rf.length_squared
    candidate[n]=mix(original[n],candidate[n],weight);candidate[n].translation=e+(hand.translation-e)*t
  for n in rest:
   if under(n,'clavicle_r') and not under(n,'hand_r'):row[n]=candidate[n]
  row['hand_r']=hand
  for n in handbones:
   if n=='hand_r':continue
   parent=parents[n];source_local=hp[parent].inverted()@hp[n];old_local=original[parent].inverted()@original[n]
   row[n]=row[parent]@mix(old_local,source_local,weight)
  if weight<1.e-8:row={n:m.copy() for n,m in original.items()}
  out.append(row)
 bake(role,out);recipes[role]={'input_action':entry['action'],'frames':count,'clock':stages}
report['clips']=authored;report['recipe']=recipes;report['source_to_target']=[list(v) for v in C]
report['contact_calibration']=[list(v) for v in contact_fit]
report['contact_keys']=contact_keys
report['release_source_phase_mapping']={'target_progress':release_clock.tolist(),'source_phase':release_phases.tolist(),'method':'25 percent phase and 75 percent source path distance; original right-arm/finger trajectory retained'}
report['runtime_tested']=False
a=bpy.data.actions[authored['reload_continuous']['action']];r.animation_data.action=a;r.animation_data.action_slot=a.slots[0];s.frame_set(31)
bpy.context.preferences.filepaths.save_version=0;bpy.ops.wm.save_as_mainfile(filepath=str(O/'M870_ReloadSource_Editable.blend'))
(O/'authoring.json').write_text(json.dumps(report,indent=2));print('M870_SOURCE_RELOAD_AUTHORED',2,flush=True)
