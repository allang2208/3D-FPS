"""Author both TS01 skinned high boots directly on their equipped bind meshes."""
from pathlib import Path
import argparse
import json
import math
import numpy as np
from scipy.spatial import ConvexHull,cKDTree
from ridge_boots_author_last import dominant_parts
from ridge_boots_author_surface import SLOTS,ease,unit

ROOT=Path(__file__).resolve().parents[2]
SET=ROOT/'SourceAssets/ModernTacticalSet20261113'
OLD=SET/'CombatShirtR4/Authored'
PANTS=SET/'FieldTrousersR2/Authored'
OUT=SET/'RidgeBootsR2/Authored'
MAT='/Game/Characters/ModularOutfit20260924/ModernTacticalSet20261113/RidgeBootsR2/Materials/M_'
TILT=math.atan2(2.00392146,12.92064786)
CT,ST=math.cos(TILT),math.sin(TILT)
def load(path):
    with path.open(encoding='utf-8-sig') as f:return json.load(f)
def rigid(a,b):
    ac=a.mean(0);bc=b.mean(0)
    u,_,v=np.linalg.svd((a-ac).T@(b-bc));r=u@v
    if np.linalg.det(r)<0:u[:,-1]*=-1;r=u@v
    return r,bc-ac@r
class SideBinding:
    def __init__(self,source,target,pants,side):
        self.side=side;p=np.asarray(source['positions']);v=np.asarray(target['positions']);tris=np.asarray(source['triangles'])
        materials=np.asarray(source['triangle_materials']); guides=np.unique(tris[materials==0])
        self.frames=[]
        for joint in ('foot','calf'):
            # Use corresponding native sole and collar to fit the actual rig pose,
            # including UE's per-character plant height from the preceding outfit.
            candidates=np.unique(tris[materials==(7 if joint=='foot' else 0)])
            cand=candidates[(p[candidates,0]*side>0)&((p[candidates,2]<3.4) if joint=='foot' else (p[candidates,2]>27.85))]
            self.frames.append(rigid(p[cand],v[cand]))
        guides=guides[p[guides,0]*side>0]
        self.tree=cKDTree(p[guides])
        names={bone['name']:bone['index'] for bone in target['bones']}; bones=source['bones']
        source_ids=self.used_bones(source,guides)
        self.bone_ids=np.array([names[bones[i]['name']] for i in source_ids])
        column={j:i for i,j in enumerate(source_ids)}
        self.weights=np.zeros((len(guides),len(source_ids)))
        for row,ix in enumerate(guides):
            for j,w in source['weights'][ix]:self.weights[row,column[j]]+=w
        # Use the lower edge of the *equipped* field trousers to define the
        # throat of each boot independently. Convex sections include the folds.
        pp=np.asarray(pants['positions']);pp=pp[pp[:,0]*side>0]
        pp=pp[pp[:,2]<32]
        target_rim=v[np.unique(tris[materials==0])]
        target_rim=target_rim[target_rim[:,0]*side>0]
        self.top=target_rim[:,2].max()
        self.levels=np.arange(self.top-7.,self.top+1.6,.5)
        self.angles=np.linspace(-math.pi,math.pi,97);self.radii=[];self.centers=[]
        for z in self.levels:
            closest=pp[np.abs(pp[:,2]-z)<.79]
            if len(closest)<12:closest=pp[np.argsort(np.abs(pp[:,2]-z))[:96]]
            hull=ConvexHull(closest[:,:2]);k=closest[hull.vertices,:2]
            ctr=(np.min(k,axis=0)+np.max(k,axis=0))*.5
            self.centers.append(ctr)
            n=hull.equations[:,:2];intercepts=-(n@ctr+hull.equations[:,2])
            dirs=np.stack((np.cos(self.angles),np.sin(self.angles)),1)
            products=n@dirs.T
            radii=np.min(intercepts[:,None]/np.where(products>1.e-7,products,1.e-9),axis=0)
            self.radii.append(radii)
        self.centers=np.array(self.centers);self.radii=np.array(self.radii)
    @staticmethod
    def used_bones(source,guides):
        return sorted({j for ix in guides for j,_ in source['weights'][ix]})
    def source_coords(self,q):
        x,y,z=q.T
        return np.stack((self.side*(14.798+CT*x+ST*y),-2.45465-ST*x+CT*y,z),1)
    def warp(self,q):
        canonical=self.source_coords(q);z=canonical[:,2]
        (rf,tf),(rc,tc)=self.frames
        foot=canonical@rf+tf;calf=canonical@rc+tc
        # Preserve the modelled rocker at the floor across both native foot pitches.
        factor=ease((z-2.05)/5.)
        foot[:,2]=z+(foot[:,2]-z)*factor
        up=ease((z-12.)/16.5)[:,None];p=foot*(1.-up)+calf*up
        w=ease((p[:,2]-(self.top-6.9))/5.9)
        if np.any(w>0):
            active=np.flatnonzero(w>0);pp=p[active];zz=pp[:,2]
            center=np.stack([np.interp(zz,self.levels,self.centers[:,j]) for j in (0,1)],1)
            # At the lip, use arc-normal distance to the actual tucked leg. The
            # shift of the shaft keeps the boot wall thickness and eyelet clearance.
            zloc=z[active]; t=np.arctan2(q[active,0],(q[active,1]+2.8)*.987)
            dirs=np.stack((self.side*(CT*np.sin(t)+ST*np.cos(t)),-ST*np.sin(t)+CT*np.cos(t)),1)
            angle=np.arctan2(dirs[:,1],dirs[:,0])
            h=np.clip((zz-self.levels[0])/.5,0,len(self.levels)-1.00001)
            k=np.clip((angle+math.pi)/(2*math.pi)*(len(self.angles)-1),0,len(self.angles)-1.00001)
            i,j=h.astype(int),k.astype(int);a,b=(h-i),(k-j)
            rr=(1-a)*((1-b)*self.radii[i,j]+b*self.radii[i,j+1])+a*((1-b)*self.radii[i+1,j]+b*self.radii[i+1,j+1])
            # The design offset from the shell is preserved in the attachment.
            baseline=np.interp(zloc,[20,23,26.3,28.8],[5.42,5.80,6.12,6.17])
            radius=np.linalg.norm(np.stack((q[active,0],(q[active,1]+2.8)*.987),1),axis=1)
            new=center+dirs*(rr+.48+radius-baseline)[:,None]
            p[active,:2]+=w[active,None]*(new-pp[:,:2])
        # Carry the fitted front of the cuff down the shin into the instep.
        # The trousers expand at their gathered hem. Applying that contour
        # only to the last two rings makes a noticeable trumpet at the top.
        angle=np.arctan2(q[:,0],q[:,1]+2.8)
        frontness=np.maximum(0,np.cos(angle))
        fullness=np.interp(z,[7,11,15,19.5,22.5,24,25,26,27,28.5,32],
                           [0,.16,2.05,4.75,4.78,4.20,3.32,2.04,.90,0,0])
        shift=fullness*frontness**1.55
        p[:,0]+=self.side*ST*shift
        p[:,1]+=CT*shift
        # Roll the entire last, toe box, rand and tread together at the toe.
        p[:,2]+=1.50*ease((q[:,1]-14.5)/8.4)*(1.-ease((z-7.5)/4.))
        return p
    def influence(self,q):
        dist,ix=self.tree.query(self.source_coords(q),k=6)
        mix=1./np.maximum(dist,.028)**2
        values=(self.weights[ix]*mix[:,:,None]).sum(1)/mix.sum(1)[:,None]
        values[values<.00015]=0
        values/=values.sum(1)[:,None]
        return [[[int(self.bone_ids[k]),round(float(row[k]),7)] for k in np.argsort(row)[::-1] if row[k]>0] for row in values]

def corner_normals(p,f):
    face=np.cross(p[f[:,2]]-p[f[:,0]],p[f[:,1]]-p[f[:,0]])
    # Weld normals at UV splits only within this cut, preserving the bevel breaks.
    _,ids=np.unique(p.round(5),axis=0,return_inverse=True);smooth=np.zeros((ids.max()+1,3))
    for k in range(3):np.add.at(smooth,ids[f[:,k]],face)
    smooth=unit(smooth);n=smooth[ids[f]]
    dot=np.sum(n*n,axis=2)
    if np.any(dot<.01):n=np.where((dot<.01)[:,:,None],unit(face)[:,None,:],n)
    return n
def export(body,boot,source):
    donor=source if body=='Jason' else load(OLD/('boots_'+body+'.json'))
    pants=load(PANTS/('pants_tactical_'+body+'.json'))
    f=np.array(donor['triangles']);m=np.array(donor['triangle_materials']);native=np.flatnonzero(m==len(donor['material_slots'])-1)
    v,reverse=np.unique(f[native],return_inverse=True)
    p=[np.array(donor['positions'])[v]];tr=[reverse.reshape(-1,3)];uv=[np.asarray(donor['uv'])[native]];normals=[np.asarray(donor['normals'])[native]]
    weights=[donor['weights'][i] for i in v];mat=[np.full(len(native),len(SLOTS),int)]
    vi=len(v);fi=len(native);parts={'native_exposed_calf_skin':[0,fi]}
    for label,side in [('l',1),('r',-1)]:
        bind=SideBinding(source,donor,pants,side)
        vertices=np.concatenate([part[2] for part in boot.parts]);world=bind.warp(vertices)
        influences=bind.influence(vertices);ix=0
        for name,slot,q,t,texture in boot.parts:
            n=len(q);xyz=world[ix:ix+n];ff=t if side>0 else t[:,::-1]
            p.append(xyz);tr.append(ff+vi);uv.append(texture[ff]);normals.append(corner_normals(xyz,ff))
            weights.extend(influences[ix:ix+n]);ix+=n
            mat.append(np.full(len(ff),slot,int));parts[label+'_'+name]=[fi,fi+len(ff)]
            vi+=n;fi+=len(ff)
    native_slot=donor['material_slots'][-1]
    out=dict(source=donor['source'],bones=donor['bones'],material_slots=SLOTS+[native_slot],materials=[MAT+s for s in SLOTS]+[native_slot[7:]],positions=np.vstack(p).round(6).tolist(),triangles=np.vstack(tr).tolist(),triangle_materials=np.concatenate(mat).tolist(),normals=np.concatenate(normals).round(6).tolist(),uv=np.concatenate(uv).round(6).tolist(),weights=weights,parts=parts,source_file=(OLD/('boots_'+body+'.json')).relative_to(ROOT).as_posix(),tuck_source=(PANTS/('pants_tactical_'+body+'.json')).relative_to(ROOT).as_posix(),contract='Open padded shaft on the paired field-trouser cuff, native exposed skin and native ankle/ball weights. Left and right component face intervals are half-open.')
    OUT.mkdir(parents=True,exist_ok=True)
    dest=OUT/('boots_'+body+'.json');tmp=dest.with_suffix('.json.tmp')
    with tmp.open('w',encoding='utf-8') as file:json.dump(out,file,separators=(',',':'),allow_nan=False)
    tmp.replace(dest)
    print(body,vi,'vertices',fi,'triangles',len(parts),'parts',dest,flush=True)
if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('bodies',nargs='*',default=['Jason','Kaitlin']);args=parser.parse_args()
    print('Cutting uppers, eyelets and sole tooling',flush=True)
    boot=dominant_parts();source=load(OLD/'boots_Jason.json')
    for body in args.bodies:export(body,boot,source)
