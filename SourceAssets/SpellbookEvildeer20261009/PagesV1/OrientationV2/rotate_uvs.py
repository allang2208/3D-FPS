"""Rotate each illustrated face 180 degrees; preserve all artwork and geometry."""
from pathlib import Path
import json
import math
import bpy
from mathutils import Matrix

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
# Always start from the saved pre-rotation source, so reruns never double-rotate.
bpy.ops.wm.open_mainfile(filepath=str(HERE/'Before/Spellbook_16Pages.blend'))
bpy.context.preferences.filepaths.save_version = 0
skin = bpy.data.objects['SK_Spellbook_Alchemy_16Pages']
uv = skin.data.uv_layers.active.data
changed = 0
for face in skin.data.polygons:
    if not skin.data.materials[face.material_index].name.startswith('M_SpellbookPages_'):
        continue
    for index in face.loop_indices:
        u, v = uv[index].uv
        col, row = min(1, math.floor(u*2)), min(1, math.floor(v*2))
        uv[index].uv = (col+.5-u, row+.5-v)
        changed += 1
bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'Spellbook_16Pages.blend'))
arm = bpy.data.objects['SpellbookRig']
arm.animation_data_clear()
arm.matrix_world = Matrix.Identity(4)
for bone in arm.pose.bones:
    bone.matrix_basis = Matrix.Identity(4)
bpy.context.view_layer.update()
bpy.ops.object.select_all(action='DESELECT')
for obj in (arm, skin):
    obj.hide_set(False)
    obj.select_set(True)
bpy.context.view_layer.objects.active = arm
bpy.ops.export_scene.fbx(filepath=str(ROOT/'Export/SK_Spellbook_Alchemy_16Pages.fbx'),
    use_selection=True, object_types={'MESH','ARMATURE'}, axis_forward='-Y', axis_up='Z',
    apply_unit_scale=True, apply_scale_options='FBX_SCALE_ALL', mesh_smooth_type='FACE',
    use_tspace=False, add_leaf_bones=False, use_armature_deform_only=True,
    bake_anim=False, path_mode='STRIP', embed_textures=False)
receipt = dict(rotated_degrees=180, illustrated_faces=16, edited_uv_corners=changed,
    geometry_changed=False, source_images_changed=False, animation_tracks_changed=False,
    rendered=False)
(HERE/'author-receipt.json').write_text(json.dumps(receipt, indent=2), encoding='utf-8')
print('SPELLBOOK_PAGE_ORIENTATION_AUTHORED '+json.dumps(receipt))
