"""Produce three explicit FBX LODs for background UE imports."""
import bpy, json
from pathlib import Path
P = Path(__file__).parent
SOURCE = P.parent
bpy.ops.wm.open_mainfile(filepath=str(SOURCE/'RuneSword_Pommels_PBR.blend'))
src = bpy.data.objects['SM_RunePommel_Meteor']
group = bpy.data.objects.new('SM_RunePommel_Meteor', None)
bpy.context.scene.collection.objects.link(group)
group['fbx_type'] = 'LodGroup'
objects = [group]
rows = []
for index, ratio in enumerate([1.0, .55, .25]):
    obj = src.copy()
    obj.data = src.data.copy()
    obj.name = 'Meteor_LOD'+str(index)
    bpy.context.scene.collection.objects.link(obj)
    obj.parent = group
    obj.hide_set(False)
    obj.hide_render = False
    bpy.ops.object.select_all(action='DESELECT')
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
    if index:
        mod = obj.modifiers.new('Closed shell LOD reduction', 'DECIMATE')
        mod.ratio = ratio
        bpy.ops.object.modifier_apply(modifier=mod.name)
    obj.data.calc_loop_triangles()
    rows.append({'lod': index, 'ratio': ratio, 'triangles': len(obj.data.loop_triangles)})
    objects.append(obj)
bpy.ops.object.select_all(action='DESELECT')
for obj in objects:
    obj.select_set(True)
bpy.context.view_layer.objects.active = objects[1]
path = P/'SM_RunePommel_Meteor_LODs.fbx'
bpy.ops.export_scene.fbx(filepath=str(path),use_selection=True,object_types={'MESH','EMPTY'},axis_forward='-Y',axis_up='Z',add_leaf_bones=False,bake_anim=False,mesh_smooth_type='FACE',use_tspace=True,path_mode='COPY',embed_textures=False)
(P/'lod_export_receipt.json').write_text(json.dumps(rows, indent=2), encoding='utf-8')
print('METEOR_CLOSED_LODS_EXPORTED', json.dumps(rows), flush=True)
