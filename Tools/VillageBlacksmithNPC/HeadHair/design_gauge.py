"""Derive a hidden scalp and jaw fitting form from the commissioned orthographic sheet."""
from pathlib import Path
import json
import numpy as np
from scipy import ndimage
from PIL import Image
ROOT=Path(__file__).resolve().parents[3]/'SourceAssets/VillageBlacksmithNPC20261118'
OUT=ROOT/'HeadHair/DesignGroom'
OUT.mkdir(parents=True,exist_ok=True)
im=np.asarray(Image.open(ROOT/'Design/head_views.png').convert('RGB')).astype(float)
h,w=im.shape[:2]
def bounds(column):
    lo=w*column//3;hi=w*(column+1)//3
    rgb=im[:,lo:hi]
    # Neutral studio backdrop surrounds warm skin. Keep the single continuous head.
    mask=(rgb[:,:,0]-rgb[:,:,2]>17)&(rgb[:,:,0]-rgb[:,:,1]>9)
    labels,_=ndimage.label(ndimage.binary_closing(mask,iterations=3))
    mask=ndimage.binary_fill_holes(labels==np.argmax(np.bincount(labels.ravel())[1:])+1)
    loc=np.where(mask);rows=np.arange(loc[0].min(),loc[0].max()+1)
    l=np.array([np.where(mask[j])[0].min() for j in rows]);r=np.array([np.where(mask[j])[0].max() for j in rows])
    return rows,ndimage.gaussian_filter1d(l.astype(float),1.5),ndimage.gaussian_filter1d(r.astype(float),1.5)
fr,fl,fx=bounds(0);pr,pl,px=bounds(1)
nose=np.argmin(pl[(pr>h*.32)&(pr<h*.70)])+np.flatnonzero(pr>h*.32)[0]
scale=14.8/(pr[nose]-pr[0])
rad=(fx-fl)*.5*scale
z_front=179.70-(fr-fr[0])*scale
z_side=179.70-(pr-pr[0])*scale
inner=13.2-(px-pl[nose])*scale;outer=13.2-(pl-pl[nose])*scale
pts=[];tris=[];cols=165;levels=np.linspace(max(z_side.min(),z_front.min()),179.68,132)
for iz,z in enumerate(levels):
    rx=float(np.interp(z,z_front[::-1],rad[::-1]))
    back=float(np.interp(z,z_side[::-1],inner[::-1]));front=float(np.interp(z,z_side[::-1],outer[::-1]))
    # The form exists only for placement. Keep the nose's profile bulge off the cheeks.
    mid=(front+back)*.5;ry=(front-back)*.5
    for k in range(cols):
        a=(k/cols)*2*np.pi
        c,s=np.cos(a),np.sin(a)
        y=mid+ry*np.sign(c)*abs(c)**.94
        if z<170 and c>0:y-=min(2.,max(0,front-9.4))*abs(s)**.8*c
        pts.append([rx*s,y,z])
        if iz:
            i=iz*cols+k;j=iz*cols+(k+1)%cols
            tris.extend([[i-cols,i,j],[j,j-cols,i-cols]])
top=len(pts);top_ring=np.asarray(pts[-cols:])
pts.append([0.,float(top_ring[:,1].mean()),179.70])
for k in range(cols):tris.append([top,top-cols+k,top-cols+(k+1)%cols])
np.savez_compressed(OUT/'surface.npz',p=pts,tri=tris)
(OUT/'fit.json').write_text(json.dumps({'rigid_head_index':9,'fit':'Orthographic design gauge only; the runtime groom is rebuilt on the commissioned Meshy head.'},indent=2))
