import bpy,json
from pathlib import Path
root=Path('D:/FPS3D/FPSGAME/SourceAssets/HandBrain20260910');out=root/'ue_export'
bpy.ops.wm.open_mainfile(filepath=str(root/'death_v01/delivery/HandBrain_FiveActions.blend'))
rig=bpy.data.objects['SK_HandBrain'];rig.animation_data.action=bpy.data.actions['Idle'];rig.animation_data.action_slot=bpy.data.actions['Idle'].slots[0];bpy.context.scene.frame_set(1)
bpy.ops.object.select_all(action='DESELECT')
for o in bpy.context.scene.objects:
 if o.type=='MESH':o.select_set(True)
bpy.context.view_layer.objects.active=bpy.data.objects['HandBrain_Body'];bpy.ops.object.join();mesh=bpy.context.object;mesh.name='SK_HandBrain'
bpy.ops.object.select_all(action='DESELECT');mesh.select_set(True);rig.select_set(True);bpy.context.view_layer.objects.active=rig
kwargs=dict(use_selection=True,path_mode='COPY',embed_textures=False,add_leaf_bones=False,bake_anim_use_all_actions=False,bake_anim_use_nla_strips=False,bake_anim_simplify_factor=0,axis_forward='-Y',axis_up='Z')
bpy.ops.export_scene.fbx(filepath=str(out/'SK_HandBrain.fbx'),bake_anim=False,**kwargs)
for name,end in [('Idle',61),('Move',31),('Attack_Slam',61),('Attack_Howl',91),('Death',85)]:
 a=bpy.data.actions[name];rig.animation_data.action=a;rig.animation_data.action_slot=a.slots[0];s=bpy.context.scene;s.frame_start=1;s.frame_end=end;s.frame_set(1)
 bpy.ops.export_scene.fbx(filepath=str(out/('A_HandBrain_'+name+'.fbx')),bake_anim=True,**kwargs)
(out/'material_slots.json').write_text(json.dumps([m.name for m in mesh.data.materials],indent=2))
print('HANDBRAIN_UE_EXPORT_COMPLETE')
