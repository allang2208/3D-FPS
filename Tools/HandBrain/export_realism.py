import bpy,json
from pathlib import Path
r=Path('D:/FPS3D/FPSGAME/SourceAssets/HandBrain20260910/realism_v05')
bpy.ops.wm.open_mainfile(filepath=str(r/'HandBrain_Refined.blend'))
rig=bpy.data.objects['SK_HandBrain'];rig.animation_data.action=bpy.data.actions['Idle'];rig.animation_data.action_slot=bpy.data.actions['Idle'].slots[0];bpy.context.scene.frame_set(1)
bpy.ops.object.select_all(action='DESELECT')
for name in ['HandBrain_Body','HandBrain_AttackArm','HandBrain_CrownHands','HandBrain_OralTeeth']:bpy.data.objects[name].select_set(True)
bpy.context.view_layer.objects.active=bpy.data.objects['HandBrain_Body'];bpy.ops.object.join();mesh=bpy.context.object;mesh.name='SK_HandBrain'
bpy.ops.object.select_all(action='DESELECT');mesh.select_set(True);rig.select_set(True);bpy.context.view_layer.objects.active=rig
kw=dict(use_selection=True,path_mode='COPY',embed_textures=False,add_leaf_bones=False,bake_anim_use_all_actions=False,bake_anim_use_nla_strips=False,bake_anim_simplify_factor=0,axis_forward='-Y',axis_up='Z')
bpy.ops.export_scene.fbx(filepath=str(r/'SK_HandBrain_Realism.fbx'),bake_anim=False,**kw)
rig.animation_data.action=bpy.data.actions['Attack_Howl'];rig.animation_data.action_slot=bpy.data.actions['Attack_Howl'].slots[0];s=bpy.context.scene;s.frame_start=1;s.frame_end=91;s.frame_set(1)
bpy.ops.export_scene.fbx(filepath=str(r/'A_HandBrain_Howl_Realism.fbx'),bake_anim=True,**kw)
(r/'export_report.json').write_text(json.dumps({'bones':len(rig.data.bones),'vertices':len(mesh.data.vertices),'slots':[m.name for m in mesh.data.materials],'howl_duration':3},indent=2))
print('HANDBRAIN_REALISM_EXPORTED')
