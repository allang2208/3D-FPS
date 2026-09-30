"""Keep the installed PKM FK chains; place the 201 weapon at the left contact.

This changes the object placement rather than solving an arm against the old
201 wrist path. No IK, elbow pole, roll redistribution or skin rewrite.
"""
import json, hashlib
from pathlib import Path
import numpy as np
from scipy.spatial.transform import Rotation as R, Slerp

O=Path(__file__).resolve().parent; P=O.parents[2]
d=json.loads((O/'input.json').read_text())
def matrix(v):
    m=np.eye(4);m[:3,:3]=R.from_quat(v['q']).as_matrix()@np.diag(v['s']);m[:3,3]=v['p'];return m
def pack(m,previous=None):
    s=np.linalg.norm(m[:3,:3],axis=0);q=R.from_matrix(m[:3,:3]/s).as_quat()
    if previous is not None and np.dot(q,previous)<0:q=-q
    return {'p':m[:3,3].tolist(),'q':q.tolist(),'s':s.tolist()}
def ramp(t,a,b):
    f=np.clip((t-a)/(b-a),0.,1.);return f*f*f*(f*(f*6-15)+10)
def mix(a,b,w):
    if w>=1:return b.copy()
    if w<=0:return a.copy()
    va,vb=pack(a),pack(b)
    return matrix({'p':(np.array(va['p'])*(1-w)+np.array(vb['p'])*w).tolist(),
        'q':Slerp([0,1],R.from_quat([va['q'],vb['q']]))([w]).as_quat()[0].tolist(),
        's':(np.array(va['s'])*(1-w)+np.array(vb['s'])*w).tolist()})
tb=d['meshes']['201']['bones']; db=d['meshes']['pkm']['bones']
def subtree(root):
    selected={root}
    while True:
        extra={n for n,v in tb.items() if v['parent'] in selected}
        if extra.issubset(selected):return [n for n in tb if n in selected]
        selected|=extra
arms={s:subtree('clavicle_'+s) for s in ['l','r']}
changed=arms['l']+arms['r']+['WPN_root']
result={'revision':'PKMFK19','method':'native complete PKM FK; weapon/right-arm placement follows the left contact',
        'ik_used':False,'twist_redistribution':False,'clips':{}}
review={'frames':{},'bones':tb};report={'donors':{},'clips':{}}
for key in ('reload','reload_empty'):
    src=d['clips']['pkm_'+key];old=d['clips']['201_'+key]
    for spec in (src,old):
        path=P/'Content'/(spec['asset'].removeprefix('/Game/')+'.uasset')
        if hashlib.sha256(path.read_bytes()).hexdigest()!=spec['sha256']:raise RuntimeError('Input changed '+str(path))
    if src['frames']!=old['frames'] or src['fps']!=old['fps']:raise RuntimeError('Source timeline mismatch')
    name=old['asset'].rsplit('/',1)[-1];duration=old['seconds'];exit_start=6.40 if key.endswith('empty') else 6.12
    tracks={n:[] for n in changed};previous={n:None for n in changed};placements=[]
    for i,(source,target) in enumerate(zip(src['poses'],old['poses'])):
        t=i*duration/(old['frames']-1)
        native=ramp(t,0,.28)*(1-ramp(t,exit_start,duration))
        sw={n:matrix(v['world']) for n,v in source.items()}
        ow={n:matrix(v['world']) for n,v in target.items()}
        # The old path defines the 201 contact on its differently sized cover,
        # feed and support. Move the gun to the donor wrist, never the left
        # shoulder to the gun. The entire mechanical hierarchy moves together.
        shift=sw['hand_l'][:3,3]-ow['hand_l'][:3,3]
        weapon=ow['WPN_root'].copy();weapon[:3,3]+=shift*native
        local={n:matrix(v['local']) for n,v in target.items()}
        # Both chains retain the donor's actual local rotations and helpers.
        # The right support follows the shifted gun; its internal shape stays
        # native. Local idle handoffs occupy only the non-contact endpoints.
        right_shift=ow['hand_r'][:3,3]+shift-sw['hand_r'][:3,3]
        for side in ('l','r'):
            for n in arms[side]:
                desired=matrix(source[n]['local'])
                if n=='clavicle_'+side:
                    world=sw[n].copy()
                    if side=='r':world[:3,3]+=right_shift
                    desired=np.linalg.inv(ow[tb[n]['parent']])@world
                local[n]=mix(local[n],desired,native)
        local['WPN_root']=np.linalg.inv(ow[tb['WPN_root']['parent']])@weapon
        for n in changed:
            v=pack(local[n],previous[n]);previous[n]=v['q'];tracks[n].append(v)
        placements.append({'t':t,'native_weight':float(native),'gun_translation_cm':(shift*native).tolist(),
                           'right_translation_from_pkm_cm':(right_shift*native).tolist()})
        if i in {round(x*120) for x in [0,.28,.55,.65,.8,.95,1.1,1.4,1.65,2.3,2.6,3.45,4.35,4.82,5.1,5.72,6.12,6.4,duration] if x<=duration}:
            worlds={}
            def world(n):
                if n not in worlds:
                    parent=tb[n]['parent'];worlds[n]=world(parent)@local[n] if parent in local else local[n]
                return worlds[n]
            for n in local:world(n)
            review['frames'][name+'_'+str(i)]={'t':t,'name':name,'native_weight':float(native),
                'before':{n:v['world'] for n,v in target.items()},'after':{n:pack(v) for n,v in worlds.items()},
                'donor':{n:v['world'] for n,v in source.items()}}
    result['clips'][name]={'asset':old['asset'],'donor':src['asset'],'expected_source_sha256':old['sha256'],
        'donor_sha256':src['sha256'],'seconds':duration,'keys':old['frames'],'fps':old['fps'],
        'tracks':tracks,'native_fk_interval':[.28,exit_start]}
    report['donors'][src['asset']]={'sha256':src['sha256'],'metadata':src['metadata']}
    report['clips'][name]={'placements':placements,'changed_tracks':changed,'native_fk_interval':[.28,exit_start]}
    print('PKMFK19_AUTHORED',name,len(changed),old['frames'],flush=True)
(O/'keys.json').write_text(json.dumps(result,separators=(',',':')),encoding='utf8')
(O/'contact_placement.json').write_text(json.dumps(report,separators=(',',':')),encoding='utf8')
(O/'pose_keys.json').write_text(json.dumps(review,separators=(',',':')),encoding='utf8')
