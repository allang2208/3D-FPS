"""Save the produced claw clip into the existing live M09 animation reference."""
import json, unreal as u
from pathlib import Path

ROOT=Path('D:/FPS3D/FPSGAME/SourceAssets/HangingBellM09Meshy20261003/CrownClawV11')
BASE='/Game/Monsters/HangingBellM09/V04'
PATH=BASE+'/Animations/A_M09_Claw'
A=u.EditorAssetLibrary
if not globals().get('M09_COMMANDLET',False):
    if u.get_editor_subsystem(u.UnrealEditorSubsystem).get_game_world():
        raise RuntimeError('PIE active: preserve current game before asset editing')
dirty={p.get_path_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()}
if PATH in dirty or BASE+'/SK_M09_Skeleton' in dirty:
    raise RuntimeError('Preserve unsaved M09 animation or skeleton')
mesh=u.load_asset(BASE+'/SK_M09')
u.SystemLibrary.execute_console_command(None,'Interchange.FeatureFlags.Import.FBX 0')
options=u.FbxImportUI()
options.automated_import_should_detect_type=False
options.mesh_type_to_import=u.FBXImportType.FBXIT_ANIMATION
options.import_as_skeletal=True
options.import_mesh=False
options.import_animations=True
options.import_materials=False
options.import_textures=False
options.skeleton=mesh.skeleton
data=options.anim_sequence_import_data
data.convert_scene=True
data.convert_scene_unit=True
data.import_uniform_scale=1.
data.set_editor_property('use_default_sample_rate',False)
data.set_editor_property('custom_sample_rate',60)
data.set_editor_property('animation_length',u.FBXAnimationLengthImportType.FBXALIT_EXPORTED_TIME)
task=u.AssetImportTask()
task.filename=str(ROOT/'Exports/A_M09_CrownClaw_V11.fbx')
task.destination_path=PATH.rsplit('/',1)[0]
task.destination_name=PATH.rsplit('/',1)[1]
task.automated=True
task.save=False
task.replace_existing=True
task.replace_existing_settings=True
task.options=options
task.factory=u.FbxFactory()
u.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
if not task.imported_object_paths:
    raise RuntimeError('Claw animation did not import')
clip=u.load_asset(PATH)
if not clip:
    raise RuntimeError('Claw animation unavailable after import')
clip.set_editor_property('enable_root_motion',False)
clip.set_editor_property('force_root_lock',True)
clip.set_editor_property('loop',False)
clip.set_editor_property('rate_scale',1.)
clip.set_preview_skeletal_mesh(mesh)
A.set_metadata_tag(clip,'M09AnimationRevision','CrownClawV11_AttackD')
A.set_metadata_tag(clip,'M09ClawDonor','M07 LibrarySweepV27 / ZombieAnimationPack Attack_D')
if not A.save_loaded_asset(clip,False):
    raise RuntimeError('Claw animation save failed')
report={'complete':True,'saved':[clip.get_path_name()],
    'source':task.filename,'skeleton_reused':mesh.skeleton.get_path_name(),
    'runtime_reference':'Existing Clips[Claw] path, including AI/F6 blueprint overrides',
    'duration':1.1,'contact':[.35,.55],'cooldown':2.5,'damage_multiplier':.55,
    'audio_reused':BASE+'/Audio/S_M09_Claw','other_animations_modified':False,
    'native_build_required':True,'tested':False,'rendered':False}
(ROOT/'Records/import_saved.json').write_text(json.dumps(report,indent=2),encoding='utf8')
print('M09_CROWN_CLAW_V11_SAVED '+clip.get_path_name())
