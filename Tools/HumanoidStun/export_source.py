"""Extract the local CC0 Dizzy motion, without rendering or running the game."""
import bpy,json
from pathlib import Path
ROOT=Path('D:/FPS3D/FPSGAME/SourceAssets/HumanoidStun20260926')
ROOT.mkdir(parents=True,exist_ok=True)
SOURCE=ROOT.parent/'FatZombieMeshy20260913/sources/human-addon-animations.glb'
bpy.ops.wm.read_factory_settings(use_empty=True)
scene=bpy.context.scene;scene.render.fps=60
bpy.ops.import_scene.gltf(filepath=str(SOURCE))
rig=next(o for o in bpy.data.objects if o.type=='ARMATURE');rig.name='M2MRoot'
for track in rig.animation_data.nla_tracks:track.mute=True
action=next(a for a in bpy.data.actions if a.name=='Dizzy' or a.name.endswith('|Dizzy'))
rig.animation_data.action=action
if action.slots:rig.animation_data.action_slot=action.slots[0]
first,last=action.frame_range
scene.frame_start=round(first);scene.frame_end=round(last);scene.frame_set(scene.frame_start)
bpy.ops.object.select_all(action='DESELECT');rig.select_set(True);bpy.context.view_layer.objects.active=rig
bpy.ops.export_scene.fbx(filepath=str(ROOT/'A_M2M_Dizzy.fbx'),use_selection=True,object_types={'ARMATURE'},
    add_leaf_bones=False,use_armature_deform_only=False,bake_anim=True,bake_anim_use_all_actions=False,
    bake_anim_use_nla_strips=False,bake_anim_force_startend_keying=True,bake_anim_simplify_factor=0,
    axis_forward='-Y',axis_up='Z',apply_unit_scale=True,apply_scale_options='FBX_SCALE_UNITS')
bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'Dizzy_Source.blend'))
(ROOT/'source_clip.json').write_text(json.dumps({'source':str(SOURCE),'clip':'Dizzy','fps':60,
    'source_frames':[first,last],'export_frames':[scene.frame_start,scene.frame_end],
    'source_seconds':(last-first)/60,'export_seconds':(scene.frame_end-scene.frame_start)/60},indent=2),encoding='utf-8')
print('DIZZY_SOURCE_EXPORTED',flush=True)
