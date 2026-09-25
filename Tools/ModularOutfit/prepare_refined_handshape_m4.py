"""Refit the non-contact hand dorsum as a broad skin surface, not glove padding."""
import json
from pathlib import Path
import numpy as np
BASE=Path('D:/FPS3D/FPSGAME/SourceAssets/ModularOutfit20260924/OriginalShapeBareM4')
ROOT=BASE/'RefinedSkinV3';ROOT.mkdir(exist_ok=True)
source=json.loads((BASE/'M4_original.json').read_text());shape=json.loads((BASE/'SmoothSkinV2/M4_bare_shape.json').read_text())
P=np.asarray(shape['positions']);T=np.asarray(source['triangles']);mat=np.asarray(shape['triangle_materials'])
N=np.zeros_like(P);count=np.zeros(len(P))
for k in range(3):
    np.add.at(N,T[:,k],np.asarray(shape['normals'])[:,k]);np.add.at(count,T[:,k],1)
N/=np.maximum(np.linalg.norm(N,axis=1,keepdims=True),1e-10)
def smooth(a,b,x):
    t=np.clip((x-a)/(b-a),0,1);return t*t*(3-2*t)
def design(t,y):
    t=t/10;y=y/5
    return np.stack((t*0+1,t,y,t*t,t*y,y*y,t*t*t,t*t*y,t*y*y,y*y*y),axis=-1)
reports=[]
for side in ('l','r'):
    frame=shape['anatomy'][side];forward=np.asarray(frame['forward']);dorsal=np.asarray(frame['dorsal'])
    across=np.cross(dorsal,forward);across/=np.linalg.norm(across)
    if across@frame['across']<0:across=-across
    q=P-frame['wrist'];t=q@forward;y=q@across;z=q@dorsal;facing=N@dorsal
    side_mask=P[:,0]<0 if side=='l' else P[:,0]>0
    hand=np.asarray(shape['hand_vertices'])&side_mask
    thumb=np.asarray([sum(v for n,v in w.items() if n.startswith('thumb_')) for w in source['weights']])
    selected=hand&(t>.8)&(t<10.5)&(facing>.60)&(thumb<.1)
    ids=np.flatnonzero(selected)
    # Equal spatial sampling prevents the dense embossed loops biasing the fit.
    cell=np.floor(np.stack((t[ids],y[ids]),axis=-1)/.30).astype(int)
    _,groups=np.unique(cell,axis=0,return_inverse=True)
    samples=[]
    for group in np.unique(groups):
        idx=ids[groups==group];samples.append([np.mean(t[idx]),np.mean(y[idx]),np.quantile(z[idx],.3)])
    samples=np.asarray(samples);X=design(samples[:,0],samples[:,1]);Z=samples[:,2]
    w=np.ones(len(Z));coef=np.zeros(X.shape[1])
    for _ in range(8):
        coef=np.linalg.solve((X.T*w)@X+np.eye(X.shape[1])*.008,(X.T*w)@Z)
        residual=Z-X@coef;w=1/(1+(residual/.18)**2)
        w*=np.where(residual>0,.6,1.)
    target=design(t,y)@coef
    # A shallow native metacarpal contour replaces embossed glove decorations.
    for stem in ('index','middle','ring','pinky'):
        joint=np.asarray(source['bones'][stem+'_01_'+side]['position'])-frame['wrist']
        target+=.065*np.exp(-((t-joint@forward)/.8)**2-((y-joint@across)/.55)**2)
    blend=smooth(.10,.68,facing)*smooth(1.2,2.6,t)*(1-smooth(9.1,10.4,t))*hand*(1-smooth(.1,.4,thumb))
    change=np.clip(target-z,-.65,.30)*blend
    P+=change[:,None]*dorsal
    reports.append({'side':side,'surface_fit_samples':len(samples),'changed':int(np.count_nonzero(np.abs(change)>.00001)),
                    'max_refit_cm':float(np.max(np.abs(change)))})
shape['positions']=P.tolist()
shape['geometry_policy']={'hand_back':'broad quadratic/cubic envelope, original contacts retained',
 'wrist':'remove old cuff span and loft a continuous skin transition',
 'original_skeleton':True,'original_grip_vertices':True,'wrist_weights':'interpolated from original cut boundaries'}
(ROOT/'hand_refit.json').write_text(json.dumps(shape,separators=(',',':')))
(ROOT/'refit_authoring.json').write_text(json.dumps(reports,indent=2))
print('M4_HAND_BACK_REFIT_AUTHORED')
