"""Resolve near-face signs against the actual non-watertight receiver shell."""
import json
from pathlib import Path
import numpy as np
import trimesh
O=Path(__file__).parent;R9=O.parent/'R9ReloadGrip'
env={'__file__':str(R9/'author_reload_grip.py')}
exec(compile((R9/'author_reload_grip.py').read_text().split("report={'method'")[0],str(R9/'author_reload_grip.py'),'exec'),env)
globals().update({k:v for k,v in env.items() if k not in ('O','__file__','__builtins__')})
profile=json.loads((O/'profile_native_registration.json').read_text());clip=motion['clips']['reload']
layer=next(c for c in profile['clips'] if c['base']==clip['path'])
body_v,body_t=geom('svch',lambda n:n in ('SVCH_Body','SVCH_Polymer','SVCH_Rubber','SVCH_BarrelSteel'))
mesh=trimesh.Trimesh(vertices=body_v,faces=body_t,process=True);mesh.fix_normals(multibody=True)
surf=Surface(mesh.vertices,mesh.faces);report={}
for frame in (240,):
 base=np.asarray(clip['frames'][frame]);pose=comp(matrices(old_pose(base,layer,frame/120)))
 local=points(rest['svch'][ROOT]@np.linalg.inv(pose[ROOT]),skin(pose,HANDIDS))
 q,d,face_ids=trimesh.proximity.closest_point(mesh,local)
 suspect=np.flatnonzero(d<2.5);triangles=mesh.triangles;out=[]
 for first in range(0,len(suspect),8):
  pts=local[suspect[first:first+8]]
  a,b,c=(triangles[None]-pts[:,None,None,:]).transpose(2,0,1,3)
  la,lb,lc=[np.linalg.norm(v,axis=-1) for v in (a,b,c)]
  dot=lambda x,y:np.einsum('...i,...i->...',x,y)
  numerator=dot(a,np.cross(b,c));den=la*lb*lc+dot(a,b)*lc+dot(b,c)*la+dot(c,a)*lb
  out.extend(np.sum(2*np.arctan2(numerator,den),axis=1)/(4*np.pi))
 w=np.asarray(out);inside=suspect[np.abs(w)>.5]
 if len(inside):
  exact,depth,face_ids=trimesh.proximity.closest_point(mesh,local[inside])
  d[inside]=depth
  q[inside]=exact
 report[frame]={'suspect_count':len(suspect),'inside_count':len(inside),
  'worst':[{'vertex':int(HANDIDS[j]),'bone':N[DOM[HANDIDS[j]]],'depth_mm':float(d[j]*10),'surface_delta_reference_cm':(q[j]-local[j]).tolist()} for j in inside[np.argsort(d[inside])[::-1]][:8]]}
 print('BODY_WINDING',frame,json.dumps(report[frame]),flush=True)
(O/'body_winding.json').write_text(json.dumps(report,indent=2))
