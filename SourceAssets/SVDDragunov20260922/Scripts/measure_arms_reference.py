"""Measure the shared arms + M4 rig: where the hands hold the weapon and where the
mechanical bones sit. This is the reference the SVD has to be aligned against.

Reads the M4 viewmodel source FBX (arms + weapon + SK_M4_Infima skeleton), reports the
key bone rest transforms in armature space, the weapon mesh placement, and renders a
side/eye view of the hold so the alignment can be judged.

Run:
    "E:/Program Files/Blender Foundation/Blender 5.1/blender.exe" --background --factory-startup \
        --python <this file> -- <case_root>
"""
import json
import math
import sys
from pathlib import Path

import bpy
from mathutils import Vector

KEY_BONES = ['WPN_root', 'WPN_SOCKET_Magazine', 'WPN_Trigger', 'WPN_bolt', 'WPN_ChargingHandle',
             'WPN_BoltCatch', 'WPN_SOCKET_Muzzle', 'WPN_SOCKET_Eject', 'WPN_RearSight',
             'WPN_FrontSight', 'ik_hand_gun', 'ik_hand_l', 'ik_hand_r', 'hand_r', 'hand_l',
             'lowerarm_r', 'lowerarm_l', 'head', 'neck_01']


def main():
    args = sys.argv[sys.argv.index("--") + 1:]
    case = Path(args[0])
    src_root = Path('D:/FPS3D/FPSGAME/SourceAssets/M4HK416Replica20260910')
    fbx = next(src_root.rglob('SK_M4_FoldingSights_HK416.fbx'), None)
    if fbx is None:
        raise RuntimeError('M4 viewmodel FBX not found under %s' % src_root)
    print('M4_FBX', fbx)

    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.fbx(filepath=str(fbx))
    bpy.context.view_layer.update()

    armature = next((o for o in bpy.context.scene.objects if o.type == 'ARMATURE'), None)
    if armature is None:
        raise RuntimeError('no armature in %s' % fbx)
    meshes = [o for o in bpy.context.scene.objects if o.type == 'MESH']

    report = {'fbx': str(fbx), 'armature': armature.name,
              'armature_matrix': [round(v, 5) for row in armature.matrix_world for v in row],
              'bones': {}, 'meshes': []}

    for name in KEY_BONES:
        bone = armature.data.bones.get(name)
        if not bone:
            report['bones'][name] = None
            continue
        head = armature.matrix_world @ bone.head_local
        tail = armature.matrix_world @ bone.tail_local
        report['bones'][name] = {
            'head': [round(v, 5) for v in head], 'tail': [round(v, 5) for v in tail],
            'length': round(bone.length, 5),
            'parent': bone.parent.name if bone.parent else None,
        }

    for o in meshes:
        pts = [o.matrix_world @ Vector(c) for c in o.bound_box]
        mn = [min(p[i] for p in pts) for i in range(3)]
        mx = [max(p[i] for p in pts) for i in range(3)]
        entry = {'name': o.name, 'verts': len(o.data.vertices),
                 'bbox_min': [round(v, 5) for v in mn], 'bbox_max': [round(v, 5) for v in mx],
                 'size': [round(mx[i] - mn[i], 5) for i in range(3)],
                 'materials': [s.material.name if s.material else None for s in o.material_slots]}
        # which vertex groups dominate -> tells which bones drive this mesh
        groups = sorted(((g.name, sum(1 for v in o.data.vertices if any(
            ge.group == g.index and ge.weight > 0.5 for ge in v.groups))) for g in o.vertex_groups),
            key=lambda kv: -kv[1])[:8]
        entry['top_vertex_groups'] = [g for g in groups if g[1] > 0]
        report['meshes'].append(entry)

    print('ARM_BONES', json.dumps({k: v for k, v in report['bones'].items() if v}))
    for m in report['meshes']:
        print('ARM_MESH', json.dumps(m))

    # reference renders: side view of the hold and the eye view
    scene = bpy.context.scene
    scene.render.engine = 'CYCLES'
    scene.cycles.device = 'CPU'
    scene.cycles.samples = 12
    scene.cycles.use_denoising = False
    scene.render.resolution_x = 1100
    scene.render.resolution_y = 620
    world = bpy.data.worlds.new('W6')
    scene.world = world
    world.use_nodes = True
    world.node_tree.nodes['Background'].inputs[0].default_value = (0.22, 0.23, 0.25, 1)
    sun = bpy.data.objects.new('Sun6', bpy.data.lights.new('Sun6', type='SUN'))
    sun.data.energy = 4.0
    sun.rotation_euler = (math.radians(52), 0, math.radians(140))
    scene.collection.objects.link(sun)
    cam_data = bpy.data.cameras.new('Cam6')
    cam = bpy.data.objects.new('Cam6', cam_data)
    scene.collection.objects.link(cam)
    scene.camera = cam
    head = report['bones'].get('head') or report['bones'].get('neck_01')
    centre = Vector(head['head']) if head else Vector((0, 0, 0))
    outdir = case / 'Previews' / 'arms_ref'
    outdir.mkdir(parents=True, exist_ok=True)
    for name, offset, ortho, lens in [
        ('hold_side', (120, 0, 0), 90.0, None),
        ('hold_three_quarter', (80, -80, 30), 90.0, None),
        ('eye_view', (0, 0, 0), None, 70.0),
    ]:
        cam.data.type = 'ORTHO' if ortho else 'PERSP'
        if ortho:
            cam.data.ortho_scale = ortho
            cam.location = centre + Vector(offset)
            direction = (centre - cam.location).normalized()
        else:
            cam.data.lens = lens
            cam.location = centre + Vector((35, 0, 0))
            direction = (centre + Vector((120, 0, -10)) - cam.location).normalized()
        cam.rotation_euler = direction.to_track_quat('-Z', 'Y').to_euler()
        scene.render.filepath = str(outdir / name)
        bpy.ops.render.render(write_still=True)

    (case / 'Receipts' / 'arms_reference.json').write_text(json.dumps(report, indent=2, default=str), encoding='utf-8')


main()
