"""Transfer the original KayKit stab's complete free arm into native thrusts.

Source shoulder, elbow and palm rotations share a single contact-aligned clock.
Transfer is chest-relative; native bone lengths and the closed fingers remain.
"""
import importlib.util
import json
from pathlib import Path
import numpy as np
from scipy.interpolate import PchipInterpolator
from scipy.spatial.transform import Rotation as R

OUT = Path(__file__).resolve().parent
ROOT = OUT.parents[1]
BASE = ROOT/'SourceAssets/KukriThirdPerson20261024/ComboV3'
spec = importlib.util.spec_from_file_location('kukri_combo_source',BASE/'author.py')
combo = importlib.util.module_from_spec(spec)
spec.loader.exec_module(combo)
DONOR = json.loads((OUT/'kaykit-stab-source.json').read_text())
SI = {n:i for i,n in enumerate(DONOR['names'])}
SR = np.asarray(DONOR['reference_world'])
SF = np.asarray(DONOR['frames'])
SFWD = combo.unit(np.mean([SR[SI['toes_'+s],:3]-SR[SI['foot_'+s],:3] for s in 'lr'],axis=0)*[1,1,0])
SBASIS = combo.frame(SFWD,np.array([0.,0.,1.]))


def arm_rotations(body, baseline, source_frames):
    _, tq = body.world(baseline)
    chest = body.ix['spine_03']
    # Attach the donor's shoulder/elbow performance to this take's actual chest.
    # The source root travel and torso lean never get applied a second time.
    source_torso = R.from_quat(source_frames[:,SI['chest'],3:7])*R.from_quat(SR[SI['chest'],3:7]).inv()*SBASIS
    target_torso = R.from_quat(tq[:,chest])*R.from_quat(body.tq[chest]).inv()*combo.frame(body.target_forward,np.array([0.,0.,1.]))
    carry = target_torso*source_torso.inv()
    desired = {}
    for name, source_name, source_child, target_child in [
        ('upperarm_l','upperarm_l','lowerarm_l','lowerarm_l'),
        ('lowerarm_l','lowerarm_l','wrist_l','hand_l'),
        ('hand_l','hand_l',None,None)]:
        i, j = body.ix[name], SI[source_name]
        if name == 'hand_l':
            # KayKit has an extra wrist before its palm, with no finger bones.
            # Its hand curve still supplies the actual animated palm rotation.
            source_frame = combo.frame(SR[j,:3]-SR[SI['wrist_l'],:3],SFWD)
            target_frame = combo.frame(body.tp[body.ix['middle_01_l']]-body.tp[i],
                                      body.tp[body.ix['index_01_l']]-body.tp[body.ix['pinky_01_l']])
        else:
            source_frame = combo.frame(SR[SI[source_child],:3]-SR[j,:3],SFWD)
            target_frame = combo.frame(body.tp[body.ix[target_child]]-body.tp[i],body.target_forward)
        mount = R.from_quat(SR[j,3:7]).inv()*source_frame*target_frame.inv()*R.from_quat(body.tq[i])
        desired[i] = carry*R.from_quat(source_frames[:,j,3:7])*mount
    return desired


def support_closed_fist(body, frames):
    """Retain source palm articulation while adapting its open hand to a fist.

    The stylized source reaches a large wrist bend during anticipation. Use a
    smooth anatomical swing limit; the shoulder/elbow movement is not clamped.
    """
    hand = body.ix['hand_l']
    native = R.from_quat(body.tq[hand])
    palm = combo.unit(native.inv().apply(body.tp[body.ix['middle_01_l']]-body.tp[hand]))
    across = native.inv().apply(body.tp[body.ix['index_01_l']]-body.tp[body.ix['pinky_01_l']])
    palm_frame = combo.frame(palm,across)
    axis = combo.unit(body.ref[hand,:3])
    reference = R.from_quat(body.ref[hand,3:7])
    neutral = combo.align(reference.apply(palm),axis)*reference*palm_frame
    local = R.from_quat(frames[:,hand,3:7])*palm_frame
    delta = (local*neutral.inv()).as_quat()
    delta = np.where(delta[:,3:]<0,-delta,delta)
    projected = (delta[:,:3]@axis)[:,None]*axis
    twist = combo.unit(np.c_[projected,delta[:,3]])
    twist = np.where(twist[:,3:]<0,-twist,twist)
    swing = R.from_quat(delta)*R.from_quat(twist).inv()
    v = swing.as_rotvec()
    angle = np.linalg.norm(v,axis=1)
    limit = np.radians(30.)
    soft_angle = limit*np.tanh(angle/limit)
    supported = R.from_rotvec(v*(soft_angle/np.maximum(angle,1e-10))[:,None])
    frames[:,hand,3:7] = (supported*R.from_quat(twist)*neutral*palm_frame.inv()).as_quat()


def author():
    # Source contact = strongest chest-relative forward reach of the sword arm.
    torso_delta = R.from_quat(SF[:,SI['chest'],3:7])*R.from_quat(SR[SI['chest'],3:7]).inv()
    reach = torso_delta.inv().apply(SF[:,SI['wrist_r'],:3]-SF[:,SI['upperarm_r'],:3])@SFWD
    source_hit = float(np.argmax(reach)/DONOR['rate'])
    report = dict(source_asset=DONOR['asset'],source_seconds=DONOR['duration'],source_contact_seconds=source_hit,
        source_license='KayKit Character Animations 1.1 / CC0',bodies={},runtime_tested=False,rendered=False)
    for label, data in combo.INPUT['targets'].items():
        body = combo.Body(data)
        current = json.loads((OUT/(label+'-current.json')).read_text())
        clip = current['clips']['Thrust']
        original = np.asarray(clip['frames'])
        ts = np.arange(len(original))/clip['rate']
        length = ts[-1]
        hit, release = clip['contact']*length, clip['release']*length
        # The complete source windup, counterbalance and recovery keep their
        # relative timing; only phase landmarks map to the existing hit clock.
        clock = np.array([0.,.16,.27,hit,release,.72,length])
        source_clock = np.array([0.,.14,.30,source_hit,.62,1.,DONOR['duration']])
        source_times = PchipInterpolator(clock,source_clock)(ts)
        source_frames = np.asarray([combo.sample(SF,t,DONOR['rate']) for t in source_times])
        frames = original.copy()
        body.set_world_rotations(frames,arm_rotations(body,original,source_frames))
        support_closed_fist(body,frames)
        # Blend the complete native arm from the second cut's actual endpoint,
        # not from the rejected V5 raised-guard trajectory.
        enter = combo.ease(ts/.24)
        leave = combo.ease((ts-.76)/(length-.76))
        arm = ['upperarm_l','lowerarm_l','hand_l']
        for name in arm:
            i = body.ix[name]
            frames[:,i,3:7] = combo.slerp(original[0,i,3:7],frames[:,i,3:7],enter[:,None])
            frames[:,i,3:7] = combo.slerp(frames[:,i,3:7],original[-1,i,3:7],leave[:,None])
        helpers = ['lowerarm_twist_01_l','lowerarm_twist_02_l']
        redistributed = body.twists(frames.copy())
        for name in helpers:
            i = body.ix[name]
            frames[:,i,3:7] = redistributed[:,i,3:7]
        frames[0] = original[0]
        frames[-1] = original[-1]
        for name in arm+helpers:
            i = body.ix[name]
            for k in range(1,len(frames)):
                if np.dot(frames[k-1,i,3:7],frames[k,i,3:7])<0:
                    frames[k,i,3:7] *= -1
        clip['frames'] = frames.tolist()
        clip['source'] = DONOR['asset']+' / complete left arm; '+current['asset']+' / retained body, blade and fist'
        clip['adaptation'] = ('KayKit original shoulder, elbow and palm performance transferred in chest space with native bone lengths; '
            'single contact-aligned clock; smooth closed-fist wrist swing accommodation; continuous combo entry and idle return; '
            'original right blade, torso, legs, finger closure and hit/release retained.')
        result = dict(mesh=data['mesh'],names=data['names'],parents=data['parents'],clips={'Thrust':clip})
        (OUT/(label+'-actions.json')).write_text(json.dumps(result,separators=(',',':')))
        report['bodies'][label] = dict(mesh=data['mesh'],previous_thrust=current['asset'],
            edited_rotation_tracks=arm+helpers,frames=len(frames),rate=clip['rate'],seconds=float(length),
            contact_seconds=hit,release_seconds=release,source_time_map=dict(target=clock.tolist(),source=source_clock.tolist()),
            source_entry_blend_seconds=.24,idle_return_start_seconds=.76)
        print('KUKRI_THRUST_SOURCE_ARM_AUTHORED '+label,flush=True)
    (OUT/'authoring.json').write_text(json.dumps(report,indent=2))


if __name__ == '__main__':
    author()
