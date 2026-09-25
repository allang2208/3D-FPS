"""Re-export the authored longbow as a centimeter mesh-only FBX for UE 5.8."""
from pathlib import Path

import bpy

HERE = Path(__file__).resolve().parent
BLEND = HERE / "WoodLongbow_Editable.blend"
FBX = HERE / "Export" / "SM_DarkBow_WoodLongbow_cm.fbx"
NAME = "SM_DarkBow_WoodLongbow"

if not BLEND.is_file():
    raise SystemExit("missing " + str(BLEND))

bpy.ops.wm.open_mainfile(filepath=str(BLEND))
obj = bpy.data.objects.get(NAME)
if obj is None or obj.type != "MESH":
    raise SystemExit("authored mesh missing")

bpy.ops.object.select_all(action="DESELECT")
obj.select_set(True)
bpy.context.view_layer.objects.active = obj
# UE 5.8 FbxFactory collapses a meter-scale 200k bow to a ~1k stub.
if max(obj.dimensions) < 5.0:
    for v in obj.data.vertices:
        v.co *= 100.0
    obj.data.update()
FBX.parent.mkdir(exist_ok=True)
bpy.ops.export_scene.fbx(
    filepath=str(FBX),
    use_selection=True,
    object_types={"MESH"},
    axis_forward="-Y",
    axis_up="Z",
    bake_anim=False,
    mesh_smooth_type="FACE",
    use_tspace=True,
    apply_scale_options="FBX_SCALE_ALL",
    path_mode="AUTO",
    embed_textures=False,
    add_leaf_bones=False,
)
print("FBX_MESH_EXPORTED", FBX.stat().st_size, flush=True)