"""Export the fitted ASH-12 mesh and all seven actions in one FBX.

The per-action FBXs produced by ``build.py`` contain only an armature and are
therefore rejected by the in-editor SkeletalMeshTools.import_file bridge.  This
fallback keeps a mesh in the file so the MCP importer accepts it, while the
armature still carries every ``ASH12_*`` action as a separate take.

Run: blender --background --factory-startup --python export_combined.py
"""
import os

import bpy

HERE = os.path.dirname(os.path.abspath(__file__))
O = os.path.normpath(os.path.join(HERE, ".."))
BLEND = os.path.join(O, "ASH12_Editable.blend")
OUT = os.path.join(O, "SK_ASH12_Manny_WithAnims.fbx")

bpy.ops.wm.open_mainfile(filepath=BLEND)
scene = bpy.context.scene
scene.render.fps = 60
scene.frame_start = 0
scene.frame_end = 180

rig = bpy.data.objects["SK_M4_Infima"]
hands = bpy.data.objects["SK_Manny_Arms_Export"]
gun = bpy.data.objects["ASH12_Export"]
bpy.ops.object.select_all(action="DESELECT")
for obj in (rig, hands, gun):
    obj.select_set(True)
bpy.context.view_layer.objects.active = rig
bpy.ops.export_scene.fbx(
    filepath=OUT,
    use_selection=True,
    object_types={"MESH", "ARMATURE"},
    axis_forward="-Y", axis_up="Z",
    add_leaf_bones=False,
    bake_anim=True,
    bake_anim_use_all_actions=True,
    bake_anim_use_nla_strips=False,
    bake_anim_force_startend_keying=True,
    bake_anim_step=0.5,
    bake_anim_simplify_factor=0,
)
print("ASH12_COMBINED_EXPORT", OUT)
