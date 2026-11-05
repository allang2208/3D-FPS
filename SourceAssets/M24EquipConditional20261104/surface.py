"""Construct the ready pose and fit the two open upper-arm ends in the hip camera."""
from pathlib import Path
import numpy as np, json,gzip,copy,math,struct,bisect
from collections import Counter
from mathutils import Matrix,Vector,Quaternion
O=Path(__file__).resolve().parent;S=O.parent
source=(S/'M24BoltShoulder20261104/shoulder.py').read_text()
pre=source.split('# An open edge')[0].split('    # Factory scope sockets')[0]
pre=pre.replace("(O/'camera_source.json')","(S/'M24BoltShoulder20261104/camera_source.json')")
exec(compile(pre+'    return hip\n','M24 hip frame','exec'))
READY='/Game/Weapons/M24/EquipConditional20261104/A_M24_equip_ready.A_M24_equip_ready'
idlepath=entry('base','idle')['base'];boltpath=entry('base','equip')['base']
duration=18/30
src_idle=D['clips'][idlepath];src_equip=D['clips'][boltpath];vm=indices['VM_Root']
regular={'path':READY,'fps':30,'keys':19,'poses':{}}
for k in range(19):
    row=src_idle['poses']['0'].copy();row[vm]=src_equip['poses'][str(k)][vm];regular['poses'][str(k)]=row
D['clips'][READY]=regular
for family,p in D['profiles'].items():
    idle=entry(family,'idle')
    tracks=[{'bone':tr['bone'],'times':[0.],'values':tr['values'][:10]} for tr in idle['tracks']]
    p['clips'].append({'base':READY,'duration':duration,'tracks':tracks})
# The real skin is sampled on the open edges at each shoulder, including any
# contributor from the opposite side or the trunk at those vertices.
V=np.array(G['positions'])*[.01,-.01,.01];F=np.array([f['vertices'] for f in G['faces']])
_,weld=np.unique(np.round(V,6),axis=0,return_inverse=True)
edges=Counter(tuple(sorted((int(a),int(b)))) for f in weld[F] for a,b in zip(f,np.roll(f,-1)))
boundary={vertex for edge,count in edges.items() if count==1 for vertex in edge}
morph=np.load(S/'M24ThumbRootRoute20261102/native_correctives.npz')
exec(compile((S/'M24ThumbRootRoute20261102/corrective_weights.py').read_text(),'JC correctives','exec'))
rims={}
for side in ('l','r'):
    joint='upperarm_'+side
    verts=np.array([i for i,p in enumerate(V) if weld[i] in boundary and np.linalg.norm(p-np.array(native[joint].translation))<.13
        and sum(w for n,w in G['weights'].get(str(i),{}).items() if n.endswith('_'+side))>.5])
    if not len(verts):raise RuntimeError('No open shoulder edge '+side)
    weights=np.array([[G['weights'][str(i)].get(n,0.) for n in names] for i in verts]);cols=np.flatnonzero(np.any(weights>0,axis=0));used=[names[i] for i in cols]
    delta={n:morph[n][verts] for n in morph.files if np.any(morph[n][verts])}
    rims[side]=(verts,weights[:,cols],used,np.asarray([np.asarray(native[n].inverted()) for n in used]),delta)
def skin(row,side):
    ids,W,used,invs,delta=rims[side];X=V[ids].copy()
    if delta:
        w,_=corrective_weights(row,delta.keys())
        for n,weight in w.items():X+=delta[n]*weight
    blend=np.einsum('ij,jkl->ikl',W,np.asarray([np.asarray(row[n]) for n in used])@invs)
    return np.einsum('ijk,ik->ij',blend,np.c_[X,np.ones(len(X))])[:,:3]
def clearance(X,C):
    P=X@C[:3,:3].T+C[:3,3];x,y,z=P.T
    tv=math.tan(math.radians(37.5))
    return float(np.maximum.reduce([1.-x,abs(y)-x*tv*16/9,abs(z)-x*tv]).min())
def stamp(x):return struct.unpack('f',struct.pack('f',x))[0]
def existing_delta(tr,t):
    if not tr:return [0.,0.,0.,0.,0.,0.,1.,0.,0.,0.]
    p,q,s=sampled(tr['values'],tr['times'],t)
    return [*p,q.x,q.y,q.z,q.w,*s]
def capture():
    reports={}
    for family in D['profiles']:
        camera=np.array(get_cameras(family));reports[family]={}
        for role in ('equip_ready','equip'):
            clip=entry(family,role);period=clip['duration']
            data={side:[] for side in rims}
            for k in range(round(period*30)+1):
                row,_=compose(clip,k/30.)
                for side in rims:data[side].append(round(clearance(skin(row,side),camera),3))
            reports[family][role]=data
        print('OPEN_RIM',family,[(r,[(s,min(v),[i for i,x in enumerate(v) if x<0]) for s,v in w.items()]) for r,w in reports[family].items()],flush=True)
    (O/'rim_source.json').write_text(json.dumps(reports,indent=2))
if __name__=='__main__':capture()
