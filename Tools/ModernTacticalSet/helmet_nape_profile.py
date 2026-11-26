"""Fit a swept posterior shell to the resting hairstyle and native head in cm."""
from pathlib import Path

import numpy as np
from scipy.interpolate import PchipInterpolator, RegularGridInterpolator
from scipy.ndimage import distance_transform_edt, gaussian_filter, maximum_filter

SET = Path(__file__).resolve().parents[2]/"SourceAssets/ModernTacticalSet20261113"
OUT = SET/"HelmetNapeR3/Authored"


def profile(rig):
    OUT.mkdir(parents=True,exist_ok=True)
    base=np.load(SET/"HelmetContourR2"/f"{rig}-profile.npz")
    origin,top,prior=base["origin"],float(base["top"]),base["rad"]
    polar=np.arange(len(prior))*float(base["step"])
    angles=np.linspace(0,np.pi,181)
    depths=np.arange(-6.,27.01,.10)
    step_angle=np.pi/180.
    old_ends=np.interp(angles,np.linspace(0,np.pi,len(base["ends"])//2+1),base["ends"][:len(base["ends"])//2+1])
    old_radius=np.empty((len(depths),len(angles)))
    old_edge=[]
    for i,angle in enumerate(angles):
        fractional=angle/(2*np.pi)*prior.shape[1]
        j=int(fractional)
        rad=(1-fractional%1)*prior[:,j]+(fractional%1)*prior[:,(j+1)%prior.shape[1]]
        d=top-origin[2]-rad*np.cos(polar)
        old_radius[:,i]=np.interp(depths,d,rad*np.sin(polar))
        old_edge.append(np.interp(old_ends[i],polar,d))
    edge=np.array(old_edge)
    drop=PchipInterpolator([0,99,107,115,125,137,151,165,180],[0,0,.18,1.05,3.25,5.44,6.28,6.42,6.18])(np.degrees(angles))
    cloud=np.load(SET/"HelmetHairFitR1"/f"{rig}-hair-envelope.npz")["positions"]
    xy=cloud[:,:2]-origin[:2]
    rho=np.linalg.norm(xy,axis=1)
    a=np.abs(np.arctan2(xy[:,0],xy[:,1]))
    d=top-cloud[:,2]
    keep=(d>=depths[0])&(d<=depths[-1])
    ai=np.rint(a[keep]/step_angle).astype(int).clip(0,len(angles)-1)
    di=np.rint((d[keep]-depths[0])/.1).astype(int).clip(0,len(depths)-1)
    body=np.zeros_like(old_radius)
    np.maximum.at(body,(di,ai),rho[keep])
    body=body[tuple(distance_transform_edt(body==0,return_distances=False,return_indices=True))]
    # A continuous manufactured arc must span individual strand ridges without imprinting them.
    guarded=maximum_filter(body,size=(7,5),mode="nearest")
    guard=np.maximum(guarded+.85,gaussian_filter(guarded,(6,4),mode="nearest")+1.03)
    inner=RegularGridInterpolator((depths,angles),guard,bounds_error=False,fill_value=None)
    lower=(depths[:,None]-(edge-6.8))/6.8
    ramp=np.clip(lower,0,1)
    ease=ramp*ramp*(3-2*ramp)
    dz=ease*drop
    dnew=depths[:,None]+dz
    zz,aa=np.broadcast_arrays(dnew,angles[None,:])
    floor=inner((np.clip(zz,depths[0],depths[-1]),aa))
    inset=np.minimum(2.65,drop*.42)
    nr=old_radius-inset*ramp**2
    # Local corrections are spread in angle and height so the production shell stays fair.
    correction=np.maximum(0,floor-nr)
    correction=gaussian_filter(maximum_filter(correction,size=(11,9),mode="nearest"),(4.5,4),mode="nearest")
    active=np.clip(drop/.8,0,1)*np.clip(lower*3,0,1)
    nr+=correction*active
    np.savez_compressed(OUT/f"nape-profile-{rig}.npz",depths=depths,angles=angles,
                        old_radius=old_radius,radial_delta=nr-old_radius,depth_delta=dz,
                        edge=edge,drop=drop,origin=origin,top=top)


if __name__=="__main__":
    for name in ("Jason","Kaitlin"):
        profile(name)
