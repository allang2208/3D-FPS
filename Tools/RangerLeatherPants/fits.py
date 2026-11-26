"""Derive short/tall boot fits with one shared deformation for all garment layers."""
import copy,json
from pathlib import Path
import numpy as np
from scipy.ndimage import maximum_filter1d,gaussian_filter1d
P=Path('D:/FPS3D/FPSGAME');R=Path(globals().get('ROOT_OVERRIDE',P/'SourceAssets/RangerLeatherPants20261021'));A=R/'Authored/ue_leather_pants'
source=json.loads((A/'Jason.json').read_text());original=np.array(source['positions'])
def profile(z,kind):
    if kind=='HighBootsFit':
        levels=[4,8,12,18,24,30,36,40]
        fields=[[14.8,14.8,14.65,14.1,13.7,13.1,12.7,12.1],[-2.45,-2.45,-2.65,-2.75,-2.95,-2.8,-2.35,-1.5],[3.79,3.79,3.39,4.09,5.29,6.04,5.79,5.69],[5.19,5.19,4.59,4.64,5.19,5.99,6.19,6.19]]
    else:
        levels=[4,8,12,18,22,27];fields=[[14.8,14.8,14.65,14.1,13.9,13.5],[-2.45,-2.45,-2.65,-2.75,-2.95,-2.8],[3.8,3.8,3.55,4.1,4.4,5.3],[4.6,4.6,4.55,4.95,5.3,6.2]]
    return [np.interp(z,levels,x) for x in fields]
reports=[]
for kind in ('ShortBootsFit','HighBootsFit'):
    cx,cy,rx,ry=profile(original[:,2],kind);sgn=np.where(original[:,0]>=0,1.,-1.);radius=np.hypot((original[:,0]-sgn*cx)/rx,(original[:,1]-cy)/ry)
    grid=np.arange(0,48.5,.5);envelope=[]
    for z in grid:
        near=radius[abs(original[:,2]-z)<1.15];envelope.append(max(1.,float(near.max())) if len(near) else 1.)
    envelope=gaussian_filter1d(maximum_filter1d(np.array(envelope),size=7),1.)
    top,span=(43.,5.) if kind=='HighBootsFit' else (27.,6.)
    def deform(p):
        out=p.copy();z=p[:,2];sgn=np.where(p[:,0]>=0,1.,-1.);cx,cy,rx,ry=profile(z,kind);limit=np.interp(z,grid,envelope);top,span=(43.,5.) if kind=='HighBootsFit' else (27.,6.)
        blend=np.clip((top-z)/span,0,1);blend=blend*blend*(3-2*blend);scale=1+(np.minimum(1,.96/limit)-1)*blend
        out[:,0]=sgn*cx+(p[:,0]-sgn*cx)*scale;out[:,1]=cy+(p[:,1]-cy)*scale;return out
    d=copy.deepcopy(source);d['profile']='Jason_'+kind;d['positions']=deform(original).tolist();eps=.002;jac=np.empty((len(original),3,3))
    for axis in range(3):
        delta=np.zeros(3);delta[axis]=eps;jac[:,:,axis]=(deform(original+delta)-deform(original-delta))/(2*eps)
    nmat=np.linalg.inv(jac).transpose(0,2,1);faces=np.array(d['triangles']);ns=np.einsum('fcij,fcj->fci',nmat[faces],np.array(d['normals']));ns/=np.maximum(np.linalg.norm(ns,axis=2,keepdims=True),1e-12);d['normals']=ns.tolist()
    d['contract']+='; '+kind+': fitted original native boot envelope; shared cloth/leather/stitch/lining deformation'
    (A/(d['profile']+'.json')).write_text(json.dumps(d,separators=(',',':')),encoding='utf-8');reports.append(dict(profile=d['profile'],top_cm=top,blend_cm=span,triangles=len(d['triangles'])))
    print('RANGER_TROUSER_FIT',kind,flush=True)
(R/'fits.json').write_text(json.dumps(dict(completed=True,variants=reports,runtime_tested=False),indent=2),encoding='utf-8')
