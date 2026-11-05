"""Evaluate the actual open shoulder rim and the M24 presentation cameras."""
from pathlib import Path
from collections import Counter
import numpy as np
exec(compile((Path(__file__).resolve().parent.parent/'M24QuickMeleeRightHandR3_20261104/common.py').read_text(),'current profile FK','exec'))
_sample_between=sampled
def sampled(values,times,t):
    if t<=times[0]:return _sample_between(values[:10],[times[0]],t)
    if t>=times[-1]:return _sample_between(values[-10:],[times[-1]],t)
    return _sample_between(values,times,t)

def basis(x,z):
    x=x.normalized();z=(z-x*z.dot(x)).normalized()
    return Matrix((x,z.cross(x),z)).transposed()

def get_cameras(family):
    reference=json.loads((O/'camera_source.json').read_text())
    hierarchy=reference['m4_bones'];index={v['index']:n for n,v in hierarchy.items()}
    ref={}
    for n,v in sorted(hierarchy.items(),key=lambda item:item[1]['index']):
        parent=index.get(v['parent']);m=transform(reference['m4_local'][n])
        ref[n]=ref[parent]@m if parent else m
    ruler=basis(ref['WPN_FrontSight'].translation-ref['WPN_RearSight'].translation,ref['WPN_root'].to_quaternion()@Vector((0,0,1)))
    rz=Matrix.Rotation(math.pi/2,3,'Z'); cm=Matrix.Diagonal((100,-100,100))
    target=Vector((0,7,-7))+rz@ref['hand_r'].translation+Vector((23.219236,1.379742,1.296371))
    row=compose(entry(family,'idle'),0)[0]
    axis=basis(cm@(row['WPN_FrontSight'].translation-row['WPN_RearSight'].translation),K.to_3x3()@row['WPN_root'].to_quaternion().to_matrix()@Vector((0,1,0)))
    rotation=rz@ruler@axis.inverted();hip=(rotation@cm).to_4x4()
    anchor=Vector((.037195854,.080805898,.026502814)) if family.startswith('skeleton_') else cm@row['hand_r'].translation
    hip.translation=target-rotation@anchor
    # Factory scope sockets are authored in gun assembly coordinates. Register
    # the sight/magazine triad exactly as M24Attachments::Mount does.
    ref_rear,ref_front,ref_mag=[cm@rest[n].translation for n in ('WPN_RearSight','WPN_FrontSight','WPN_SOCKET_Magazine')]
    rear,front,mag=[Vector(v) for v in ((-.0254083425,.1819224795,17.7973091602),(-.0254083425,-41.1078542471,17.7973091602),(.0000016143,-18.4658959508,5.5959127843))]
    alignment=basis(ref_front-ref_rear,ref_rear-ref_mag)@basis(front-rear,rear-mag).inverted()
    scale=(ref_front-ref_rear).length/(front-rear).length
    aim=compose({'base':entry(family,'aim')['base'],'tracks':[]},0.)[0];gun=aim['WPN_root']@rest['WPN_root'].inverted()
    scope=[cm@(gun@(cm.inverted()@(ref_rear+alignment@(Vector(reference['scope'][n])-rear)*scale))) for n in ('SightRear','SightFront','SightUp')]
    rotation=basis(scope[1]-scope[0],scope[2]-scope[0]).inverted()
    ads=(rotation@cm).to_4x4();ads.translation=Vector((42.,0,0))-rotation@scope[0]
    return {'hip':hip,'scope':ads}

# An open edge in the welded skin identifies the cut end of the real arm.
# A normal, visible part of the biceps is not an exposed shoulder opening.
V=np.asarray(G['positions'])*[.01,-.01,.01]
F=np.asarray([f['vertices'] for f in G['faces']])
_,weld=np.unique(np.round(V,6),axis=0,return_inverse=True)
edges=Counter(tuple(sorted((int(a),int(b)))) for f in weld[F] for a,b in zip(f,np.roll(f,-1)))
boundary={v for edge,count in edges.items() if count==1 for v in edge}
rim=np.array([i for i,p in enumerate(V) if weld[i] in boundary and np.linalg.norm(p-np.asarray(native['upperarm_l'].translation))<.13 and sum(w for n,w in G['weights'].get(str(i),{}).items() if n.endswith('_l'))>.5])
if not len(rim):raise ValueError('No welded left shoulder rim')
W=np.array([[G['weights'].get(str(i),{}).get(n,0.) for n in names] for i in rim])
used=[n for j,n in enumerate(names) if np.any(W[:,j]>0)]
weights=W[:,[indices[n] for n in used]]
inverses=np.array([np.asarray(native[n].inverted()) for n in used])
morph=np.load(S/'M24ThumbRootRoute20261102/native_correctives.npz')
deltas={n:morph[n][rim] for n in morph.files if np.any(morph[n][rim])}
exec(compile((S/'M24ThumbRootRoute20261102/corrective_weights.py').read_text(),'JC skin','exec'))
def skin_rim(row):
    X=V[rim].copy()
    if deltas:
        values,_=corrective_weights(row,deltas.keys())
        for n,w in values.items():X+=deltas[n]*w
    mats=np.asarray([np.asarray(row[n]) for n in used])@inverses
    blend=np.einsum('vk,kij->vij',weights,mats)
    return np.einsum('vij,vj->vi',blend,np.c_[X,np.ones(len(X))])[:,:3]

tan_v=math.tan(math.radians(37.5))
def clearance(X,camera,fov=75.):
    P=(np.c_[X,np.ones(len(X))]@np.asarray(camera).T)[:,:3]
    x,y,z=P.T
    tan_v=math.tan(math.radians(fov*.5))
    # Signed clearance from the view pyramid, including the near plane.
    outside=np.maximum.reduce([1.-x,abs(y)-x*tan_v*16/9,abs(z)-x*tan_v])
    return float(np.min(outside)),int(np.sum(outside<0))

roles=('fire','cycle','equip','reload_empty')
def window(role,clip):
    # The magazine-contact edit ends at frame 46. Lead into the bolt with
    # the proximal correction before the first frame of the charging segment.
    if role=='reload_empty': return (49/30.,clip['duration'])
    return (0.,clip['duration'])

def blend_camera(hip,ads,alpha):
    units=Matrix.Diagonal((100,-100,100))
    h=(hip.to_3x3()@units.inverted()).to_quaternion()
    a=(ads.to_3x3()@units.inverted()).to_quaternion()
    out=(h.slerp(a,alpha).to_matrix()@units).to_4x4()
    out.translation=hip.translation.lerp(ads.translation,alpha)
    return out

def summarize():
    data={}
    for family in D['profiles']:
        cams=get_cameras(family);record={}
        for role in ('idle','aim',*roles):
            clip=entry(family,role);start,end=window(role,clip)
            ts=[0.] if role=='idle' else np.linspace(start,end,round((end-start)*30)+1)
            readings=[]
            for t in ts:
                row,_=compose(clip,float(t));X=skin_rim(row)
                readings.append({'t':float(t),**{k:clearance(X,m,55. if k=='scope' else 75.) for k,m in cams.items() if k=='hip' or role in ('fire','aim')}})
            record[role]={k:min(readings,key=lambda r:r[k][0]) for k in readings[0] if k!='t'}
        data[family]=record
        print('RIM',family,[(role,[(k,tuple(round(a,2) for a in (r['t'],r[k][0],r[k][1]))) for k,r in v.items()]) for role,v in record.items()],flush=True)
    (O/'diagnosis.json').write_text(json.dumps(data,indent=2))
if __name__=='__main__':summarize()
