"""Finish the weapon-space measurements the SVD asset header needs.

Reports, in the WEAPON's own space (the frame FPSGAMECharacter's Rear/Front calibration and
MuzzleBackOffset are expressed in): the muzzle tip, the WPN_SOCKET_Muzzle bone, WPN_root and
WPN_Trigger, plus the scope's optical axis. Only the animated pose puts the bones where the
game actually uses them, so the AKM idle is sampled.

Run:
    "E:/Program Files/Blender Foundation/Blender 5.1/blender.exe" --background --factory-startup \
        --python <this file> -- <case_root>
"""
import json
import math
import sys
from pathlib import Path

import bpy
from mathutils import Matrix, Vector

PARTS = ['SM_SVD_Body', 'SM_SVD_ScopeLens', 'SM_SVD_ScopeBody', 'SM_SVD_Trigger']


def bbox(obj):
    pts = [obj.matrix_world @ Vector(c) for c in obj.bound_box]
    mn = Vector((min(p[i] for p in pts) for i in range(3)))
    mx = Vector((max(p[i] for p in pts) for i in range(3)))
    return mn, mx


def main():
    args = sys.argv[sys.argv.index("--") + 1:]
    case = Path(args[0])
    anim = Path('D:/FPS3D/FPSGAME/SourceAssets/AKM/A_AKM_idle.fbx')

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
    inv = placement.inverted()

    for name in PARTS:
        bpy.ops.import_scene.fbx(filepath=str(case / 'Authored' / (name + '.fbx')))
        obj = next(o for o in bpy.context.scene.objects if o.type == 'MESH' and o.name.startswith(name))
        obj.name = name
        obj.matrix_world = placement @ obj.matrix_world
    bpy.context.view_layer.update()

    def bone_model(name):
        pb = armature.pose.bones.get(name)
        if not pb:
            return None
        return inv @ (armature.matrix_world @ pb.head)

    body = bpy.context.scene.objects['SM_SVD_Body']
    mn, mx = bbox(body)
    # muzzle tip: the extreme +Y point of the body, sampled from real vertices
    tip = max(((body.matrix_world @ v.co) for v in body.data.vertices), key=lambda p: p.y)
    lens_mn, lens_mx = bbox(bpy.context.scene.objects['SM_SVD_ScopeLens'])
    axis = (lens_mn + lens_mx) / 2.0

    def cm(p):
        return [round(v * 100, 2) for v in inv @ p] if p is not None else None

    muzzle_socket = bone_model('WPN_SOCKET_Muzzle')
    magazine_socket = bone_model('WPN_SOCKET_Magazine')
    magazine = bpy.context.scene.objects.get('SM_SVD_Magazine')
    report = {
        'model_space_cm': {
            'muzzle_tip': cm(tip),
            'WPN_SOCKET_Muzzle': cm(muzzle_socket),
            'WPN_SOCKET_Magazine': cm(magazine_socket),
            'magazine_center': cm(sum((magazine.matrix_world @ Vector(c) for c in magazine.bound_box), Vector()) / 8.0) if magazine else None,
            'WPN_root': cm(bone_model('WPN_root')),
            'WPN_bolt': cm(bone_model('WPN_bolt')),
            'WPN_BoltCatch': cm(bone_model('WPN_BoltCatch')),
            'WPN_RearSight': cm(bone_model('WPN_RearSight')),
            'WPN_FrontSight': cm(bone_model('WPN_FrontSight')),
            'WPN_Trigger': cm(bone_model('WPN_Trigger')),
            'WPN_ChargingHandle': cm(bone_model('WPN_ChargingHandle')),
            'scope_axis_center': cm(axis),
            'scope_ocular_end': cm(Vector((axis.x, lens_mn.y, axis.z))),
            'scope_objective_end': cm(Vector((axis.x, lens_mx.y, axis.z))),
        },
        'body_y_range_cm': [round((inv @ p).y * 100, 2) for p in (Vector((tip.x, mn.y, tip.z)), tip)],
    }
    if magazine is not None and magazine_socket is not None:
        centre = sum((magazine.matrix_world @ Vector(c) for c in magazine.bound_box), Vector()) / 8.0
        delta = (inv @ centre) - (inv @ magazine_socket)
        report['magazine_relative_to_socket_cm'] = [round(v * 100, 2) for v in delta]
    if muzzle_socket is not None:
        report['muzzle_back_offset_cm'] = round((tip - muzzle_socket).length * 100, 2)
        report['muzzle_axis_delta_cm'] = [round(v * 100, 2) for v in (inv @ tip) - (inv @ muzzle_socket)]
    (case / 'Receipts' / 'weapon_space.json').write_text(json.dumps(report, indent=2, default=str), encoding='utf-8')
    print('WEAPON_SPACE', json.dumps(report, default=str))


main()
