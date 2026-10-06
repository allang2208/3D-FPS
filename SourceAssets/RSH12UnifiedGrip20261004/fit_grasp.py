"""Author a common RSH grasp with anatomical hinges and both visible hand skins.

The native 715 metacarpals and every bone length remain unchanged. Each finger
joint has one flexion degree of freedom, derived from its posed bend plane;
there are no independent Euler or axial-twist variables.
"""
import os
os.environ['OPENBLAS_NUM_THREADS']='1'
os.environ['OMP_NUM_THREADS']='1'
import json
from pathlib import Path
import numpy as np
from scipy.spatial.transform import Rotation as R
from scipy.spatial import cKDTree
from scipy.interpolate import RegularGridInterpolator
from scipy.optimize import least_squares

O=Path(__file__).parent
OLD=O.parent/'RSH12InspectGrip20261004'
STEEL=O.parent/'MetalGauntlet20260927/SteelGauntletV1/Authored/DW715.json'
steel=json.loads(STEEL.read_text())
sd=np.load(OLD/'full_sdf.npz')
axes=[sd[k] for k in ('x','y','z')]
lo=np.array([a[0] for a in axes]);hi=np.array([a[-1] for a in axes])
field=RegularGridInterpolator(axes,sd['field'],bounds_error=False,fill_value=None)
def distance(points):
    q=np.clip(points,lo,hi)
    return (field(q)+np.linalg.norm(points-q,axis=1))*1000
def bone_matrix(b):
    m=np.eye(4);m[:3,:3]=np.array(b['axes']).T;m[:3,3]=b['position'];return m

class Grasp:
    def __init__(self,side):
        self.side=side
        d=np.load(OLD/f'input_single_{side}_idle.npz')
        self.names=list(d['names']);self.parents=d['parents']
        self.base=d['world'].astype(float);self.local=d['local'].astype(float)
        self.hand=self.names.index('hand_'+side)
        self.chain=[i for i,n in enumerate(self.names) if n.endswith('_'+side) and n.startswith(('thumb','index','middle','ring','pinky'))]
        self.joints=[i for i in self.chain if 'metacarpal' not in self.names[i]]
        self.hinges=[]
        for i in self.joints:
            f=self.names[i].split('_')[0]
            ids=[self.names.index(f'{f}_{j:02}_{side}') for j in range(1,4)]
            a,b,c=self.base[ids,:3,3]
            axis=np.cross(b-a,c-b);axis/=np.linalg.norm(axis)
            axis=self.base[i,:3,:3].T@axis
            # The actual phalanx longitudinal axis is local X in this imported rig.
            # Project it out even at DIP, whose authored segment is mildly skewed.
            axis[0]=0;axis/=np.linalg.norm(axis);self.hinges.append(axis)
        self.hinges=np.array(self.hinges)
        labels=[max(w,key=w.get) if w else '' for w in steel['weights']]
        ids=[i for i,l in enumerate(labels) if l.endswith('_'+side) and l.startswith(('hand','thumb','index','middle','ring','pinky'))]
        sw=[steel['weights'][i] for i in ids]
        self.steel_ids=np.array(ids)
        used=sorted({n for w in sw for n in w})
        points=np.c_[np.array(steel['positions'])[ids],np.ones(len(ids))]
        reflect=np.diag([1.,-1.,1.,1.])
        bound=np.stack([points@(reflect@np.linalg.inv(bone_matrix(steel['bones'][n]))).T for n in used])
        weights=np.array([[w.get(n,0) for n in used] for w in sw]);weights/=weights.sum(axis=1)[:,None]
        self.skins=[dict(used=d['used'],weights=d['weights'],bound=d['bound'],labels=d['labels']),
                    dict(used=np.array([self.names.index(n) for n in used]),weights=weights,bound=bound,labels=np.array(labels)[ids])]
        self.reference=self.base.copy()
        self.inspect_local=np.load(OLD/f'input_single_{side}_inspect.npz')['local']

    def pose(self,x,inspect=False):
        p=self.reference.copy()
        p[self.hand,:3,3]+=x[:3]*.001
        p[self.hand,:3,:3]=self.reference[self.hand,:3,:3]@R.from_rotvec(np.radians(x[3:6])).as_matrix()
        rotations=R.from_rotvec(self.hinges*np.radians(x[6:])[:,None]).as_matrix()
        ji=0
        for i in self.chain:
            local=self.local[i].copy()
            if i in self.joints:
                # Inspection retains the native index's extension, with no fitting rotation.
                if inspect and self.names[i].startswith('index'):local=self.inspect_local[i].copy()
                else:local[:3,:3]=local[:3,:3]@rotations[ji]
                ji+=1
            elif inspect and self.names[i].startswith('index'):local=self.inspect_local[i].copy()
            p[i]=p[self.parents[i]]@local
        return p

    def points(self,p,skin,indices):
        s=self.skins[skin]
        return np.einsum('bij,bpj,pb->pi',p[s['used']],s['bound'][:,indices],s['weights'][indices],optimize=True)[:,:3]

    def write(self,x):
        p=self.pose(x)
        rotations={}
        for i in self.chain:
            lp=np.linalg.inv(p[self.parents[i]])@p[i]
            rotations[self.names[i]]=R.from_matrix(lp[:3,:3]).as_quat().tolist()
        result=dict(side=self.side,source='RSH12Speedloader20261003',parameters=x.tolist(),
                    hand_in_grip=p[self.hand].tolist(),local_grasp_rotations=rotations,
                    hinge_axes={self.names[i]:a.tolist() for i,a in zip(self.joints,self.hinges)},
                    source_inspect_index_preserved=True,metacarpal_orientation_preserved=True,
                    skins=['native V7','DW715 steel glove full mixed weights'])
        (O/f'grasp_{self.side}.json').write_text(json.dumps(result,indent=2))
        return p

def solve(g,right=None):
    # A maximum 22-degree anatomical flex correction keeps the donor grasp recognizable.
    limits=np.array([14,14,10,6,6,6]+[12 if g.names[i].startswith(('index','thumb')) else 22 for i in g.joints],float)
    initial=np.zeros(len(limits))
    sample=[np.arange(0,len(s['labels']),5 if k==0 else 15) for k,s in enumerate(g.skins)]
    contacts=[]
    for k,s in enumerate(g.skins):
        # Contact uses the flexible palm/underside, not the decorative dorsal plates.
        for f in ('hand','thumb','middle','ring','pinky'):
            ids=np.flatnonzero(np.char.startswith(s['labels'],f))
            if k==1:ids=ids[g.steel_ids[ids]<13044]
            if len(ids):contacts.append((k,f,ids[::3]))
    if right:
        right_g,right_p=right
        # Carry the support hand with the firing palm before its small independent fit.
        delta=right_p[right_g.hand]@np.linalg.inv(right_g.base[right_g.hand])
        g.reference=np.einsum('ij,bjk->bik',delta,g.base)
        positions=right_g.points(right_p,1,np.arange(len(right_g.steel_ids)))
        tris=np.array(steel['triangles'])
        remap={v:i for i,v in enumerate(right_g.steel_ids)}
        tris=np.array([[remap[v] for v in t] for t in tris if all(v in remap for v in t)])
        normals=np.zeros_like(positions)
        face=np.cross(positions[tris[:,1]]-positions[tris[:,0]],positions[tris[:,2]]-positions[tris[:,0]])
        for j in range(3):np.add.at(normals,tris[:,j],face)
        normals/=np.maximum(np.linalg.norm(normals,axis=1)[:,None],1e-12)
        tree=cKDTree(positions)
        def contact(q):
            dist,ids=tree.query(q)
            signed=np.einsum('ij,ij->i',q-positions[ids],normals[ids])*1000
            return dist*1000,signed
    def residual(x):
        p=g.pose(x)
        residuals=[x[:3]*.2,x[3:6]*.24,x[6:]*.14]
        for k,ids in enumerate(sample):
            pts=g.points(p,k,ids);d=distance(pts)
            residuals.append(np.minimum(d-.25,0)*.7)
            if right:
                near,signed=contact(pts)
                residuals.append(np.minimum(signed-.2,0)*(near<8)*.5)
        for k,f,ids in contacts:
            pts=g.points(p,k,ids)
            d=distance(pts) if not right else contact(pts)[0]
            # Multiple points on each pad participate; one accidental tip contact cannot win.
            closest=np.sort(d)[:min(16,len(d))]
            residuals.append(np.maximum(closest-1.2,0)*(.8 if f=='hand' else .35))
        if not right:
            pi=g.pose(x,True)
            for k,s in enumerate(g.skins):
                ids=np.flatnonzero(np.char.startswith(s['labels'],'index'))[::8]
                residuals.append(np.minimum(distance(g.points(pi,k,ids))-.2,0)*.9)
        return np.concatenate(residuals)
    fit=least_squares(residual,initial,bounds=(-limits,limits),diff_step=.002,max_nfev=90,ftol=2e-4,xtol=2e-4,gtol=1e-3)
    p=g.write(fit.x)
    print('GRASP_AUTHORED',g.side,'placement_mm',fit.x[:3].round(3).tolist(),
          'wrist_degrees',fit.x[3:6].round(2).tolist(),'hinges',fit.x[6:].round(2).tolist(),flush=True)
    return p

if __name__=='__main__':
    r=Grasp('r');rp=solve(r)
    l=Grasp('l');solve(l,(r,rp))
