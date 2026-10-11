"""Scoped source checks for the user's wrist/idle/bolt screenshots, not PIE."""
import json
from pathlib import Path
import numpy as np
from scipy.interpolate import RegularGridInterpolator
from repair_core import O,g,rest,ri,rack_time
src=json.loads((O/'source_poses.json').read_text());new=json.loads((O/'repaired_poses.json').read_text());families=json.loads((O/'family_repaired_poses.json').read_text())
mesh=g['meshes']['Super90_V7_M4_BareArmsV6'];weights=mesh['weights'];vertices=np.c_[mesh['positions'],np.ones(len(mesh['positions']))]
groups={}
for n in rest:
    ids=np.array([i for i,w in enumerate(weights) if w.get(n,0)>1e-5])
    if len(ids):groups[n]=(ids,np.array([weights[i][n] for i in ids]),vertices[ids]@ri[n].T)
digits=[n for n in rest if n.endswith('_l') and n.startswith(('thumb','index','middle','ring','pinky'))]
hand=np.array([i for i,w in enumerate(weights) if sum(v for n,v in w.items() if n in digits or n=='hand_l')>.98])
station=(vertices[:,:3]-rest['lowerarm_l'][:3,3])@(rest['hand_l'][:3,3]-rest['lowerarm_l'][:3,3])/np.linalg.norm(rest['hand_l'][:3,3]-rest['lowerarm_l'][:3,3])**2
wrist=np.array([i for i,w in enumerate(weights) if .7<station[i]<1.12 and sum(v for n,v in w.items() if n.endswith('_l'))>.98])
grid=np.load(O/'receiver_surface.npz');lookup=RegularGridInterpolator((grid['ys'],grid['zs']),grid['surface'],bounds_error=False,fill_value=-1.)
def skin(raw):
    p={n:np.array(m) for n,m in raw.items()};points=np.zeros((len(vertices),3));linear=np.zeros((len(vertices),3,3))
    for n,(ids,w,local) in groups.items():
        points[ids]+=(local@p[n].T)[:,:3]*w[:,None]
        linear[ids]+=(p[n]@ri[n])[:3,:3]*w[:,None,None]
    return p,points,linear
report=dict(scope='Offline native skin / receiver-side clearance; no game run',wrist_samples=[],receiver=[])
for f in (0,85,92,100,110,126):
    row=dict(frame=f)
    for tag,data in (('before',src),('after',new)):
        _,_,linear=skin(data['empty'][f]);sv=np.linalg.svd(linear[wrist],compute_uv=False)[:,-1]
        row[tag+'_wrist_min_singular']=np.percentile(sv,[0,5,50]).tolist()
    report['wrist_samples'].append(row)
for fam,data in [('base',new),*families.items()]:
    for branch in ('empty','cycle'):
        samples=[]
        for f,raw in enumerate(data[branch]):
            t=rack_time(branch,f)
            if not 26<=t<=51:continue
            p,points,_=skin(raw);gi=np.linalg.inv(p['WPN_root']@ri['WPN_root']);v=(np.c_[points[hand],np.ones(len(hand))]@gi.T)[:,:3]
            inside=np.maximum(0,lookup(v[:,1:3])-v[:,0])*1000
            samples.append((float(inside.max()),f,float(t),int((inside>.5).sum())))
        worst=max(samples);report['receiver'].append(dict(family=fam,branch=branch,worst_mm=worst[0],frame=worst[1],rack_time=worst[2],vertices_over_half_mm=worst[3]))
(O/'source_defect_report.json').write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2),flush=True)
