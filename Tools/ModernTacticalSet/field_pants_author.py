"""Tailor the MCDU-derived TS01 trousers on the ten native R4 footwear shells."""
import argparse
import functools
import hashlib
import json
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor

import numpy as np
from scipy.ndimage import gaussian_filter, map_coordinates
from scipy.sparse import coo_matrix
from scipy.sparse.csgraph import connected_components

from coyote_glove_author_surface import Chart,unit
from field_pants_author_pattern import Tailoring,ease

P=Path(__file__).resolve().parents[2]
SET=P/"SourceAssets/ModernTacticalSet20261113"
R=SET/"FieldTrousersR2"
OUT=R/"Authored"
OLD=SET/"CombatShirtR4/Authored"
CUTS=SET/"CombatShirtR2/Authored"
MAT="/Game/Characters/ModularOutfit20260924/ModernTacticalSet20261113/FieldTrousersR2/Materials/M_"
SLOTS=["FT_Ripstop","FT_Stretch","FT_Reinforcement","FT_Webbing","FT_Thread","FT_Hardware"]
KINDS=["pants","pants_boot","pants_short","pants_high","pants_tactical"]


def load(file):
    return json.loads(file.read_bytes())


def write(file,d):
    tmp=file.with_suffix(".writing")
    with tmp.open("w",encoding="utf8") as out:
        json.dump(d,out,separators=(",",":"),allow_nan=False)
    tmp.replace(file)


def bone_positions(d):
    return {bone["name"]:np.asarray(bone["position"]) for bone in d["bones"]}


def axis_at(points,bones,side):
    shape=points.shape;z=points.reshape(-1,3)[:,2]
    foot,knee,hip=[bones[n+"_"+side] for n in ("foot","calf","thigh")]
    levels=[foot[2],knee[2],hip[2]]
    return np.column_stack((np.interp(z,levels,[foot[0],knee[0],hip[0]]),
                            np.interp(z,levels,[foot[1],knee[1],hip[1]]),z)).reshape(shape)


class Native:
    def __init__(self,d):
        self.p=np.asarray(d["positions"])
        self.f=np.asarray(d["triangles"])
        self.n=np.asarray(d["normals"])
        self.uv=np.asarray(d["uv"])
        self.m=np.asarray(d["triangle_materials"])
        self.weights=d["weights"]
        self.b=bone_positions(d)


def shell_mask(base):
    p=base.p;f=base.f;m=base.m
    _,w=np.unique(p.round(4),axis=0,return_inverse=True)
    v=w[f];edges=v.ravel(),np.roll(v,1,axis=1).ravel()
    _,label=connected_components(coo_matrix((np.ones(v.size),edges),shape=(w.max()+1,w.max()+1)),directed=False)
    group=label[v[:,0]];counts=np.bincount(group);core=group==counts.argmax()
    # Retain the full continuous outer and inner shell, its cuff rings, the
    # complete native waist interface, fly, belt loops and waist skin insert.
    # Remove the old hard shields, floating cargo pleats, and duplicate straps.
    used=core.copy()
    for g in np.unique(group):
        if g==counts.argmax():continue
        ids=np.flatnonzero(group==g);lo=p[f[ids]].min(axis=(0,1));hi=p[f[ids]].max(axis=(0,1))
        waist=lo[2]>95.45
        fly=lo[2]>80 and hi[0]-lo[0]<3. and abs((lo[0]+hi[0])*.5)<1.8 and lo[1]>9
        original_hem=hi[2]<15.7
        if waist or fly or original_hem or np.all(m[ids]==6):
            used[ids]=True
    return core,used


def chart_coords(points,base,side,hip=False):
    sg=1 if side=="l" else -1
    if hip:
        origin=np.array([0.,base.b["pelvis"][1],0.])
        offsets=points-origin;radius=14.
    else:
        offsets=points-axis_at(points,base.b,side);radius=8.5
    theta=np.arctan2(sg*offsets[:,:,0],offsets[:,:,1])
    theta=theta[:,:1]+(theta-theta[:,:1]+np.pi)%(2*np.pi)-np.pi
    return np.stack((theta*radius,points[:,:,2],np.linalg.norm(offsets[:,:,:2],axis=2)),axis=2),offsets


def chart(base,core,side,hip=False):
    sg=1 if side=="l" else -1
    selected=np.flatnonzero(core)
    points=base.p[base.f[selected]]
    q,offsets=chart_coords(points,base,side,hip)
    normals=base.n[selected].mean(1)
    facing=(normals[:,:2]*unit(offsets.mean(1)[:,:2])).sum(1)
    mask=(facing>.055)&(points[:,:,0].mean(1)*sg>(-.45 if hip else .20))
    if hip:mask&=points[:,:,2].max(1)>82
    else:mask&=points[:,:,2].min(1)<86
    ids=selected[mask];q=q[mask]
    radius=14. if hip else 8.5
    tr=np.tile(q,(3,1,1))
    tr[:len(q),:,0]-=2*np.pi*radius
    tr[2*len(q):,:,0]+=2*np.pi*radius
    return Chart(None,np.tile(ids,3),tr,"hip" if hip else "leg")


@functools.lru_cache(maxsize=1)
def pattern():
    base=Native(load(CUTS/"pants_Jason.json"))
    core,used=shell_mask(base);parts=[]
    for side in ("l","r"):
        charts={k:chart(base,core,side,k=="hip") for k in ("hip","leg")}
        parts+=Tailoring(charts,side).make()
    return base,core,used,parts


def press_knee(positions,flat,core,side,plain,cut):
    """Sample the native knee by azimuth. Press out the armour-shaped crosswise corrugations."""
    knee=flat.b["calf_"+side]
    sign=1 if side=="l" else -1
    xy=positions[:,:2]-knee[:2]
    r=np.linalg.norm(xy,axis=1)
    theta=np.arctan2(xy[:,0],xy[:,1])
    height=positions[:,2]-knee[2]
    leg=(flat.p[:,0]*sign>0)&(np.abs(height)<24)
    faces=flat.f[core & leg[flat.f].all(1)]
    qtheta=theta[faces].copy()
    qtheta=qtheta[:,:1]+(qtheta-qtheta[:,:1]+np.pi)%(2*np.pi)-np.pi
    native=np.stack((qtheta,height[faces],r[faces]),axis=2)
    q=np.tile(native,(3,1,1))
    q[:len(native),:,0]-=2*np.pi;q[2*len(native):,:,0]+=2*np.pi
    chart=Chart(None,np.tile(np.arange(len(faces)),3),q,"knee")
    nangle=96;angle_step=np.pi*2/nangle;zstep=.5
    angles=np.arange(nangle)*angle_step-np.pi;levels=np.arange(-20.,20.01,zstep)
    angle_grid,h_grid=np.meshgrid(angles,levels)
    ids,w=chart.locate(np.c_[angle_grid.ravel(),h_grid.ravel()])
    profile=(r[faces[ids]]*w).sum(1).reshape(angle_grid.shape)
    pressed=gaussian_filter(profile,(3.45/zstep,1.25),mode=("nearest","wrap"))
    # Preserve the original shell thickness, stroke the knee lengthwise and
    # keep a little compression in the hollow behind the joint.
    coords=np.vstack((np.clip((height-levels[0])/zstep,0,len(levels)-1),
                      ((theta+np.pi)/angle_step)%nangle))
    def interp(field):
        tiled=np.column_stack((field[:,-1],field,field[:,0]))
        return map_coordinates(tiled,coords+np.array([[0.],[1.]]),order=1,mode="nearest")
    blend=ease((height+10.4)/3.1)*ease((12.-height)/3.1)*leg
    blend[np.unique(flat.f[flat.m==6])]=0.
    if not plain:blend*=ease((positions[:,2]-cut)/7.)
    back=ease((-np.cos(theta)-.20)/.65)
    blend*=1.-.21*back
    radial=xy/r[:,None].clip(1.e-8)
    correction=interp(pressed-profile)*blend
    positions[:,:2]+=radial*correction[:,None]
    # A tangent normal from the pressed surface also removes the alternating
    # slopes baked into the donor's split normals. Blend at both cut edges.
    dtheta=(np.roll(pressed,-1,axis=1)-np.roll(pressed,1,axis=1))/(2.*angle_step)
    angular=interp(dtheta)/interp(pressed).clip(.1)
    lateral=np.column_stack((radial[:,1],-radial[:,0]))
    analytic=unit(np.column_stack((radial-angular[:,None]*lateral,-interp(np.gradient(pressed,zstep,axis=0)))))
    return blend,analytic


def drape(src,flat,d,plain,core):
    # The settled source drops up to 8 cm just above a pinned cuff. Recut on
    # its pre-simulation topology to recover a clean, continuous leg.
    p=src.p.copy();sewn=np.unique(flat.f[flat.m!=6]);body=flat.b
    cut=d["cloth_production"]["boot_tuck_preserved_below_cm"]
    for side,sg in (("l",1),("r",-1)):
        ix=sewn[flat.p[sewn,0]*sg>=0];q=flat.p[ix];z=q[:,2]
        radius=q-axis_at(q,body,side);radius[:,2]=0.
        direction=unit(radius);theta=np.arctan2(radius[:,0]*sg,radius[:,1])
        relax=(1.-ease((z-82.)/12.))*(1.-ease((z-65.)/10.)*(1.-ease(np.abs(q[:,0])/7.)))
        cuff=np.ones(len(z)) if plain else ease((z-cut)/7.)
        # The free hem hangs nearly straight from the calf. Fitted shafts
        # retain their old skirt radius, height and native weights at contact.
        wide=np.interp(z,[12.,19.,29.,37.,47.,56.,68.,79.,90.],
                         [3.15,2.85,1.72,1.28,1.10,.78,.46,.14,0.])
        fold=np.zeros(len(q));phase=.23 if side=="l" else -.30
        for level,height,width,angle,offset in (
             (27.,.20,1.65,2.9,.95),(36.6,.56,1.50,-3.15,.5),
             (40.2,.39,1.34,2.8,1.8),(52.,.43,1.40,-2.66,1.5),
             (61.8,.21,1.62,3.65,2.4),(79.6,.37,1.48,-3.4,1.05)):
            curve=level+angle*np.cos(theta+offset+phase)+.58*np.sin(2*theta+phase)
            section=(z-curve)/width
            fold+=height*(np.exp(-.5*section**2)-.48*np.exp(-.5*(section-1.45)**2))*(.4+.6*np.cos(theta+offset)**2)
        fold+=.23*np.cos(3.*theta+.12*(z-20)+phase)*np.exp(-((z-27.)/11.)**2)
        target=q+direction*((wide*(.90+.10*np.cos(theta)**2)+fold)*relax)[:,None]
        restoration=cuff*(1.-ease((z-87.)/7.))
        p[ix]=src.p[ix]+(target-src.p[ix])*restoration[:,None]
    knees=[press_knee(p,flat,core,side,plain,cut) for side in ("l","r")]
    z=flat.p[:,2]
    alpha=(np.ones(len(z)) if plain else ease((z-cut)/7.))*(1-ease((z-87.)/7.))
    alpha[np.unique(flat.f[flat.m==6])]=0.
    ref=src.p+(flat.p-src.p)*alpha[:,None]
    rn=unit(src.n+(flat.n-src.n)*alpha[src.f][:,:,None])
    old=ref[src.f];new=p[src.f]
    before=unit(np.cross(old[:,1]-old[:,0],old[:,2]-old[:,0]))
    after=unit(np.cross(new[:,1]-new[:,0],new[:,2]-new[:,0]))
    axis=np.cross(before,after);c=np.sum(before*after,axis=1).clip(-.99999,1)
    n=rn+np.cross(axis[:,None],rn)+np.cross(axis[:,None],np.cross(axis[:,None],rn))/(1+c[:,None,None])
    for blend,outer in knees:
        weight=blend[src.f]*core[:,None]
        sample=outer[src.f]
        sign=np.where((sample*n).sum(2)<0,-1,1)
        n=n*(1-weight[:,:,None])+sample*(weight*sign)[:,:,None]
    return p,unit(n)


def fabric_uv(template,keep):
    pts=template.p[template.f[keep]]
    # Slacks are cut on the vertical grain. Unwrap each leg around its centre;
    # a simple per-triangle dominant-axis box map would flip bias at the knee.
    uv=template.uv[keep].copy()
    center=pts.mean(1);m=template.m[keep]
    for side,sg in (("l",1),("r",-1)):
        for hip in [False,True]:
            mask=(center[:,0]*sg>=0)&(m!=6)&((center[:,2]>82)==hip)
            q,_=chart_coords(pts[mask],template,side,hip)
            uv[mask]=q[:,:,:2]/8.
    return uv


def rest_panel(src,part,positions,normals,cut,plain):
    ids=part["face"];tri=src.f[ids];w=part["w"]
    at=(positions[tri]*w[:,:,None]).sum(1)
    n=unit((normals[ids]*w[:,:,None]).sum(1))
    h=part["h"].copy()
    # Larger boots are covered by the original native-insert garment. Taper
    # the knee/ankle detail to that same envelope above each boot shaft.
    blend=np.ones(len(h)) if plain else ease((at[:,2]-cut)/3.)
    f=part["faces"]
    keep=blend[f].max(1)>.08
    if not keep.any():return None
    p=at+n*(h*blend)[:,None]
    f=f[keep];v=p[f]
    face_n=-np.cross(v[:,1]-v[:,0],v[:,2]-v[:,0])
    good=np.linalg.norm(face_n,axis=1)>1e-8
    f=f[good];face_n=face_n[good]
    if not len(f):return None
    flip=np.sum(face_n*n[f].mean(1),axis=1)<0
    f[flip]=f[flip,::-1];face_n[flip]*=-1
    v,inv=np.unique(f,return_inverse=True);faces=inv.reshape(-1,3)
    smooth_n=np.zeros((len(v),3))
    for j in range(3):np.add.at(smooth_n,faces[:,j],face_n)
    nn=unit(smooth_n)
    missing=np.linalg.norm(nn,axis=1)<.01;nn[missing]=n[v[missing]]
    weights=[]
    for ff,ws in zip(tri[v],w[v]):
        accum={}
        for ix,amount in zip(ff,ws):
            for bone,strength in src.weights[ix]:
                accum[bone]=accum.get(bone,0.)+strength*amount
        row=sorted(((b,a) for b,a in accum.items() if a>1.e-7),key=lambda t:-t[1])[:8]
        total=sum(a for b,a in row)
        weights.append([[int(b),round(a/total,8)] for b,a in row])
    return p[v],faces,nn[faces],part["uv"][v][faces],weights


def author(slug):
    kind,body=slug.rsplit("_",1)
    file=OLD/("wear_"+slug+".json")
    raw=file.read_bytes();d=json.loads(raw)
    src=Native(d);base,core,used,parts=pattern()
    if not np.array_equal(src.f,base.f):
        raise ValueError("Native cut topology has changed for "+slug)
    original=d["material_slots"]
    slots=SLOTS+[s for s in original if s.startswith("NATIVE:")]
    original_mat=np.array([5,0,2,4,3,1,6]);keep=np.flatnonzero(used)
    flat=Native(load(CUTS/(slug+".json")))
    if not np.array_equal(flat.f,src.f):raise ValueError("Pre-simulation chart topology differs on "+slug)
    positions,normals=drape(src,flat,d,kind=="pants",core)
    v,inv=np.unique(src.f[keep],return_inverse=True)
    p=[positions[v]];f=[inv.reshape(-1,3)];n=[normals[keep]]
    uv=[fabric_uv(base,keep)]
    mat=[original_mat[src.m[keep]]]
    weights=[src.weights[i] for i in v]
    ranges={"Native_shell_waist_hem_and_skin":[0,len(keep)]}
    first=len(keep);vi=len(v)
    cut=d["cloth_production"]["boot_tuck_preserved_below_cm"]
    for part in parts:
        result=rest_panel(src,part,positions,normals,cut,kind=="pants")
        if result is None:continue
        pp,ff,nn,uu,ww=result
        ranges[part["name"]]=[first,first+len(ff)]
        first+=len(ff);p.append(pp);f.append(ff+vi);vi+=len(pp)
        n.append(nn);uv.append(uu);weights.extend(ww);mat.append(np.full(len(ff),part["slot"],int))
    outfits=OUT/(slug+".json")
    dossier=dict(source=d["source"],bones=d["bones"],material_slots=slots,
                 materials=[MAT+s if not s.startswith("NATIVE:") else s[7:] for s in slots],
                 positions=np.vstack(p).round(6).tolist(),triangles=np.vstack(f).tolist(),
                 triangle_materials=np.concatenate(mat).tolist(),normals=np.concatenate(n).round(6).tolist(),
                 uv=np.concatenate(uv).round(6).tolist(),weights=weights,parts=ranges,
                 source_file=file.relative_to(P).as_posix(),source_sha256=hashlib.sha256(raw).hexdigest(),
                 contract="Native waist and matched boot envelopes; patterned cargo bellows, articulated knee, posterior knee stretch and ankle closure.")
    write(outfits,dossier)
    metadata=dict(file=outfits.name,donor=file.relative_to(P).as_posix(),source_sha256=dossier["source_sha256"],
                  sha256=hashlib.sha256(outfits.read_bytes()).hexdigest(),triangles=first,vertices=vi,parts=len(ranges))
    write(OUT/(slug+"-source.json"),metadata)
    print("FIELD_TROUSERS_AUTHORED",slug,first,vi,len(ranges),flush=True)


def main():
    ap=argparse.ArgumentParser();ap.add_argument("slug",nargs="*");ap.add_argument("--jobs",type=int,default=2)
    opt=ap.parse_args();OUT.mkdir(parents=True,exist_ok=True)
    names=[kind+"_"+body for body in ("Jason","Kaitlin") for kind in KINDS]
    work=opt.slug or names
    if set(work)-set(names):raise ValueError("Unknown trouser cut")
    if opt.jobs<=1 or len(work)==1:
        for slug in work:author(slug)
    else:
        with ProcessPoolExecutor(max_workers=opt.jobs) as pool:list(pool.map(author,work))
    if all((OUT/(k+"-source.json")).is_file() for k in names):
        write(OUT/"cuts.json",{"reference":"Helikon-Tex MCDU DyNyCo Coyote",
                              "variants":{k:load(OUT/(k+"-source.json")) for k in names}})


if __name__=="__main__":
    main()
