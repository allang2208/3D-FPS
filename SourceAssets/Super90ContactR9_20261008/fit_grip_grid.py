import os
os.environ['OPENBLAS_NUM_THREADS']='1'
import sys,json,numpy as np
from pathlib import Path
O=Path(__file__).parent;sys.path.insert(0,str(O/'pydeps'));import igl
from scipy.spatial.transform import Rotation
from scipy.spatial import ConvexHull
from scipy.ndimage import map_coordinates
from scipy.optimize import least_squares
D=np.load(O/'fit_inputs.npz');names=D['names'].tolist();ix={n:i for i,n in enumerate(names)};rest=D['rest'];ri=np.linalg.inv(rest);parents=D['parents'];vs=D['vertices'];ws=D['weights'];idle=D['idle']
digits=D['finger_names'].tolist();selected=['hand_l']+digits;ids=np.flatnonzero(ws[:,[ix[n] for n in selected]].sum(axis=1)>.995);v=vs[ids];w=ws[ids];dominant=np.argmax(w,axis=1)
weighted={n:np.flatnonzero(w[:,ix[n]]>1e-6) for n in selected};pre={n:v[weighted[n]]@ri[ix[n]].T for n in selected}
seeds=json.loads((O/'grip_hand_seeds.json').read_text());parts=json.loads((O/'Diagnostics/foregrip_geometry.json').read_text());gun=np.load(O/'gun_idle_mesh.npz');mount=idle[ix['WPN_root']]@ri[ix['WPN_root']]
def matrices(h,local):
 p={'hand_l':h}
 for n in digits:p[n]=p[names[parents[ix[n]]]]@local[n]
 return p
def skin(p):
 out=np.zeros((len(ids),3))
 for n in selected:
  j=ix[n];vi=weighted[n];out[vi]+=(pre[n]@p[n].T)[:,:3]*w[vi,j,None]
 return out

out={};candidates=[seeds]+[json.loads((O/f).read_text()) for f in ('grip_hand_fits.json','grip_hand_fits3.json')]
for family in seeds:
 field=np.load(O/('grip_sdf_'+family+'.npz'));grid=field['values'].astype(float);origin=field['origin'];step=field['step']
 def sdf(pp):return map_coordinates(grid,((pp-origin)/step).T,order=1,mode='nearest')
 best=None
 for ci,candidate in enumerate(candidates):
  row=candidate[family];h=np.array(row['hand']);loc={n:np.array(m) for n,m in row['local'].items()};points=skin(matrices(h,loc));active=points[::3]
  for x in np.arange(-.03,.031,.005):
   for y in np.arange(-.03,.031,.005):
    for z in np.arange(-.03,.031,.005):
     offset=np.array((x,y,z));d=sdf(active+offset);pen=np.minimum(d-.002,0);score=np.linalg.norm(pen)*1000+np.linalg.norm(offset)*.1
     if best is None or score<best[0]:best=(score,ci,offset)
 ci=best[1];offset=best[2];row=candidates[ci][family];h=np.array(row['hand']);h[:3,3]+=offset;loc={n:np.array(m) for n,m in row['local'].items()};d=sdf(skin(matrices(h,loc)))
 out[family]={'hand':h.tolist(),'local':{n:m.tolist() for n,m in loc.items()},'inside_vertices':int(sum(d<0)),'min_mm':float(min(d)*1000),'seed':ci,'offset':offset.tolist()};print('GRIP_GRID',family,ci,offset,'inside',sum(d<0),'min',d.min()*1000,flush=True);(O/'grip_hand_grid.json').write_text(json.dumps(out,indent=2))
