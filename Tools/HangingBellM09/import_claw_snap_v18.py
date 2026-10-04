"""Import/save only the faster and sharper V18 claw into the existing M09 reference."""
import json,shutil,traceback,unreal as u
from pathlib import Path
ROOT=Path('D:/FPS3D/FPSGAME/SourceAssets/HangingBellM09Meshy20261003/ClawSnapV18')
BASE='/Game/Monsters/HangingBellM09/V04';PATH=BASE+'/Animations/A_M09_Claw';A=u.EditorAssetLibrary
report={'complete':False,'saved':[],'game_tested':False,'rendered':False,'native_build_required':False}
def receipt():(ROOT/'Records/import_saved.json').write_text(json.dumps(report,indent=2),encoding='utf8')
def save(asset):
    if not A.save_loaded_asset(asset,False):raise RuntimeError('Could not save '+asset.get_path_name())
    report['saved'].append(asset.get_path_name());receipt()
try:
    if not globals().get('M09_COMMANDLET',False) and u.get_editor_subsystem(u.UnrealEditorSubsystem).get_game_world():
        raise RuntimeError('PIE active; preserve user game before animation import')
    dirty={p.get_path_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()}
    if PATH in dirty or BASE+'/SK_M09_Skeleton' in dirty:raise RuntimeError('Preserve unsaved M09 animation or skeleton changes')
    mesh=u.load_asset(BASE+'/SK_M09');skeleton=mesh.skeleton
    backup=ROOT/'Before';backup.mkdir(exist_ok=True)
    for path in (PATH,skeleton.get_path_name().split('.')[0]):
        source=Path('D:/FPS3D/FPSGAME/Content')/(path.removeprefix('/Game/')+'.uasset')
        dest=backup/source.name
        if not dest.exists():shutil.copy2(source,dest)
    u.SystemLibrary.execute_console_command(None,'Interchange.FeatureFlags.Import.FBX 0')
    options=u.FbxImportUI();options.automated_import_should_detect_type=False
    options.mesh_type_to_import=u.FBXImportType.FBXIT_ANIMATION
    options.import_as_skeletal=True;options.import_mesh=False;options.import_animations=True
    options.import_materials=False;options.import_textures=False;options.skeleton=skeleton
    data=options.anim_sequence_import_data;data.convert_scene=True;data.convert_scene_unit=True;data.import_uniform_scale=1.
    data.set_editor_property('use_default_sample_rate',False);data.set_editor_property('custom_sample_rate',60)
    data.set_editor_property('animation_length',u.FBXAnimationLengthImportType.FBXALIT_EXPORTED_TIME)
    task=u.AssetImportTask();task.filename=str(ROOT/'Exports/A_M09_CrownClaw_Snap_V18.fbx')
    task.destination_path=PATH.rsplit('/',1)[0];task.destination_name=PATH.rsplit('/',1)[1]
    task.automated=True;task.save=False;task.replace_existing=True;task.replace_existing_settings=True
    task.options=options;task.factory=u.FbxFactory()
    u.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
    if not task.imported_object_paths:raise RuntimeError('No animation imported')
    clip=u.load_asset(PATH)
    clip.set_editor_property('enable_root_motion',False);clip.set_editor_property('force_root_lock',True)
    clip.set_editor_property('loop',False);clip.set_editor_property('rate_scale',1.);clip.set_preview_skeletal_mesh(mesh)
    A.set_metadata_tag(clip,'M09AnimationRevision','V18 faster rake and sharper body impulse with fixed ceiling grips')
    A.set_metadata_tag(clip,'M09ClawDonor','V16 continuous arms; V18 65ms rake and 50ms follow-through hold')
    save(clip)
    if skeleton.get_path_name().split('.')[0] in {p.get_path_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()}:save(skeleton)
    report.update({'complete':True,'duration':1.1,'contact':[.35,.55],
        'source':task.filename,'rapid_rake':[.38,.445],'followthrough_hold':[.445,.495],
        'mesh_weights_physics_unchanged':True,
        'damage_cooldown_AI_unchanged':True,'other_animations_modified':False,
        'runtime_reference':PATH,'ceiling_support':'Baked support-chain solution and existing M09 runtime hand IK'})
    receipt();print('M09_CLAW_SNAP_V18_SAVED')
except Exception:
    report['error']=traceback.format_exc();receipt();raise
