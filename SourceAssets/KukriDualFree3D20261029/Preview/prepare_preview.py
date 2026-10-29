"""Skin saved UE poses on the native body, with the actual dual knife mounts."""
import importlib.util,json,sys
from pathlib import Path
import numpy as np
from scipy.spatial.transform import Rotation as R

OUT=Path(__file__).resolve().parent;ROOT=OUT.parents[2]
s=importlib.util.spec_from_file_location('preview_math',ROOT/'SourceAssets/KukriDualCombatThirdPerson20261028/author.py')
a=importlib.util.module_from_spec(s);s.loader.exec_module(a)
body=a.c.Body(a.base.rig.DATA['jason'])
source=json.loads((OUT/(sys.argv[1] if len(sys.argv)>1 else 'saved-poses.json')).read_text())
geo=json.loads((ROOT/'SourceAssets/FarreachBackpack20261024/SlimFitR2_20261024/BodyInputs/Normalized/Jason/body.json').read_text())
vertices=np.asarray(geo['positions']);weights=geo['weights'];width=max(map(len,weights))
wi=np.zeros((len(weights),width),int);wv=np.zeros((len(weights),width))
gi=[body.ix[n['name'] if isinstance(n,dict) else n] for n in geo['bones']]
for k,row in enumerate(weights):
    for j,(i,w) in enumerate(row):wi[k,j]=gi[i];wv[k,j]=w
ref=np.array([geo['reference'][name] for name in body.names]);inv=R.from_quat(ref[:,3:7]).inv().as_matrix()
rest=np.einsum('nvij,nvj->nvi',inv[wi],vertices[:,None,:]-ref[wi,:3])/ref[wi,7:]
# Use actual head skin weights, copying shared body bones and retaining the
# facial reference transforms. No hair, clothing or gameplay layers are shown.
head=json.loads((OUT/'head-weighted.json').read_text())
hn=[b['name'] for b in head['bones']];hpar=[b['parent'] for b in head['bones']]
href=np.array([head['reference'][n] for n in hn]);hr=R.from_quat(href[:,3:7])
hlp=href[:,:3].copy();hlq=href[:,3:7].copy()
for i,par in enumerate(hpar):
    if par>=0:
        hlp[i]=hr[par].inv().apply(href[i,:3]-href[par,:3])/href[par,7:]
        hlq[i]=(hr[par].inv()*hr[i]).as_quat()
width=max(map(len,head['weights']));hwi=np.zeros((len(head['positions']),width),int);hwv=np.zeros(hwi.shape)
for k,row in enumerate(head['weights']):
    for j,(i,w) in enumerate(row):hwi[k,j]=i;hwv[k,j]=w
hrest=np.einsum('nvij,nvj->nvi',hr.inv().as_matrix()[hwi],np.asarray(head['positions'])[:,None,:]-href[hwi,:3])/href[hwi,7:]
rp,rq=a.base.native.blade_mount(body);_,lp,lq=a.carry.dual.v1.left_grip(body)
order=[source['names'].index(n) for n in body.names]
for role,data in source['clips'].items():
    f=np.asarray(data['frames'])[:,order];p,q=body.world(f)
    mesh=[];heads=[];blades=[]
    for k in range(len(f)):
        rot=R.from_quat(q[k]).as_matrix()
        mesh.append(np.sum((np.einsum('nvij,nvj->nvi',rot[wi],rest)+p[k,wi])*wv[:,:,None],axis=1))
        hp=href[:,:3].copy();hq=href[:,3:7].copy()
        for i,(name,par) in enumerate(zip(hn,hpar)):
            if name in body.ix:
                hp[i]=p[k,body.ix[name]];hq[i]=q[k,body.ix[name]]
            elif par>=0:
                parent=R.from_quat(hq[par]);hp[i]=hp[par]+parent.apply(hlp[i]);hq[i]=(parent*R.from_quat(hlq[i])).as_quat()
        heads.append(np.sum((np.einsum('nvij,nvj->nvi',R.from_quat(hq).as_matrix()[hwi],hrest)+hp[hwi])*hwv[:,:,None],axis=1))
        pair=[]
        for side,mp,mq in [('r',rp,rq),('l',lp,lq)]:
            i=body.ix['hand_'+side];hr=R.from_quat(q[k,i]);pair.append(np.r_[p[k,i]+hr.apply(mp),(hr*mq).as_quat()])
        blades.append(pair)
    np.savez_compressed(OUT/(role+'.npz'),vertices=np.asarray(mesh,dtype=np.float32),triangles=geo['triangles'],head=np.asarray(heads,dtype=np.float32),head_triangles=head['triangles'],blades=blades,times=data['times'])
    print('PREPARED',role,len(f),data['asset'])
