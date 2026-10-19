"""Prepare native fit fields and retain the existing capri production inputs."""
import json,shutil
from pathlib import Path
import numpy as np
from scipy.ndimage import gaussian_filter
P=Path('D:/FPS3D/FPSGAME');R=P/'SourceAssets/ST6LowerSet20261018';R.mkdir(exist_ok=True)
for name in ('Textures','Before','Authored','Exports'):(R/name).mkdir(exist_ok=True)
paths=[*list((P/'Tools/SmokeGreyCapri').glob('*.py')),
       *[P/'SourceAssets/SmokeGreyCapri20261004'/n for n in ('Jason_SmokeGreyCapri_Garment.json','Jason_SmokeGreyCapri.json','Jason_SmokeGreyCapri_HighBootsFit.json','SmokeGreyCapri.blend','Capri_Construction.blend','ue_smoke_grey_capri.png','saved_assets.json')]]
for p in paths:
    target=R/'Before'/p.relative_to(P)
    if p.exists() and not target.exists():target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(p,target)
native=json.loads((P/'SourceAssets/ST6Reset20261017/Read/Jason.json').read_text())
p=np.array(native['positions']);f=np.array(native['triangles']);m=np.array(native['triangle_materials'])
f=f[np.isin(m,[3,8,9,10,12,14,16])];tri=p[f]
levels=np.arange(80,104.01,.5);theta=np.linspace(0,2*np.pi,192,endpoint=False);radii=[];centers=[]
for z in levels:
    ft=tri[(tri[:,:,2].min(1)<=z)&(tri[:,:,2].max(1)>=z)]
    segments=[]
    for face in ft:
        points=[]
        for a,b in zip(face,np.roll(face,-1,axis=0)):
            if (a[2]<z)!=(b[2]<z):points.append(a+(b-a)*(z-a[2])/(b[2]-a[2]))
        if len(points)==2:segments.append(points)
    seg=np.array(segments)[:,:,:2];cloud=seg.reshape(-1,2)
    center=np.array([0.,(cloud[:,1].max()+cloud[:,1].min())*.5]);centers.append(center)
    a=seg[:,0]-center;b=seg[:,1]-seg[:,0];row=[]
    for t in theta:
        direction=np.array([np.sin(t),np.cos(t)])
        det=direction[1]*b[:,0]-direction[0]*b[:,1]
        valid=abs(det)>1e-9
        along=np.divide(a[:,1]*b[:,0]-a[:,0]*b[:,1],det,out=np.zeros(len(a)),where=valid)
        edge=np.divide(direction[0]*a[:,1]-direction[1]*a[:,0],det,out=np.zeros(len(a)),where=valid)
        use=valid&(along>0)&(edge>=-1e-6)&(edge<=1+1e-6)
        row.append(float(along[use].max()) if use.any() else float(np.linalg.norm(cloud-center,axis=1).max()))
    radii.append(row)
radii=gaussian_filter(np.array(radii),(.55,.6),mode=('nearest','wrap'))
np.savez(R/'waist_fit.npz',levels=levels,angles=theta,centers=np.array(centers),radii=radii,clearance_cm=.55)
(R/'native_reference.json').write_text((P/'SourceAssets/BrownLeatherSet20261004/native_reference.json').read_text())
shutil.copy2(P/'Tools/BrownLeatherSet/geometry.py',P/'Tools/ST6LowerSet/geometry.py')
print('ST6_NATIVE_FIT_FIELD_PREPARED',flush=True)
