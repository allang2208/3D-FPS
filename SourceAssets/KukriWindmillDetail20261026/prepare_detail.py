"""Native skin and palm frames for the requested close hand review."""
import json, sys
from pathlib import Path
import numpy as np
from scipy.spatial.transform import Rotation as R
import author as a
OUT=Path(__file__).resolve().parent
version=sys.argv[1] if len(sys.argv)>1 else 'V17'
source=OUT.parent/'KukriWindmillGrip20261026' if version=='V16' else OUT
compressed=version=='V16' or '--compressed' in sys.argv
decoded=json.loads((source/'preview-compressed.json').read_text()) if compressed else None
tuning=a.effective_tuning()
durations=[tuning[k] for k in ('readySeconds','spinSeconds','recoverSeconds')]
offsets=np.r_[0.,np.cumsum(durations)]
times=np.array([0.,.5,.525,.55,.575,.60,.625,.70,.95,1.20,1.26,1.34,1.42,1.50,1.58,1.66,sum(durations)])
for label,data in a.rig.DATA.items():
    body=a.c.Body(data)
    geo=json.loads((a.ROOT/f'SourceAssets/FarreachBackpack20261024/SlimFitR2_20261024/BodyInputs/Normalized/{label.capitalize()}/body.json').read_text())
    if compressed:
        clips=decoded[label]['clips']
    else:
        authored=json.loads((source/(label+'-actions.json')).read_text())
        clips={}
        for role,clip in authored['clips'].items():
            p,q=body.world(np.asarray(clip['frames']))
            clips[role]={'world':np.concatenate([p,q,np.ones_like(p)],axis=2)}
    samples=[]
    for t in times:
        stage=min(2,int(np.searchsorted(offsets[1:],t,side='right')))
        f=np.asarray(clips[a.ROLES[stage]]['world'])
        samples.append(a.c.sample(f,np.clip((t-offsets[stage])/durations[stage],0.,1.)*(len(f)-1),1.))
    samples=np.asarray(samples);p=samples[:,:,:3];q=samples[:,:,3:7]
    vertices=np.asarray(geo['positions']);weights=geo['weights']
    width=max(map(len,weights));wi=np.zeros((len(weights),width),int);wv=np.zeros((len(weights),width))
    for k,row in enumerate(weights):
        for j,(i,w) in enumerate(row):wi[k,j]=i;wv[k,j]=w
    reference=np.asarray([geo['reference'][n] for n in body.names])
    inv=R.from_quat(reference[:,3:7]).inv().as_matrix()
    rest=np.einsum('nvij,nvj->nvi',inv[wi],vertices[:,None,:]-reference[wi,:3])/reference[wi,7:]
    skinned=[];blade=[];mount_pos,mount_rot=a.native.blade_mount(body)
    for k in range(len(samples)):
        rot=R.from_quat(q[k]).as_matrix()
        skinned.append(np.sum((np.einsum('nvij,nvj->nvi',rot[wi],rest*samples[k,wi,7:])+p[k,wi])*wv[:,:,None],axis=1))
        hr=R.from_quat(q[k,body.ix['hand_r']])
        blade.append(np.r_[p[k,body.ix['hand_r']]+hr.apply(mount_pos),(hr*mount_rot).as_quat()])
    hands=[];normals=[];lengths=[];elbows=[]
    for side in 'rl':
        hand=p[:,body.ix['hand_'+side]]
        longitudinal=a.c.unit(p[:,body.ix['middle_01_'+side]]-hand)
        across=a.c.unit(p[:,body.ix['index_01_'+side]]-p[:,body.ix['pinky_01_'+side]])
        normal=a.c.unit(np.cross(longitudinal,across))*(1 if side=='r' else -1)
        hands.append(hand);normals.append(normal);lengths.append(longitudinal)
        elbows.append(p[:,body.ix['lowerarm_'+side]])
    regions={};triangles=np.asarray(geo['triangles'])
    for side in 'rl':
        bones=np.array([n.endswith('_'+side) and n.startswith(('lowerarm','hand_','thumb','index','middle','ring','pinky')) for n in body.names])
        selected=(bones[wi]*wv).sum(axis=1)>.5
        regions['arm_'+side]=triangles[np.all(selected[triangles],axis=1)]
    np.savez_compressed(OUT/f'{label}-{version}-detail.npz',vertices=np.asarray(skinned,dtype=np.float32),triangles=triangles,blade=blade,times=times,hands=np.stack(hands,axis=1),normal=np.stack(normals,axis=1),longitudinal=np.stack(lengths,axis=1),elbows=np.stack(elbows,axis=1),**regions)
print('DETAIL_GEOMETRY',version,'compressed' if compressed else 'authoring')
