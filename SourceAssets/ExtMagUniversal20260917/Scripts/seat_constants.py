import bpy, json, math
from mathutils import Matrix, Vector
SA = r"D:\FPS3D\FPSGAME\SourceAssets"
GUNS = {
    "M4": (SA + r"\M4HK416Replica20260910\SK_M4_FoldingSights_HK416.fbx", (0.058, 0.257, -0.070), 15.0),
    "AKM": (SA + r"\AKMSoviet20260911\SK_AKM_MannyNative.fbx", (0.062, 0.243, -0.105), 20.0),
    "QBZ": (SA + r"\QBZ191MagazineSeat20260913\SK_QBZ191_Manny.fbx", (0.054, 0.260, -0.056), 13.0),
}
out = {}
for gun, (path, loc, rake) in GUNS.items():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.fbx(filepath=path)
    arm = next(o for o in bpy.context.scene.objects if o.type == "ARMATURE")
    arm.data.pose_position = "REST"
    bpy.context.view_layer.update()
    socket = arm.data.bones["WPN_SOCKET_Magazine"]
    sw = arm.matrix_world @ socket.matrix_local
    # EXT frame -> socket-local: R(rake about X) with translation loc
    R = Matrix.Rotation(math.radians(rake), 4, 'X')
    seat_world = Matrix.Translation(Vector(loc)) @ R
    rel = sw.inverted() @ seat_world
    q = rel.to_quaternion()
    out[gun] = {
        "loc": [round(v, 6) for v in rel.to_translation()],
        "quat_xyzw": [round(v, 8) for v in q],
        "socket_head": [round(v, 4) for v in sw.translation],
    }
with open("Reference/seat_socket_local.json", "w") as f:
    json.dump(out, f, indent=1)
print(json.dumps(out, indent=1))
