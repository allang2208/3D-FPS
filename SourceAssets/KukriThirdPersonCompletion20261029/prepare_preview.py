"""Skin the native author poses; use the exact mount-local runtime flight keys."""
import json,sys
from pathlib import Path
import numpy as np
from scipy.spatial.transform import Rotation as R
import author as a
OUT=a.OUT/'Preview';OUT.mkdir(exist_ok=True);ROOT=a.ROOT
label=sys.argv[1] if len(sys.argv)>1 else 'jason'
b=a.c.Body(a.old.base.rig.DATA[label]);source=json.loads((a.OUT/(label+'-actions.json')).read_text())
saved='--saved' in sys.argv
if saved:source=json.loads((a.OUT/'saved-poses.json').read_text())[label]
present=json.loads((a.OUT/'presentation.json').read_text())[label]
geo=json.loads((ROOT/'SourceAssets/FarreachBackpack20261024/SlimFitR2_20261024/BodyInputs/Normalized'/label.capitalize()/'body.json').read_text())
def weights(data,index):
    rows=data['weights'];wi=np.zeros((len(rows),max(map(len,rows))),int);wv=np.zeros(wi.shape)
    for k,row in enumerate(rows):
        for j,(i,w) in enumerate(row):wi[k,j]=index[i];wv[k,j]=w
    return wi,wv
wi,wv=weights(geo,[b.ix[n['name']] for n in geo['bones']]);ref=np.array([geo['reference'][n] for n in b.names])
rest=np.einsum('nvij,nvj->nvi',R.from_quat(ref[:,3:7]).inv().as_matrix()[wi],np.asarray(geo['positions'])[:,None,:]-ref[wi,:3])/ref[wi,7:]
head=json.loads((ROOT/'SourceAssets/KukriDualFree3D20261029/Preview/head-weighted.json').read_text())
hn=[n['name'] for n in head['bones']];hp=[n['parent'] for n in head['bones']];hr=np.array([head['reference'][n] for n in hn]);hl=hr.copy()
for i,par in enumerate(hp):
    if par>=0:
        rot=R.from_quat(hr[par,3:7]);hl[i,:3]=rot.inv().apply(hr[i,:3]-hr[par,:3]);hl[i,3:7]=(rot.inv()*R.from_quat(hr[i,3:7])).as_quat()
hwi,hwv=weights(head,list(range(len(hn))))
hrest=np.einsum('nvij,nvj->nvi',R.from_quat(hr[:,3:7]).inv().as_matrix()[hwi],np.asarray(head['positions'])[:,None,:]-hr[hwi,:3])/hr[hwi,7:]
ms=a.mounts(b);meta={}
for role,v in source['clips'].items():
    full=np.array(v['frames']);length=v['duration'] if saved else (len(full)-1)/120
    times=np.array(v['times']) if saved else np.linspace(0,length,round(length*20)+1)
    indices=np.arange(len(full)) if saved else np.clip(np.round(times/length*(len(full)-1)).astype(int),0,len(full)-1)
    f=full[indices];p,q=b.world(f)
    vertices=[];heads=[];blades=[]
    for k,idx in enumerate(indices):
        if saved:idx=round(times[k]*120)
        rot=R.from_quat(q[k]).as_matrix();vertices.append(np.sum((np.einsum('nvij,nvj->nvi',rot[wi],rest)+p[k,wi])*wv[:,:,None],axis=1))
        hh=hr.copy()
        for i,(name,par) in enumerate(zip(hn,hp)):
            if name in b.ix:hh[i,:3]=p[k,b.ix[name]];hh[i,3:7]=q[k,b.ix[name]]
            elif par>=0:
                r=R.from_quat(hh[par,3:7]);hh[i,:3]=hh[par,:3]+r.apply(hl[i,:3]);hh[i,3:7]=(r*R.from_quat(hl[i,3:7])).as_quat()
        heads.append(np.sum((np.einsum('nvij,nvj->nvi',R.from_quat(hh[:,3:7]).as_matrix()[hwi],hrest)+hh[hwi,:3])*hwv[:,:,None],axis=1))
        pair=[]
        for s in 'rl':
            bp,bq=ms[s];dq=R.identity();dp=np.zeros(3)
            take='DualEquip' if role=='Kukri.FullBody.Dual.Equip' else 'Equip' if role=='Kukri.FullBody.Equip' else 'Uppercut' if role=='Pistol.KukriUppercut' else None
            if take and s in present[take]['blades']:
                key=np.array(present[take]['blades'][s][idx]);dp=key[:3];dq=R.from_quat(key[3:])
            if take=='Uppercut' and s=='l':
                import re
                text=(ROOT/'Source/FPSGAME/Weapons/Kukri/OffhandKukriAuthoredPose.h').read_text()
                m=re.search(r'KukriInHand=FTransform\(FQuat\(([^)]*)\),FVector\(([^)]*)\)',text)
                parse=lambda x:np.array([float(v) for v in x.split(',')]);palm,offset=a.solver.carry.palm_mount(b,'l')
                bp=palm.apply(parse(m[2]))+offset;bq=palm*R.from_quat(parse(m[1]))
            if role=='Kukri.FullBody.Dual.Run' and s=='r':dq=R.from_rotvec([0,np.pi*a.c.ease(times[k]/length),0])
            mp=bp+bq.apply(dp);mq=bq*dq;i=b.ix['hand_'+s];r=R.from_quat(q[k,i])
            key=np.r_[p[k,i]+r.apply(mp),(r*mq).as_quat()]
            if (role=='Kukri.FullBody.Equip' and s=='l') or (role=='Pistol.KukriUppercut' and s=='r'):key[:3]=np.nan
            pair.append(key)
        blades.append(pair)
    key=label+'-'+role;meta[key]=dict(times=times.tolist(),duration=length,role=role,author_candidate=not saved)
    np.savez_compressed(OUT/(key+'.npz'),vertices=np.array(vertices,dtype=np.float32),triangles=geo['triangles'],head=np.array(heads,dtype=np.float32),head_triangles=head['triangles'],blades=blades,times=times)
    print('PREPARED',key,len(f),flush=True)
(OUT/'index.json').write_text(json.dumps(meta,indent=2))
