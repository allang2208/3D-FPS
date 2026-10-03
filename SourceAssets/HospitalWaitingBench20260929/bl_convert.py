# Hospital Waiting Bench GLB -> FBX for UE5.8 (same house rules as the bed:
# UE +X forward, floor pivot, real-world scale; source is meters, no rescale).
import bpy
import math
from mathutils import Matrix, Vector

SRC = "D:/FPS3D/FPSGAME/SourceAssets/HospitalWaitingBench20260929/Hospital_Waiting_Bench.glb"
OUT = "D:/FPS3D/FPSGAME/SourceAssets/HospitalWaitingBench20260929/Exports/SM_Hospital_Waiting_Bench.fbx"

bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=SRC)

meshes = [o for o in bpy.context.scene.objects if o.type == "MESH"]
print("MESH_OBJECTS", [o.name for o in meshes], flush=True)

# detach from importer empties, keeping world transform
for o in meshes:
    mw = o.matrix_world.copy()
    o.parent = None
    o.matrix_world = mw

for o in bpy.context.scene.objects:
    o.select_set(o.type == "MESH")
bpy.context.view_layer.objects.active = meshes[0]
bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)


def bbox(objs):
    lo = Vector((1e9,) * 3)
    hi = Vector((-1e9,) * 3)
    for o in objs:
        for v in o.data.vertices:
            w = o.matrix_world @ v.co
            lo.x, lo.y, lo.z = min(lo.x, w.x), min(lo.y, w.y), min(lo.z, w.z)
            hi.x, hi.y, hi.z = max(hi.x, w.x), max(hi.y, w.y), max(hi.z, w.z)
    return lo, hi


lo, hi = bbox(meshes)
print("AFTER_IMPORT ext_m:", [round(v, 3) for v in (hi - lo)], flush=True)

# rotate so the long axis lands on +X
if (hi - lo).x < (hi - lo).y:
    R = Matrix.Rotation(math.radians(90.0), 4, "Z")
    for o in meshes:
        o.data.transform(R)
    lo, hi = bbox(meshes)
    print("ROTATED, ext_m:", [round(v, 3) for v in (hi - lo)], flush=True)

# pivot at floor center (source already meters -> no rescale)
center = (lo + hi) * 0.5
T = Matrix.Translation(Vector((-center.x, -center.y, -lo.z)))
for o in meshes:
    o.data.transform(T)

lo, hi = bbox(meshes)
print("FINAL ext_cm:", [round(v * 100, 1) for v in (hi - lo)],
      "min_z_cm:", round(lo.z * 100, 3),
      "center_xy_cm:", [round(c * 100, 2) for c in ((lo.x + hi.x) * 0.5, (lo.y + hi.y) * 0.5)],
      flush=True)

for o in meshes:
    for slot in o.material_slots:
        print("MAT_SLOT", o.name, "->", slot.material.name, flush=True)

bpy.ops.export_scene.fbx(
    filepath=OUT,
    use_selection=True,
    global_scale=1.0,
    apply_unit_scale=True,
    apply_scale_options="FBX_SCALE_NONE",
    object_types={"MESH"},
    use_mesh_modifiers=True,
    mesh_smooth_type="FACE",
    add_leaf_bones=False,
    bake_anim=False,
    path_mode="ABSOLUTE",
    embed_textures=False,
    axis_forward="-Y",
    axis_up="Z",
    use_space_transform=True,
)
print("FBX_WRITTEN", OUT, flush=True)
