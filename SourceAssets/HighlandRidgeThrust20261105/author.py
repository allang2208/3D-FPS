"""Build a continuous 120 Hz take on both native grips, then split at release."""
from pathlib import Path
import json
import runpy
import sys
from mathutils import Quaternion, Vector

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
OUT=ROOT/'Saved/RidgeThrustAuthor'
OUT.mkdir(parents=True,exist_ok=True)
rig=runpy.run_path(str(HERE.parent/'HighlandBroadbladeSweep20261104/VideoFitV3/author_v3.py'))
A=rig['A']
blend, transform=rig['blend'],rig['transform']
place_arm, ue_keys=rig['place_arm'],rig['ue_keys']
redistribute=runpy.run_path(str(HERE/'arm_chain.py'))['redistribute']
motion_tools=runpy.run_path(str(HERE/'charge_motion.py'))
stroke=runpy.run_path(str(HERE/'strike_timing.py'))
support_elbow=runpy.run_path(str(HERE.parent/'ThrustElbowRepair20260923/elbow_support.py'))['support_elbow']
FPS=120

def bake(grip):
    data=rig['POSES'][grip]
    idle=A.pose_from_rows(data['idle'])
    rows=json.loads((HERE/(grip+'-fit.json')).read_text())
    first, last=rows[0]['frame'], rows[-1]['frame']
    poses=[]
    for i in range((last-first)*2+1):
        frame=first+i/2.
        a,b=rows[i//2],rows[min(i//2+1,len(rows)-1)]
        alpha=(i%2)*.5
        enter=A.smooth((frame-first)/6.)
        recover=A.smooth((frame-3264.)/(last-3264.))
        scale=idle['WPN_root'].to_scale()
        weapon=blend(transform(a,scale),transform(b,scale),alpha)
        weapon=blend(idle['WPN_root'],weapon,enter*(1.-recover))
        pose=dict(idle)
        move=weapon@idle['WPN_root'].inverted()
        for n in A.descendants('WPN_root')|{'ik_hand_gun'}:pose[n]=move@idle[n]
        for s,side in enumerate(('r','l')):
            spin=((1-alpha)*a['spin'][s]+alpha*b['spin'][s])*enter*(1.-recover)
            change=weapon@Quaternion((0,0,1),spin).to_matrix().to_4x4()@idle['WPN_root'].inverted()
            for n in A.HANDS[side]|{'ik_hand_'+side}:pose[n]=change@idle[n]
            guide=Vector(a['elbows'][s]).lerp(Vector(b['elbows'][s]),alpha)*.01
            place_arm(pose,idle,idle,idle,side,guide,enter,recover,None)
        if i==0 or i==(last-first)*2:pose=idle
        poses.append(pose)
    rest={n:A.canonical(A.native(row)) for n,row in A.DATA['reference'].items()}
    for side in ('r','l'):
        redistribute(A,poses,idle,side,rest,support_elbow)
    split=(3216-first)*2
    spins=rows[3216-first]['spin']
    charge=motion_tools['build_charge'](A,idle,poses[(3120-first)*2:split+1],spins)
    def save_take(role, motion):
        previous={}
        frames=[ue_keys(pose,previous) for pose in motion]
        arm_bones=[n for n in frames[0] if n.startswith(('clavicle_','upperarm_','lowerarm_','hand_'))]
        for i,keys in enumerate(frames):
            for bone in arm_bones:
                if any(abs(x/y-1.)>.003 for x,y in zip(keys[bone]['s'],frames[0][bone]['s'])):
                    raise ValueError(f'Unexpected {grip} {role} arm scale at {i}: {bone}')
        (OUT/(grip+role+'.json')).write_text(json.dumps(dict(skeleton=data['skeleton'],fps=FPS,frames=frames),separators=(',',':')))
        print('Baked',grip,role,len(frames),'keys at',FPS,'Hz',flush=True)
    if '--strike-only' not in sys.argv:
        save_take('Charge',charge)
    if '--charge-only' in sys.argv:
        return
    release=motion_tools['build_release'](A,idle,poses[split:],spins)
    release=stroke['retime_release'](release)
    entry=motion_tools['build_short_entry'](A,idle,charge[-1],spins)
    save_take('Release',release)
    save_take('Counter',entry[:-1]+release)

for grip in ('Standard','LongGrip'):
    bake(grip)
