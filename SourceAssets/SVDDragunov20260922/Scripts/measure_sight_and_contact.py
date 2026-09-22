"""Measure the SVD's own sight points and finger contact in the rig frame.

The ADS calibration (FPSGAMECharacter.cpp ~2708) takes Rear/Front as points in the WEAPON's
local space and puts the camera EyeDistance in front of Rear along the sight axis; the AKM
supplies its own pair (AKMSoviet::Rear/Front) instead of using the shared sight bones. So a
new weapon needs: (a) its optic's axis and ocular point in model space, (b) where the
animated trigger finger actually falls.

Run:
    "E:/Program Files/Blender Foundation/Blender 5.1/blender.exe" --background --factory-startup \
        --python <this file> -- <case_root> [animation.fbx]
"""
import json
import math
import sys
from pathlib import Path

import bpy
from mathutils import Matrix, Vector

PARTS = ['SM_SVD_Body', 'SM_SVD_Magazine', 'SM_SVD_Trigger', 'SM_SVD_ChargingHandle',
         'SM_SVD_SafetyLever', 'SM_SVD_ScopeBody', 'SM_SVD_ScopeMount', 'SM_SVD_ScopeLens']


def bbox(obj):
    pts = [obj.matrix_world @ Vector(c) for c in obj.bound_box]
    mn = Vector((min(p[i] for p in pts) for i in range(3)))
    mx = Vector((max(p[i] for p in pts) for i in range(3)))
    return mn, mx


def center(obj):
    mn, mx = bbox(obj)
    return (mn + mx) / 2.0


def main():
    args = sys.argv[sys.argv.index("--") + 1:]
    case = Path(args[0])
    anim = Path(args[1]) if len(args) > 1 else Path('D:/FPS3D/FPSGAME/SourceAssets/AKM/A_AKM_idle.fbx')

    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.fbx(filepath=str(anim))
    bpy.context.view_layer.update()
    armature = next(o for o in bpy.context.scene.objects if o.type == 'ARMATURE')
    scene = bpy.context.scene
    if bpy.data.actions:
        start, end = bpy.data.actions[0].frame_range
        scene.frame_set(int(round(start + (end - start) / 2.0)))
        bpy.context.view_layer.update()

    ref = json.loads((case / 'Receipts' / 'alignment.json').read_text(encoding='utf-8-sig'))
    placement = Matrix.Translation(Vector(ref['translation'])) @ Matrix.Rotation(math.radians(ref['yaw_deg']), 4, 'Z')

    svd = {}
    for name in PARTS:
        bpy.ops.import_scene.fbx(filepath=str(case / 'Authored' / (name + '.fbx')))
        obj = next(o for o in bpy.context.scene.objects if o.type == 'MESH' and o.name.startswith(name))
        obj.name = name
        obj.matrix_world = placement @ obj.matrix_world
        svd[name] = obj
    bpy.context.view_layer.update()

    def bone_point(name):
        pb = armature.pose.bones.get(name)
        return armature.matrix_world @ pb.head if pb else None

    lens_mn, lens_mx = bbox(svd['SM_SVD_ScopeLens'])
    scope_mn, scope_mx = bbox(svd['SM_SVD_ScopeBody'])
    trigger = center(svd['SM_SVD_Trigger'])
    muzzle_y = bbox(svd['SM_SVD_Body'])[1].y

    # model-space (weapon-local) coordinates: undo the placement transform
    inv = placement.inverted()
    to_model = lambda p: inv @ p  # noqa: E731

    report = {
        'animation': str(anim),
        'rig_frame': {
            'scope_axis_point_cm': [round(v * 100, 2) for v in center(svd['SM_SVD_ScopeLens'])],
            'ocular_end_cm': [round(v * 100, 2) for v in Vector((center(svd['SM_SVD_ScopeLens']).x, lens_mn.y, center(svd['SM_SVD_ScopeLens']).z))],
            'objective_end_cm': [round(v * 100, 2) for v in Vector((center(svd['SM_SVD_ScopeLens']).x, lens_mx.y, center(svd['SM_SVD_ScopeLens']).z))],
            'scope_body_y_range_cm': [round(scope_mn.y * 100, 2), round(scope_mx.y * 100, 2)],
            'muzzle_tip_y_cm': round(muzzle_y * 100, 2),
            'trigger_center_cm': [round(v * 100, 2) for v in trigger],
        },
        'model_space': {
            'scope_axis_point_cm': [round(v * 100, 2) for v in to_model(center(svd['SM_SVD_ScopeLens']))],
            'ocular_end_cm': [round(v * 100, 2) for v in to_model(Vector((center(svd['SM_SVD_ScopeLens']).x, lens_mn.y, center(svd['SM_SVD_ScopeLens']).z)))],
            'objective_end_cm': [round(v * 100, 2) for v in to_model(Vector((center(svd['SM_SVD_ScopeLens']).x, lens_mx.y, center(svd['SM_SVD_ScopeLens']).z)))],
            'trigger_center_cm': [round(v * 100, 2) for v in to_model(trigger)],
        },
    }

    # trigger finger contact in the animated pose
    tip = bone_point('index_03_r')
    mid = bone_point('index_02_r')
    if tip and mid:
        finger = (tip + mid) / 2.0
        delta = trigger - finger
        report['finger_contact'] = {
            'index_tip_cm': [round(v * 100, 2) for v in tip],
            'trigger_center_cm': [round(v * 100, 2) for v in trigger],
            'distance_cm': round(delta.length * 100, 2),
            'offset_cm': [round(v * 100, 2) for v in delta],
        }
    hand_r = bone_point('hand_r')
    if hand_r:
        report['right_hand_cm'] = [round(v * 100, 2) for v in hand_r]

    (case / 'Receipts' / 'sight_and_contact.json').write_text(json.dumps(report, indent=2, default=str), encoding='utf-8')
    print('SIGHT_CONTACT', json.dumps(report, default=str))


main()
