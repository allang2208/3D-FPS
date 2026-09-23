"""Normalise every statue in Config/statues.json and export the UE import inputs.

Per statue: import source OBJ -> bring the up axis to +Z (the author's photogrammetry
exports are not all oriented the same way: Muse lies along +Y, the others stand on +Z)
-> uniform scale to the per-statue target height -> pivot on the base centre with the
base plane at Z=0 -> save editable .blend -> export FBX -> write a 4096 base-colour PNG.

Outputs per key (names from Config/statues.json):
    Authored/<mesh_name>.fbx
    Authored/<key>_Editable.blend
    Textures/T_Statue_<Key>_BaseColor.png
    Receipts/prepare.json

Run:
    "E:/Program Files/Blender Foundation/Blender 5.1/blender.exe" --background --factory-startup \
        --python <this file> -- <case_root> [key,key]
"""
import json
import math
import sys
from pathlib import Path

import bpy
from mathutils import Vector

TEX_SIZE = 4096


def find_source(case, key):
    obj = sorted((case / 'Source' / key).rglob('*.obj'))
    if not obj:
        return None, None
    png = sorted(obj[0].parent.glob('*.png'))
    return obj[0], (png[0] if png else None)


def bounds(objs):
    pts = [o.matrix_world @ Vector(c) for o in objs for c in o.bound_box]
    return (Vector((min(p.x for p in pts), min(p.y for p in pts), min(p.z for p in pts))),
            Vector((max(p.x for p in pts), max(p.y for p in pts), max(p.z for p in pts))))


def max_loop_angle(mesh):
    corners = mesh.corner_normals
    per_vert = {}
    for loop in mesh.loops:
        per_vert.setdefault(loop.vertex_index, []).append(Vector(corners[loop.index].vector))
    worst = 0.0
    for normals in per_vert.values():
        base = normals[0]
        for n in normals[1:]:
            if base.length and n.length:
                worst = max(worst, base.angle(n))
    return math.degrees(worst)


def main():
    args = sys.argv[sys.argv.index("--") + 1:]
    case = Path(args[0])
    only = set(args[1].split(',')) if len(args) > 1 and args[1] else None
    cfg = json.loads((case / 'Config' / 'statues.json').read_text(encoding='utf-8-sig'))

    for sub in ('Authored', 'Textures', 'Receipts'):
        (case / sub).mkdir(parents=True, exist_ok=True)
    receipt_path = case / 'Receipts' / 'prepare.json'
    receipt = json.loads(receipt_path.read_text(encoding='utf-8')) if receipt_path.exists() else {'statues': {}}
    receipt.setdefault('statues', {})

    for statue in cfg['statues']:
        key = statue['key']
        if only and key not in only:
            continue
        obj_path, png_path = find_source(case, key)
        if not obj_path:
            print('MISSING_SOURCE', key)
            continue

        up_axis = statue.get('up_axis', 'Z')
        yaw_deg = float(statue.get('yaw_deg', 0.0))
        target_h = float(statue['target_height_m'])
        mesh_name = statue['mesh_name']

        bpy.ops.wm.read_factory_settings(use_empty=True)
        bpy.ops.wm.obj_import(filepath=str(obj_path), forward_axis='NEGATIVE_Y', up_axis='Z')
        meshes = [o for o in bpy.context.scene.objects if o.type == 'MESH']
        assert len(meshes) == 1, '%s: expected 1 mesh, got %d' % (key, len(meshes))
        obj = meshes[0]
        obj.name = mesh_name
        obj.data.name = mesh_name

        bpy.context.view_layer.objects.active = obj
        obj.select_set(True)
        # The OBJ importer leaves its own -180 deg Z rotation on the *object* (verified by
        # Scripts/test_rotation_routes.py: baseline euler = (0,0,-180)), it is not baked into
        # the mesh. Overwriting rotation_euler below would silently drop it and shift every
        # facing by 180 deg (0 and 180 became indistinguishable), so bake it in first.
        bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
        raw_mn, raw_mx = bounds([obj])
        raw_size = [round(raw_mx[i] - raw_mn[i], 4) for i in range(3)]

        # Bring the statue upright when the source's long axis is not +Z. The sign is
        # per-model: after the import rotation is baked in, a source lying along -Y needs
        # -90 about X (a +90 there lands the head at -Z, i.e. upside down).
        if up_axis.upper() == 'Y':
            obj.rotation_euler = (math.radians(float(statue.get('up_axis_rot_deg', 90.0))), 0.0, 0.0)
            bpy.ops.object.transform_apply(location=False, rotation=True, scale=False)
        if yaw_deg:
            obj.rotation_euler = (0.0, 0.0, math.radians(yaw_deg))
            bpy.ops.object.transform_apply(location=False, rotation=True, scale=False)

        mn, mx = bounds([obj])
        height = mx.z - mn.z
        scale = target_h / height
        cx = (mn.x + mx.x) / 2.0
        cy = (mn.y + mx.y) / 2.0
        obj.scale = (scale, scale, scale)
        obj.location = (-cx * scale, -cy * scale, -mn.z * scale)
        bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)

        mn2, mx2 = bounds([obj])
        obj.data.calc_loop_triangles()

        entry = {
            'title': statue['title'], 'uid': statue['uid'], 'license': statue['license'],
            'source_obj': str(obj_path), 'source_atlas': str(png_path) if png_path else None,
            'up_axis_in_source': up_axis, 'yaw_applied_deg': yaw_deg,
            'source_size': raw_size,
            'tris': len(obj.data.loop_triangles), 'verts': len(obj.data.vertices),
            'has_custom_normals': bool(obj.data.has_custom_normals),
            'max_loop_normal_angle_deg': round(max_loop_angle(obj.data), 2),
            'scale_factor': round(scale, 8), 'target_height_m': target_h,
            'normalised_size_m': [round(mx2[i] - mn2[i], 5) for i in range(3)],
            'pivot': 'base centre, base plane at Z=0',
        }

        images = [i for i in bpy.data.images if i.size[0] > 0]
        if images:
            img = images[0]
            entry['source_texture'] = {'name': img.name, 'width': img.size[0], 'height': img.size[1]}
            if img.size[0] > TEX_SIZE:
                img.scale(TEX_SIZE, TEX_SIZE)
            tex_path = case / 'Textures' / ('T_Statue_%s_BaseColor.png' % key.capitalize())
            img.filepath_raw = str(tex_path)
            img.file_format = 'PNG'
            img.save()
            img.filepath = str(tex_path)
            img.reload()
            entry['game_texture'] = {'path': str(tex_path), 'width': img.size[0], 'height': img.size[1]}

        bpy.ops.file.pack_all()
        blend = case / 'Authored' / ('%s_Editable.blend' % key)
        bpy.ops.wm.save_as_mainfile(filepath=str(blend))
        entry['editable_source'] = str(blend)

        fbx = case / 'Authored' / (mesh_name + '.fbx')
        bpy.ops.object.select_all(action='DESELECT')
        obj.select_set(True)
        bpy.context.view_layer.objects.active = obj
        bpy.ops.export_scene.fbx(filepath=str(fbx), use_selection=True, object_types={'MESH'},
                                 axis_forward='-Y', axis_up='Z', bake_anim=False,
                                 mesh_smooth_type='FACE', use_tspace=True, add_leaf_bones=False)
        entry['fbx'] = str(fbx)
        entry['stage'] = 'exported'

        receipt['statues'][key] = entry
        receipt['stage'] = 'partial'
        receipt_path.write_text(json.dumps(receipt, indent=2, default=str), encoding='utf-8')
        print('PREPARE_STATUE', key, json.dumps(entry))

    done = all(v.get('stage') == 'exported' for v in receipt['statues'].values())
    receipt['stage'] = 'exported' if done and receipt['statues'] else 'partial'
    receipt_path.write_text(json.dumps(receipt, indent=2, default=str), encoding='utf-8')


main()
