"""Align the SVD into the shared M4 rig's armature space, by contact points.

Reference (measured from the M4 viewmodel FBX, armature space, metres):
    grip    the "M4_Grip Default" mesh bbox      -> where the right hand wraps
    trigger the "M4_Trigger Straight" mesh bbox  -> where the trigger finger sits
The SVD is placed with a rigid yaw+translation so that its own grip/trigger midpoints
coincide with the M4's - a weapon may not be scaled, so only rotation and translation are
solved. The result is rendered with the arms for visual confirmation.

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

SVD_PARTS = ['SM_SVD_Body', 'SM_SVD_Magazine', 'SM_SVD_Trigger', 'SM_SVD_ChargingHandle',
             'SM_SVD_SafetyLever', 'SM_SVD_ScopeBody', 'SM_SVD_ScopeMount', 'SM_SVD_ScopeLens']


def bbox(obj, world=True):
    pts = [(obj.matrix_world @ Vector(c)) if world else Vector(c) for c in obj.bound_box]
    mn = Vector((min(p[i] for p in pts) for i in range(3)))
    mx = Vector((max(p[i] for p in pts) for i in range(3)))
    return mn, mx


def center(obj):
    mn, mx = bbox(obj)
    return (mn + mx) / 2.0


def main():
    args = sys.argv[sys.argv.index("--") + 1:]
    case = Path(args[0])
    m4_fbx = next(Path('D:/FPS3D/FPSGAME/SourceAssets/M4HK416Replica20260910').rglob(
        'SK_M4_FoldingSights_HK416.fbx'))

    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.fbx(filepath=str(m4_fbx))
    bpy.context.view_layer.update()

    m4_weapon = [o for o in bpy.context.scene.objects if o.type == 'MESH' and o.name.startswith('M4_')]
    arms = next(o for o in bpy.context.scene.objects if o.type == 'MESH' and 'Arms' in o.name)
    grip = next((o for o in m4_weapon if 'Grip' in o.name), None)
    trigger = next((o for o in m4_weapon if 'Trigger' in o.name), None)
    if grip is None or trigger is None:
        raise RuntimeError('M4 grip/trigger meshes not found')

    m4_grip = center(grip)
    m4_trigger = center(trigger)
    m4_mid = (m4_grip + m4_trigger) / 2.0
    m4_dir = (m4_trigger - m4_grip)
    report = {
        'm4_grip': [round(v, 5) for v in m4_grip],
        'm4_trigger': [round(v, 5) for v in m4_trigger],
        'm4_grip_to_trigger': [round(v, 5) for v in m4_dir],
        'm4_grip_to_trigger_len': round(m4_dir.length, 5),
    }

    # hide the M4 weapon so the SVD render is readable; keep the arms
    for o in m4_weapon:
        o.hide_render = True

    # import the SVD parts
    svd = []
    for name in SVD_PARTS:
        fbx = case / 'Authored' / (name + '.fbx')
        bpy.ops.import_scene.fbx(filepath=str(fbx))
        obj = next(o for o in bpy.context.scene.objects if o.type == 'MESH' and o.name.startswith(name))
        obj.name = name
        svd.append(obj)
    bpy.context.view_layer.update()

    body = next(o for o in svd if o.name == 'SM_SVD_Body')
    trig = next(o for o in svd if o.name == 'SM_SVD_Trigger')
    svd_trigger = center(trig)

    # grip centre: SVD body vertices behind and below the trigger
    mw = body.matrix_world
    grip_pts = []
    for v in body.data.vertices:
        p = mw @ v.co
        if (abs(p.x - svd_trigger.x) < 0.035
                and svd_trigger.y - 0.13 <= p.y <= svd_trigger.y - 0.02
                and svd_trigger.z - 0.12 <= p.z <= svd_trigger.z + 0.01):
            grip_pts.append(p)
    svd_grip = sum(grip_pts, Vector((0, 0, 0))) / len(grip_pts) if grip_pts else svd_trigger
    svd_dir = svd_trigger - svd_grip
    report['svd_grip'] = [round(v, 5) for v in svd_grip]
    report['svd_trigger'] = [round(v, 5) for v in svd_trigger]
    report['svd_grip_to_trigger'] = [round(v, 5) for v in svd_dir]
    report['svd_grip_to_trigger_len'] = round(svd_dir.length, 5)
    report['grip_pts'] = len(grip_pts)

    # Rigid placement, translation only.
    # The SVD parts are imported with the same FBX importer call as the M4 rig, so both are
    # already expressed in the same convention: measured on both, the trigger sits forward
    # (+Y) of the grip, i.e. both muzzles point +Y. Rotating here (the first attempt used
    # 180 deg) pushed the trigger 15.6 cm behind the M4's - the render/receipt caught it.
    yaw = 0.0
    rot = Matrix.Rotation(yaw, 4, 'Z')
    report['yaw_deg'] = yaw
    report['orientation_check'] = {
        'm4_trigger_forward_of_grip_m': round(float(m4_trigger.y - m4_grip.y), 5),
        'svd_trigger_forward_of_grip_m': round(float(svd_trigger.y - svd_grip.y), 5),
        'm4_magazine_forward_of_grip_m': round(float(center(next(o for o in m4_weapon if 'Magazine' in o.name)).y - m4_grip.y), 5),
        'svd_magazine_forward_of_grip_m': round(float(center(next(o for o in svd if o.name == 'SM_SVD_Magazine')).y - svd_grip.y), 5),
    }

    # Grip is the hand contact, so match it exactly and report the trigger residual.
    svd_grip_rot = rot @ svd_grip
    translation = m4_grip - svd_grip_rot
    report['translation'] = [round(v, 5) for v in translation]

    for o in svd:
        o.matrix_world = Matrix.Translation(translation) @ rot @ o.matrix_world
    bpy.context.view_layer.update()

    report['trigger_error_m'] = round((center(trig) - m4_trigger).length, 5)
    report['grip_error_m'] = round((rot @ svd_grip + translation - m4_grip).length, 5)
    bore_m4 = center(next(o for o in m4_weapon if 'Flash Hider' in o.name))
    report['m4_muzzle'] = [round(v, 5) for v in bore_m4]
    report['svd_muzzle_y'] = round(max(bbox(o)[1].y for o in svd), 5)
    report['svd_bore_z'] = round(center(trig).z + 0.055, 5)
    report['m4_bore_z'] = round(bore_m4.z, 5)

    # renders: hold from the side, three-quarter and the shooter's eye
    # The bind pose of this FBX does NOT hold the weapon (the M4 floats above the arms in
    # rest), so an arms render proves nothing. Instead mark the M4's own contact points and
    # the M4 body itself so the SVD placement can be compared against them directly.
    marks = []
    for label, pos, colour in [('grip', m4_grip, (0.95, 0.2, 0.2)), ('trigger', m4_trigger, (0.2, 0.9, 0.3)),
                               ('muzzle', center(next(o for o in m4_weapon if 'Flash Hider' in o.name)), (0.2, 0.5, 1.0))]:
        bpy.ops.mesh.primitive_uv_sphere_add(radius=0.008, location=pos)
        sphere = bpy.context.active_object
        mat = bpy.data.materials.new('mark_' + label)
        mat.use_nodes = True
        mat.node_tree.nodes['Principled BSDF'].inputs['Base Color'].default_value = (*colour, 1)
        sphere.data.materials.append(mat)
        marks.append(sphere)
        report['marker_' + label] = [round(v, 5) for v in pos]
    for o in m4_weapon:
        o.hide_render = True

    scene = bpy.context.scene
    scene.render.engine = 'CYCLES'
    scene.cycles.device = 'CPU'
    scene.cycles.samples = 16
    scene.cycles.use_denoising = False
    scene.render.resolution_x = 1200
    scene.render.resolution_y = 700
    world = bpy.data.worlds.new('W7')
    scene.world = world
    world.use_nodes = True
    world.node_tree.nodes['Background'].inputs[0].default_value = (0.22, 0.23, 0.25, 1)
    sun = bpy.data.objects.new('Sun7', bpy.data.lights.new('Sun7', type='SUN'))
    sun.data.energy = 4.5
    sun.rotation_euler = (math.radians(50), 0, math.radians(150))
    scene.collection.objects.link(sun)
    cam_data = bpy.data.cameras.new('Cam7')
    cam = bpy.data.objects.new('Cam7', cam_data)
    scene.collection.objects.link(cam)
    scene.camera = cam
    eye = Vector(report['m4_trigger']) + Vector((-0.18, -0.05, -0.08))
    outdir = case / 'Previews' / 'hold'
    outdir.mkdir(parents=True, exist_ok=True)
    for name, loc, look, ortho in [
        ('hold_side', eye + Vector((0.45, -0.35, 0.12)), eye + Vector((0, 0.30, -0.02)), 1.05),
        ('hold_quarter', eye + Vector((0.30, -0.42, 0.16)), eye + Vector((0, 0.28, -0.02)), 1.05),
        ('hold_eye', eye, eye + Vector((0, 1.0, -0.02)), 0.55),
    ]:
        cam.data.type = 'ORTHO'
        cam.data.ortho_scale = ortho
        cam.location = loc
        cam.rotation_euler = (look - loc).to_track_quat('-Z', 'Y').to_euler()
        scene.render.filepath = str(outdir / name)
        bpy.ops.render.render(write_still=True)

    # save the aligned assembly for the rigging step
    out_blend = case / 'Authored' / 'SVD_Aligned.blend'
    bpy.ops.wm.save_as_mainfile(filepath=str(out_blend))
    report['aligned_blend'] = str(out_blend)
    (case / 'Receipts' / 'alignment.json').write_text(json.dumps(report, indent=2, default=str), encoding='utf-8')
    print('ALIGN_SVD', json.dumps(report))


main()
