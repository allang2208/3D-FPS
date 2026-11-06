"""Measure steel from the original image; hand labels only initialize a search tube."""
from pathlib import Path
import json
import cv2,numpy as np
from scipy.interpolate import PchipInterpolator
HERE=Path(__file__).resolve().parent
WORK=HERE.parents[2]/'Saved/RidgeMotionReview'
def unit(v):return v/max(1.e-7,np.linalg.norm(v))
def centerline(n,hilt,tip):
    mask=cv2.imread(str(WORK/'Ref'/f'{n}-mask.png'),0)
    image=cv2.imread(str(WORK/'Ref'/f'{n}.png'))
    d=unit(hilt-tip);side=np.array([-d[1],d[0]]);length=np.linalg.norm(hilt-tip)
    distances=np.arange(-28.,length*.76,1.)
    def samples(p,d,side):
        dist=np.arange(-18,19)
        pts=p+distances[:,None,None]*d+dist[None,:,None]*side
        pix=np.rint(pts).astype(int);x,y=pix[:,:,0],pix[:,:,1]
        valid=(x>=0)&(x<640)&(y>=0)&(y<360)
        x=x.clip(0,639);y=y.clip(0,359)
        return pts,valid&(mask[y,x]>0),dist
    for _ in range(2):
        pts,good,dist=samples(tip,d,side);centers=[]
        for i,s in enumerate(distances):
            if not np.clip(length*.14,6,25)<s<length*.64:continue
            ids=np.flatnonzero(good[i])
            if not len(ids):continue
            runs=np.split(ids,np.flatnonzero(np.diff(ids)>1)+1)
            group=min(runs,key=lambda r:abs(dist[r].mean()))
            if group[0]==0 or group[-1]==len(dist)-1:continue
            centers.append(pts[i,group].mean(0))
        if len(centers)<9:return None
        pts=np.array(centers)
        mid=pts.mean(0);direction=np.linalg.svd(pts-mid,full_matrices=False)[2][0]
        if direction@d<0:direction=-direction
        d=direction;side=np.array([-d[1],d[0]])
        tip=tip+side*((mid-tip)@side)
    _,good,dist=samples(tip,d,side)
    on=good[:,np.abs(dist)<=2].any(1)
    hits=np.flatnonzero(np.convolve(on.astype('int'),np.ones(5,dtype='int'),'valid')==5)
    if not len(hits):return None
    actual=tip+distances[hits[0]]*d
    visible=bool(3<actual[0]<637 and 3<actual[1]<357 and hits[0]>0 and distances[hits[0]]<25)
    return dict(tip=actual.tolist(),tip_visible=visible,axis=d.tolist(),axis_point=mid.tolist(),
                width=len(centers))

if __name__=='__main__':
    keys=np.loadtxt(HERE.parent/'screen.txt'); interp=PchipInterpolator(keys[:,0],keys[:,1:5]*2,axis=0)
    rows={}
    for n in range(3120,3241):
        guard,tip=interp(n).reshape(2,2);r=centerline(n,guard,tip)
        if r is not None:rows[n]=r
    (WORK/'edges.json').write_text(json.dumps(rows,indent=1))
    print(len(rows),sum(r['tip_visible'] for r in rows.values()))
