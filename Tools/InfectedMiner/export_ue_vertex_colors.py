"""Export the accepted mesh with its authored color layer first for UE FBX.

Geometry, weights, bind and source blend remain unchanged. The mature donor's
unused white color layer otherwise takes precedence over MinerForearmColor.
"""
import bpy
from pathlib import Path
R=Path('D:/FPS3D/FPSGAME/SourceAssets/InfectedMiner20260912/Delivery')
bpy.ops.wm.open_mainfile(filepath=str(R/'InfectedMiner_Editable.blend'))
r=bpy.data.objects['MinerRig'];r.animation_data.action=None;r.data.pose_position='REST'
bpy.ops.object.select_all(action='DESELECT');r.select_set(True)
for o in bpy.context.scene.objects:
    if o.type!='MESH' or not any(m.type=='ARMATURE' and m.object==r for m in o.modifiers):continue
    o.select_set(True)
    if o.data.color_attributes.get('MinerForearmColor'):
        for a in list(o.data.color_attributes):
            if a.name!='MinerForearmColor':o.data.color_attributes.remove(a)
        o.data.color_attributes.active_color_name='MinerForearmColor'
bpy.context.view_layer.objects.active=r
bpy.ops.export_scene.fbx(filepath=str(R/'SK_InfectedMiner_UE.fbx'),use_selection=True,object_types={'ARMATURE','MESH'},add_leaf_bones=False,bake_anim=False,axis_forward='-Y',axis_up='Z',apply_unit_scale=True,use_mesh_modifiers=True,mesh_smooth_type='FACE')
print('MINER_UE_COLOR_LAYER_EXPORTED')
