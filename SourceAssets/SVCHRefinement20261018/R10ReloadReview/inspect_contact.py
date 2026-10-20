"""Inspect the hand-side surface, using winding for an open shell rather than face signs alone."""
import json
from pathlib import Path
import numpy as np
import trimesh
O=Path(__file__).parent;R9=O.parent/'R9ReloadGrip'
env={'__file__':str(R9/'author_reload_grip.py')}
exec(compile((R9/'author_reload_grip.py').read_text().split("report={'method'")[0],str(R9/'author_reload_grip.py'),'exec'),env)
globals().update({k:v for k,v in env.items() if k not in ('O','__file__','__builtins__')})
profile=json.loads((O/'profile_native_registration.json').read_text());clip=motion['clips']['reload'];base=np.asarray(clip['frames'][220])
layer=next(c for c in profile['clips'] if c['base']==clip['path']);pose=comp(matrices(old_pose(base,layer,clip['times'][220])))
mag_inv=np.linalg.inv(rigid(pose[MAG]));allskin=points(mag_inv,skin(pose,np.arange(len(AV))))
local=allskin[HANDIDS]
mesh=trimesh.Trimesh(vertices=mag['svch'][0],faces=mag['svch'][1],process=True);mesh.fix_normals(multibody=True)
q,d,faces=trimesh.proximity.closest_point(mesh,local)
def winding(pts,triangles):
 out=[]
 for first in range(0,len(pts),32):
  a,b,c=(triangles[None]-pts[first:first+32,None,None,:]).transpose(2,0,1,3)
  la,lb,lc=[np.linalg.norm(v,axis=-1) for v in (a,b,c)]
  dot=lambda u,v:np.einsum('...i,...i->...',u,v)
  numerator=dot(a,np.cross(b,c));den=la*lb*lc+dot(a,b)*lc+dot(b,c)*la+dot(c,a)*lb
  out.extend(np.sum(2*np.arctan2(numerator,den),axis=1)/(4*np.pi))
 return np.asarray(out)
suspect=np.flatnonzero(d<2.5);w=winding(local[suspect],mesh.triangles)
inside=suspect[np.abs(w)>.5];trusted=suspect[np.abs(w)>.85]
details=[]
for j in inside[np.argsort(d[inside])[::-1]][:16]:
 details.append({'vertex':int(HANDIDS[j]),'bone':N[DOM[HANDIDS[j]]],'depth_mm':float(d[j]*10),'winding':float(w[np.where(suspect==j)[0][0]])})
report={'frame':220,'nearest_method':'Exact triangle AABB query','magazine_watertight':bool(mesh.is_watertight),'suspect_count':len(suspect),
        'inside_winding_gt_half':len(inside),'inside_winding_gt_085':len(trusted),'worst':details}
(O/'contact_winding.json').write_text(json.dumps(report,indent=2));print(json.dumps(report),flush=True)
tris=np.asarray(arms['triangles']);left=np.array([N[i].endswith('_l') for i in DOM]);selected=tris[left[tris].all(axis=1)]
handpos=points(mag_inv,pose[HAND:HAND+1,:3,3])[0]
selected=selected[(np.linalg.norm(allskin[selected].mean(axis=1)-handpos,axis=1)<13)]
shell=Shell(mag['svch'][0],np.array([0.,0.,1.]));fs,size=shell.frame(shell.length*.6,local.mean(0))
payload={'skin_vertices':allskin.tolist(),'skin_triangles':selected.tolist(),'mag_vertices':mag['svch'][0].tolist(),
         'mag_triangles':mag['svch'][1].tolist(),'axes':fs[:3,:3].tolist(),'focus':((local.mean(0)+mag['svch'][0].mean(0))*.5).tolist()}
(O/'contact_scene.json').write_text(json.dumps(payload,separators=(',',':')))
