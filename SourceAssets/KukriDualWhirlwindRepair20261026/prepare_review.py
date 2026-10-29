"""Skin scoped diagnostic frames; preserve real native helpers and two grips."""
import importlib.util,json,sys
from pathlib import Path
import numpy as np
from scipy.spatial.transform import Rotation as R
OUT=Path(__file__).resolve().parent;ROOT=OUT.parents[1]
s=importlib.util.spec_from_file_location('dual_v1',ROOT/'SourceAssets/KukriDualWhirlwind20261026/author.py')
a=importlib.util.module_from_spec(s);s.loader.exec_module(a)
version=sys.argv[1] if len(sys.argv)>1 else 'before'
origin=OUT if version=='after' else ROOT/'SourceAssets/KukriDualWhirlwind20261026'
decoded_path=OUT/(version+'-compressed.json')
decoded=json.loads(decoded_path.read_text()) if decoded_path.exists() else None
tuning=a.base.effective_tuning();durations=[tuning[k] for k in ('readySeconds','spinSeconds','recoverSeconds')]
offsets=np.r_[0.,np.cumsum(durations)]
times=np.array([0.,.5,.61,.80,1.,offsets[2],1.35,1.55,offsets[3]])
for label,data in a.base.rig.DATA.items():
    body=a.c.Body(data)
    geo=json.loads((ROOT/f'SourceAssets/FarreachBackpack20261024/SlimFitR2_20261024/BodyInputs/Normalized/{label.capitalize()}/body.json').read_text())
    if decoded:clips=decoded[label]['clips']
    else:
        authored=json.loads((origin/(label+'-actions.json')).read_text());clips={}
        for role,clip in authored['clips'].items():
            p,q=body.world(np.asarray(clip['frames']))
            clips[role]={'world':np.concatenate([p,q,np.ones_like(p)],axis=2)}
    samples=[]
    for t in times:
        stage=min(2,int(np.searchsorted(offsets[1:],t,side='right')))
        f=np.asarray(clips[a.ROLES[stage]]['world'])
        samples.append(a.c.sample(f,np.clip((t-offsets[stage])/durations[stage],0.,1.)*(len(f)-1),1.))
    samples=np.asarray(samples);p=samples[:,:,:3];q=samples[:,:,3:7]
    vertices=np.asarray(geo['positions']);weights=geo['weights'];width=max(map(len,weights))
    wi=np.zeros((len(weights),width),int);wv=np.zeros((len(weights),width))
    for k,row in enumerate(weights):
        for j,(i,w) in enumerate(row):wi[k,j]=i;wv[k,j]=w
    ref=np.array([geo['reference'][n] for n in body.names]);inv=R.from_quat(ref[:,3:7]).inv().as_matrix()
    rest=np.einsum('nvij,nvj->nvi',inv[wi],vertices[:,None,:]-ref[wi,:3])/ref[wi,7:]
    mesh=[];blades=[]
    rp,rq=a.base.native.blade_mount(body);_,lp,lq=a.left_grip(body)
    for k in range(len(samples)):
        rot=R.from_quat(q[k]).as_matrix()
        mesh.append(np.sum((np.einsum('nvij,nvj->nvi',rot[wi],rest*samples[k,wi,7:])+p[k,wi])*wv[:,:,None],axis=1))
        pair=[]
        for side,mp,mq in [('r',rp,rq),('l',lp,lq)]:
            i=body.ix['hand_'+side];hr=R.from_quat(q[k,i]);pair.append(np.r_[p[k,i]+hr.apply(mp),(hr*mq).as_quat()])
        blades.append(pair)
    np.savez_compressed(OUT/f'{label}-{version}-review.npz',vertices=np.asarray(mesh,dtype=np.float32),triangles=geo['triangles'],blades=blades,times=times)
    print('DUAL_REVIEW_GEOMETRY',label,version,'UE compressed' if decoded else 'authoring')
