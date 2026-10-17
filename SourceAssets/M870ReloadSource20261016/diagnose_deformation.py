import bpy,json,gzip,math,numpy as np
from pathlib import Path
from mathutils import Vector,Matrix
O=Path(__file__).parent
bpy.ops.wm.open_mainfile(filepath=str(O/'M870_ReloadSource_Editable.blend'),use_scripts=False)
r=bpy.data.objects['SK_Super90'];s=bpy.context.scene;d=json.loads((O/'authoring.json').read_text());a=bpy.data.actions[d['clips']['reload_continuous']['action']]
r.animation_data.action=a;r.animation_data.action_slot=a.slots[0];s.frame_set(31)
R={b.name:b.matrix_local.copy() for b in r.data.bones};P={b.name:b.matrix.copy() for b in r.pose.bones};rf=R['hand_r'].translation-R['lowerarm_r'].translation;fore=P['hand_r'].translation-P['lowerarm_r'].translation
out={'axis_errors':{}}
for n in ('lowerarm_r','lowerarm_aux_r','lowerarm_twist_02_r','lowerarm_twist_01_r','hand_r'):
 d=P[n]@R[n].inverted();out['axis_errors'][n]=math.degrees((d.to_3x3()@rf).angle(fore))
with gzip.open(O.parent/'M870ReloadWrist20261016/native_arms.json.gz','rt',encoding='utf-8') as f:skin=json.load(f)
v=np.array(skin['vertices'])*[.01,-.01,.01];vs=np.c_[v,np.ones(len(v))];posed=np.zeros_like(v);Ri={n:np.array(m.inverted()) for n,m in R.items()}
for n in R:
 ids=[i for i,w in enumerate(skin['weights']) if w.get(n,0)>0]
 if not ids:continue
 weights=np.array([skin['weights'][i][n] for i in ids])[:,None]
 posed[ids]+=weights*((vs[ids]@(np.array(P[n])@Ri[n]).T)[:,:3])
fids=[i for i,w in enumerate(skin['weights']) if sum(value for n,value in w.items() if n.startswith('lowerarm') and n.endswith('_r'))>.8]
edges=np.array(list({tuple(sorted((a,b))) for face in skin['faces'] for a,b in zip(face,face[1:]+face[:1]) if a in set(fids) and b in set(fids)}))
length=np.linalg.norm(v[edges[:,0]]-v[edges[:,1]],axis=1);new=np.linalg.norm(posed[edges[:,0]]-posed[edges[:,1]],axis=1);ratio=new/(length+1e-12)
out['forearm_edge_strain_percentiles']=np.percentile(ratio,[0,1,5,50,95,99,100]).tolist()
out['forearm_bounds_m']=[posed[fids].min(0).tolist(),posed[fids].max(0).tolist()]
(O/'deformation.json').write_text(json.dumps(out,indent=2));print(json.dumps(out),flush=True)
