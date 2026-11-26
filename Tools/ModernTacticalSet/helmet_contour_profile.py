"""Shape the crown against the captured resting hair and head, in native cm."""
from pathlib import Path
import json
import numpy as np
from scipy.ndimage import maximum_filter, gaussian_filter, distance_transform_edt
from scipy.interpolate import PchipInterpolator
from scipy.special import sph_harm_y
from scipy.optimize import minimize

ROOT=Path(__file__).resolve().parents[2]/'SourceAssets/ModernTacticalSet20261113'
OLD=ROOT/'HelmetHairFitR1'
OUT=ROOT/'HelmetContourR2'
def rim(top,theta):
    angles=[0,.42,.76,.99,1.15,1.50,1.75,2.02,2.33,2.66,np.pi]
    depth=[7.4,7.7,9.2,10.15,10.0,8.1,7.65,8.7,11.55,12.8,13.25]
    return top-PchipInterpolator(angles,depth)(abs(np.arctan2(np.sin(theta),np.cos(theta))))
def profile(rig):
    fit=json.loads((OLD/'fit.json').read_bytes())['profiles'][rig]
    cloud=np.load(OLD/(rig+'-hair-envelope.npz'))['positions']
    head=cloud[-fit['head_points']:];top=float(head[:,2].max())
    band=cloud[abs(cloud[:,2]-(top-5))<.5]
    cy=float(np.mean([np.min(band[:,1]),np.max(band[:,1])]))
    origin=np.array([0,cy,top-8.5])
    points=cloud-origin;theta=np.arctan2(points[:,0],points[:,1]);r=np.linalg.norm(points,axis=1)
    phi=np.arccos(np.clip(points[:,2]/np.maximum(r,1.e-8),-1,1))
    keep=(cloud[:,2]>rim(top,theta)-1.3)&(phi<2.28)
    # Use mirrored maxima so the helmet remains a manufactured symmetrical shell.
    N=144; M=79; step=2.3/(M-1)
    ti=np.int32(np.round(theta*N/(2*np.pi)))%N
    pi=np.int32(np.round(phi/step)).clip(0,M-1)
    rad=np.zeros((M,N))
    for index in (ti,(-ti)%N):
        np.maximum.at(rad,(pi[keep],index[keep]),r[keep])
    tiled=np.tile(rad,(1,3))
    nearest=distance_transform_edt(tiled==0,return_distances=False,return_indices=True)
    rad=tiled[tuple(nearest)][:,N:N*2]
    mode=('nearest','wrap')
    rad=maximum_filter(rad,size=(3,3),mode=mode)
    rad=gaussian_filter(rad,sigma=(2.9,4.6),mode=mode)
    crest=gaussian_filter(rad[0],4,mode='wrap').mean()
    blend=np.minimum(1,np.arange(M)[:,None]/6.)
    rad=rad*blend+crest*(1-blend)
    rad+=.98
    # Correct any local underestimate after smoothing, in the under-shell region.
    for _ in range(4):
        err=r[keep]+.81-rad[pi[keep],ti[keep]]
        adjust=np.zeros_like(rad)
        for ix in [ti,(-ti)%N]:np.maximum.at(adjust,(pi[keep],ix[keep]),err)
        rad+=gaussian_filter(maximum_filter(adjust,size=(5,7),mode=mode),sigma=(2.5,3.5),mode=mode)
    th=np.arange(N)*2*np.pi/N
    # A low-order spherical fit removes curls, strand bundles and local hairline
    # ripples from the hard shell. Only the low-frequency head shape survives.
    polar,azimuth=np.meshgrid(np.arange(M)*step,th,indexing='ij')
    design=np.stack([sph_harm_y(l,m,polar,azimuth).real
                     for l in range(5) for m in range(l+1)],axis=-1)
    weights=np.sqrt(np.maximum(.08,np.sin(polar)))
    coeff=np.linalg.lstsq((design*weights[:,:,None]).reshape(-1,design.shape[-1]),(rad*weights).ravel(),rcond=None)[0]
    target=rad.copy()
    bounds=np.zeros_like(rad)
    for ix in (ti,(-ti)%N):np.maximum.at(bounds,(pi[keep],ix[keep]),r[keep]+.96)
    actual=bounds>0;B=design[actual];minimum=bounds[actual]
    X=(design*weights[:,:,None]).reshape(-1,design.shape[-1]);y=(target*weights).ravel()
    M2=X.T@X/len(y);rhs=X.T@y/len(y)
    base=lambda x: .5*x@M2@x-x@rhs
    sol=minimize(base,coeff,jac=lambda x:M2@x-rhs,method='SLSQP',
                 constraints={'type':'ineq','fun':lambda x:B@x-minimum,'jac':lambda x:B},
                 options={'maxiter':150,'ftol':1e-8})
    if np.min(B@sol.x-minimum)<-.01:raise ValueError('Smooth crown cannot enclose native head and hair')
    rad=design@sol.x
    # Shape a short brow lip blended into the temples and a tapered crown ridge.
    ph=np.arange(M)[:,None]*step
    rad+=.28*np.maximum(0,np.cos(th))[None,:]**5*np.exp(-((ph-1.48)/.25)**2)
    edge=rim(top,th);phis=np.arange(M)*step
    ends=np.array([np.interp(edge[i],(origin[2]+rad[:,i]*np.cos(phis))[::-1],phis[::-1]) for i in range(N)])
    np.savez(OUT/(rig+'-profile.npz'),origin=origin,rad=rad,step=step,ends=ends,top=top)
    print(rig,'top',top,'center',origin,'rim heights',edge.min(),edge.max(),flush=True)
if __name__=='__main__':
    for rig in ['Jason','Kaitlin']:profile(rig)

