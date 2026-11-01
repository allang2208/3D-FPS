"""Build a conditional pistol-grip pose layer; keep the original M24 profiles."""
import bpy,json,gzip,ast,bisect,math,copy
from pathlib import Path
from mathutils import Matrix,Vector,Quaternion
O=Path(__file__).resolve().parent
D=json.load(gzip.open(O/'Inputs/m24_motion.json.gz','rt'));names=D['names'];parents=D['parents'];indices={n:i for i,n in enumerate(names)}
source=json.loads((O.parent/'M24ArmRebuild20261027/source_after.json').read_text())
rest={n:Matrix(m) for n,m in source['rest'].items()};local_rest={n:rest[parents[n]].inverted()@m if parents[n] else m for n,m in rest.items()}
K=Matrix.Diagonal((1,-1,1,1));Q=Matrix.Translation((0,.027,.078))@Matrix.Diagonal((-1,1,1,1))
donor=json.loads((O/'Inputs/m4_donor.json').read_text());layout=json.loads((O/'Inputs/layout.json').read_text())
contact_masks=json.loads((O.parent/'M24GripOutfit20261030/right_contact_mask.json').read_text())
tree=ast.parse((O.parent/'M24ReloadRefine20261028/install.py').read_text())
for n in tree.body:
 if isinstance(n,ast.FunctionDef) and n.name in ('qlerp','sample'):exec(compile(ast.unparse(n),n.name,'exec'))

def under(n,parent):
 while n:
  if n==parent:return True
  n=parents.get(n)
 return False

def raw(data,time,n):
 f=max(0.,min(time*data['fps'],data['keys']-1));lo=int(f);hi=min(lo+1,data['keys']-1);w=f-lo
 a=data['poses'][str(lo)][indices[n]];b=data['poses'][str(hi)][indices[n]]
 v=[x+(y-x)*w for x,y in zip(a,b)];v[3:7]=qlerp(a[3:7],b[3:7],w);return v

def transform(v):return Matrix.LocRotScale(Vector(v[:3]),Quaternion((v[6],*v[3:6])),Vector(v[7:10]))

def compose(entry,time):
 data=D['clips'][entry['base']];tracks={t['bone']:t for t in entry['tracks']};out={};local={}
 for n in names:
  v=raw(data,time,n);p,q,s=transform(v).decompose()
  if n in tracks:
   delta=sample(tracks[n],time,10,'values');p+=Vector(delta[:3]);q=Quaternion((delta[6],*delta[3:6]))@q;s+=Vector(delta[7:10])
  local[n]=K@Matrix.LocRotScale(p,q,s)@K;out[n]=out[parents[n]]@local[n] if parents[n] else local[n]
 return out,local

def frame(x,z):
 x=x.normalized();z=(z-x*z.dot(x)).normalized();return Matrix((x,z.cross(x).normalized(),z)).transposed()

def solve(row,target):
 # Shoulder and each native limb length are retained at this source instant.
 out={n:m.copy() for n,m in row.items()};S=row['upperarm_r'].translation;H=target.translation
 beforeU=row['lowerarm_r'].translation-S;beforeL=row['hand_r'].translation-row['lowerarm_r'].translation
 A,B=beforeU.length,beforeL.length;axis=H-S;d=axis.length;axis.normalize()
 if d>=A+B-.0001 or d<=abs(A-B)+.0001:raise RuntimeError(f'Unreachable pistol grip in {role} at {time}: {d}/{A+B}')
 pole=row['lowerarm_r'].translation-S;pole=(pole-axis*pole.dot(axis)).normalized()
 along=(A*A-B*B+d*d)/(2*d);E=S+axis*along+pole*math.sqrt(max(0,A*A-along*along))
 n0=beforeU.cross(beforeL).normalized();n1=(E-S).cross(H-E).normalized()
 uq=(frame(E-S,n1)@frame(beforeU,n0).transposed()).to_quaternion()@row['upperarm_r'].to_quaternion()
 lq=(frame(H-E,n1)@frame(beforeL,n0).transposed()).to_quaternion()@row['lowerarm_r'].to_quaternion()
 U=Matrix.LocRotScale(S,uq,row['upperarm_r'].to_scale());L=Matrix.LocRotScale(E,lq,row['lowerarm_r'].to_scale())
 for n in names:
  if under(n,'hand_r'):out[n]=target@row['hand_r'].inverted()@row[n]
  elif under(n,'lowerarm_r'):out[n]=L@row['lowerarm_r'].inverted()@row[n]
  elif under(n,'upperarm_r'):out[n]=U@row['upperarm_r'].inverted()@row[n]
 # Distribute only axial roll; wrist bend never becomes forearm twist.
 ax=rest['lowerarm_r'].to_quaternion().inverted()@(rest['hand_r'].translation-rest['lowerarm_r'].translation).normalized()
 relative=lq.inverted()@target.to_quaternion()@(rest['lowerarm_r'].to_quaternion().inverted()@rest['hand_r'].to_quaternion()).inverted()
 if relative.w<0:relative=-relative
 roll=2*math.atan2(Vector((relative.x,relative.y,relative.z)).dot(ax),relative.w)
 for j,w in ((1,1.),(2,.5)):
  n=f'lowerarm_twist_{j:02d}_r';lr=local_rest[n]
  out[n]=L@Matrix.LocRotScale(lr.translation,Quaternion(ax,roll*w)@lr.to_quaternion(),lr.to_scale())
 out['ik_hand_r']=target@row['hand_r'].inverted()@row['ik_hand_r'];return out

def smooth(x):
 x=max(0.,min(1.,x));return x*x*x*(10+x*(-15+6*x))

def mask(path,t,family,row,old_contact):
 values=contact_masks[family].get(path)
 if values:
  # Extend the actual contact blend to 100 ms, rather than snapping to the
  # donor between two 30 Hz keys. Preserve the entire bolt contact interior.
  first=next(a[0] for a in values if a[1]<.99);last=next(a[0] for a in reversed(values) if a[1]<.99)
  return 1-smooth((t-(first-.10))/.10) if t<first else smooth((t-last)/.10) if t>last else 0.
 if 'quick_melee' in path:
  # The existing stick-like strike grip is intentional. Change only release
  # from the rear grip and its return, using distance to the saved idle grip.
  rel=row['WPN_root'].inverted()@row['hand_r'];distance=(rel.translation-old_contact.translation).length
  angle=rel.to_quaternion().rotation_difference(old_contact.to_quaternion()).angle
  return (1-smooth((distance-.008)/.025))*(1-smooth((angle-.12)/.45))
 return 1.

donor_rest={n:K@Matrix(m)@K for n,m in donor['rest'].items()}
donor_local_rest={n:donor_rest[donor['parents'][n]].inverted()@m if donor['parents'][n] else m for n,m in donor_rest.items()}
fingers=[n for n in names if under(n,'hand_r') and n!='hand_r']
finger_rot={}
for n in fingers:
 p=K@transform(donor['pose'][n])@K
 finger_rot[n]=(local_rest[n]@donor_local_rest[n].inverted()@p).to_quaternion()
# Retarget the hand's local bone axes while preserving its physical grasp frame.
target_hand=Q@Matrix(layout['m4_donor_root_matrices']['hand_r'])@K
owned=[n for n in names if under(n,'upperarm_r')]+['ik_hand_r']
result=copy.deepcopy(D['profiles']);report={'profiles':{},'owned_bones':owned,'right_hand_source':donor['names'],'runtime_tested':False}
for family,spec in result.items():
 idle_entry=next(c for c in D['profiles'][family]['clips'] if c['base'].endswith('A_M24_idle'))
 idle,_=compose(idle_entry,0.);old_contact=idle['WPN_root'].inverted()@idle['hand_r']
 spec['family']='skeleton_'+family
 for entry in spec['clips']:
  original=next(c for c in D['profiles'][family]['clips'] if c['base']==entry['base']);role=entry['base'].split('.')[-1];duration=entry['duration'];data=D['clips'][entry['base']]
  rate=200 if 'Bipod' in role else 120
  times=sorted({0.,duration,*[i/rate for i in range(int(duration*rate)+1)]});tracks={n:{'bone':n,'times':times,'values':[]} for n in owned};last={}
  for time in times:
   row,local=compose(original,time);weight=mask(entry['base'],time,family,row,old_contact)
   fixed=row
   if weight>0:
    gun_motion=row['WPN_root']@rest['WPN_root'].inverted();desired=gun_motion@target_hand
    p0,q0,s0=row['hand_r'].decompose();p1,q1,_=desired.decompose()
    target=Matrix.LocRotScale(p0.lerp(p1,weight),q0.slerp(q1,weight),s0)
    fixed=solve(row,target)
    for n in fingers:
     p,q,s=local[n].decompose();fixed[n]=fixed[parents[n]]@Matrix.LocRotScale(p,q.slerp(finger_rot[n],weight),s)
   for n,track in tracks.items():
    loc=fixed[parents[n]].inverted()@fixed[n] if parents[n] else fixed[n];p,q,sc=(K@loc@K).decompose();v=raw(data,time,n)
    dq=q@Quaternion((v[6],*v[3:6])).inverted()
    if n in last and dq.dot(last[n])<0:dq=-dq
    last[n]=dq.copy();track['values'].extend([*(p-Vector(v[:3])),dq.x,dq.y,dq.z,dq.w,*(sc-Vector(v[7:10]))])
  entry['tracks']=[t for t in entry['tracks'] if t['bone'] not in owned]+list(tracks.values())
  report['profiles'][family+'/'+role]={'duration':duration,'sample_rate':rate,'contact_source': 'existing bolt windows' if entry['base'] in contact_masks[family] else 'pistol grip with melee release'}
  print('GRASP_AUTHORED',family,role,flush=True)
with gzip.open(O/'grip_profiles.json.gz','wt') as f:json.dump(result,f)
(O/'grasp_authoring.json').write_text(json.dumps(report,indent=2))
print('M24_PISTOL_GRASP_AUTHORED',flush=True)
