"""Skin saved compressed V14 transforms on the native body geometry."""
import json,sys
from pathlib import Path
import numpy as np
from scipy.spatial.transform import Rotation as R
import author as a
OUT=Path(__file__).resolve().parent
candidate='--authoring' in sys.argv
if candidate:
    decoded={}
    for label,data in a.rig.DATA.items():
        body=a.c.Body(data)
        authored=json.loads((OUT/(label+'-actions.json')).read_text())
        clips={}
        for role,clip in authored['clips'].items():
            f=np.asarray(clip['frames']);p,q=body.world(f)
            clips[role]=dict(asset='AUTHORING CANDIDATE / '+role,world=np.concatenate([p,q,np.ones_like(p)],axis=2).tolist())
        decoded[label]=dict(mesh=authored['mesh'],names=authored['names'],clips=clips)
else:
    decoded=json.loads((OUT/'preview-compressed.json').read_text())
tuning=a.effective_tuning()
durations=[tuning[k] for k in ('readySeconds','spinSeconds','recoverSeconds')]
offsets=np.r_[0.,np.cumsum(durations)]
fps=30
times=np.linspace(0.,sum(durations),round(sum(durations)*fps)+1)
phases=a.old.arms.phase(np.clip((times-durations[0])/durations[1],0.,1.))
report=dict(source='Authoring candidate' if candidate else 'UE compressed V14 assets',fps=fps,times=times.tolist(),durations=durations,
            actor_turn_degrees=tuning['turnDegrees'],runtime_tested=False,body_geometry='Native export; no clothing or separate head',bodies={})
for label,entry in decoded.items():
    body=a.c.Body(a.rig.DATA[label])
    geo=json.loads((a.ROOT/f'SourceAssets/FarreachBackpack20261024/SlimFitR2_20261024/BodyInputs/Normalized/{label.capitalize()}/body.json').read_text())
    if geo['source']!=entry['mesh'] or [b['name'] for b in geo['bones']]!=entry['names']:
        raise RuntimeError('Native skin mismatch')
    vertices=np.asarray(geo['positions']);weights=geo['weights']
    width=max(map(len,weights));wi=np.zeros((len(weights),width),int);wv=np.zeros((len(weights),width))
    for k,row in enumerate(weights):
        for j,(i,w) in enumerate(row):wi[k,j]=i;wv[k,j]=w
    reference=np.asarray([geo['reference'][n] for n in entry['names']])
    inv=R.from_quat(reference[:,3:7]).inv().as_matrix()
    rest=np.einsum('nvij,nvj->nvi',inv[wi],vertices[:,None,:]-reference[wi,:3])/reference[wi,7:]
    samples=[];roles=[]
    for t in times:
        i=min(2,int(np.searchsorted(offsets[1:],t,side='right')))
        role=a.ROLES[i];clip=entry['clips'][role];f=np.asarray(clip['world'])
        u=np.clip((t-offsets[i])/durations[i],0.,1.)
        sample=a.c.sample(f,u*(len(f)-1),1.)
        samples.append(sample);roles.append(role)
    samples=np.asarray(samples);p=samples[:,:,:3];q=samples[:,:,3:7]
    scaled=samples[:,:,7:]
    skinned=[];mount_pos,mount_rot=a.native.blade_mount(body);blade=[]
    for k in range(len(samples)):
        rot=R.from_quat(q[k]).as_matrix()
        verts=np.sum((np.einsum('nvij,nvj->nvi',rot[wi],rest*scaled[k,wi])+p[k,wi])*wv[:,:,None],axis=1)
        skinned.append(verts.astype(np.float32))
        hr=R.from_quat(q[k,body.ix['hand_r']]);br=hr*mount_rot
        blade.append(np.r_[p[k,body.ix['hand_r']]+hr.apply(mount_pos),br.as_quat()])
    np.savez_compressed(OUT/(label+'-gif-preview.npz'),vertices=np.asarray(skinned),triangles=np.asarray(geo['triangles']),blade=np.asarray(blade),yaw=tuning['turnDegrees']*phases,times=times,hands=p[:,[body.ix['hand_r'],body.ix['hand_l']]])
    joins=[]
    for left,right in zip(a.ROLES[:-1],a.ROLES[1:]):
        l=np.asarray(entry['clips'][left]['world'][-1]);r=np.asarray(entry['clips'][right]['world'][0])
        ang=np.degrees((R.from_quat(l[:,3:7])*R.from_quat(r[:,3:7]).inv()).magnitude())
        joins.append(dict(left=left,right=right,max_position_cm=float(np.linalg.norm(l[:,:3]-r[:,:3],axis=1).max()),max_rotation_deg=float(ang.max())))
    spin_pose=np.asarray(entry['clips']['Whirlwind.Loop']['world'])
    recover_pose=np.asarray(entry['clips']['Whirlwind.End']['world'])
    hip=body.ix['pelvis'];left=body.ix['hand_l'];shoulder=body.ix['upperarm_l']
    report['bodies'][label]=dict(mesh=entry['mesh'],assets=[v['asset'] for v in entry['clips'].values()],joins=joins,
        spin_pelvis_start_end_cm=spin_pose[[0,-1],hip,2].tolist(),
        spin_max_upward_step_cm=float(np.diff(spin_pose[:,hip,2]).max()),
        recovery_pelvis_start_end_cm=recover_pose[[0,-1],hip,2].tolist(),
        recovery_max_downward_step_cm=float(np.maximum(0.,-np.diff(recover_pose[:,hip,2])).max()),
        spin_left_hand_below_shoulder_cm=[float(x) for x in (np.min(spin_pose[:,shoulder,2]-spin_pose[:,left,2]),np.max(spin_pose[:,shoulder,2]-spin_pose[:,left,2]))])
    print('V14_GIF_GEOMETRY '+label,flush=True)
(OUT/'gif-preview.json').write_text(json.dumps(report,indent=2))
