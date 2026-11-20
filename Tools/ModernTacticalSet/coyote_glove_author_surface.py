"""Barycentric surface charts on the two continuous glove shells."""
import json
from pathlib import Path

import numpy as np
import shapely
from scipy.sparse import coo_matrix
from scipy.sparse.csgraph import connected_components
from scipy.spatial import cKDTree


P=Path(__file__).resolve().parents[2]
SET=P/"SourceAssets/ModernTacticalSet20261113"
OUT=SET/"CoyoteGlovesR2/Authored"
SLOTS=["CG_"+s for s in ("Knit","Suede","Stretch","Rubber","Webbing","Thread","Label")]
DIGITS=("thumb","index","middle","ring","pinky")


def unit(a):
    return a/np.maximum(np.linalg.norm(a,axis=-1,keepdims=True),1.e-12)


def read(file):
    return json.loads(file.read_bytes())


def write(file,d):
    tmp=file.with_suffix(".writing")
    with tmp.open("w",encoding="utf8") as fh:
        json.dump(d,fh,separators=(",",":"),allow_nan=False)
    tmp.replace(file)


def input_file(rig):
    if rig=="Super90":return SET/"NativeGloveR1/ShotgunGloves.json"
    if rig=="M16":return SET/"NativeGloveR1/M16/M16Gloves.json"
    return SET/"CombatShirtR4/Authored"/f"gloves_{rig}.json"


class Shell:
    def __init__(self,rig):
        self.rig=rig;d=read(input_file(rig));self.src=d
        if "bones" not in d:
            folder=SET/"NativeGloveR1"/("M16" if rig=="M16" else "")
            bs=read(folder/"Read"/f"{rig}_Jason.json")["bones"]
            d["bones"]=[dict(name=n,**b) for n,b in bs.items()]
        self.bones={b["name"]:np.array(b["position"]) for b in d["bones"]}
        bone_names={b["index"]:b["name"] for b in d["bones"]}
        if rig in ("Jason","Kaitlin"):
            from coyote_glove_author_body import build_body_native
            skin=read(SET/"CombatShirtR3/CuffRepairR1/Inputs"/f"Body_{rig}.json")
            self.p,self.f,self.ns,self.old_uv,self.ws,self.side=build_body_native(d,skin)
        else:
            self.from_fitted_shell(d,bone_names)
        self.sideface=self.side[self.f[:,0]]
        self.uvcode=np.rint(self.old_uv*100000).astype(np.int64)
        def zone(ws):
            totals=np.zeros(6)
            for i,w in ws:
                fields=bone_names[i].split("_")
                digit=fields[0] in DIGITS and len(fields)>1 and fields[1] in ("01","02","03")
                totals[DIGITS.index(fields[0])+1 if digit else 0]+=w
            return totals
        self.fzones=np.argmax(np.array([zone(w) for w in self.ws])[self.f].mean(1),axis=1)

    def from_fitted_shell(self,d,bone_names):
        p=np.asarray(d["positions"]);f=np.asarray(d["triangles"])
        _,weld=np.unique(p.round(4),axis=0,return_inverse=True)
        welded=weld[f];sz=int(weld.max())+1
        graph=coo_matrix((np.ones(welded.size),(welded.ravel(),np.roll(welded,1,axis=1).ravel())),shape=(sz,sz))
        _,groups=connected_components(graph,directed=False)
        group=groups[welded[:,0]]
        keep=np.flatnonzero(np.bincount(group)[group]>8000)
        self.selected=keep;v,inv=np.unique(f[keep],return_inverse=True)
        self.p=p[v];self.f=inv.reshape(-1,3)
        self.ns=np.asarray(d["normals"])[keep];self.old_uv=np.asarray(d["uv"])[keep]
        self.ws=[d["weights"][i] for i in v]
        self.side=np.array([bone_names[max(ws,key=lambda row:row[1])[0]][-1] for ws in self.ws])

    def map_from(self,base,required):
        if self is base:
            ids=np.arange(len(self.f));corner=np.tile(np.arange(3),(len(ids),1))
            return ids,corner,ids,corner
        # Corner UVs identify homologous sewn triangles even if the UE importer
        # split vertices or reordered faces. Select left/right independently.
        def codes(shell):
            src=shell.uvcode
            order=np.lexsort((src[:,:,1],src[:,:,0]),axis=1)
            uv=src[np.arange(len(src))[:,None],order]
            keys=[(s,u.tobytes()) for s,u in zip(shell.sideface,uv)]
            return keys,order
        keys,order=codes(self);bkeys,border=codes(base)
        lookup={};reverse={}
        for i,key in enumerate(keys):lookup.setdefault(key,[]).append(i)
        for i,key in enumerate(bkeys):reverse.setdefault(key,[]).append(i)
        result=np.full(len(bkeys),-1,int);base_for=np.full(len(keys),-1,int)
        for key,ids in reverse.items():
            hits=lookup.get(key,[])
            if not hits:continue
            for i,bi in enumerate(ids):result[bi]=hits[min(i,len(hits)-1)]
            for i,h in enumerate(hits):base_for[h]=ids[min(i,len(ids)-1)]
        def match_missing(ids,query,target,source,other):
            # A few UE source triangles carry sub-texel rounding differences.
            for s in ("l","r"):
                ids0=ids[source.sideface[ids]==s];pool=np.flatnonzero(other.sideface==s)
                if not len(ids0) or not len(pool):continue
                q=source.old_uv[ids0].mean(1);p=other.old_uv[pool].mean(1)
                _,near=cKDTree(p).query(q,k=min(12,len(pool)))
                for j,src in enumerate(ids0):
                    cand=pool[near[j]]
                    delta=query[src][None,:,None,:]-target[cand][:,None,:,:]
                    dist=np.linalg.norm(delta,axis=-1).min(2).max(1)
                    yield src,cand[np.argmin(dist)]
        for i,j in match_missing(np.flatnonzero((result<0)&np.isin(base.sideface,list(required))),base.old_uv,self.old_uv,base,self):result[i]=j
        for i,j in match_missing(np.flatnonzero(base_for<0),self.old_uv,base.old_uv,self,base):base_for[i]=j
        def corners(source,target,faces):
            delta=source.old_uv[:,:,None,:]-target.old_uv[np.maximum(faces,0)][:,None,:,:]
            cmap=np.linalg.norm(delta,axis=3).argmin(2)
            # UV-degenerate triangles are valid source topology. For exact
            # triplets use the stable source corner order for tied coordinates.
            for i in np.flatnonzero((cmap[:,0]==cmap[:,1])|(cmap[:,1]==cmap[:,2])|(cmap[:,0]==cmap[:,2])):
                a=np.lexsort((source.uvcode[i,:,1],source.uvcode[i,:,0]))
                b=np.lexsort((target.uvcode[max(faces[i],0),:,1],target.uvcode[max(faces[i],0),:,0]))
                cmap[i,a]=b
            return cmap
        return result,corners(base,self,result),base_for,corners(self,base,base_for)


class Chart:
    def __init__(self,shell,faces,coords,name):
        self.shell=shell;self.name=name
        x=coords
        den=(x[:,1,0]-x[:,0,0])*(x[:,2,1]-x[:,0,1])-(x[:,2,0]-x[:,0,0])*(x[:,1,1]-x[:,0,1])
        valid=np.abs(den)>1.e-8
        self.faces=faces[valid];self.q=x[valid];self.den=den[valid]
        self.polys=shapely.polygons(self.q[:,:,:2]);self.tree=shapely.STRtree(self.polys)
        self.approx=cKDTree(self.q[:,:,:2].mean(1))

    def bary(self,q,i):
        tr=self.q[i];d=q-tr[:,0,:2];a=tr[:,1,:2]-tr[:,0,:2];b=tr[:,2,:2]-tr[:,0,:2]
        w=(d[:,0]*b[:,1]-d[:,1]*b[:,0])/self.den[i]
        v=(a[:,0]*d[:,1]-a[:,1]*d[:,0])/self.den[i]
        return np.stack([1.-w-v,w,v],axis=1)

    def locate(self,q):
        q=np.asarray(q,float);pi,ti=self.tree.query(shapely.points(q),predicate="intersects")
        b=self.bary(q[pi],ti);z=np.einsum("ij,ij->i",self.q[ti,:,2],b)
        order=np.lexsort((-z,pi));indices,first=np.unique(pi[order],return_index=True)
        rows=order[first];hit=np.full(len(q),-1,int);hit[indices]=ti[rows]
        bary=np.zeros((len(q),3));bary[indices]=b[rows]
        missed=np.flatnonzero(hit<0)
        if len(missed):
            point=shapely.points(q[missed]);near=self.tree.nearest(point)
            lines=shapely.shortest_line(point,self.polys[near])
            nearest=shapely.get_coordinates(shapely.get_point(lines,-1))
            hit[missed]=near;bary[missed]=self.bary(nearest,near)
        bary=np.clip(bary,0,1);bary/=np.maximum(1.e-12,bary.sum(1,keepdims=True))
        return self.faces[hit],bary


class Hand:
    def __init__(self,shell,side):
        self.shell=shell;self.side=side;b=shell.bones
        self.origin=b["hand_"+side];y=unit(b["middle_01_"+side]-self.origin)
        x=b["index_01_"+side]-b["pinky_01_"+side];x=unit(x-(x@y)*y)
        z=np.cross(x,y);z*= -np.sign(z@(b["middle_03_"+side]-b["middle_01_"+side]))
        self.frame=np.array([x,y,z]);self.loc=(shell.p-self.origin)@self.frame.T
        self.ids=np.flatnonzero(shell.sideface==side);self.all=self.loc[shell.f[self.ids]]
        self.panel={}
        # Include the basal thumb influence: it owns much of the thenar pad.
        # Project only onto the matching face of the hand. Excluding all
        # thumb-weighted triangles here would send the palm panel through the
        # hand onto its back at gaps in the chart.
        names={b["index"]:b["name"] for b in shell.src["bones"]}
        distal=np.array([sum(w for i,w in ws if names[i].startswith(("thumb_02","thumb_03"))) for ws in shell.ws])
        facing=shell.ns[self.ids].mean(1)@z
        for sign in [1,-1]:
            keep=(distal[shell.f[self.ids]].mean(1)<.28)&(self.all[:,:,1].min(1)<10.7)&(sign*facing>.035)
            local=self.all[keep].copy();local[:,:,2]*=sign
            self.panel[sign]=Chart(shell,self.ids[keep],local,"hand")
        self.mat=np.where(shell.ns[self.ids].mean(1)@z>.18,0,1)
        sidewall=abs(shell.ns[self.ids].mean(1)@z)<.23
        self.mat[sidewall]=2
        self.mat[self.all[:,:,1].mean(1)<.18]=2
        self.uv=self.all[:,:,[0,1]].copy()/4.
        self.digits={}
        for k,digit in enumerate(DIGITS,1):
            faces=self.ids[shell.fzones[self.ids]==k]
            def joint(j):return (b[f"{digit}_0{j}_{side}"]-self.origin)@self.frame.T
            joints=np.array([joint(j) for j in [1,2,3]])
            direction=unit(joints[-1]-joints[-2])
            points=self.loc[shell.f[faces]]
            extension=np.percentile((points-joints[-1])@direction,99.7)
            joints=np.vstack([joints,joints[-1]+direction*max(extension,.8)])
            delta=np.diff(joints,axis=0);seg=np.linalg.norm(delta,axis=1);tangent=unit(delta)
            dist=points[:,:,None,:]-joints[None,None,:-1,:]
            frac=np.clip(np.einsum("fcsi,si->fcs",dist,tangent)/seg,0,1)
            nearest=joints[:-1]+frac[:,:,:,None]*delta
            choose=np.argmin(np.linalg.norm(points[:,:,None,:]-nearest,axis=3),axis=2)
            a=np.arange(len(points))[:,None];c=np.arange(3)[None,:]
            off=points-nearest[a,c,choose];station=(np.r_[0,np.cumsum(seg)[:-1]]+frac*seg)[a,c,choose]
            # A transported dorsal axis for each phalanx keeps the suede cap
            # wrapped along a bent finger instead of projected from above.
            dorsal=np.array([0.,0.,1.])
            if digit=="thumb":dorsal=unit(np.array([.75,.02,.8]))
            radial=unit(dorsal-(tangent@dorsal)[:,None]*tangent)
            lateral=unit(np.cross(tangent,radial))
            theta=np.arctan2(np.einsum("fci,fci->fc",off,lateral[choose]),np.einsum("fci,fci->fc",off,radial[choose]))
            for j in [1,2]:
                theta[:,j]=theta[:,0]+(theta[:,j]-theta[:,0]+np.pi)%(2*np.pi)-np.pi
            rad=np.linalg.norm(off,axis=2)
            radius=max(.55,np.median(rad[(station>seg.sum()*.28)&(station<seg.sum()*.68)]))
            tr=np.stack((theta*radius,station,rad),axis=2)
            variants=np.tile(tr,(3,1,1));variants[:len(tr),:,0]-=2*np.pi*radius;variants[2*len(tr):,:,0]+=2*np.pi*radius
            ch=Chart(shell,np.tile(faces,3),variants,digit)
            ls=seg.sum();self.digits[digit]=(ch,ls,radius)
            q=np.searchsorted(self.ids,faces);angle=np.abs(np.angle(np.mean(np.exp(1j*theta),axis=1)))
            self.mat[q]=np.select([station.mean(1)>ls*.72,angle<1.15,angle<1.87],[1,0,2],default=1)
            self.uv[q]=tr[:,:,:2]/4.
