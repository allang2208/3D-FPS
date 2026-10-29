"""Skin the requested cut diagnostics using each body's actual mesh bind."""
import importlib.util,json,sys
from pathlib import Path
import numpy as np
from scipy.spatial.transform import Rotation as R
OUT=Path(__file__).resolve().parent;ROOT=OUT.parents[1]
s=importlib.util.spec_from_file_location('review_math',ROOT/'SourceAssets/KukriDualCombatThirdPerson20261028/author.py')
a=importlib.util.module_from_spec(s);s.loader.exec_module(a)
version=sys.argv[1] if len(sys.argv)>1 else 'before';origin=OUT if version=='after' else a.OUT
selected=[('Dual.Slash1',t) for t in (.23,.36,.72,.85)]+[('Dual.Slash2',t) for t in (.25,.38,.72,.87)]
for label in ('jason','kaitlin'):
    body=a.c.Body(a.base.rig.DATA[label]);src=json.loads((origin/(label+'-actions.json')).read_text())
    f=np.array([a.c.sample(np.asarray(src['clips'][role]['frames']),t,120) for role,t in selected]);p,q=body.world(f)
    geo=json.loads((ROOT/f'SourceAssets/FarreachBackpack20261024/SlimFitR2_20261024/BodyInputs/Normalized/{label.capitalize()}/body.json').read_text())
    vertices=np.asarray(geo['positions']);weights=geo['weights'];width=max(map(len,weights))
    wi=np.zeros((len(weights),width),int);wv=np.zeros((len(weights),width))
    for k,row in enumerate(weights):
        for j,(i,w) in enumerate(row):wi[k,j]=i;wv[k,j]=w
    ref=np.array([geo['reference'][name] for name in body.names]);inv=R.from_quat(ref[:,3:7]).inv().as_matrix()
    rest=np.einsum('nvij,nvj->nvi',inv[wi],vertices[:,None,:]-ref[wi,:3])/ref[wi,7:]
    mesh=[];blades=[];rp,rq=a.base.native.blade_mount(body);_,lp,lq=a.carry.dual.v1.left_grip(body)
    for k in range(len(f)):
        rot=R.from_quat(q[k]).as_matrix();mesh.append(np.sum((np.einsum('nvij,nvj->nvi',rot[wi],rest)+p[k,wi])*wv[:,:,None],axis=1))
        pair=[]
        for side,mp,mq in [('r',rp,rq),('l',lp,lq)]:
            i=body.ix['hand_'+side];hr=R.from_quat(q[k,i]);pair.append(np.r_[p[k,i]+hr.apply(mp),(hr*mq).as_quat()])
        blades.append(pair)
    np.savez_compressed(OUT/f'{label}-{version}-review.npz',vertices=np.asarray(mesh,dtype=np.float32),triangles=geo['triangles'],blades=blades)
(OUT/'review-times.json').write_text(json.dumps(selected))
print('COMBO_REVIEW_SKINNED',version)
