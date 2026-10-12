import json,math
from pathlib import Path
import numpy as np
from scipy.spatial.transform import Rotation as R,Slerp
O=Path(__file__).parent;S=O.parent
D=json.loads((O/'inputs.json').read_text())
NAMES,PARENTS=D['names'],D['parents'];I=np.eye(4)
def matrix(v):
 m=I.copy();m[:3,:3]=R.from_quat(v[3:7]).as_matrix()*v[7:];m[:3,3]=v[:3];return m
def pack(m):
 s=np.linalg.norm(m[:3,:3],axis=0);return np.r_[m[:3,3],R.from_matrix(m[:3,:3]/s).as_quat(),s]
def world(row):
 w={}
 for n in NAMES:w[n]=w.get(PARENTS[n],I)@matrix(row[n])
 return w
def posed(role,family='base'):
 clip=D['clips'][role];rows=[{n:np.array(v) for n,v in row.items()} for row in clip['rows']]
 if family!='base':
  layer=D['profiles'][family]['clips'][clip['path']]
  for track in layer['tracks']:
   n=track['bone'];ts=np.array(track['times']);v=np.array(track['values']).reshape(-1,10);times=np.clip(clip['times'],ts[0],ts[-1])
   if len(ts)==1:delta=np.repeat(v,len(rows),axis=0)
   else:
    delta=np.array([np.interp(times,ts,v[:,i]) for i in range(10)]).T
    delta[:,3:7]=Slerp(ts,R.from_quat(v[:,3:7]))(times).as_quat()
   for row,d in zip(rows,delta):
    row[n][:3]+=d[:3];row[n][3:7]=(R.from_quat(d[3:7])*R.from_quat(row[n][3:7])).as_quat();row[n][7:]+=d[7:]
 return [world(row) for row in rows]
def axes(d,up):
 r=matrix(d['WPN_root']);x=np.array(d['WPN_FrontSight'][:3])-d['WPN_RearSight'][:3];x/=np.linalg.norm(x)
 z=r[:3,:3]@up;y=np.cross(z,x);y/=np.linalg.norm(y);z=np.cross(x,y)
 return np.column_stack([x,y,z])
def camera():
 f=json.loads((O/'framing.json').read_text());base=R.from_euler('z',90,degrees=True).as_matrix()
 m=I.copy();m[:3,:3]=base@axes(f['M4'],[0,0,1])@axes(f['Super90'],[0,-1,0]).T
 m[:3,3]=np.array([6,7,-7])+base@f['M4']['hand_r'][:3]-m[:3,:3]@f['Super90']['hand_r'][:3]
 return m
native=json.loads((S/'Super90Foregrips20261007/native.json').read_text())
rest={n:matrix(v) for n,v in native['rest'].items()};ri={n:np.linalg.inv(v) for n,v in rest.items()}
geo=json.loads((O/'geometry.json').read_text());verts=geo['vertices']
points=np.array([v['position'] for v in verts]);points=np.c_[points,np.ones(len(points))]
cap=np.array([i for i,v in enumerate(verts) if v['boundary'] and v['weights'].get('upperarm_l',0)>.9])
upper=np.array([i for i,v in enumerate(verts) if v['weights'].get('upperarm_l',0)>.5])
groups={}
for n in NAMES:
 ids=np.array([i for i,v in enumerate(verts) if v['weights'].get(n,0)>.00001],dtype=int)
 if len(ids):groups[n]=(ids,np.array([verts[i]['weights'][n] for i in ids]),(ri[n]@points[ids].T).T)
def skin(w,cm):
 out=np.zeros((len(points),3))
 for n,(ids,weights,local) in groups.items():out[ids]+=((cm@w[n])@local.T).T[:,:3]*weights[:,None]
 return out
# Use the existing widest authored first-person frame, plus portrait-like play aspect.
TH=math.tan(math.radians(56));TV=TH/(1276/837)
def measure(w,cm):
 pts=skin(w,cm);p=pts[cap];x,y,z=p.T
 edge=np.minimum.reduce((z+TV*x,y+TH*x,-y+TH*x,-z+TV*x));mask=(x>0)&(edge>0)
 v=pts[upper];x,y,z=v.T;seen=(x>0)&(abs(y)<TH*x)&(abs(z)<TV*x)
 return dict(cap_visible=int(mask.sum()),cap_penetration_cm=float(np.max(np.where(p[:,0]>0,edge,-100))),
  nearest_upper_cm=float(np.linalg.norm(v[seen],axis=1).min()) if seen.any() else None,
  shoulder=(cm@w['upperarm_l'])[:3,3].round(3).tolist(),elbow=(cm@w['lowerarm_l'])[:3,3].round(3).tolist())

CHANGED=['clavicle_l','upperarm_l','lowerarm_l','lowerarm_aux_l','lowerarm_twist_02_l','lowerarm_twist_01_l','hand_l']
fore=rest['hand_l'][:3,3]-rest['lowerarm_l'][:3,3]
stations={n:float(np.clip(np.dot(rest[n][:3,3]-rest['lowerarm_l'][:3,3],fore)/np.dot(fore,fore),0,1)) for n in CHANGED if n.startswith('lowerarm_')}
def smooth(x):
 x=float(np.clip(x,0,1));return x*x*x*(x*(x*6-15)+10)
def envelope(frame):
 return smooth((frame-125)/12)*(1-smooth((frame-145)/15))
def norm(v):return v/max(np.linalg.norm(v),1e-12)
def basis(axis,normal):
 x=norm(axis);z=norm(normal);y=norm(np.cross(z,x));return np.column_stack([x,y,np.cross(x,y)])
def between(a,b):
 a,b=norm(a),norm(b);axis=np.cross(a,b);length=np.linalg.norm(axis)
 return np.eye(3) if length<1e-10 else R.from_rotvec(axis/length*math.atan2(length,np.dot(a,b))).as_matrix()
def support_pose(w,offset,angle,weight,cm):
 if weight<=0:return w
 a0,e0,t=[w[n][:3,3] for n in ('upperarm_l','lowerarm_l','hand_l')]
 a=a0+cm[:3,:3].T@(np.asarray(offset)*weight)
 l1,l2=np.linalg.norm(e0-a0),np.linalg.norm(t-e0);axis0=norm(t-a0);axis=norm(t-a);d=np.linalg.norm(t-a)
 limit=max(.965,np.linalg.norm(t-a0)/(l1+l2)+.00001)
 if d>limit*(l1+l2) or d<abs(l1-l2)+.001:raise ValueError('Unreachable shoulder candidate')
 pole0=e0-a0-axis0*np.dot(e0-a0,axis0)
 pole=norm(R.from_rotvec(axis*math.radians(angle)*weight).apply(between(axis0,axis)@pole0))
 s=(l1*l1-l2*l2+d*d)/(2*d);e=a+axis*s+pole*math.sqrt(max(0,l1*l1-s*s))
 normal0=np.cross(e0-a0,t-e0);normal=np.cross(e-a,t-e)
 qu=basis(e-a,normal)@basis(e0-a0,normal0).T;qf=basis(t-e,normal)@basis(t-e0,normal0).T
 mu=I.copy();mu[:3,:3]=qu;mu[:3,3]=a-qu@a0
 mf=I.copy();mf[:3,:3]=qf;mf[:3,3]=e-qf@e0
 out=dict(w);out['clavicle_l']=w['clavicle_l'].copy();out['clavicle_l'][:3,3]+=a-a0
 out['upperarm_l']=mu@w['upperarm_l'];out['lowerarm_l']=mf@w['lowerarm_l']
 fa=norm(t-e);dq=R.from_matrix(w['hand_l'][:3,:3])*(R.from_matrix(qf)*R.from_matrix(w['hand_l'][:3,:3])).inv()
 q=dq.as_quat();twist=2*math.atan2(np.dot(q[:3],fa),q[3]);twist=(twist+math.pi)%(2*math.pi)-math.pi
 for n,station in stations.items():
  m=mf@w[n];centre=e+(t-e)*station;turn=R.from_rotvec(fa*twist*station).as_matrix()
  m[:3,3]=centre+turn@(m[:3,3]-centre);m[:3,:3]=turn@m[:3,:3];out[n]=m
 return out

def shoulder_under_frame(w,frame,clearance,cm):
 weight=envelope(frame)
 if weight<=0:return w
 a=(cm@w['upperarm_l'])[:3,3];t=(cm@w['hand_l'])[:3,3]
 normal=norm(np.array([TV,0.,1.]));radius=np.linalg.norm(a-t)
 # Slide the shoulder around the fixed wrist on a sphere of its original
 # shoulder/wrist distance: both segment lengths and elbow bend stay unchanged.
 boundary=-clearance/np.linalg.norm([TV,0.,1.]);depth=float(np.dot(normal,a))
 gap=depth-boundary
 if gap<=-.5:return w
 correction=gap if gap>=.5 else (gap+.5)**2/2.
 target_depth=depth-correction*weight
 plane_t=float(np.dot(normal,t));distance=plane_t-target_depth
 if abs(distance)>=radius:raise ValueError('No shoulder position below frame at original reach')
 centre=t-normal*distance
 tangent=a-t-normal*np.dot(normal,a-t);tangent=norm(tangent)
 target=centre+tangent*math.sqrt(max(0.,radius*radius-distance*distance))
 offset=target-a
 return support_pose(w,offset,0.,1.,cm)
