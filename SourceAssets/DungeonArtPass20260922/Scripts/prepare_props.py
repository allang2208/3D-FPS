"""Normalise the seven props and export the UE import inputs.

Per prop: load the heterogeneous source (FBX / OBJ / .blend) -> scale to a real-world
size, centre the pivot on the footprint and put the base plane at Z=0 -> optionally
split by material (the cobweb pack becomes three separate cards) -> save an editable
.blend -> export one FBX per output mesh -> re-import each FBX and check the round trip.

Material *textures* are prepared separately (Scripts/prepare_textures.py); this script
only reports the material slot names plus any constant values found in the source
(the rope ships as a plain .blend with no image maps).

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


def reset():
    bpy.ops.wm.read_factory_settings(use_empty=True)


def load(path, fmt):
    if fmt == 'fbx':
        bpy.ops.import_scene.fbx(filepath=str(path))
    elif fmt == 'obj':
        bpy.ops.wm.obj_import(filepath=str(path), forward_axis='NEGATIVE_Y', up_axis='Z')
    elif fmt == 'blend':
        bpy.ops.wm.open_mainfile(filepath=str(path))
    else:
        raise RuntimeError('unsupported format %s' % fmt)
    return [o for o in bpy.context.scene.objects if o.type == 'MESH']


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


def material_constants(mat):
    """Read the Principled BSDF defaults so image-less sources (rope) keep their look."""
    out = {}
    if not mat or not mat.use_nodes:
        return out
    for node in mat.node_tree.nodes:
        if node.type != 'BSDF_PRINCIPLED':
            continue
        for key, socket in (('base_color', 'Base Color'), ('roughness', 'Roughness'), ('metallic', 'Metallic')):
            if socket in node.inputs:
                value = node.inputs[socket].default_value
                if hasattr(value, '__len__'):
                    out[key] = [round(float(c), 4) for c in value]
                else:
                    out[key] = round(float(value), 4)
        break
    return out


def normalise(objs, spec):
    """Bake the importer's transform first, then scale uniformly about the world origin.

    Sources arrive with their own (sometimes non-uniform) object scale - multiplying it
    by a uniform factor keeps the distortion, which is what left the ladder's base 1.5 m
    off the floor and the bucket 2 cm below it. Baking first makes local == world, so a
    single uniform scale is exact.
    """
    bpy.context.view_layer.update()
    for o in objs:
        bpy.ops.object.select_all(action='DESELECT')
        o.select_set(True)
        bpy.context.view_layer.objects.active = o
        bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
    bpy.context.view_layer.update()

    mn, mx = bounds(objs)
    size = mx - mn
    mode = spec['mode']
    if mode == 'height':
        scale = float(spec['target_m']) / size.z
    elif mode == 'xy_max':
        scale = float(spec['target_m']) / max(size.x, size.y)
    elif mode == 'scale':
        scale = float(spec['factor'])
    else:
        raise RuntimeError('unknown normalise mode %s' % mode)

    cx = (mn.x + mx.x) / 2.0
    cy = (mn.y + mx.y) / 2.0
    for o in objs:
        o.scale = (scale, scale, scale)
        o.location = (-cx * scale, -cy * scale, -mn.z * scale)
    bpy.context.view_layer.update()
    for o in objs:
        bpy.ops.object.select_all(action='DESELECT')
        o.select_set(True)
        bpy.context.view_layer.objects.active = o
        bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
    bpy.context.view_layer.update()
    return scale


def main():
    args = sys.argv[sys.argv.index("--") + 1:]
    case = Path(args[0])
    only = set(args[1].split(',')) if len(args) > 1 and args[1] else None
    spec = json.loads((case / 'Config' / 'import_spec.json').read_text(encoding='utf-8-sig'))

    for sub in ('Authored', 'Receipts'):
        (case / sub).mkdir(parents=True, exist_ok=True)
    receipt_path = case / 'Receipts' / 'prepare.json'
    receipt = json.loads(receipt_path.read_text(encoding='utf-8-sig')) if receipt_path.exists() else {'props': {}}
    receipt.setdefault('props', {})

    for prop in spec['props']:
        key = prop['key']
        if only and key not in only:
            continue
        src = case / 'Source' / key / prop['source']['file']
        if not src.exists():
            print('MISSING_SOURCE', key, src)
            continue

        reset()
        meshes = load(src, prop['source']['format'])
        scale = normalise(meshes, prop['normalise'])

        if prop.get('split_by_material') and len(meshes) == 1:
            obj = meshes[0]
            bpy.context.view_layer.objects.active = obj
            obj.select_set(True)
            bpy.ops.object.mode_set(mode='EDIT')
            bpy.ops.mesh.select_all(action='SELECT')
            bpy.ops.mesh.separate(type='MATERIAL')
            bpy.ops.object.mode_set(mode='OBJECT')
            meshes = [o for o in bpy.context.scene.objects if o.type == 'MESH']
            # Separating keeps the pack's coordinate frame, so each card would carry a
            # pivot up to 66 cm away from its own geometry. Re-centre every piece on its
            # own footprint (scale untouched) so they can be dropped anywhere.
            for piece in meshes:
                bpy.context.view_layer.update()
                mn_p, mx_p = bounds([piece])
                piece.location = (piece.location.x - (mn_p.x + mx_p.x) / 2.0,
                                  piece.location.y - (mn_p.y + mx_p.y) / 2.0,
                                  piece.location.z - mn_p.z)
                bpy.context.view_layer.update()
                bpy.ops.object.select_all(action='DESELECT')
                piece.select_set(True)
                bpy.context.view_layer.objects.active = piece
                bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)

        meshes.sort(key=lambda o: o.name)
        outputs = []
        for index, obj in enumerate(meshes, 1):
            suffix = '' if len(meshes) == 1 else '_%d' % index
            obj.name = 'SM_Prop_%s%s' % (prop['name'], suffix)
            obj.data.name = obj.name
            obj.data.calc_loop_triangles()
            slots = []
            for s in obj.material_slots:
                slots.append({
                    'name': s.material.name if s.material else None,
                    'constants': material_constants(s.material),
                    'images': sorted({n.image.name for n in (s.material.node_tree.nodes if s.material and s.material.use_nodes else [])
                                      if n.type == 'TEX_IMAGE' and n.image}),
                })
            fbx = case / 'Authored' / (obj.name + '.fbx')
            bpy.ops.object.select_all(action='DESELECT')
            obj.select_set(True)
            bpy.context.view_layer.objects.active = obj
            bpy.ops.export_scene.fbx(filepath=str(fbx), use_selection=True, object_types={'MESH'},
                                     axis_forward='-Y', axis_up='Z', bake_anim=False,
                                     mesh_smooth_type='FACE', use_tspace=True, add_leaf_bones=False)
            mn2, mx2 = bounds([obj])
            outputs.append({
                'mesh_name': obj.name, 'fbx': str(fbx), 'tris': len(obj.data.loop_triangles),
                'verts': len(obj.data.vertices), 'material_slots': slots,
                'size_m': [round(mx2[i] - mn2[i], 5) for i in range(3)],
                'base_z': round(mn2.z, 5),
                'max_loop_normal_angle_deg': round(max_loop_angle(obj.data), 2),
            })

        blend = case / 'Authored' / ('%s_Editable.blend' % key)
        bpy.ops.wm.save_as_mainfile(filepath=str(blend))

        # Round-trip check: re-import each exported FBX and compare counts and normals.
        for entry in outputs:
            reset()
            bpy.ops.import_scene.fbx(filepath=entry['fbx'])
            reimported = [o for o in bpy.context.scene.objects if o.type == 'MESH']
            tris = 0
            worst = 0.0
            for o in reimported:
                o.data.calc_loop_triangles()
                tris += len(o.data.loop_triangles)
                worst = max(worst, max_loop_angle(o.data))
            mn3, mx3 = bounds(reimported)
            entry['roundtrip'] = {
                'objects': len(reimported), 'tris': tris, 'tris_match': tris == entry['tris'],
                'max_loop_normal_angle_deg': round(worst, 2),
                'size_m': [round(mx3[i] - mn3[i], 5) for i in range(3)],
                'base_z': round(mn3.z, 5),
            }

        receipt['props'][key] = {
            'title': prop['title'], 'uid': prop['uid'], 'license': prop['license'],
            'source': str(src), 'format': prop['source']['format'],
            'normalise': prop['normalise'], 'scale_factor': round(scale, 8),
            'editable_source': str(blend), 'outputs': outputs, 'stage': 'exported',
        }
        receipt['stage'] = 'partial'
        receipt_path.write_text(json.dumps(receipt, indent=2, default=str), encoding='utf-8')
        print('PREPARE_PROP', key, json.dumps(receipt['props'][key], default=str))

    done = all(v.get('stage') == 'exported' for v in receipt['props'].values())
    receipt['stage'] = 'exported' if done and receipt['props'] else 'partial'
    receipt_path.write_text(json.dumps(receipt, indent=2, default=str), encoding='utf-8')


main()
