"""Keep the V17 original skin/UV/reference and author bounded gill contact inputs."""
import copy
import json
from pathlib import Path
import shutil

ROOT = Path('D:/FPS3D/FPSGAME/SourceAssets/BlindSupplicantM07Meshy20261001')
OUT = ROOT / 'BodyMotionV18/Cloth'


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    skin = json.loads((ROOT / 'LegJointsV17/Skin/leg_skin_manifest_v17.json').read_text(encoding='utf-8-sig'))
    export = OUT / 'SK_M07_Display_BodyMotionV18.fbx'
    shutil.copy2(skin['display_fbx'], export)
    skin.update(revision='BodyMotionV18', display_fbx=str(export),
                previous_skin_revision='LegJointsV17', geometry_modified=False,
                weights_modified=False, uv_modified=False, reference_pose_modified=False,
                ue_imported=False, ue_saved=False, user_review_pending=True)
    for key in ('ue_save_receipt', 'ue_display_asset'):
        skin.pop(key, None)
    (OUT / 'original_skin_manifest_v18.json').write_text(json.dumps(skin, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')

    cloth = json.loads((ROOT / 'RecoveryOriginalV13/cloth_ue_manifest_original_v13.json').read_text(encoding='utf-8-sig'))
    capsules = cloth['collision_capsules']
    # Separate body hit/ragdoll shapes remain untouched. These are only the
    # six-island cloth's animated kinematic contact shapes.
    keep = {'pelvis', 'ribcage', 'upper_chest', 'shoulder_span', 'upperarm', 'forearm', 'thigh', 'shin'}
    reduced = [copy.deepcopy(c) for c in capsules if c['region'] in keep]
    for c in reduced:
        if c['region'] == 'upperarm':
            c['radius_cm'] += .8
        elif c['region'] == 'forearm':
            c['radius_cm'] = 8.1  # includes the original cuff without a second capsule
    # A palm envelope replaces two palm tubes and the small thumb shape. The
    # distal finger animation stays independent; no rigid finger bodies added.
    for side in ('l', 'r'):
        palms = [c for c in capsules if c['bone'] == 'hand_' + side]
        hand = copy.deepcopy(palms[0])
        for key in ('a_cm', 'b_cm', 'a_reference_cm', 'b_reference_cm'):
            hand[key] = [sum(c[key][axis] for c in palms)/len(palms) for axis in range(3)]
        separation = sum((palms[0]['b_reference_cm'][i]-palms[1]['b_reference_cm'][i])**2 for i in range(3))**.5
        hand['radius_cm'] = separation*.5 + max(c['radius_cm'] for c in palms)
        hand['region'] = 'palm_envelope'
        hand['driver'] = 'Animated hand bone; bounded palm envelope; fingers remain articulated'
        reduced.append(hand)
    cloth['collision_capsules'] = reduced
    # Give the moving membrane room to respond, tapering to unchanged fixed
    # roots. Vertices, triangles, island labels and pin ownership are unchanged.
    for panel in cloth['panels']:
        limit = {'01': 28., '04': 28., '02': 22., '05': 22., '03': 16., '06': 16.}[panel['id']]
        maximum = max(panel['max_distance_cm'])
        panel['max_distance_cm'] = [d*limit/maximum if d > 0 else 0. for d in panel['max_distance_cm']]
        panel['proxy_revision'] = 'V18 retained V13 topology, same pins, tapered contact travel'
    cloth.update(revision='BodyMotionV18', previous_revision='OriginalV13',
                 method='Original six-island proxy and stable leaf mapping; 14 kinematic capsules; local bone clearance plus bounded secondary cloth',
                 solver_substeps=1, solver_iterations=4, solver_max_iterations=6,
                 particle_face_self_collision=False, sphere_self_repulsion=True,
                 geometry_modified=False, proxy_topology_modified=False,
                 cloth_resume_distance_cm=650., cloth_suspend_distance_cm=850.,
                 tested=False, runtime_tested=False, rendered=False,
                 previous_collision_capsules=len(capsules), collision_capsule_count=len(reduced))
    path = OUT / 'cloth_ue_manifest_v18.json'
    path.write_text(json.dumps(cloth, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print('M07_V18_ORIGINAL_SKIN_AND_CLOTH_INPUTS ' + str(path), flush=True)


if __name__ == '__main__':
    main()
