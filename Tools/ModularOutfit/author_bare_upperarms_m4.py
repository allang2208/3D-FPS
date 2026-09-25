"""Fair the V4 clothing surface into bare upper arms, keeping native binding.

Only positions and local smooth normals change. Distal forearms, wrists, hands,
vertex weights, face winding, UVs and the skeleton remain the accepted source.
"""
import json
from pathlib import Path
import numpy as np
from scipy.spatial import cKDTree
from scipy.interpolate import CubicSpline

BASE=Path('D:/FPS3D/FPSGAME/SourceAssets/ModularOutfit20260924/OriginalShapeBareM4')
SOURCE=BASE/'WristContourV4';ROOT=BASE/'BareUpperArmsV6'
ROOT.mkdir(parents=True,exist_ok=True)
original=json.loads((SOURCE/'M4_original.json').read_text())
shape=json.loads((SOURCE/'M4_bare_shape.json').read_text())
if original.get('surface_winding')!='ue_native':
    raise RuntimeError('The accepted, corrected V4 mesh is required')
P=np.asarray(shape['positions']);T=np.asarray(original['triangles']);M=np.asarray(shape['triangle_materials'])
result=P.copy();influence=np.zeros(len(P))
arm=np.zeros(len(P),bool);arm[T[M<2].ravel()]=True
hand=np.zeros(len(P),bool);hand[T[M==2].ravel()]=True
arm&=~hand

def unit(v):return v/np.maximum(np.linalg.norm(v,axis=-1,keepdims=True),1e-12)
def smooth(a,b,x):
    t=np.clip((x-a)/(b-a),0,1);return t*t*t*(t*(t*6-15)+10)
def fourier(theta):
    return np.stack([theta*0+1]+[f(k*theta) for k in range(1,4) for f in (np.cos,np.sin)],axis=-1)

report={'source':str(SOURCE),'method':'Low-frequency periodic radial fairing along the original shoulder-elbow-wrist chain',
        'topology_changed':False,'weights_changed':False,'animation_changed':False,'runtime_tested':False,'sides':[]}
for side in ('l','r'):
    shoulder,elbow,wrist=[np.asarray(original['bones'][n+'_'+side]['position']) for n in ('upperarm','lowerarm','hand')]
    length=np.linalg.norm(elbow-shoulder);lower_length=np.linalg.norm(wrist-elbow)
    upper=unit(elbow-shoulder);lower=unit(wrist-elbow)
    bend=unit(lower-upper*np.dot(upper,lower));lateral=unit(np.cross(upper,bend))

    def centre(s):
        s=np.asarray(s);t=np.clip((s-length+6)/12,0,1)
        a=elbow-upper*6;b=elbow;c=elbow+lower*6
        curve=(1-t[:,None])**2*a+2*t[:,None]*(1-t[:,None])*b+t[:,None]**2*c
        tangent=(1-t[:,None])*upper+t[:,None]*lower
        curvature=np.broadcast_to((lower-upper)/12,curve.shape).copy()
        before=s<length-6;after=s>length+6
        curve[before]=shoulder+s[before,None]*upper
        curve[after]=elbow+(s[after,None]-length)*lower
        tangent[before]=upper;tangent[after]=lower
        curvature[before|after]=0
        return curve,tangent,curvature

    ids=np.flatnonzero(arm&((P[:,0]<0) if side=='l' else (P[:,0]>0)))
    positions=P[ids]
    grid=np.linspace(-10,length+lower_length+2,1500)
    samples=centre(grid)[0]
    s=grid[cKDTree(samples).query(positions)[1]]
    for _ in range(3):
        c,d,dd=centre(s);offset=positions-c
        s+=np.clip(np.sum(offset*d,axis=1)/np.maximum(np.sum(d*d,axis=1)-np.sum(offset*dd,axis=1),.3),-.12,.12)
    c,d,_=centre(s);tangent=unit(d)
    front=unit(bend-tangent*np.sum(tangent*bend,axis=1,keepdims=True))
    across=unit(np.cross(tangent,front))
    offset=positions-c;u=np.sum(offset*front,axis=1);v=np.sum(offset*across,axis=1)
    theta=np.arctan2(v,u);radius=np.sqrt(u*u+v*v)

    # Equal-sized surface cells keep dense stitched seams from dominating the
    # fit. Three angular harmonics keep broad anatomy, not garment wrinkles.
    bins=np.stack((np.floor(s/.75),np.floor((theta+np.pi)/.15)),axis=1).astype(int)
    _,group=np.unique(bins,axis=0,return_inverse=True)
    rows=[]
    for g in np.unique(group):
        mask=(group==g)&(radius>1)
        if mask.any():rows.append([s[mask].mean(),np.arctan2(np.sin(theta[mask]).mean(),np.cos(theta[mask]).mean()),np.median(radius[mask])])
    rows=np.asarray(rows);X=fourier(rows[:,1]);r=rows[:,2]
    stations=np.arange(-8,length+16,.75);coefficients=[]
    for station in stations:
        window=np.exp(-.5*((rows[:,0]-station)/2.3)**2)
        weight=window.copy();coef=np.zeros(7)
        for _ in range(4):
            penalty=np.diag([.002,.025,.025,.15,.15,.5,.5])
            coef=np.linalg.solve((X.T*weight)@X+penalty,(X.T*weight)@r)
            residual=r-X@coef
            weight=window/(1+(residual/.48)**2)
        coefficients.append(coef)
    fitted=np.sum(fourier(theta)*CubicSpline(stations,np.asarray(coefficients))(s),axis=1)

    # Remove the clothing allowance, then author restrained muscle/bone forms.
    cloth_allowance=.72*(1-smooth(length-5,length+8,s))+.24*np.exp(-((s-1)/6)**2)
    target=fitted-cloth_allowance
    anterior=np.clip(np.cos(theta),0,1);posterior=np.clip(-np.cos(theta),0,1)
    sidewall=np.abs(np.sin(theta))
    target+=.26*np.exp(-((s-12.5)/6.5)**2)*anterior**3
    target+=.20*np.exp(-((s-13.5)/8)**2)*posterior**3
    target+=.18*np.exp(-((s-2)/5)**2)*sidewall**3
    target-=.07*np.exp(-((s-6)/1.9)**2)*sidewall**4
    target+=.17*np.exp(-((s-length-.6)/1.8)**2)*posterior**5
    target-=.08*np.exp(-((s-length)/.75)**2)*anterior**5
    target=np.maximum(target,2.4)
    envelope=smooth(-6.6,-2.8,s)*(1-smooth(length+7,length+13,s))
    envelope*=smooth(.6,2.1,radius)
    change=np.clip(target-radius,-2.0,1.0)*envelope*.97
    radial=unit(front*u[:,None]+across*v[:,None])
    result[ids]+=radial*change[:,None]
    influence[ids]=envelope
    report['sides'].append({'side':side,'upper_bone_length_cm':float(length),
        'author_vertices':int(np.count_nonzero(np.abs(change)>1e-7)),
        'max_inward_cm':float(max(0,-change.min())),'max_outward_cm':float(max(0,change.max())),
        'distal_transition_cm_from_elbow':[7,13],'uniform_surface_samples':len(rows),
        'shoulder_origin_cm':shoulder.tolist(),'elbow_origin_cm':elbow.tolist(),'wrist_origin_cm':wrist.tolist()})

# Rebuild smooth geometry normals in the former cloth region. Keep every
# original corner normal on the accepted distal forearms, wrists and hands.
corners=result[T];face=-unit(np.cross(corners[:,1]-corners[:,0],corners[:,2]-corners[:,0]))
norm=np.zeros_like(P)
for k in range(3):
    a=unit(corners[:,(k+1)%3]-corners[:,k]);b=unit(corners[:,(k+2)%3]-corners[:,k])
    angle=np.arccos(np.clip(np.sum(a*b,axis=1),-1,1))
    np.add.at(norm,T[:,k],face*angle[:,None])
norm=unit(norm)
oldnorm=np.asarray(shape['normals']);blend=influence[T,None]
normal=np.where(blend>0,unit(oldnorm*(1-blend)+norm[T]*blend),oldnorm)
shape['positions']=result.tolist();shape['normals']=normal.tolist()
shape['geometry_policy']={**shape.get('geometry_policy',{}),
    'upperarms_v6':'Clothing volume and folds faired into restrained upper-arm/elbow forms; original topology, UVs and weights retained',
    'distal_preservation':'V4 distal forearm, wrist and all hand vertices are untouched'}
original['positions']=shape['positions'];original['normals']=shape['normals']
for name,data in [('M4_original.json',original),('M4_bare_shape.json',shape),('upperarm_authoring.json',report)]:
    (ROOT/name).write_text(json.dumps(data,indent=2 if name.startswith('upperarm') else None,separators=None if name.startswith('upperarm') else (',',':')))
print('M4_BARE_UPPERARMS_AUTHORED',sum(r['author_vertices'] for r in report['sides']))
