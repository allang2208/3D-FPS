import gzip,json,sys
from pathlib import Path
import numpy as np
import trimesh
O=Path(__file__).parent;R9=O.parent/'R9ReloadGrip';R10=O.parent/'R10ReloadReview'
env={'__file__':str(R9/'author_reload_grip.py')}
exec(compile((R9/'author_reload_grip.py').read_text().split("report={'method'")[0],str(R9/'author_reload_grip.py'),'exec'),env)
globals().update({k:v for k,v in env.items() if k not in ('O','__file__','__builtins__')})
motion=json.load(gzip.open(O/'CurrentSource/motion.json.gz','rt'));clip=motion['clips']['reload_empty'];bone=NI['WPN_bolt'];f=int(sys.argv[1]) if len(sys.argv)>1 else 320
suffix='' if f==320 else '_'+str(f)
weapon=data['svch'];wv=np.asarray(weapon['positions']);wt=np.asarray(weapon['triangles']);wm=np.asarray(weapon['material_ids'])
weights=np.zeros((len(wv),len(N)))
for i,row in enumerate(weapon['weights']):
 for b,w in row:weights[i,NI[weapon['weight_bones'][b]]]=w
variants={};bounds=[];body_vertices,body_faces=geom('svch',lambda n:n in ('SVCH_Body','SVCH_Polymer','SVCH_Rubber','SVCH_BarrelSteel'))
for label,path in [('before',R10/'profile_native_registration.json'),('after',O/'profile_charge.json')]:
 profile=json.loads(path.read_text());layer=next(c for c in profile['clips'] if c['base']==clip['path'])
 pose=comp(matrices(old_pose(np.asarray(clip['frames'][f]),layer,f/120)))
 hand=skin(pose,np.arange(len(AV)));right=np.array([N[b].endswith('_r') for b in DOM]);tri=np.asarray(arms['triangles']);tri=tri[right[tri].all(axis=1)]
 tri=tri[np.linalg.norm(hand[tri].mean(1)-pose[NI['hand_r'],:3,3],axis=1)<15]
 gun=np.zeros_like(wv)
 for b in np.flatnonzero(weights.max(0)>0):gun+=points(pose[b]@np.linalg.inv(rest['svch'][b]),wv)*weights[:,b,None]
 handlemat=weapon['materials'].index('SVCH_BoltCarrier');selected=wt[wm==handlemat]
 handlepoints=gun[np.unique(selected)];focus=handlepoints.mean(0)
 variants[label]={'hand_vertices':hand.tolist(),'hand_faces':tri.tolist(),'gun_vertices':gun.tolist(),'gun_faces':wt[wm<9].tolist(),
                  'focus':focus.tolist(),'hand_center':pose[NI['hand_r'],:3,3].tolist()}
 if label=='after':
  ids=np.flatnonzero(right&np.array([N[b].startswith(('hand_','thumb','index','middle','ring','pinky')) for b in DOM]))
  body=trimesh.Trimesh(vertices=points(pose[ROOT]@np.linalg.inv(rest['svch'][ROOT]),body_vertices),faces=body_faces,process=True);body.fix_normals(multibody=True)
  q,d,ids_=trimesh.proximity.closest_point(body,hand[ids]);near=np.flatnonzero(d<2.5);winding=[]
  for start in range(0,len(near),8):
   a,b,c=(body.triangles[None]-hand[ids[near[start:start+8]],None,None,:]).transpose(2,0,1,3)
   la,lb,lc=[np.linalg.norm(v,axis=-1) for v in (a,b,c)];dot=lambda x,y:np.einsum('...i,...i->...',x,y)
   winding.extend(np.sum(2*np.arctan2(dot(a,np.cross(b,c)),la*lb*lc+dot(a,b)*lc+dot(b,c)*la+dot(c,a)*lb),axis=1)/(4*np.pi))
  inside=near[np.abs(winding)>.5]
  report={'frame':f,'receiver_inside_vertices':len(inside),'max_receiver_depth_mm':float(d[inside].max()*10) if len(inside) else 0.,
          'worst':[(N[DOM[ids[j]]],float(d[j]*10)) for j in inside[np.argsort(d[inside])[::-1]][:10]]}
  (O/('charge_collision'+suffix+'.json')).write_text(json.dumps(report,indent=2));print(json.dumps(report),flush=True)
(O/('charge_scene'+suffix+'.json')).write_text(json.dumps(variants,separators=(',',':')))
