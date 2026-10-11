"""Preserve the R19 hand and mechanically timed tracks; move only its arm support."""
from pathlib import Path
O=Path(__file__).parent
exec(compile((O/'r20_core.py').read_text(encoding='utf-8'),str(O/'r20_core.py'),'exec'))
source_rows={b:[{n:Matrix(m) for n,m in p.items()} for p in ps] for b,ps in json.loads((O/'source_poses.json').read_text(encoding='utf-8')).items()}
changed=['clavicle_l',*changed]
cloth=json.loads((S/'BenelliM4Super9020261006/EquipmentAuthored/Super90_ue_chainmail_shirt.json').read_text(encoding='utf-8'))
positions=np.asarray(cloth['positions']);weights=cloth['weights']
left=np.asarray([i for i,w in enumerate(weights) if sum(v for n,v in w.items() if n.endswith('_l'))>.9])
native_rest={n:mat(native['rest'][n]) for n in names}
native_inv={n:m.inverted() for n,m in native_rest.items()}
na=np.asarray(native_rest['upperarm_l'].translation);ne=np.asarray(native_rest['lowerarm_l'].translation)
station=(positions-na)@(ne-na)/np.dot(ne-na,ne-na)
upper=np.asarray([i for i in left if weights[i].get('upperarm_l',0)>.5])
proximal=np.asarray([i for i in upper if station[i]<.38])
support_surface=np.asarray([i for i in upper if station[i]<.85])
# Use all real vertices for the final report; fitting can reuse the same small
# shoulder subset and a uniform surface sample, never a pivot-only proxy.
groups={}
for n in names:
    ids=np.asarray([int(i) for i in left if weights[i].get(n,0)>.00001])
    if len(ids):groups[n]=(ids,np.asarray([weights[i][n] for i in ids]),np.asarray(native_inv[n])@np.column_stack((positions[ids],np.ones(len(ids)))).T)

def cloth_points(p):
    out=np.zeros((len(positions),3))
    for n,(ids,w,local) in groups.items():out[ids]+=(cam_matrix@np.asarray(p[n]@K[n])@local).T[:,:3]*w[:,None]
    return out

TH=math.tan(math.radians(56));TV=TH/(1276/837)
cam_inv=cm.to_3x3().inverted()

def envelope(f,end):
    # Smoothly make room before release; the source hand still pushes with the
    # exact same motion. Restore the existing grip at the authored end frame.
    return smooth((f-88)/24)*smooth((end-f)/22)

def frame_basis(axis,normal):
    x=axis.normalized();z=normal.normalized();y=z.cross(x).normalized();z=x.cross(y).normalized()
    return Matrix((x,y,z)).transposed().to_quaternion()

def support_pose(p,offset,angle,w):
    if w<=0:return p
    a0,e0,t=[p[n].translation for n in ('upperarm_l','lowerarm_l','hand_l')]
    a=a0+cam_inv@(Vector(offset)*w);l1=(e0-a0).length;l2=(t-e0).length
    axis0=(t-a0).normalized();axis=(t-a).normalized();d=(t-a).length
    if d>min(.965*(l1+l2),l1+l2-1e-5) or d<abs(l1-l2)+1e-5:raise ValueError('Arm reach')
    pole0=(e0-a0)-axis0*(e0-a0).dot(axis0)
    pole=(Quaternion(axis,math.radians(angle)*w)@(axis0.rotation_difference(axis)@pole0)).normalized()
    s=(l1*l1-l2*l2+d*d)/(2*d);r=math.sqrt(max(0,l1*l1-s*s));e=a+axis*s+pole*r
    oldnormal=(e0-a0).cross(t-e0).normalized();normal=(e-a).cross(t-e).normalized()
    qu=frame_basis(e-a,normal)@frame_basis(e0-a0,oldnormal).inverted()
    qf=frame_basis(t-e,normal)@frame_basis(t-e0,oldnormal).inverted()
    upper_move=Matrix.Translation(a)@qu.to_matrix().to_4x4()@Matrix.Translation(-a0)
    fore_move=Matrix.Translation(e)@qf.to_matrix().to_4x4()@Matrix.Translation(-e0)
    out=dict(p);out['clavicle_l']=p['clavicle_l'].copy();out['clavicle_l'].translation+=a-a0
    out['upperarm_l']=upper_move@p['upperarm_l']
    out['lowerarm_l']=fore_move@p['lowerarm_l']
    fa=(t-e).normalized();carried=qf@p['hand_l'].to_quaternion()
    dq=p['hand_l'].to_quaternion()@carried.inverted()
    twist=2*math.atan2(Vector((dq.x,dq.y,dq.z)).dot(fa),dq.w);twist=(twist+math.pi)%(2*math.pi)-math.pi
    for n,station in stations.items():
        m=fore_move@p[n];centre=e.lerp(t,station);turn=Quaternion(fa,twist*station)
        pos,q,scale=m.decompose();out[n]=Matrix.LocRotScale(centre+turn@(pos-centre),turn@q,scale)
    # Preserve hands and every finger in component space, including the R17 hook.
    return out

def coverage(pts,ids):
    v=pts[ids];x,y,z=v.T;mask=(x>1)&(abs(y)<x*TH)&(abs(z)<x*TV)
    return dict(visible=int(mask.sum()),nearest_cm=float(np.linalg.norm(v[mask],axis=1).min()) if mask.any() else None,
                forward_cm=float(x[mask].min()) if mask.any() else None)

def clearance_cost(p):
    pts=cloth_points(p);v=pts[support_surface];x,y,z=v.T
    inside=np.minimum.reduce((z+TV*x,y+TH*x,-y+TH*x,-z+TV*x))
    edge=np.where(x>0,np.maximum(0,inside+2),0)
    v=pts[left[::4]];x,y,z=v.T;visible=(x>0)&(abs(y)<x*TH)&(abs(z)<x*TV)
    close=np.where(visible,np.maximum(0,17-np.linalg.norm(v,axis=1)),0)
    return float(np.max(edge)**2+np.mean(edge**2)+2*np.max(close)**2)
