"""Probe why a per-weapon icon frame missed its subject (read-only, no render)."""
import bpy
import os
import sys
from mathutils import Vector

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, ".."))
FBXDIR = os.path.join(ROOT, "FBX")
SA = r"D:\FPS3D\FPSGAME\SourceAssets"

FBX = os.path.join(FBXDIR, "SM_ExtMag_AKM40_finish.fbx")
RIFLE = os.path.join(SA, r"AKMSoviet20260911\SK_AKM_MannyNative.fbx")


def import_fbx(path):
    before = set(bpy.context.scene.objects)
    bpy.ops.import_scene.fbx(filepath=path)
    return [o for o in bpy.context.scene.objects if o not in before]


bpy.ops.wm.read_factory_settings(use_empty=True)
rifle = import_fbx(RIFLE)
arm = next(o for o in rifle if o.type == "ARMATURE")
arm.data.pose_position = "REST"
bpy.context.view_layer.update()
socket = arm.matrix_world @ arm.data.bones["WPN_SOCKET_Magazine"].matrix_local
print("PROBE rifle_objects", [(o.name, o.type) for o in rifle], flush=True)
print("PROBE arm_matrix_world", tuple(round(v, 5) for row in arm.matrix_world for v in row), flush=True)
print("PROBE socket_matrix", [tuple(round(v, 5) for v in row) for row in socket], flush=True)
for o in rifle:
    bpy.data.objects.remove(o, do_unlink=True)

objs = [o for o in import_fbx(FBX) if o.type == "MESH"]
print("PROBE mag_meshes", [(o.name, len(o.data.vertices), tuple(round(v, 5) for v in o.dimensions)) for o in objs],
      flush=True)
ob = objs[-1]
bpy.ops.object.select_all(action='DESELECT')
ob.select_set(True)
bpy.context.view_layer.objects.active = ob
bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
for vert in ob.data.vertices:
    vert.co = socket @ vert.co
ob.data.update()
pts = [ob.matrix_world @ vert.co for vert in ob.data.vertices]
lo = Vector((min(p.x for p in pts), min(p.y for p in pts), min(p.z for p in pts)))
hi = Vector((max(p.x for p in pts), max(p.y for p in pts), max(p.z for p in pts)))
print("PROBE after_socket lo", tuple(round(v, 5) for v in lo), "hi", tuple(round(v, 5) for v in hi),
      "dims", tuple(round(v, 5) for v in (hi - lo)), flush=True)
print("PROBE uv_layers", [(layer.name, layer.active_render) for layer in ob.data.uv_layers], flush=True)
