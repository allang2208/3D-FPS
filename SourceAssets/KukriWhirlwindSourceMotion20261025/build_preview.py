"""Skin the real native body geometry for the requested offline motion review."""
import json
from pathlib import Path
import numpy as np
from scipy.spatial.transform import Rotation as R
import author as a
OUT=Path(__file__).resolve().parent
times=[0.,.16,.28,.40,.52,.64,.76,.90,1.0666667]
manifest={'samples':[],'heading_normalized':True,'runtime_tested':False}
for label,data in a.DATA.items():
    body=a.c.Body(data)
    geo=json.loads((a.ROOT/f'SourceAssets/FarreachBackpack20261024/SlimFitR2_20261024/BodyInputs/Normalized/{label.capitalize()}/body.json').read_text())
    if [b['name'] for b in geo['bones']]!=body.names:raise RuntimeError('Skin bone order mismatch')
    positions=np.asarray(geo['positions']);weights=geo['weights']
    width=max(map(len,weights));wi=np.zeros((len(weights),width),dtype=int);wv=np.zeros((len(weights),width))
    for k,row in enumerate(weights):
        for j,(i,w) in enumerate(row):wi[k,j]=i;wv[k,j]=w
    inv=R.from_quat(body.tq).inv().as_matrix()
    rest=np.einsum('nvij,nvj->nvi',inv[wi],positions[:,None,:]-body.tp[wi])
    actions=json.loads((OUT/(label+'-actions.json')).read_text())['clips']
    poses=[];entries=[]
    for version in ('before','after'):
        clip=data['clips']['Whirlwind.Loop'] if version=='before' else actions['Whirlwind.Loop']
        for t in times:
            poses.append(a.c.sample(np.asarray(clip['frames']),t,clip['rate']))
            entries.append(dict(body=label,version=version,role='loop',time=t))
    for role in ('Whirlwind.Start','Whirlwind.End'):
        clip=actions[role]
        for t in (0.,.125,.25,.375,(len(clip['frames'])-1)/clip['rate']):
            poses.append(a.c.sample(np.asarray(clip['frames']),t,clip['rate']))
            entries.append(dict(body=label,version='after',role=role,time=t))
    p,q=body.world(np.asarray(poses));skinned=[];mount_pos,mount_rot=a.native.blade_mount(body)
    blade=[]
    for k in range(len(poses)):
        rot=R.from_quat(q[k]).as_matrix()
        verts=np.sum((np.einsum('nvij,nvj->nvi',rot[wi],rest)+p[k,wi])*wv[:,:,None],axis=1)
        skinned.append(verts)
        hr=R.from_quat(q[k,body.ix['hand_r']]);br=hr*mount_rot
        blade.append(np.r_[p[k,body.ix['hand_r']]+hr.apply(mount_pos),br.as_quat()])
    np.savez_compressed(OUT/(label+'-preview.npz'),vertices=np.asarray(skinned),triangles=np.asarray(geo['triangles']),blade=np.asarray(blade))
    for i,e in enumerate(entries):e['index']=i;manifest['samples'].append(e)
(OUT/'preview-manifest.json').write_text(json.dumps(manifest,indent=2))
print('NATIVE_SKIN_PREVIEW_PREPARED')
