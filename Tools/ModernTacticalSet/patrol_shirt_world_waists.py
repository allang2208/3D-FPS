"""Transfer the eight existing waist fits and cut the TS01 hem to the five actual waistbands."""
import gc
from pathlib import Path
import numpy as np
from scipy.ndimage import distance_transform_edt
from patrol_shirt_world import ROOT,SET,WORLD,BODY_NAMES,read,sha,smooth
from patrol_shirt_world_join import put
from field_pants_wear_waist import load_shell

ANGLES=np.linspace(0,2*np.pi,96,endpoint=False)
HEIGHTS=np.arange(92.,110.1,.5)
LEGACY_BONES=['pelvis','spine_01','spine_02','spine_03','thigh_l','thigh_r','thigh_twist_01_l','thigh_twist_01_r']

# The trousers use directional thigh correctives around the pelvis in deep flexion.
BONES=LEGACY_BONES+[f'thigh_{group}_{side}' for group in
                    ('fwd','bck','in','out','fwd_lwr','bck_lwr','twistCor_01','twistCor_02')
                    for side in ('l','r')]

def ray_grid(points,faces,weights=None,bones=None):
    # Intersect all waist triangles with each vertical profile and interpolate
    # their radial coordinates at half-centimetre stations along that profile.
    grid=np.full((len(HEIGHTS),len(ANGLES),1+len(BONES)),np.nan)
    tops=np.full(len(ANGLES),np.nan)
    q=points.copy();q[:,:,:2]-=[0.,.8]
    for t,theta in enumerate(ANGLES):
        radial=np.array([np.cos(theta),np.sin(theta)])
        profile=q[:,:,:2]@[-radial[1],radial[0]]
        select=(profile.min(1)<.00001)&(profile.max(1)>-.00001)&((q[:,:,:2]@radial).max(1)>2)
        ids=np.flatnonzero(select);x=profile[ids];panel=q[ids];rr=panel[:,:,:2]@radial
        if weights:
            # Local rim height at the actual half-plane intersection of the cloth.
            other=np.roll(x,-1,axis=1)
            cross=(x>0)!=(other>0)
            t0=x[cross]/(x[cross]-other[cross])
            start=panel[cross];end=np.roll(panel,-1,axis=1)[cross]
            pts=start+(end-start)*t0[:,None]
            tops[t]=pts[pts[:,:2]@radial>2,2].max()
        for j,z in enumerate(HEIGHTS):
            h=panel[:,:,2]-z
            a=x[:,1]*h[:,2]-x[:,2]*h[:,1];b=x[:,2]*h[:,0]-x[:,0]*h[:,2];c=x[:,0]*h[:,1]-x[:,1]*h[:,0]
            det=a+b+c;valid=np.abs(det)>1e-7
            denom=np.where(valid,det,1)
            co=np.column_stack((a,b,c))/denom[:,None];r=(rr*co).sum(1)
            valid &= (co.min(1)>-.00001)&(r>2)
            if not valid.any():continue
            i=np.argmin(np.where(valid,r,1e10)) if weights else np.argmax(np.where(valid,r,-1e10))
            grid[j,t,0]=r[i];grid[j,t,1:]=0
            if weights:
                for v,mul in zip(faces[ids[i]],co[i]):
                    for bone,w in weights[v]:
                        name=bones[bone]
                        if name in BONES:grid[j,t,1+BONES.index(name)]+=w*mul
    for t in range(len(ANGLES)):
        ix=np.flatnonzero(np.isfinite(grid[:,t,0]))
        if not len(ix):continue
        for k in range(grid.shape[2]):grid[:,t,k]=np.interp(HEIGHTS,HEIGHTS[ix],grid[ix,t,k])
    mask=~np.isfinite(grid[:,:,0]);idx=distance_transform_edt(np.tile(mask,(1,3)),return_distances=False,return_indices=True)
    if mask.all():raise ValueError('No waist intersections')
    return np.tile(grid,(1,3,1))[idx[0][:,96:192],idx[1][:,96:192]],tops

def shirt(path):
    d=read(path);m=np.asarray(d['triangle_materials']);end=np.flatnonzero(m==3)[0]
    f=np.array(d['triangles'][:end]);p=np.array(d['positions']);q=p[f]
    keep=(np.abs(q[:,:,0]).max(1)<22.5)&(q[:,:,2].min(1)<112)&(q[:,:,2].max(1)>92)
    return ray_grid(q[keep],f[keep])[0][:,:,0]

def trousers(rig):
    paths=[SET/'FieldTrousersR2/Authored'/f'pants{suffix}_{rig}.json' for suffix in ('','_boot','_short','_high','_tactical')]
    grids=[];tops=[]
    for path in paths:
        pts,f,w,b,top=load_shell(read(path));g,rim=ray_grid(pts,f,w,b);grids.append(g);tops.append(rim);del pts,f,w,b
    arrays=np.asarray(grids);inner=np.argmin(arrays[:,:,:,0],axis=0)
    grid=arrays[inner,*np.indices(inner.shape)]
    return grid,np.min(tops,axis=0),{p.name:sha(p) for p in paths}

def main(tactical_only=False):
    routes=read(WORLD/'routes.json')
    out=read(WORLD/'Fits/waists.json')['routes'] if tactical_only else {}
    for rig in BODY_NAMES:
        tr,top,fingerprints=trousers(rig)
        for owner in (False,True):
            entries={key:r for key,r in routes.items() if r['rig']==rig and r['owner']==owner}
            base=next(row for row in entries.values() if row['base']);source=shirt(base['legacy'])
            for key,row in entries.items():
                if row['base'] or (tactical_only and not row['tactical']):continue
                grid=np.zeros((*source.shape,2+len(BONES if row['tactical'] else LEGACY_BONES)))
                if row['tactical']:
                    # Keep an existing tight section; tuck free cloth inside
                    # the inner fabric and ease back into the jersey above it.
                    rim_offset=HEIGHTS[:,None]-top[None,:]
                    ease=1-smooth((rim_offset-.10)/4.0)
                    grid[:,:,0]=np.minimum(0,tr[:,:,0]-.75-source)*ease
                    grid[:,:,1]=1-smooth((rim_offset-.15)/4.5)
                    w=tr[:,:,1:];grid[:,:,2:]=w/np.maximum(w.sum(2,keepdims=True),1e-8)
                else:
                    fit=shirt(row['legacy']);grid[:,:,0]=fit-source
                grid[-1]=0
                name=key+'.bin';path=WORLD/'Fits'/name;path.parent.mkdir(parents=True,exist_ok=True)
                grid.astype('<f4').tofile(path)
                out[key]={'grid':name,'sha256':sha(path),'previous':row['previous'],'body':rig,'owner':owner,
                          'pants_sources':fingerprints if row['tactical'] else {},'legacy_source':row['legacy']}
                print('PATROL_WAIST',key,flush=True)
                gc.collect()
    put(WORLD/'Fits/waists.json',dict(bones=LEGACY_BONES,tactical_bones=BONES,angles=96,heights=HEIGHTS.tolist(),routes=out))

if __name__=='__main__':
    import argparse
    parser=argparse.ArgumentParser()
    parser.add_argument('--tactical-only',action='store_true')
    main(parser.parse_args().tactical_only)
