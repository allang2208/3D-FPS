"""Fit an existing held pose with bounded rigid and flexion-only adjustments."""
import json,numpy as np
from pathlib import Path
from scipy.optimize import least_squares
from scipy.interpolate import RegularGridInterpolator
from scipy.spatial.transform import Rotation
O=Path(__file__).parent;d=json.loads((O/'grip_input.json').read_text(encoding='utf-8'));pad=json.loads((O/'trigger_pad.json').read_text())
fields=np.load(O/'contact_fields.npz');axes=tuple(fields[k] for k in ('x','y','z'))
body=RegularGridInterpolator(axes,fields['M870_body'],bounds_error=False,fill_value=.1)
trigger=RegularGridInterpolator(axes,fields['M870_trigger'],bounds_error=False,fill_value=.1)
rest={n:np.array(m) for n,m in d['rest'].items()};base={n:np.array(m) for n,m in d['reference_hand'].items()};parent=d['parents'];names=list(base)
local={n:np.linalg.inv(base[parent[n]])@m for n,m in base.items() if n!='hand_r'}
chosen=sorted(set(d['hand_ids']+pad['vertices']));ids=np.array(chosen)
verts=np.c_[np.array(d['native_points'])[ids],np.ones(len(ids))];weights=np.array([[d['weights'][i].get(n,0) for i in ids] for n in names])
inverses={n:np.linalg.inv(rest[n]) for n in names}
pad_ids=[chosen.index(i) for i in pad['vertices']];pad_targets=np.array(pad['targets'])+np.array(pad['normals'])*.0008
variables=[];joint_axes={}
for word in ('thumb','index','middle','ring','pinky'):
 ps=[base[f'{word}_{j:02d}_r'][:3,3] for j in (1,2,3)]
 a=ps[1]-ps[0];b=ps[2]-ps[1];normal=np.cross(a,b);normal/=np.linalg.norm(normal)
 for j in (1,2,3):
  n=f'{word}_{j:02d}_r';joint_axes[n]=base[n][:3,:3].T@normal;variables.append(n)
limits=np.deg2rad([({'middle_01_r':25,'middle_02_r':22,'middle_03_r':12}.get(n,12 if '_01_' in n else 10 if '_02_' in n else 8)) for n in variables])
lo=np.r_[[-.035]*3,[-np.deg2rad(18)]*3,-limits];hi=-lo

def pose(x):
 root=base['hand_r'].copy();rot=Rotation.from_rotvec(x[3:6]).as_matrix();root[:3,:3]=rot@root[:3,:3];root[:3,3]+=x[:3]
 row={'hand_r':root};angle=dict(zip(variables,x[6:]))
 for n in names:
  if n=='hand_r':continue
  m=local[n].copy()
  if n in angle:m[:3,:3]=m[:3,:3]@Rotation.from_rotvec(joint_axes[n]*angle[n]).as_matrix()
  row[n]=row[parent[n]]@m
 return row

def skin(row,vi=verts,w=weights):
 p=np.zeros((len(vi),3))
 for j,n in enumerate(names):p+=(vi@(row[n]@inverses[n]).T)[:,:3]*w[j,:,None]
 return p

groups={}
for word in ('thumb','index','middle','ring','pinky'):
 groups[word]=np.array([j for j,i in enumerate(ids) if sum(d['weights'][i].get(f'{word}_{k:02d}_r',0) for k in (2,3))>.85])
groups['palm']=np.array([j for j,i in enumerate(ids) if d['weights'][i].get('hand_r',0)+sum(d['weights'][i].get(f'{w}_metacarpal_r',0) for w in ('index','middle','ring','pinky'))>.7])
def residual(x):
 p=skin(pose(x));bd=body(p);td=trigger(p[groups['index']]);terms=[]
 terms.append(np.minimum(bd-.0003,0)*1000*3)
 terms.append(np.minimum(td-.0002,0)*1000*.8)
 terms.append(((p[pad_ids]-pad_targets)*1000*4).ravel())
 for word in ('thumb','middle','ring','pinky','palm'):
  vals=bd[groups[word]];near=vals[np.argsort(abs(vals-.0008))[:6]]
  terms.append((near-.0008)*1000*.5)
 terms.extend((x[:3]/.020*.6,x[3:6]/.25*.6,x[6:]/limits*.75))
 return np.concatenate(terms)
previous=json.loads((O/'grip_fit.json').read_text())
x0=np.r_[np.array(previous['whole_hand_translation_mm'])/1000,np.deg2rad(previous['whole_hand_rotvec_deg']),[np.deg2rad(previous['joint_flexion_delta_deg'].get(n,0)) for n in variables]];x0=np.clip(x0,lo+1e-8,hi-1e-8)
fit=least_squares(residual,x0,bounds=(lo,hi),max_nfev=180,diff_step=.0005,ftol=1e-6,xtol=1e-6,gtol=1e-6)
row=pose(fit.x);allids=np.array(d['hand_ids']);vv=np.c_[np.array(d['native_points'])[allids],np.ones(len(allids))];ww=np.array([[d['weights'][i].get(n,0) for i in allids] for n in names]);points=skin(row,vv,ww);bd=body(points)
report={'reference':'Original UC M870 Idle evaluated pose; fixed native bind mapping from ReloadSource','whole_hand_translation_mm':(fit.x[:3]*1000).tolist(),'whole_hand_rotvec_deg':np.rad2deg(fit.x[3:6]).tolist(),'joint_flexion_delta_deg':dict(zip(variables,np.rad2deg(fit.x[6:]).tolist())),'joint_axes':{n:a.tolist() for n,a in joint_axes.items()},'hand_world':{n:m.tolist() for n,m in row.items()},'cost':float(fit.cost),'evaluations':fit.nfev,'fit_status':str(fit.message),'contact_pad_mean_error_mm':float(np.mean(np.linalg.norm(skin(row)[pad_ids]-pad_targets,axis=1))*1000),'stock_surface_min_mm':float(np.min(bd)*1000),'stock_vertices_below_minus2mm':int(np.sum(bd<-.002)),'runtime_tested':False}
(O/'grip_fit.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print(json.dumps({k:v for k,v in report.items() if k not in ('hand_world','joint_axes')},indent=2))
