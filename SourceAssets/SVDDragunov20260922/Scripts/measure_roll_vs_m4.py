"""Measure the SVD's body roll against the M4's own, using the SKILL's method.

SKILL references/integration.md: take the area-weighted normal of the weapon's TOP surface and
compare it with the up direction of the sight-markup side. The ADS calibration only aligns the
sight axis (FindBetweenNormals maps one axis), so whatever roll the mesh carries relative to the
rig is what the player sees. The M4 is the reference: measuring both meshes in the same rig
space turns "the gun looks crooked" into a number that can be baked out about the grip contact.

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

PARTS = ['SM_SVD_Body', 'SM_SVD_Magazine', 'SM_SVD_Trigger', 'SM_SVD_ChargingHandle',
         'SM_SVD_SafetyLever', 'SM_SVD_ScopeBody', 'SM_SVD_ScopeMount', 'SM_SVD_ScopeLens']


def top_normal(obj, up_axis=Vector((0, 0, 1)), min_dot=0.5):
    """Area-weighted normal of the surfaces facing `up_axis`."""
    mesh = obj.data
    mesh.calc_loop_triangles()
    mw = obj.matrix_world
    normal_matrix = mw.to_3x3().inverted().transposed()
    weighted = Vector((0.0, 0.0, 0.0))
    area = 0.0
    for tri in mesh.loop_triangles:
        n = (normal_matrix @ tri.normal).normalized()
        if n.dot(up_axis) > min_dot:
            weighted += n * tri.area
            area += tri.area
    return (weighted.normalized() if area > 0 else up_axis), area


def roll_vs(normal, up_axis, fwd_axis):
    """Roll of `normal` about `fwd_axis`, relative to the plane containing up_axis."""
    side = fwd_axis.cross(up_axis).normalized()      # right-hand lateral axis
    return math.degrees(math.atan2(normal.dot(side), normal.dot(up_axis)))


def main():
    args = sys.argv[sys.argv.index("--") + 1:]
    case = Path(args[0])
    m4_fbx = next(Path('D:/FPS3D/FPSGAME/SourceAssets/M4HK416Replica20260910').rglob(
        'SK_M4_FoldingSights_HK416.fbx'))

    report = {}

    # --- the M4, in its own rig space ---
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.fbx(filepath=str(m4_fbx))
    bpy.context.view_layer.update()
    m4_body = max((o for o in bpy.context.scene.objects if o.type == 'MESH' and o.name.startswith('M4_')),
                  key=lambda o: len(o.data.polygons))
    n_m4, a_m4 = top_normal(m4_body)
    # the M4's own bore direction: stock end -> flash hider
    flash = next((o for o in bpy.context.scene.objects if o.type == 'MESH' and 'Flash' in o.name), None)
    stock = next((o for o in bpy.context.scene.objects if o.type == 'MESH' and 'Stock' in o.name), None)
    axis_m4 = None
    if flash and stock:
        c = lambda o: sum((o.matrix_world @ Vector(v) for v in o.bound_box), Vector()) / 8.0  # noqa: E731
        axis_m4 = (c(flash) - c(stock)).normalized()
    report['m4'] = {
        'top_normal': [round(v, 5) for v in n_m4],
        'top_area': round(a_m4, 5),
        'roll_deg': round(roll_vs(n_m4, Vector((0, 0, 1)), Vector((0, 1, 0))), 3),
        'bore_axis': [round(v, 5) for v in axis_m4] if axis_m4 else None,
        'body': m4_body.name,
    }

    # --- the SVD, placed in the same rig space by the recorded alignment ---
    bpy.ops.wm.read_factory_settings(use_empty=True)
    for name in PARTS:
        bpy.ops.import_scene.fbx(filepath=str(case / 'Authored' / (name + '.fbx')))
        obj = next(o for o in bpy.context.scene.objects if o.type == 'MESH' and o.name.startswith(name))
        obj.name = name
    ref = json.loads((case / 'Receipts' / 'alignment.json').read_text(encoding='utf-8-sig'))
    placement = Matrix.Translation(Vector(ref['translation'])) @ Matrix.Rotation(math.radians(ref['yaw_deg']), 4, 'Z')
    for name in PARTS:
        bpy.context.scene.objects[name].matrix_world = placement @ bpy.context.scene.objects[name].matrix_world
    bpy.context.view_layer.update()

    body = bpy.context.scene.objects['SM_SVD_Body']
    n_svd, a_svd = top_normal(body)
    report['svd'] = {
        'top_normal': [round(v, 5) for v in n_svd],
        'top_area': round(a_svd, 5),
        'roll_deg': round(roll_vs(n_svd, Vector((0, 0, 1)), Vector((0, 1, 0))), 3),
    }
    # receiver-top only: the wooden cheek piece and sloped stock otherwise bias the average
    mw = body.matrix_world
    recv = [v for v in body.data.vertices if (mw @ v.co).z > 0.06 and abs((mw @ v.co).x - 0.019) < 0.012
            and -0.20 < (mw @ v.co).y < 0.10]
    report['svd']['receiver_top_verts'] = len(recv)
    report['roll_difference_deg'] = round(report['svd']['roll_deg'] - report['m4']['roll_deg'], 3)

    grip = Vector(ref['translation']) + Vector((0.0186, -0.282, -0.0388))
    report['grip_contact_m'] = [round(v, 5) for v in grip]
    report['corrective_rotation'] = {
        'axis': [0, 1, 0],
        'angle_deg': round(-report['roll_difference_deg'], 3),
        'about': 'grip contact (SKILL: 装配矩阵绕握把接触点反向旋该角度)',
    }
    (case / 'Receipts' / 'roll_vs_m4.json').write_text(json.dumps(report, indent=2, default=str), encoding='utf-8')
    print('ROLL_VS_M4 ' + json.dumps(report, default=str))


main()
