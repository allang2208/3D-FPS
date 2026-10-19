"""User-requested geometry/normal-map review of the authored source."""
import json,math
from pathlib import Path
import numpy as np
from PIL import Image
P=Path('D:/FPS3D/FPSGAME');O=P/'SourceAssets/Saiga12KDetail20261018';R={'models':{},'textures':{},'checks_requested_by_user':True}
for key in ('gun','ext12'):
 d=json.loads((O/('Authoring/'+key+'.json')).read_text());p=np.array(d['positions']);t=np.array(d['triangles']);n=np.array(d['normals']);uv=np.array(d['uv']);q=p[t];cross=np.cross(q[:,1]-q[:,0],q[:,2]-q[:,0]);area=np.linalg.norm(cross,axis=1)*.5
 uvarea=np.abs((uv[:,1,0]-uv[:,0,0])*(uv[:,2,1]-uv[:,0,1])-(uv[:,1,1]-uv[:,0,1])*(uv[:,2,0]-uv[:,0,0]))*.5
 report={'triangles':len(t),'vertices':len(p),'finite_positions_normals_uv':bool(np.isfinite(p).all() and np.isfinite(n).all() and np.isfinite(uv).all()),'near_zero_triangles':int((area<1e-10).sum()),'near_zero_uv_triangles':int((uvarea<1e-14).sum()),'normal_length_min_max':[float(np.linalg.norm(n,axis=2).min()),float(np.linalg.norm(n,axis=2).max())],'bounds_cm':[p.min(0).tolist(),p.max(0).tolist()],'parts':{}}
 for part in set(d['parts']):
  ids=np.array([i for i,x in enumerate(d['parts']) if x==part]);report['parts'][part]={'triangles':len(ids),'area_cm2':float(area[ids].sum()),'degenerate_triangles':int((area[ids]<1e-10).sum())}
 R['models'][key]=report
 for suffix in ('N','Mask'):
  path=O/('Textures/T_Saiga12K_'+key+'_'+suffix+'.png');im=Image.open(path);a=np.array(im).astype(float)/255.;r={'size':list(im.size),'mean':a.mean((0,1)).tolist(),'min':a.min((0,1)).tolist(),'max':a.max((0,1)).tolist()}
  if suffix=='N':
   v=a[:,:,:3]*2-1;covered=a[:,:,2]>.5;r['z_mean_covered']=float(v[:,:,2][covered].mean());r['xy_rms_covered']=float(np.sqrt(np.square(v[:,:,:2][covered]).mean()));r['convention']='OpenGL, green flip on UE import only'
  R['textures'][path.name]=r
R['geometry_finite']=all(x['finite_positions_normals_uv'] for x in R['models'].values());R['degenerate_free']=all(x['near_zero_triangles']==0 and x['near_zero_uv_triangles']==0 for x in R['models'].values())
(O/'Reports/source-check.json').write_text(json.dumps(R,indent=2),encoding='utf-8')
print(json.dumps({'finite':R['geometry_finite'],'degenerate_free':R['degenerate_free'],'models':{k:{x:v[x] for x in ['triangles','near_zero_triangles','near_zero_uv_triangles','normal_length_min_max']} for k,v in R['models'].items()}},indent=2))
