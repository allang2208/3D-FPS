"""Align only the rigid pick head with the mining swing; preserve the grip."""
import bpy,json,math
from mathutils import Vector,Matrix
from pathlib import Path
ROOT=Path('D:/FPS3D/FPSGAME/SourceAssets/InfectedMiner20260913/PickaxeSingleHand')
delivery=ROOT/'Delivery'
bpy.ops.wm.open_mainfile(filepath=str(delivery/'InfectedMiner_Editable.blend'))
rig=bpy.data.objects['MinerRig'];head=bpy.data.objects['Pickaxe_ForgedHead']
grip=json.loads(Path('D:/FPS3D/FPSGAME/SourceAssets/InfectedMiner20260912/Review/Hand_UserAccepted_20260912/grip-authoring.json').read_text())
axis=Vector(grip['shaft']).normalized();pivot=Vector(grip['palm'])
degrees=90-head.get('pickaxe_strike_alignment_degrees',0)
rotation=Matrix.Rotation(math.radians(degrees),4,axis)
transform=head.matrix_world.inverted()@Matrix.Translation(pivot)@rotation@Matrix.Translation(-pivot)@head.matrix_world
for vertex in head.data.vertices:vertex.co=transform@vertex.co
head['pickaxe_strike_alignment_degrees']=90
head.data.update()
bpy.ops.wm.save_as_mainfile(filepath=str(delivery/'InfectedMiner_Editable.blend'))
report=json.loads((delivery/'rebuild.json').read_text())
report['mesh_rest_skin_materials_weapon']='body, hands, bind, weights and materials retained; rigid pick head rotated 90 degrees about handle'
report['pick_head_rotation_degrees']=90
(delivery/'rebuild.json').write_text(json.dumps(report,indent=2))

# Export the same editable bind and skin, with the corrected head vertices.
rig.animation_data.action=None
for bone in rig.pose.bones:bone.matrix_basis.identity()
bpy.context.view_layer.update()
bpy.ops.object.select_all(action='DESELECT');rig.select_set(True)
for obj in bpy.context.scene.objects:
    if obj.type=='MESH' and any(m.type=='ARMATURE' and m.object==rig for m in obj.modifiers):
        obj.select_set(True)
        colors=obj.data.color_attributes
        if 'MinerForearmColor' in colors:
            for color in list(colors):
                if color.name!='MinerForearmColor':colors.remove(color)
            colors.active_color=colors['MinerForearmColor'];colors.render_color_index=0
bpy.context.view_layer.objects.active=rig
bpy.ops.export_scene.fbx(filepath=str(delivery/'SK_InfectedMiner_Pickaxe.fbx'),use_selection=True,
    object_types={'ARMATURE','MESH'},add_leaf_bones=False,bake_anim=False,
    axis_forward='-Y',axis_up='Z',apply_unit_scale=True,use_mesh_modifiers=True,mesh_smooth_type='FACE')
print('MINER_PICK_HEAD_ALIGNED',flush=True)
