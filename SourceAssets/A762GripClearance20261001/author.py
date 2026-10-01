"""R09: smooth local rearward clearance deformation; no remesh or new faces."""
import json
from pathlib import Path
import numpy as np
O=Path(__file__).parent;PREV=O.parent/'A762ReceiverGrip20261001'
FLIP=np.array([.01,-.01,.01]);REFLECT=np.array([1.,-1.,1.])
ROOT=np.array(json.loads((PREV/'Input/frames.json').read_text())['root_rest'])
INV=np.linalg.inv(ROOT)

def smooth(t):
 s=np.clip(t,0,1);return s*s*(3-2*s),np.where((t>0)&(t<1),6*s*(1-s),0.)

def deform(points,normals=None):
 """Keep the top mating rim, backstrap and lower gripping area fixed.
 In root-local metres +Y points rearwards, away from the trigger.
 """
 p=np.asarray(points,dtype=np.float64);y,z=p[...,1],p[...,2]
 upper,du=smooth((.0125-z)/.0085);lower,dl=smooth((z+.044)/.029)
 front,df=smooth((y-.004)/.032)
 amp=.0115;wz=upper*lower;dy=amp*wz*(1-front)
 out=p.copy();out[...,1]+=dy
 if normals is None:return out
 # Inverse-transpose of the exact deformation Jacobian preserves source
 # custom shading while rotating only the edited surface normals.
 a=1-amp*wz*df/.032
 b=amp*((-du/.0085)*lower+upper*dl/.029)*(1-front)
 ns=np.asarray(normals,dtype=np.float64).copy();ny=ns[...,1]/a
 ns[...,2]-=b*ny;ns[...,1]=ny;ns/=np.maximum(np.linalg.norm(ns,axis=-1,keepdims=True),1e-12)
 return out,ns

def author():
 outdir=O/'Exports';outdir.mkdir(exist_ok=True);report={'revision':'GripClearance09-20261001','meshes':{},'runtime_tested':False}
 for key in ['Body','phantom_reargrip']:
  with (O/'Input'/(key+'.bin')).open('rb') as f:
   h=json.loads(f.readline());v,nt=h['vertices'],h['selected_triangles']
   p=np.fromfile(f,np.float32,v*3).reshape(v,3);tids=np.fromfile(f,np.int32,nt)
   tris=np.fromfile(f,np.int32,nt*3).reshape(nt,3);ns=np.fromfile(f,np.float32,nt*9).reshape(nt,3,3)
  local=p.astype(np.float64)*FLIP;nn=ns.astype(np.float64)*REFLECT
  if key=='Body':local=local@INV[:3,:3].T+INV[:3,3];nn=nn@INV[:3,:3].T
  selected=np.unique(tris);positions=deform(local[selected]);moved=np.max(np.abs(positions-local[selected]),axis=1)>1e-10
  vids=selected[moved];positions=positions[moved]
  affected=np.any(np.isin(tris,vids),axis=1);_,normals=deform(local[tris[affected]],nn[affected])
  if key=='Body':positions=positions@ROOT[:3,:3].T+ROOT[:3,3];normals=normals@ROOT[:3,:3].T
  positions/=FLIP;normals*=REFLECT
  head={'key':key,'moved_vertices':len(vids),'normal_triangles':int(affected.sum()),'vertices':h['vertices'],'triangles':h['triangles']}
  with (outdir/(key+'_edit.bin')).open('wb') as f:
   f.write((json.dumps(head)+'\n').encode());vids.astype(np.int32).tofile(f);positions.astype(np.float32).tofile(f)
   tids[affected].astype(np.int32).tofile(f);normals.astype(np.float32).tofile(f)
  report['meshes'][key]={**head,'maximum_rearward_edit_mm':round(float(np.max(deform(local[selected])[:,1]-local[selected,1]))*1000,3)}
  print('A762_CLEARANCE_AUTHORED',key,report['meshes'][key],flush=True)
 report['region']={'root_local_metres':True,'top_fixed_above_z':.0125,'lower_fixed_below_z':-.044,'back_fixed_above_y':.036,'amplitude_mm':11.5}
 (O/'authoring.json').write_text(json.dumps(report,indent=2))

if __name__=='__main__':author()
