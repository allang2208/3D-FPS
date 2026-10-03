"""Author V12 animated body/hand colliders and membrane travel from V11.

Production only: read the original connected V11 body in its reference pose,
fit bounded cloth-only collision shapes, and write a new manifest. No geometry,
UV, skeleton, actions or old master are edited; no simulation or render runs.
Invoke with Blender --background --python this_file.py.
"""
import json
from pathlib import Path

import bpy
import numpy as np

ROOT = Path('D:/FPS3D/FPSGAME/SourceAssets/BlindSupplicantM07Meshy20261001')
BASE = ROOT/'RecoveryHandsV11'
OUT = ROOT/'ArmGillCollisionV12'


def write(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding='utf-8')


def reflected(point):
    return np.asarray(point, dtype=np.float64)*np.asarray([1., -1., 1.])


def prepare():
    OUT.mkdir(parents=True, exist_ok=True)
    source = BASE/'M07_Original_HandArm_Master_V11.blend'
    bpy.ops.wm.open_mainfile(filepath=str(source))
    rig = next(obj for obj in bpy.data.objects if obj.type == 'ARMATURE')
    rig.animation_data_clear()
    rig.data.pose_position = 'REST'
    body = bpy.data.objects['M07_OriginalBody_High']
    points = np.asarray([vertex.co[:] for vertex in body.data.vertices], dtype=np.float64)
    group_indices = {group.name: group.index for group in body.vertex_groups}
    bone_rows = {}
    for name in ('upperarm_l', 'upperarm_r', 'lowerarm_l', 'lowerarm_r'):
        index = group_indices[name]
        if name in rig.data.bones:
            bone_rows[name] = np.asarray([
                vertex.index for vertex in body.data.vertices
                if any(group.group == index and group.weight >= .18 for group in vertex.groups)
            ], dtype=np.int32)
    frames = {bone.name: np.asarray(bone.matrix_local, dtype=np.float64) for bone in rig.data.bones}
    heads = {name: matrix[:3, 3] for name, matrix in frames.items()}
    shapes = []

    def fitted_radius(name, a, b, low, high, fallback):
        selected = bone_rows.get(name, np.empty(0, np.int32))
        if not len(selected):
            return fallback, 0
        p = points[selected]
        axis = b-a
        squared = float(axis@axis)
        if squared < .0001:
            return fallback, 0
        t = (p-a)@axis/squared
        keep = (t >= .12) & (t <= .88)
        if not np.any(keep):
            return fallback, 0
        radial = np.linalg.norm(p[keep]-(a+t[keep, None]*axis), axis=1)
        radius = float(np.clip(np.percentile(radial, 98.5)+.25, low, high))
        return radius, int(keep.sum())

    def add(name, a, b, radius, region, fit_samples=0):
        # Bone-local arrays remain human-readable authoring metadata. The C++
        # V12 path consumes mesh-reference endpoints and converts using actual
        # imported reference frames, accounting for FBX post rotations/scale.
        inverse = np.linalg.inv(frames[name])
        local_a = (inverse@np.r_[a, 1.])[:3]
        local_b = (inverse@np.r_[b, 1.])[:3]
        shapes.append({
            'bone': name, 'a_cm': reflected(local_a).tolist(), 'b_cm': reflected(local_b).tolist(),
            'a_reference_cm': reflected(a).tolist(), 'b_reference_cm': reflected(b).tolist(),
            'radius_cm': float(radius), 'region': region, 'source_fit_samples': fit_samples,
            'driver': 'Animated kinematic cloth collider; no rigid finger body or animation blocking',
        })

    def segment(name, end, radius, region, fitted=None, trim=(.04, .96)):
        a, b = heads[name], heads[end]
        samples = 0
        if fitted:
            radius, samples = fitted_radius(name, a, b, *fitted, radius)
        add(name, a+(b-a)*trim[0], a+(b-a)*trim[1], radius, region, samples)

    segment('pelvis', 'spine_02', 18., 'pelvis', trim=(.2, .8))
    segment('spine_02', 'spine_05', 18., 'ribcage', trim=(.1, .9))
    segment('spine_05', 'neck_01', 17., 'upper_chest', trim=(.2, .8))
    segment('neck_01', 'head', 10., 'neck', trim=(.25, .78))
    head_axis = heads['head']-heads['neck_02']
    head_axis /= max(float(np.linalg.norm(head_axis)), 1.e-8)
    add('head', heads['head']-head_axis*3., heads['head']+head_axis*5., 17., 'sensory_head')
    shoulder_left, shoulder_right = heads['upperarm_l'], heads['upperarm_r']
    add('spine_05', shoulder_left*.88+shoulder_right*.12,
        shoulder_left*.12+shoulder_right*.88, 8., 'shoulder_span')

    for side in ('l', 'r'):
        upper, fore, hand = (name+'_'+side for name in ('upperarm', 'lowerarm', 'hand'))
        segment(upper, fore, 8., 'upperarm', fitted=(6.8, 10.5))
        segment(fore, hand, 6.2, 'forearm', fitted=(5.4, 7.3))
        # Actual joint spheres bridge bending elbow/wrist seams; the short
        # wrist capsule includes the old metal cuff without inflating the arm.
        add(fore, heads[fore], heads[fore], 6.4, 'elbow_joint')
        cuff_axis = heads[hand]-heads[fore]
        cuff_axis /= max(float(np.linalg.norm(cuff_axis)), 1.e-8)
        add(fore, heads[hand]-cuff_axis*8., heads[hand]-cuff_axis*2., 7.2, 'wrist_metal_cuff')
        add(hand, heads[hand], heads[hand], 5.2, 'wrist_joint')

        # Three overlapping channels form the ORIGINAL broad palm. One long
        # middle-finger capsule leaves the thumb/pinky edges unprotected.
        for finger in ('index', 'middle', 'pinky'):
            mcp = heads[f'{finger}_01_{side}']
            axis = mcp-heads[hand]
            add(hand, heads[hand]+axis*.16, heads[hand]+axis*.93, 3.7, 'palm_'+finger)

        for finger in ('thumb', 'index', 'middle', 'ring', 'pinky'):
            for phalanx in (1, 2, 3):
                name = f'{finger}_{phalanx:02d}_{side}'
                bone = rig.data.bones[name]
                a, b = np.asarray(bone.head_local[:]), np.asarray(bone.tail_local[:])
                radius = (2.8, 2.25, 1.55)[phalanx-1] if finger == 'thumb' else (2.25, 1.8, 1.35)[phalanx-1]
                # Joint-to-joint shaft follows this phalanx's own bone, also
                # during finger curling, rather than its palm/forearm owner.
                add(name, a+(b-a)*.06, a+(b-a)*.96, radius, f'{finger}_phalanx_{phalanx}')

        segment('thigh_'+side, 'calf_'+side, 9.5, 'thigh', trim=(.08, .93))
        segment('calf_'+side, 'foot_'+side, 6.8, 'shin', trim=(.06, .95))
        segment('foot_'+side, 'ball_'+side, 5.7, 'foot', trim=(.04, .96))

    manifest = json.loads((BASE/'cloth_ue_manifest_original_v11.json').read_text(encoding='utf-8'))
    changes = []
    for panel in manifest['panels']:
        index = int(panel['id'])-1
        previous_limit = (2.5, 1.8, 1.1)[index % 3]
        limit = (42., 34., 26.)[index % 3]
        distances = np.asarray(panel['max_distance_cm'], dtype=np.float64)
        # Retain the exact shoulder/common-fold anchors and their smooth
        # attachment-to-free profile. Release membrane travel, not its roots.
        mobility = np.clip(distances/previous_limit, 0., 1.)
        panel['max_distance_cm'] = (mobility*limit).tolist()
        panel['collision_travel_policy'] = 'Existing zero-distance shoulder/common-fold anchors retained; smooth free-leaf travel for arm deflection'
        changes.append({'id': panel['id'], 'pinned_vertices_retained': int(np.count_nonzero(distances == 0.)),
                        'previous_max_distance_cm': previous_limit, 'max_distance_cm': limit})

    manifest.update({
        'revision': 'OriginalV12ArmGillCollision', 'reference_revision': 'OriginalV11',
        'collision_capsules': shapes,
        'coordinate_frame': 'FBX/UE mesh-reference centimeters; Blender Y reflected. V12 reference endpoints are converted to each actual imported bone frame.',
        'method': manifest['method']+'; V12 dedicated animated original-body arm/palm/phalanx collision and released leaf travel, unchanged fixed roots',
        'arm_gill_collision': {
            'model_surface': 'Retained OriginalV11 body and OriginalV09 six gill surfaces, UV and simulation topology',
            'dedicated_cloth_asset': True, 'ragdoll_asset': '/Game/Monsters/BlindSupplicantM07/PA_M07_OriginalV12',
            'cloth_collision_thickness_cm': .9, 'self_collision_thickness_cm': .8,
            'ccd': True, 'solver_substeps': 3, 'solver_iterations': 7, 'solver_max_iterations': 10,
            'anim_drive_stiffness': .045, 'anim_drive_damping': .12,
            'speed_contract_cm_s': {'SlowWalk': 160., 'Chase': 360.},
            'boundary': 'Animated body shapes push mobile membranes; fixed shoulder/common-fold tissue remains skin-driven, so arm trajectories retain root clearance.',
        },
        'tested': False, 'runtime_tested': False, 'rendered': False,
    })
    destination = OUT/'cloth_ue_manifest_original_v12.json'
    write(destination, manifest)
    write(OUT/'arm_gill_collision_delivery_v12.json', {
        'revision': 'OriginalV12ArmGillCollision', 'source_master': str(source),
        'cloth_manifest': str(destination), 'source_reference_skeleton': 'SK_M07_ReferenceOriginalV11',
        'mesh': '/Game/Monsters/BlindSupplicantM07/SK_M07_OriginalV12',
        'simulation_mesh': '/Game/Monsters/BlindSupplicantM07/Working/SK_M07_ClothBuildSource_OriginalV12',
        'body_physics': '/Game/Monsters/BlindSupplicantM07/PA_M07_OriginalV12',
        'collider_shapes': len(shapes), 'collider_bones': len(set(shape['bone'] for shape in shapes)),
        'phalange_colliders': sum('phalanx' in shape['region'] for shape in shapes),
        'panel_travel': changes, 'original_geometry_uv_and_skin_unchanged': True,
        'source_model_reconstructed': False, 'simulation_topology_unchanged': True,
        'source_revision': 'V11 corrected reference retained; V09 stable per-leaf capture policy retained in V12',
        'ue_imported': False, 'tested': False, 'runtime_tested': False, 'rendered': False,
        'root_causes': [
            'Previous membrane max travel capped at 1.1 to 2.5 cm, unable to yield around a swinging forearm or palm.',
            'Previous continuous cloth used broad ragdoll hand-to-middle03 bodies, with no thumb/pinky or separate phalanx cloth collision.',
            'One solver substep and anim drive .28 pulled movable sheets toward penetrating authored positions.',
        ],
    })
    print('M07_V12_ARM_GILL_COLLISION_MANIFEST_AUTHORED '+str(destination), flush=True)


if __name__ == '__main__':
    prepare()
