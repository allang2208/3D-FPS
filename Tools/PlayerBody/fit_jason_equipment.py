"""Author garment clearance, hip coverage, and a shoulder-bound backpack offline."""
import json
import runpy
from pathlib import Path
import numpy as np
from scipy.spatial import cKDTree

PROJECT=Path('D:/FPS3D/FPSGAME')
ROOT=PROJECT/'SourceAssets/JasonEquipmentRepair20261003'
fit=runpy.run_path(str(PROJECT/'Tools/PlayerBody/fit_jason_outfits.py'))
source=json.loads((ROOT/'backpack.json').read_text())
v=np.array(source['positions'])
t=np.array(source['triangles'],int)
signed_volume=np.einsum('ij,ij->i',v[t[:,0]],np.cross(v[t[:,1]],v[t[:,2]])).sum()/6.
# UE's OBJ importer reflected Y. Rotate the imported asset, not the pre-import
# OBJ convention, so the shell is behind the player and the straps face in.
p=v*np.array([-.9,-.9,.9])+np.array([0.,-10.5,120.])
strap=np.clip((-v[:,1]-.4)/4.,0,1)
strap=strap*strap*(3-2*strap)
ids,cw=fit['project_surface'](p,np.full(len(p),'torso'))
surface=(fit['tv'][ids]*cw[:,:,None]).sum(1)
normal=(fit['normals'][ids]*cw[:,:,None]).sum(1)
normal/=np.maximum(np.linalg.norm(normal,axis=1),1e-9)[:,None]
# Fit shoulder and chest portions to the clothed envelope. Keep attachment
# roots and dangling tails rigidly tied to the bag instead of pulling them in.
contact=strap*np.clip((p[:,2]-96.)/8.,0,1)
delta=(surface+normal*1.0-p)*contact[:,None]
for side in [-1,1]:
    side_ids=np.flatnonzero(v[:,0]*side>=0)
    _,near=cKDTree(p[side_ids]).query(p[side_ids],k=8)
    delta[side_ids]=delta[side_ids[near]].mean(1)
p+=delta
spine=fit['target_by_name']['spine_03']['index']
weights=[]
for i in range(len(p)):
    total={spine:1.-contact[i]}
    for vertex,mix in zip(ids[i],cw[i]):
        for bone,w in fit['target']['weights'][vertex]:
            total[bone]=total.get(bone,0.)+contact[i]*mix*w
    top=sorted(total.items(),key=lambda x:-x[1])[:8]
    den=sum(w for _,w in top)
    weights.append([[int(b),float(w/den)] for b,w in top if w>1e-6])
(ROOT/'backpack_fitted.json').write_text(json.dumps({'source':source['asset'],
    'positions':p.tolist(),'weights':weights,'materials':source['materials'],
    'flip_winding':bool(signed_volume>0),'rig':'Jason','shell_bone':'spine_03'},separators=(',',':')))
print('JASON_BACKPACK_FITTED '+str(len(p)),flush=True)
# Reapply the continuous shoulder sections after rebuilding the coarse mount.
runpy.run_path(str(PROJECT/'Tools/PlayerBody/refit_jason_backpack_straps.py'),run_name='__main__')
