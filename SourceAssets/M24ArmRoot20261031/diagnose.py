import bpy,numpy as np
from pathlib import Path
exec(compile((Path(__file__).parent/'motion.py').read_text().split("if __name__=='__main__':")[0],'motion','exec'))
G=json.loads((O/'kaitlin_skin_geometry.json').read_text())
P=np.array(G['positions'])*[.01,-.01,.01];F=np.array([f['vertices'] for f in G['faces']]);W=np.zeros((len(P),len(names)))
for i,ws in G['weights'].items():
 for n,w in ws.items():
  if n in indices:W[int(i),indices[n]]=w
L=[j for j,n in enumerate(names) if n.endswith('_l')];left=W[:,L].sum(1)>.5
C=np.array(json.loads((O.parent/'M24SprintShoulder20261031/current_camera_frame.json').read_text()))
base_idle=compose(entry('base','idle'),0)[0];skeleton_idle=compose(entry('skeleton_base','idle'),0)[0]
# FRifleHipFraming reanchors each active profile using its real right-hand point.
C[:3,3]+=(C[:3,:3]@(np.array(base_idle['hand_r'].translation)-np.array(skeleton_idle['hand_r'].translation)))
rest_inv={n:np.linalg.inv(np.array(m)) for n,m in rest.items()}
HP=np.c_[P,np.ones(len(P))];edge=np.array(sorted({tuple(sorted((int(a),int(b)))) for f in F for a,b in zip(f,np.roll(f,-1))}));length0=np.linalg.norm(P[edge[:,0]]-P[edge[:,1]],axis=1)
def skin(row,weights=W):
 out=np.zeros((len(P),4))
 for j,n in enumerate(names):
  ids=np.where(weights[:,j]>.000001)[0]
  if len(ids):out[ids]+=(HP[ids]@(np.array(row[n])@rest_inv[n]).T)*weights[ids,j,None]
 return out[:,:3]
def metrics(X):
 cp=np.c_[X,np.ones(len(X))]@C.T;x,y,z=cp[:,:3].T
 visible=(x>1)&(abs(y)<x*.7673*16/9)&(abs(z)<x*.7673)
 length=np.linalg.norm(X[edge[:,0]]-X[edge[:,1]],axis=1);ratio=length/np.maximum(length0,1e-8)
 order=np.argsort(ratio*(left[edge].all(1)))[-15:][::-1]
 return {'max_left_edge_ratio':float(ratio[left[edge].all(1)].max()),'spikes':[{'ids':e.tolist(),'ratio':float(ratio[i]),'length_cm':float(length[i]*100),'source_cm':float(length0[i]*100),'positions_cm':cp[e,:3].tolist(),'weights':[G['weights'][str(v)] for v in e]} for i in order for e in [edge[i]]]},cp,visible
if __name__=='__main__':
 out={}
 for role in ('idle','sprint_enter','sprint_loop','sprint_exit'):
  e=entry('skeleton_base',role);t=e['duration']*.5;row,_=compose(e,t);X=skin(row);out[role]=metrics(X)[0]
 (O/'diagnosis.json').write_text(json.dumps(out,indent=2))
 print('M24_REAL_SKIN_DIAGNOSIS',json.dumps({k:{'max':v['max_left_edge_ratio'],'spike':v['spikes'][0]} for k,v in out.items()}),flush=True)
