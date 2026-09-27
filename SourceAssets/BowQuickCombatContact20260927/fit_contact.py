"""Fit upper-riser contact on real body geometry; retain native bone lengths."""
import bpy,json,math,sys
import numpy as np
from pathlib import Path
from mathutils import Matrix,Vector
from mathutils.bvhtree import BVHTree
P=Path(__file__).parent;ROOT=P.parents[1]
case=P.parent/'BowQuickCombatPush20260927';script=case/'generated_push_v3.py'
ns={'__file__':str(script)}
exec(compile(script.read_text().split('bpy.ops.wm.open_mainfile')[0],str(script),'exec'),ns)
data=ns['ns']['data'];R=ns['R'];rest=ns['rest'];w=ns['pose'](.32)
with bpy.data.libraries.load(str(P.parent/'BowModular20260926/Bow_ModularParts.blend'),link=False) as (a,b):b.objects=['SM_Bow_BodyModular']
body=b.objects[0];verts=[Vector((v.x,-v.y,v.z)) for v in [body.matrix_world@v.co for v in body.data.vertices]]
bvh=BVHTree.FromPolygons(verts,[tuple(reversed(p.vertices)) for p in body.data.polygons])
# The asset contains nested wood/binding shells with mixed winding. Build an
# outer radial envelope from ray intersections, rather than treating inward
# normals on a decorative shell as solid-volume containment.
ev=[];N=96;zs=np.arange(15.,43.001,.25)
for z in zs:
    section=[p for p in verts if abs(p.z-z)<.6]
    cx=(min(p.x for p in section)+max(p.x for p in section))*.5
    cy=(min(p.y for p in section)+max(p.y for p in section))*.5
    center=Vector((cx,cy,z))
    for j in range(N):
        ray=Vector((math.cos(j*2*math.pi/N),math.sin(j*2*math.pi/N),0))
        co,no,idx,dist=bvh.ray_cast(center+ray*15,-ray,15)
        if co is None:raise RuntimeError('Missing section '+str((z,j)))
        ev.append(co)
faces=[]
for k in range(len(zs)-1):
    for j in range(N):faces.append((k*N+j,k*N+(j+1)%N,(k+1)*N+(j+1)%N,(k+1)*N+j))
envelope=BVHTree.FromPolygons(ev,faces)
hand_ids=[i for i,weights in enumerate(data['weights']) if sum(v for n,v in weights.items() if n=='hand_r' or (n.endswith('_r') and n.split('_')[0] in ('index','middle','ring','pinky','thumb')))>0.8]
names=[n for n in ns['order'] if n=='hand_r' or n in ns['right_closed_local']]
bind_inv={n:rest[n].inverted() for n in names}
base={n:w['bow_grip'].inverted()@w[n] for n in names}
closed={n:base[ns['parent'][n]].inverted()@base[n] for n in names if n!='hand_r'}
raw=np.array([list(R@Vector(data['positions'][i]))+[1] for i in hand_ids])
weights={n:np.array([data['weights'][i].get(n,0) for i in hand_ids]) for n in names}
influence={n:np.where(v>.0001)[0] for n,v in weights.items()}
weighted={n:(raw[idx]@np.array(bind_inv[n]).T)*weights[n][idx,None] for n,idx in influence.items()}
groups={d:np.array([j for j,i in enumerate(hand_ids) if max(data['weights'][i],key=data['weights'][i].get).split('_')[0]==d]) for d in ('hand','thumb','index','middle','ring','pinky')}
digit_names=[d+'_'+f'{s:02d}'+'_r' for d in ('thumb','index','middle','ring','pinky') for s in (1,2,3)]
axis={n:rest[ns['parent'][n]].to_3x3().inverted()@(R@Vector(next(d['across'] for d in ns['anatomy']['r']['digits'] if d['bone']==n))) for n in digit_names}
center=Vector((-3.734,.025,30.8))
def frames(x):
    turn=Matrix.Rotation(math.radians(x[2]),4,'Y')
    correction=Matrix.Translation((x[0],x[1],0))@Matrix.Translation(center)@turn@Matrix.Translation(-center)
    f={'hand_r':correction@base['hand_r']}
    for n in names[1:]:
        local=closed[n].copy()
        if n in digit_names:
            local=ns['mat'](local.translation,Matrix.Rotation(math.radians(x[3+digit_names.index(n)]),3,axis[n])@local.to_3x3())
        f[n]=f[ns['parent'][n]]@local
    return f
def skin(f):
    pts=np.zeros((len(hand_ids),3))
    for n,idx in influence.items():pts[idx]+=(weighted[n]@np.array(f[n]).T)[:,:3]
    return pts
def distances(pts):
    ds=[]
    for p in pts:
        co,no,idx,dist=envelope.find_nearest(Vector(p))
        ds.append(dist if (Vector(p)-co).dot(no)>=0 else -dist)
    return np.array(ds)
def report(x):
    ds=distances(skin(frames(x)))
    return {d:{'min_cm':float(ds[ids].min()),'p05_cm':float(np.quantile(ds[ids],.05)),'penetration_vertices':int(sum(ds[ids]<-.05))} for d,ids in groups.items()}
print('BEFORE',report(np.zeros(18)),flush=True)
np.savez(P/'contact-envelope.npz',vertices=np.array(ev),faces=np.array(faces))

# Bounded coordinate descent preserves the original grasp and optimizes the
# full weighted surface, with every phalange remaining its native length.
def loss(x):
    ds=distances(skin(frames(x)))
    collision=np.square(np.minimum(ds-.08,0))
    value=500*collision.mean()+180*collision.max()
    for d,idx in groups.items():
        value+=.12*max(0,np.quantile(ds[idx],.025)-.22)**2
    value+=.003*(x[0]**2+x[1]**2)+.000015*(x[2]+14)**2
    value+=.000008*sum(x[3:]**2)
    return value
x=np.zeros(18);x[2]=-14
if '--refine' in sys.argv:
    previous=json.loads((P/'contact-fit.json').read_text())
    x=np.array(previous['correction_translation_cm']+[previous['upper_limb_pitch_degrees']]+[previous['finger_delta_degrees'][n] for n in digit_names])
lo=np.array([-3,-2,-25]+[-42]*15);hi=np.array([3,3.4,0]+[32]*3+[20]*12)
best=loss(x)
for step in ((1.,.5,.25,.125) if '--refine' in sys.argv else (4.,2.,1.,.5)):
    for iteration in range(7):
        improved=False
        for i in range(len(x)):
            stride=step*(.08 if i<2 else 1.)
            candidates=[]
            for sign in (-1,1):
                trial=x.copy();trial[i]=np.clip(x[i]+sign*stride,lo[i],hi[i]);candidates.append((loss(trial),trial))
            val,trial=min(candidates,key=lambda p:p[0])
            if val<best-1e-8:x=trial;best=val;improved=True
        print('FIT',step,iteration,best,x.tolist(),flush=True)
        if not improved:break
print('AFTER',report(x),flush=True)
result={'correction_translation_cm':x[:2].tolist(),'upper_limb_pitch_degrees':float(x[2]),'rotation_pivot_cm':list(center),
    'finger_delta_degrees':dict(zip(digit_names,x[3:].tolist())),'before':report(np.zeros(18)),'after':report(x),
    'right_contact':list(map(list,frames(x)['hand_r'])),'right_closed_local':{n:list(map(list,frames(x)[ns['parent'][n]].inverted()@m)) for n,m in frames(x).items() if n!='hand_r'}}
(P/'contact-fit.json').write_text(json.dumps(result,indent=2))
