from pathlib import Path
O=Path(__file__).parent
exec((O/'solve_natural_contact.py').read_text().split('lo=np.array')[0])
from scipy.spatial import cKDTree
import trimesh
meshdata=np.load(O/'grip_surface.npz');mesh=trimesh.Trimesh(meshdata['vertices'],meshdata['faces'],process=False)
v,f=trimesh.remesh.subdivide_to_size(mesh.vertices,mesh.faces,max_edge=.001,max_iter=8)
tri=v[f];norm=np.cross(tri[:,1]-tri[:,0],tri[:,2]-tri[:,0]);norm/=np.maximum(np.linalg.norm(norm,axis=1,keepdims=True),1e-12)
surf=tri.mean(axis=1);tree=cKDTree(surf)
print('SURFACE',len(surf),mesh.is_watertight,flush=True)
def sdf(points):
 dist,nearest=tree.query(points,workers=1);signed=np.einsum('ij,ij->i',points-surf[nearest],norm[nearest]);return np.where(signed<0,-dist,dist)
seed=np.array(json.loads((O/'natural_solution.json').read_text())['parameters'])
def objective(x):
 p=np.einsum('bij,bnj->ni',pose(x)[active],pre)[:,:3];sd=sdf(p);out=[np.minimum(sd-.001,0)*6500]
 for d in digits:
  for j,ids in enumerate(seg[d]):out.append(np.array([(np.sort(sd[ids])[:4].mean()-.0015)*(500 if j else 200)]))
 for ids in [palm,seg['thumb'][2]]:out.append(np.array([(np.sort(sd[ids])[:4].mean()-.003)*180]))
 for a,b in zip(digits,digits[1:]):
  gap=(p[di[a]]@row).min()-(p[di[b]]@row).max();out.append(np.array([min(gap-.0007,0)*3500]))
 out.extend([(x[:3]-seed[:3])*.04,(x[3:6]-seed[3:6])*.08,(x[6:]-seed[6:])*.025]);return np.concatenate(out)
lo=np.array([-30,-30,-25]+[-20]*3+[-15,-55,-55,-18]*4,float);hi=np.array([30,30,25]+[20]*3+[15,55,45,18]*4,float)
x=seed
for attempt in range(3):
 r=least_squares(objective,x,bounds=(lo,hi),max_nfev=350,diff_step=.008,ftol=1e-5,xtol=1e-5,gtol=1e-5);x=r.x
 print('EXACT_FIT',attempt,np.linalg.norm(r.fun),x.tolist(),flush=True)
 (O/'natural_solution.json').write_text(json.dumps({'parameters':x.tolist(),'pose':{n:pose(x)[i].tolist() for i,n in enumerate(names)}},indent=2))
