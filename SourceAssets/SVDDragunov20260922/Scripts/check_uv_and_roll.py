"""Find why the viewmodel reads as untextured, and measure the body roll for the ADS fix.

Two independent checks in one pass:

1. UV survival: re-import the exported FBX and report each object's UV layers, their area and
   whether the coordinates are degenerate. A mesh whose UVs are all (0,0) samples one texel and
   renders as a single flat colour - which looks exactly like "no texture" even though every
   material and texture in UE is correct.

2. Body roll (SKILL references/integration.md): the area-weighted normal of the weapon's top
   surface versus the up axis of its sight line. The ADS calibration only aligns the sight axis
   (FindBetweenNormals maps one axis), so any roll in the source model is what the player sees
   as a crooked gun. The fix is to rotate the assembly about the grip contact by -angle.

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

PARTS = ['SM_SVD_Body', 'SM_SVD_Magazine', 'SM_SVD_Trigger', 'SM_SVD_ChargingHandle',
         'SM_SVD_SafetyLever', 'SM_SVD_ScopeBody', 'SM_SVD_ScopeMount', 'SM_SVD_ScopeLens']


def uv_report(obj, label):
    mesh = obj.data
    layers = [layer.name for layer in mesh.uv_layers]
    entry = {'object': label, 'uv_layers': layers, 'polys': len(mesh.polygons)}
    if not layers:
        entry['verdict'] = 'NO UV LAYER'
        return entry
    layer = mesh.uv_layers[0]
    us = [d.uv[0] for d in layer.data]
    vs = [d.uv[1] for d in layer.data]
    entry['u_range'] = [round(min(us), 4), round(max(us), 4)]
    entry['v_range'] = [round(min(vs), 4), round(max(vs), 4)]
    entry['span'] = [round(max(us) - min(us), 4), round(max(vs) - min(vs), 4)]
    entry['distinct_uvs'] = len({(round(d.uv[0], 4), round(d.uv[1], 4)) for d in layer.data})
    entry['verdict'] = ('degenerate' if entry['span'][0] < 1e-4 and entry['span'][1] < 1e-4
                        else 'ok' if entry['distinct_uvs'] > 10 else 'suspicious')
    return entry


def main():
    args = sys.argv[sys.argv.index("--") + 1:]
    case = Path(args[0])
    report = {'viewmodel_fbx': str(case / 'Authored' / 'SK_SVD_Manny.fbx'), 'uv': [], 'roll': {}}

    # --- 1. does the exported viewmodel FBX still carry UVs? ---
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.fbx(filepath=str(case / 'Authored' / 'SK_SVD_Manny.fbx'))
    bpy.context.view_layer.update()
    for obj in sorted((o for o in bpy.context.scene.objects if o.type == 'MESH'), key=lambda o: o.name):
        label = 'arms' if 'Arm' in obj.name or 'Manny' in obj.name else obj.name
        report['uv'].append(uv_report(obj, label))
    report['uv_ok'] = all(e['verdict'] == 'ok' for e in report['uv'])

    # --- 2. body roll of the assembled weapon ---
    bpy.ops.wm.read_factory_settings(use_empty=True)
    for name in PARTS:
        bpy.ops.import_scene.fbx(filepath=str(case / 'Authored' / (name + '.fbx')))
        obj = next(o for o in bpy.context.scene.objects if o.type == 'MESH' and o.name.startswith(name))
        obj.name = name
    bpy.context.view_layer.update()
    body = bpy.context.scene.objects['SM_SVD_Body']

    mesh = body.data
    mesh.calc_loop_triangles()
    weighted = Vector((0.0, 0.0, 0.0))
    area_total = 0.0
    for tri in mesh.loop_triangles:
        normal = tri.normal.copy()
        area = tri.area
        if normal.z > 0.5:                      # top-facing surfaces only
            weighted += normal * area
            area_total += area
    top_normal = weighted.normalized() if area_total > 0 else Vector((0, 0, 1))

    # sight line up: the PSO-1 axis runs along Y, so the reference up is +Z
    sight_rear = Vector((0.0186, -0.3893, 0.0942))
    sight_front = Vector((0.0186, -0.0889, 0.0942))
    axis = (sight_front - sight_rear).normalized()
    ref_up = Vector((0, 0, 1))
    # roll = how far the body's top has tilted about the sight axis
    roll_deg = math.degrees(math.atan2(top_normal.x, top_normal.z))

    report['roll'] = {
        'top_normal_area_weighted': [round(v, 5) for v in top_normal],
        'top_area_m2': round(area_total, 5),
        'sight_axis': [round(v, 5) for v in axis],
        'reference_up': [round(v, 5) for v in ref_up],
        'roll_deg_about_sight_axis': round(roll_deg, 3),
        'm4_reference_deg': {'aim': -0.03, 'idle': 0.37},
        'ash12_first_integration_deg': 3.92,
    }

    # grip contact point: rotate about it, per the SKILL
    mw = body.matrix_world
    trig = bpy.context.scene.objects['SM_SVD_Trigger']
    tmin = Vector((min((trig.matrix_world @ Vector(c))[i] for c in trig.bound_box) for i in range(3)))
    tmax = Vector((max((trig.matrix_world @ Vector(c))[i] for c in trig.bound_box) for i in range(3)))
    trigger = (tmin + tmax) / 2.0
    pts = []
    for v in body.data.vertices:
        p = mw @ v.co
        if (abs(p.x - trigger.x) < 0.035 and trigger.y - 0.13 <= p.y <= trigger.y - 0.02
                and trigger.z - 0.12 <= p.z <= trigger.z + 0.01):
            pts.append(p)
    grip = sum(pts, Vector()) / len(pts) if pts else trigger
    report['roll']['grip_contact_m'] = [round(v, 5) for v in grip]
    report['roll']['corrective_rotation_axis'] = [0, 1, 0]
    report['roll']['corrective_angle_deg'] = round(-roll_deg, 3)

    (case / 'Receipts' / 'uv_and_roll.json').write_text(json.dumps(report, indent=2, default=str), encoding='utf-8')
    print('UV_AND_ROLL ' + json.dumps(report, default=str))


main()
