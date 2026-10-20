"""Restore native SVD/V9 binding on the existing SVCH quick-melee animation.

Keep the existing SVCH trajectory, dynamic SVD hand pose and fingers. Restore the native SVD/V9
child offsets and segment axes. Twist helpers receive only axial rotation at
their original stations. No independent joint-position, hand-shape or weapon-motion edits.

Reference: ue5-fps-arms-animation/references/grip-arm-refinement.md;
the original-arm reconnection contract in ASH12Fix20260925.
"""
from pathlib import Path
import sys, json, copy
HERE = Path(__file__).resolve().parent
R3 = HERE.parent / 'QuickMeleeHandR3_20261019'
R2 = HERE.parent / 'QuickMeleeSVDReferenceR2_20261019'
sys.path.insert(0, str(R3))
from check_surfaces import *
from bend_plane import solve as solve_bend_plane,shift_root
HERE = Path(__file__).resolve().parent
O = HERE
clip = motion['clips']['quick_melee']
times = np.array(clip['times'])
root, hand, lower = [ids[n] for n in ('WPN_root', 'hand_r', 'lowerarm_r')]
digits = ('thumb', 'index', 'middle', 'ring', 'pinky')
chain = [j for j, n in enumerate(names) if n.endswith('_r') and n.startswith(('clavicle', 'upperarm', 'lowerarm', 'hand') + digits)]
fingers = [j for j, n in enumerate(names) if n.endswith('_r') and n.startswith(digits)]
axis = rigid(ref[lower])[:3,:3].T @ unit(ref[hand,:3,3] - ref[lower,:3,3])
rel_hand = rigid(ref[lower])[:3,:3].T @ rigid(ref[hand])[:3,:3]

def write_profile(source, poses, family):
    result = copy.deepcopy(source)
    entry = next(c for c in result['clips'] if c['base'] == clip['path'])
    tracks = []
    for j, n in enumerate(names):
        values = []
        for i, p in enumerate(poses):
            local = relative(p[parents[j]], p[j]) if parents[j] >= 0 else p[j]
            raw = np.array(clip['frames'][i][j]); v = np.zeros(10)
            v[:3] = local[:3,3] - raw[:3]
            v[3:7] = (R.from_matrix(rigid(local)[:3,:3]) * R.from_quat(raw[3:7]).inv()).as_quat()
            v[7:] = np.linalg.norm(local[:3,:3], axis=0) - raw[7:]
            if values and values[-1][3:7] @ v[3:7] < 0: v[3:7] *= -1
            values.append(v)
        ar = np.array(values)
        if np.max(abs(ar - np.array([0,0,0,0,0,0,1,0,0,0]))) > 1e-7:
            tracks.append({'bone':n, 'times':times.tolist(), 'values':np.round(ar,10).ravel().tolist()})
    entry['tracks'] = tracks
    (O/'Profiles').mkdir(exist_ok=True)
    (O/'Profiles'/f'{family}.json').write_text(json.dumps(result,separators=(',',':')))

def main():
    sequences = {}; report = {'method':'Native SVD/V9 axes and stations; approved pistol-grip digits; ASH12 exact two-bone bending-plane rotation', 'bend_plane_degrees':20, 'families':{}}
    for family in ('base','angled','vertical','canted','prism'):
        source = json.loads((R3/'SavedReadback'/f'{family}.json').read_text())
        prior = json.loads((R2/'SavedReadback'/f'{family}.json').read_text())
        old = np.array([pose('quick_melee',i,prior) for i in range(len(times))])
        fixed = np.array([pose('quick_melee',i,source) for i in range(len(times))])
        out = []
        for i, p in enumerate(old):
            q = p.copy()
            # Keep the existing trajectory. Repair only the native hierarchy,
            # following the SVD/V9 segment and twist-station contract.
            target = p[hand].copy()
            shift = target[:3,3]-q[hand,:3,3]
            for j in chain: q[j,:3,3] += shift
            q[hand] = target
            for j in fingers: q[j] = q[parents[j]] @ relative(fixed[i,parents[j]],fixed[i,j])
            upper,clavicle = ids['upperarm_r'],ids['clavicle_r']
            for main,child in [(upper,lower),(lower,hand)]:
                native_axis = rigid(ref[main])[:3,:3].T@unit(ref[child,:3,3]-ref[main,:3,3])
                current_axis = rigid(q[main])[:3,:3]@native_axis
                q[main,:3,:3] = swing(current_axis,q[child,:3,3]-q[main,:3,3])@q[main,:3,:3]
            native = relative(ref[clavicle],ref[upper])
            q[clavicle,:3,3] = q[upper,:3,3]-q[clavicle,:3,:3]@native[:3,3]
            for prefix,par in [('upperarm',upper),('lowerarm',lower)]:
                for suffix in ('01','02'):
                    j = ids[prefix+'_twist_'+suffix+'_r']; native = relative(ref[par],ref[j])
                    q[j,:3,3] = (q[par]@native)[:3,3]
                    if prefix=='upperarm': q[j,:3,:3] = (q[par]@native)[:3,:3]
            out.append(q)
        out = np.array(out)
        # Retain the existing SVD helper rotations. Only their native stations
        # were repaired above. Apply the documented ASH-12 bending-plane method
        # at a single 20-degree amount, eased over the existing action clock.
        weights=ease(0,.1,times)*(1-ease(.76,.9,times))
        out=np.array([solve_bend_plane(p,ids,names,unit,swing,20.*weights[i]) for i,p in enumerate(out)])
        # Saved native readback: 1.5 mm of the cut edge crossed the lower border
        # at ultrawide aspect during recovery. Only a 6 mm native root shift is
        # needed; do not change hand/weapon motion or force a different arm pose.
        clearance=ease(.44,.50,times)*(1-ease(.64,.71,times))
        out=np.array([shift_root(p,ids,names,unit,swing,np.array([0.,0.,-.6*clearance[i]])) for i,p in enumerate(out)])
        write_profile(source,out,family); sequences[family] = out
        report['families'][family] = {'gun_world_difference':float(np.max(abs(out[:,root]-old[:,root]))),
            'native_offset_error_cm':max(max(offsets(p).values()) for p in out),
            'hand_relative_to_gun_error':max(float(np.max(abs(relative(p[root],p[hand])-relative(f[root],f[hand])))) for p,f in zip(out,old))}
    np.savez_compressed(O/'poses.npz',**sequences)
    (O/'authoring.json').write_text(json.dumps(report,indent=2))
    print(json.dumps(report,indent=2),flush=True)

if __name__ == '__main__': main()
