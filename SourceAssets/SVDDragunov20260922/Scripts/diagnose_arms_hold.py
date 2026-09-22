"""Diagnostic: do the arms actually hold the M4 in this FBX?

The SVD hold render showed the weapon floating above the forearms, so before trusting the
alignment reference this renders the untouched M4 + arms from the same camera. If the M4
sits in the hands, the reference frame is sound and the SVD placement is what needs work;
if the M4 also floats, the FBX's arms/weapon relationship is not a usable reference.

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


def center(obj):
    pts = [obj.matrix_world @ Vector(c) for c in obj.bound_box]
    return sum(pts, Vector((0, 0, 0))) / 8.0


def main():
    args = sys.argv[sys.argv.index("--") + 1:]
    case = Path(args[0])
    m4_fbx = next(Path('D:/FPS3D/FPSGAME/SourceAssets/M4HK416Replica20260910').rglob(
        'SK_M4_FoldingSights_HK416.fbx'))

    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.fbx(filepath=str(m4_fbx))
    bpy.context.view_layer.update()

    armature = next(o for o in bpy.context.scene.objects if o.type == 'ARMATURE')
    meshes = [o for o in bpy.context.scene.objects if o.type == 'MESH']
    report = {'objects': [], 'armature_pose_position': str(armature.data.pose_position)}

    for o in meshes:
        c = center(o)
        report['objects'].append({
            'name': o.name, 'center': [round(v, 4) for v in c],
            'parent': o.parent.name if o.parent else None,
            'parent_type': o.parent_type,
            'modifiers': [m.type for m in o.modifiers],
            'hide_render': o.hide_render,
            'matrix_world_translation': [round(v, 4) for v in o.matrix_world.translation],
        })

    # hands: where are the wrist bones in world space, and how far from the M4 grip?
    grip = next((o for o in meshes if 'Grip' in o.name), None)
    hand_r = armature.data.bones.get('hand_r')
    hand_l = armature.data.bones.get('hand_l')
    for label, bone in (('hand_r', hand_r), ('hand_l', hand_l)):
        if bone:
            head = armature.matrix_world @ bone.head_local
            report[label] = [round(v, 4) for v in head]
    if grip:
        gc = center(grip)
        report['grip_center'] = [round(v, 4) for v in gc]
        if hand_r:
            hr = armature.matrix_world @ hand_r.head_local
            report['hand_r_to_grip_cm'] = round((hr - gc).length * 100, 2)

    scene = bpy.context.scene
    scene.render.engine = 'CYCLES'
    scene.cycles.device = 'CPU'
    scene.cycles.samples = 14
    scene.cycles.use_denoising = False
    scene.render.resolution_x = 1200
    scene.render.resolution_y = 700
    world = bpy.data.worlds.new('W8')
    scene.world = world
    world.use_nodes = True
    world.node_tree.nodes['Background'].inputs[0].default_value = (0.22, 0.23, 0.25, 1)
    sun = bpy.data.objects.new('Sun8', bpy.data.lights.new('Sun8', type='SUN'))
    sun.data.energy = 4.5
    sun.rotation_euler = (math.radians(50), 0, math.radians(150))
    scene.collection.objects.link(sun)
    cam_data = bpy.data.cameras.new('Cam8')
    cam = bpy.data.objects.new('Cam8', cam_data)
    scene.collection.objects.link(cam)
    scene.camera = cam
    trigger = next((o for o in meshes if 'Trigger' in o.name), None)
    eye = center(trigger) + Vector((-0.18, -0.05, -0.08)) if trigger else Vector((0, 0, 0))
    outdir = case / 'Previews' / 'arms_ref'
    outdir.mkdir(parents=True, exist_ok=True)
    for name, loc, look, ortho in [
        ('m4_hold_side', eye + Vector((0.45, -0.35, 0.12)), eye + Vector((0, 0.30, -0.02)), 1.05),
        ('m4_hold_eye', eye, eye + Vector((0, 1.0, -0.02)), 0.55),
    ]:
        cam.data.type = 'ORTHO'
        cam.data.ortho_scale = ortho
        cam.location = loc
        cam.rotation_euler = (look - loc).to_track_quat('-Z', 'Y').to_euler()
        scene.render.filepath = str(outdir / name)
        bpy.ops.render.render(write_still=True)

    (case / 'Receipts' / 'arms_hold_diagnostic.json').write_text(
        json.dumps(report, indent=2, default=str), encoding='utf-8')
    print('HOLD_DIAG', json.dumps(report, default=str))


main()
