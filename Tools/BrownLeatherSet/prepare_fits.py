"""Preserve leather panel thickness while fitting cuffs to short and tall boots."""
import copy,json
from pathlib import Path
import numpy as np
from scipy.ndimage import maximum_filter1d,gaussian_filter1d
R=Path('D:/FPS3D/FPSGAME/SourceAssets/BrownLeatherSet20261004')
source=json.loads((R/'Jason_LeatherPants.json').read_text());original=np.array(source['positions'])

def fit(kind):
    def profile(z):
        if kind=='HighBootsFit':
            levels=[4,8,12,18,24,30,36,40]
            fields=[[14.8,14.8,14.65,14.1,13.7,13.1,12.7,12.1],[-2.45,-2.45,-2.65,-2.75,-2.95,-2.8,-2.35,-1.5],
                    [4.45,4.45,4.05,4.75,5.95,6.7,6.45,6.35],[5.85,5.85,5.25,5.3,5.85,6.65,6.85,6.85]]
            cx,cy,rx,ry=[np.interp(z,levels,x) for x in fields];return cx,cy,rx-.66,ry-.66
        levels=[4,8,12,18,22,27]
        return tuple(np.interp(z,levels,x) for x in [[14.8,14.8,14.65,14.1,13.9,13.5],[-2.45,-2.45,-2.65,-2.75,-2.95,-2.8],
            [3.8,3.8,3.55,4.10,4.4,5.3],[4.6,4.6,4.55,4.95,5.3,6.2]])
    cx,cy,rx,ry=profile(original[:,2]);sign=np.where(original[:,0]>=0,1.,-1.)
    rad=np.sqrt(((original[:,0]-sign*cx)/rx)**2+((original[:,1]-cy)/ry)**2)
    grid=np.arange(0,48.5,.5);envelope=[]
    for z in grid:
        nearby=rad[np.abs(original[:,2]-z)<1.15];envelope.append(float(max(1.,nearby.max())) if len(nearby) else 1.)
    # One scale for each complete cross section keeps cloth, lining and seams
    # separated; it does not project all surfaces onto the same cylinder.
    envelope=gaussian_filter1d(maximum_filter1d(np.array(envelope),size=7),1.0)
    def deform(points):
        points=np.array(points,float);out=points.copy();z=points[:,2];sgn=np.where(points[:,0]>=0,1.,-1.)
        cx,cy,rx,ry=profile(z);limit=np.interp(z,grid,envelope)
        top,span=(43.,5.) if kind=='HighBootsFit' else (27.,6.)
        t=np.clip((top-z)/span,0,1);t=t*t*(3-2*t);scale=1+(np.minimum(1,.96/limit)-1)*t
        out[:,0]=sgn*cx+(points[:,0]-sgn*cx)*scale;out[:,1]=cy+(points[:,1]-cy)*scale;return out
    d=copy.deepcopy(source);d['positions']=deform(original).tolist();eps=.002;jac=np.empty((len(original),3,3))
    for axis in range(3):
        delta=np.zeros(3);delta[axis]=eps;jac[:,:,axis]=(deform(original+delta)-deform(original-delta))/(2*eps)
    normals=np.transpose(np.linalg.inv(jac),(0,2,1))
    faces=np.array(d['triangles'],int);ns=np.array(d['normals']);result=np.einsum('fcij,fcj->fci',normals[faces],ns)
    result/=np.maximum(np.linalg.norm(result,axis=2,keepdims=True),1e-12);d['normals']=result.tolist()
    d['contract']+='; '+kind+' cuff fit, panel spacing and native weights retained'
    (R/('Jason_LeatherPants_'+kind+'.json')).write_text(json.dumps(d,separators=(',',':')),encoding='utf-8')
    return dict(envelope_cm=grid.tolist(),scales=np.minimum(1,.96/envelope).tolist())
receipt={kind:fit(kind) for kind in ['ShortBootsFit','HighBootsFit']}
(R/'fit_construction.json').write_text(json.dumps(receipt,indent=2))
print('BROWN_LEATHER_CUFFS_AUTHORED',flush=True)
