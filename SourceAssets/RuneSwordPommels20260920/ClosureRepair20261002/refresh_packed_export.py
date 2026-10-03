"""Refresh the saved meteor PBR images after a scoped rebake."""
import bpy
from pathlib import Path
P = Path(__file__).parent.parent
bpy.context.preferences.filepaths.save_version = 0
bpy.ops.wm.open_mainfile(filepath=str(P/'RuneSword_Pommels_PBR.blend'))
obj = bpy.data.objects['SM_RunePommel_Meteor']
for mat in obj.data.materials:
    if not mat or not mat.use_nodes:
        continue
    for node in mat.node_tree.nodes:
        if node.type=='TEX_IMAGE' and node.image:
            color_space = node.image.colorspace_settings.name
            node.image = bpy.data.images.load(bpy.path.abspath(node.image.filepath), check_existing=False)
            node.image.colorspace_settings.name = color_space
bpy.ops.object.select_all(action='DESELECT')
obj.hide_set(False)
obj.hide_render=False
obj.select_set(True)
bpy.context.view_layer.objects.active = obj
bpy.ops.export_scene.fbx(filepath=str(P/'Export/SM_RunePommel_Meteor.fbx'),use_selection=True,object_types={'MESH'},axis_forward='-Y',axis_up='Z',add_leaf_bones=False,bake_anim=False,mesh_smooth_type='FACE',use_tspace=True,path_mode='COPY',embed_textures=False)
bpy.ops.export_scene.gltf(filepath=str(P/'Export/SM_RunePommel_Meteor.glb'),export_format='GLB',use_selection=True,export_apply=True,export_texcoords=True,export_normals=True,export_tangents=True)
bpy.ops.file.pack_all()
bpy.ops.wm.save_as_mainfile(filepath=str(P/'RuneSword_Pommels_PBR.blend'))
print('METEOR_PACKED_PBR_REFRESHED', flush=True)
