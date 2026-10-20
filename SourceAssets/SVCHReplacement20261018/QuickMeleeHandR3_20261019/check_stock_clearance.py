"""Stock/arm proximity in the actual camera frustum; candidate or saved poses."""
from pathlib import Path
import sys,json,numpy as np,trimesh
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE))
from check_surfaces import *
O=HERE;mode=sys.argv[1] if len(sys.argv)>1 else 'source'
fixture=json.loads((O/('native-'+('candidate' if mode=='source' else mode)+'.json')).read_text())['families'][0]
order=[fixture['names'].index(n) for n in names];cam=matrices([fixture['view_to_camera']])[0]
tx=np.tan(np.radians(fixture['camera_horizontal_fov']/2));ty=tx/fixture['camera_aspect']
gun=Surface(weapon);wi=ids['WPN_root'];vr=np.c_[weapon['positions'],np.ones(len(weapon['positions']))]@np.linalg.inv(matrices(weapon['reference'])[wi]).T
select=np.zeros(len(vr),bool)
for t,m in zip(weapon['triangles'],weapon['material_ids']):
    if m>=2 and m not in (5,7):select[t]=True
select &=vr[:,1]<-.17
bn=np.array([names[j] for j in bare.weights.argmax(1)]);at=np.array(arms['triangles'])
mask=np.array([sum(bn[j].endswith('_r') and bn[j].startswith(('lowerarm','upperarm')) for j in t)>=2 for t in at])
if mode=='source':rows=[(i,q,None) for i,q in enumerate(np.load(O/'poses.npz')['base'])]
else:rows=[(r['frame'],matrices(np.array(r['bones'])[order]),r['morphs']) for r in fixture['frames']]
out=[]
for fi,q,morphs in rows:
    v=bare.evaluate(q,morphs);g=gun.evaluate(q)[select]
    camera=g@cam[:3,:3].T+cam[:3,3]
    visible=(camera[:,0]>1)&(abs(camera[:,1])<camera[:,0]*tx)&(abs(camera[:,2])<camera[:,0]*ty)
    mesh=trimesh.Trimesh(v,at[mask],process=False);close,dist,tid=trimesh.proximity.closest_point(mesh,g);norm=mesh.face_normals[tid]
    A=q[ids['lowerarm_r'],:3,3];B=q[ids['hand_r'],:3,3];axis=B-A;t=np.clip(((close-A)@axis)/(axis@axis),0,1)
    rad=close-(A+t[:,None]*axis);norm*=np.sign(np.einsum('ij,ij->i',norm,rad))[:,None]
    signed=np.einsum('ij,ij->i',g-close,norm);near=dist<2
    out.append({'frame':fi,'minimum_distance_cm':float(min(dist)),
        'inside_near_stock_vertices':int(((signed<-.05)&near).sum()),
        'onscreen_inside_near_stock_vertices':int(((signed<-.05)&near&visible).sum()),
        'deepest_near_signed_cm':float(signed[near].min()) if near.any() else None})
report={'mode':mode,'method':'closest arm surface with outward forearm normal; signed depth threshold 0.5 mm; 2 cm search band',
        'frames':out,'maximum_onscreen_penetrating_vertices':max(r['onscreen_inside_near_stock_vertices'] for r in out)}
(O/('stock-arm-'+mode+'.json')).write_text(json.dumps(report,indent=2))
print('Stock proximity',report['maximum_onscreen_penetrating_vertices'],[(r['frame'],r['onscreen_inside_near_stock_vertices']) for r in out if r['onscreen_inside_near_stock_vertices']],flush=True)
