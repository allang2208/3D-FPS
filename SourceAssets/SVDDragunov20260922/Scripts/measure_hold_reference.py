"""Measure the real hold: where the hands sit relative to WPN_root in an animated pose.

The M4 viewmodel FBX's bind pose does not hold the weapon (verified: the M4 floats above
the arms in rest), so the contacts must come from an animation. All project weapons share
the same Manny arms and the same WPN_* bones, so any project idle gives the hand positions
relative to WPN_root - which is exactly what a new weapon has to match.

Run:
    "E:/Program Files/Blender Foundation/Blender 5.1/blender.exe" --background --factory-startup \
        --python <this file> -- <case_root> [animation.fbx]
"""
import json
import math
import sys
from pathlib import Path

import bpy
from mathutils import Vector

KEY = ['WPN_root', 'WPN_SOCKET_Magazine', 'WPN_Trigger', 'WPN_ChargingHandle', 'WPN_bolt',
       'WPN_SOCKET_Muzzle', 'ik_hand_gun', 'hand_r', 'hand_l', 'lowerarm_r', 'lowerarm_l',
       'thumb_01_r', 'index_01_r', 'index_03_r', 'thumb_01_l', 'index_01_l', 'index_03_l']


def main():
    args = sys.argv[sys.argv.index("--") + 1:]
    case = Path(args[0])
    anim = Path(args[1]) if len(args) > 1 else Path('D:/FPS3D/FPSGAME/SourceAssets/AKM/A_AKM_idle.fbx')
    if not anim.exists():
        raise RuntimeError('animation not found: %s' % anim)

    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.fbx(filepath=str(anim))
    scene = bpy.context.scene
    bpy.context.view_layer.update()

    armature = next((o for o in scene.objects if o.type == 'ARMATURE'), None)
    if armature is None:
        raise RuntimeError('no armature in %s' % anim)

    actions = [a.name for a in bpy.data.actions]
    frames = []
    for action in bpy.data.actions:
        rng = action.frame_range
        frames.append((action.name, rng[0], rng[1]))
    report = {'animation': str(anim), 'armature': armature.name, 'actions': frames,
              'objects': [o.name for o in scene.objects]}

    if frames:
        name, start, end = frames[0]
        mid = start + (end - start) / 2.0
        scene.frame_set(int(round(mid)))
        bpy.context.view_layer.update()
        report['sampled_frame'] = int(round(mid))

    def bone_point(name, which='head'):
        pb = armature.pose.bones.get(name)
        if pb is None:
            return None
        local = pb.head if which == 'head' else pb.tail
        return armature.matrix_world @ local

    root = bone_point('WPN_root')
    report['bones_world'] = {}
    report['bones_relative_to_wpn_root'] = {}
    for name in KEY:
        p = bone_point(name)
        if p is None:
            continue
        report['bones_world'][name] = [round(v, 5) for v in p]
        if root is not None:
            rel = p - root
            report['bones_relative_to_wpn_root'][name] = [round(v, 5) for v in rel]

    # palm centres: average of the hand bone's head and the index/thumb bases
    for side in ('r', 'l'):
        pts = [bone_point(n) for n in ('hand_%s' % side, 'thumb_01_%s' % side, 'index_01_%s' % side)]
        pts = [p for p in pts if p is not None]
        if pts and root is not None:
            palm = sum(pts, Vector((0, 0, 0))) / len(pts)
            report['palm_%s_relative_to_wpn_root' % side] = [round(v, 5) for v in (palm - root)]
            report['palm_%s_world' % side] = [round(v, 5) for v in palm]
            report['palm_%s_distance_to_wpn_root_cm' % side] = round((palm - root).length * 100, 2)

    (case / 'Receipts' / 'hold_reference.json').write_text(json.dumps(report, indent=2, default=str), encoding='utf-8')
    print('HOLD_REF', json.dumps(report, default=str))


main()
