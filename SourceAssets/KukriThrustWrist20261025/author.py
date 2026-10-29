"""Replace the down-facing free wrist with a forearm-relative closed guard.

The V4 fist and the complete attack performance are retained. The new wrist
curve is authored in each body's own palm frame, not in fixed component space.
"""
import importlib.util
import json
from pathlib import Path

import numpy as np
from scipy.spatial.transform import Rotation as R

OUT = Path(__file__).resolve().parent
ROOT = OUT.parents[1]
BASE = ROOT/'SourceAssets/KukriThirdPerson20261024/ComboV3'
spec = importlib.util.spec_from_file_location('kukri_combo_source', BASE/'author.py')
combo = importlib.util.module_from_spec(spec)
spec.loader.exec_module(combo)


def wrist_measurements(body, frames):
    p, q = body.world(frames)
    hand, lower, middle = [body.ix[n] for n in ('hand_l', 'lowerarm_l', 'middle_01_l')]
    arm = combo.unit(p[:, hand]-p[:, lower])
    palm = combo.unit(p[:, middle]-p[:, hand])
    bend = np.degrees(np.arccos(np.clip(np.sum(arm*palm, axis=1), -1, 1)))
    delta = (R.from_quat(frames[:, hand, 3:7])*R.from_quat(body.ref[hand, 3:7]).inv()).as_quat()
    axis = combo.unit(body.ref[hand, :3])
    twist = np.degrees(2*np.arctan2(delta[:, :3]@axis, delta[:, 3]))
    twist = (twist+180)%360-180
    return dict(max_palm_forearm_angle_deg=float(bend.max()),
                max_angle_frame=int(bend.argmax()),
                max_abs_wrist_twist_deg=float(np.abs(twist).max()),
                contact_palm_forearm_angle_deg=float(bend[22]),
                contact_wrist_twist_deg=float(twist[22]))


def author():
    receipt = dict(bodies={}, runtime_tested=False, rendered=False,
                   diagnosis='Idle component-space palm direction was retained while the free forearm lifted into guard.')
    for label, target in combo.INPUT['targets'].items():
        body = combo.Body(target)
        current = json.loads((OUT/(label+'-current.json')).read_text())
        clip = current['clips']['Thrust']
        original = np.asarray(clip['frames'])
        frames = original.copy()
        hand = body.ix['hand_l']
        axis = combo.unit(body.ref[hand, :3])
        hand_bind = R.from_quat(body.tq[hand])
        palm = hand_bind.inv().apply(body.tp[body.ix['middle_01_l']]-body.tp[hand])
        across = hand_bind.inv().apply(body.tp[body.ix['index_01_l']]-body.tp[body.ix['pinky_01_l']])
        palm_frame = combo.frame(palm, across)
        ref_hand = R.from_quat(body.ref[hand, 3:7])
        # A straight wrist is an anatomical constraint: middle metacarpal along
        # the actual forearm, with the native palm roll preserved.
        neutral = combo.align(ref_hand.apply(combo.unit(palm)), axis)*ref_hand
        bend_axis = neutral.apply(palm_frame.apply([0., 1., 0.]))

        def guard(bend, roll):
            return (R.from_rotvec(axis*np.radians(roll))*
                    R.from_rotvec(bend_axis*np.radians(bend))*neutral).as_quat()

        length = (len(frames)-1)/clip['rate']
        clock = np.array([0., .16, .27, .367, .45, .70, length])
        keys = np.asarray([original[0, hand, 3:7], guard(4., 0.), guard(6., -4.),
                           guard(3., 3.), guard(5., 4.), guard(4., 0.), original[-1, hand, 3:7]])
        for k in range(len(frames)):
            t = k/clip['rate']
            segment = min(max(0, np.searchsorted(clock, t, side='right')-1), len(clock)-2)
            weight = combo.ease((t-clock[segment])/(clock[segment+1]-clock[segment]))
            frames[k, hand, 3:7] = combo.slerp(keys[segment], keys[segment+1], weight)

        # Recompute only the two left forearm helpers from the corrected wrist.
        # These are native MetaHuman helper stations already used by this take;
        # applying the old V4 twists would leave a visibly wound-up forearm.
        redistributed = body.twists(frames.copy())
        edited = ['hand_l', 'lowerarm_twist_01_l', 'lowerarm_twist_02_l']
        for name in edited[1:]:
            i = body.ix[name]
            frames[:, i, 3:7] = redistributed[:, i, 3:7]
        frames[0] = original[0]
        frames[-1] = original[-1]
        # Choose continuous signs in these rotation tracks for editable curves.
        for name in edited:
            i = body.ix[name]
            for k in range(1, len(frames)):
                if np.dot(frames[k-1, i, 3:7], frames[k, i, 3:7]) < 0:
                    frames[k, i, 3:7] *= -1

        compressed = np.asarray(current['compressed']['frames'])
        arm = combo.unit(compressed[:, 1, :3]-compressed[:, 0, :3])
        palm_vector = combo.unit(compressed[:, 2, :3]-compressed[:, 1, :3])
        compressed_bend = np.degrees(np.arccos(np.clip(np.sum(arm*palm_vector, axis=1), -1, 1)))
        clip['frames'] = frames.tolist()
        clip['source'] = current['asset']+' / native forearm-relative wrist correction'
        clip['adaptation'] = ('Closed left guard aligned to each native forearm with small timed wrist give; '
                              'left twist helpers recomputed; V4 fingers, shoulder/elbow/wrist positions, '
                              'right blade, body, feet, contact/release and endpoint poses retained.')
        result = dict(mesh=target['mesh'], names=target['names'], parents=target['parents'], clips={'Thrust': clip})
        (OUT/(label+'-actions.json')).write_text(json.dumps(result, separators=(',', ':')))
        receipt['bodies'][label] = dict(mesh=target['mesh'], previous_thrust=current['asset'],
            edited_rotation_tracks=edited, frames=len(frames), rate=clip['rate'], seconds=length,
            source_before=wrist_measurements(body, original),
            compressed_before_max_palm_forearm_angle_deg=float(compressed_bend.max()),
            authored_after=wrist_measurements(body, frames))
        print('KUKRI_THRUST_WRIST_AUTHORED '+label+' '+json.dumps(receipt['bodies'][label]['authored_after']), flush=True)
    (OUT/'authoring.json').write_text(json.dumps(receipt, indent=2))


if __name__ == '__main__':
    author()
