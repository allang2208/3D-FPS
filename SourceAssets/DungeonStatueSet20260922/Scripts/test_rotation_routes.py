"""Minimal test: does a 180 deg Z rotation actually change the imported OBJ mesh?

Compares three routes on the same source:
  A. no rotation (baseline)
  B. obj.rotation_euler = (0,0,pi) then bpy.ops.object.transform_apply(rotation=True)
  C. mesh.transform(Matrix.Rotation(pi, 4, 'Z'))
Each route prints a checksum of the first 200 vertex coordinates plus the bounding box,
so "the rotation silently did nothing" is distinguishable from "the config was not read".

Run:
    blender --background --factory-startup --python <this file> -- <obj>
"""
import hashlib
import math
import sys

import bpy
from mathutils import Matrix, Vector


def load(path):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.wm.obj_import(filepath=path, forward_axis='NEGATIVE_Y', up_axis='Z')
    obj = [o for o in bpy.context.scene.objects if o.type == 'MESH'][0]
    return obj


def signature(obj, tag):
    me = obj.data
    pts = [obj.matrix_world @ v.co for v in me.vertices[:200]]
    blob = b''.join(b'%08x%08x%08x' % (int(p.x * 1000) & 0xFFFFFFFF, int(p.y * 1000) & 0xFFFFFFFF,
                                       int(p.z * 1000) & 0xFFFFFFFF) for p in pts)
    allpts = [o.matrix_world @ Vector(c) for o in [obj] for c in o.bound_box]
    bbox = [round(min(p[i] for p in allpts), 3) for i in range(3)] + \
           [round(max(p[i] for p in allpts), 3) for i in range(3)]
    print('TEST %-26s checksum=%s bbox=%s rot_mode=%s euler=%s' % (
        tag, hashlib.sha1(blob).hexdigest()[:12], bbox,
        obj.rotation_mode, tuple(round(math.degrees(a), 2) for a in obj.rotation_euler)))


def main():
    src = sys.argv[sys.argv.index("--") + 1]

    obj = load(src)
    signature(obj, 'A baseline (no rotation)')

    obj = load(src)
    bpy.context.view_layer.objects.active = obj
    obj.select_set(True)
    obj.rotation_euler = (0.0, 0.0, math.pi)
    bpy.ops.object.transform_apply(location=False, rotation=True, scale=False)
    signature(obj, 'B euler+transform_apply 180')

    obj = load(src)
    obj.data.transform(Matrix.Rotation(math.pi, 4, 'Z'))
    obj.data.update()
    signature(obj, 'C mesh.transform 180')

    obj = load(src)
    bpy.context.view_layer.objects.active = obj
    obj.select_set(True)
    obj.rotation_euler = (0.0, 0.0, math.radians(90))
    bpy.ops.object.transform_apply(location=False, rotation=True, scale=False)
    signature(obj, 'D euler+transform_apply 90')


main()
