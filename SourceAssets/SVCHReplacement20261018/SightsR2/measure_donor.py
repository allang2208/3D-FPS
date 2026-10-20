"""Measure physical aperture and post from the existing detailed sight geometry."""
import json,numpy as np,trimesh
from scipy.ndimage import label
from pathlib import Path
O=Path(__file__).parent;P=O.parents[2]
raw=np.load(O/'donor_geometry.npz');data=json.loads((P/'SourceAssets/HK416Reworked20260930/authoring.json').read_text());D=np.array(data['root_matrix'])@np.array(data['source_to_weapon_root']);v=(np.c_[raw['v'],np.ones(len(raw['v']))]@np.linalg.inv(D).T)[:,:3]*400;t=raw['t'];rear=t[(v[t,1]<0).all(1)];front=t[(v[t,1]>0).all(1)]
m=trimesh.Trimesh(v,rear,process=True);m.remove_unreferenced_vertices()
xs=np.linspace(-.55,.55,221);zs=np.linspace(14.10,15.20,221);origins=np.array([[x,-12,z] for z in zs for x in xs]);dirs=np.tile([0,1,0],(len(origins),1));hits=m.ray.intersects_any(origins,dirs).reshape(len(zs),len(xs));ids,n=label(~hits);regions=[]
for i in range(1,n+1):
 z,x=np.where(ids==i)
 if len(z)<8 or min(z)==0 or max(z)==len(zs)-1 or min(x)==0 or max(x)==len(xs)-1:continue
 regions.append({'area':len(z),'center':[float(xs[x].mean()),float(zs[z].mean())],'bounds':[[float(xs[x].min()),float(zs[z].min())],[float(xs[x].max()),float(zs[z].max())]]})
print('APERTURES',regions,flush=True)
f=trimesh.Trimesh(v,front,process=True);f.remove_unreferenced_vertices();post=f.vertices[np.abs(f.vertices[:,0])<.15];tip=post[np.argmax(post[:,2])]
result={'donor_to_source_cm':(np.diag([400,400,400,1])@np.linalg.inv(D)).tolist(),'rear_apertures':regions,'front_post_tip_source_cm':tip.tolist(),'source_triangle_count':len(t),'rear_triangles':len(rear),'front_triangles':len(front)}
if not regions:raise RuntimeError('No through aperture in the source rear sight')
r=max(regions,key=lambda r:r['area']);result['rear_center_source_cm']=[*r['center'][:1],-9.82,r['center'][1]]
(O/'donor_measurements.json').write_text(json.dumps(result,indent=2));print(json.dumps(result),flush=True)
