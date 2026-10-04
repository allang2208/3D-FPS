"""Save the scoped claw animation and small-arm joint skin to the live M09 assets."""
import json,shutil,traceback,unreal as u
from pathlib import Path
ROOT=Path('D:/FPS3D/FPSGAME/SourceAssets/HangingBellM09Meshy20261003/CrownClawV15')
BASE='/Game/Monsters/HangingBellM09/V04';PATH=BASE+'/Animations/A_M09_Claw'
A=u.EditorAssetLibrary
report={'complete':False,'saved':[],'game_tested':False,'native_build_required':False}
def receipt():(ROOT/'Records/import_saved.json').write_text(json.dumps(report,indent=2),encoding='utf8')
def save(asset):
    if not A.save_loaded_asset(asset,False):raise RuntimeError('Save failed: '+asset.get_path_name())
    report['saved'].append(asset.get_path_name());receipt()
def import_asset(filename,path,options):
    t=u.AssetImportTask();t.filename=str(filename);t.destination_path=path.rsplit('/',1)[0];t.destination_name=path.rsplit('/',1)[1]
    t.automated=True;t.save=False;t.replace_existing=True;t.replace_existing_settings=True;t.options=options;t.factory=u.FbxFactory()
    u.AssetToolsHelpers.get_asset_tools().import_asset_tasks([t])
    if not t.imported_object_paths:raise RuntimeError('Import produced no asset: '+str(filename))
    return u.load_asset(path)
try:
    if not globals().get('M09_COMMANDLET',False) and u.get_editor_subsystem(u.UnrealEditorSubsystem).get_game_world():
        raise RuntimeError('PIE active; preserve running game and defer the M09 import')
    dirty=[p.get_path_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()]
    if any(p.startswith(BASE) for p in dirty):raise RuntimeError('M09 has unsaved changes; preserve them')
    mesh=u.load_asset(BASE+'/SK_M09');skeleton=mesh.skeleton;physics=mesh.physics_asset
    backup=ROOT/'Before';backup.mkdir(exist_ok=True)
    for asset in (mesh,skeleton,u.load_asset(PATH)):
        relative=asset.get_path_name().split('.')[0].removeprefix('/Game/')+'.uasset'
        source=Path('D:/FPS3D/FPSGAME/Content')/relative;dest=backup/source.name
        if not dest.exists():shutil.copy2(source,dest)
    slots_before=list(mesh.materials)
    u.SystemLibrary.execute_console_command(None,'Interchange.FeatureFlags.Import.FBX 0')
    o=u.FbxImportUI();o.automated_import_should_detect_type=False;o.mesh_type_to_import=u.FBXImportType.FBXIT_SKELETAL_MESH
    o.import_as_skeletal=True;o.import_mesh=True;o.import_animations=False;o.import_materials=False;o.import_textures=False
    o.skeleton=skeleton;o.create_physics_asset=False;o.physics_asset=physics
    data=o.skeletal_mesh_import_data;data.convert_scene=True;data.convert_scene_unit=True;data.import_uniform_scale=1.
    data.set_editor_property('update_skeleton_reference_pose',False);data.set_editor_property('use_t0_as_ref_pose',False)
    data.normal_import_method=u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS
    mesh=import_asset(ROOT/'Exports/M09_Rigged_ClawV15.fbx',BASE+'/SK_M09',o)
    slot_map={str(s.material_slot_name):s.material_interface for s in slots_before}
    slots=list(mesh.materials)
    for slot in slots:
        if str(slot.material_slot_name) in slot_map:slot.material_interface=slot_map[str(slot.material_slot_name)]
    mesh.materials=slots
    if mesh.physics_asset!=physics:raise RuntimeError('Import did not retain the existing V13 corpse physics asset')
    A.set_metadata_tag(mesh,'M09SkinRevision','V15 V13 ownership + continuous small elbow/wrist bands')
    save(mesh)
    o=u.FbxImportUI();o.automated_import_should_detect_type=False;o.mesh_type_to_import=u.FBXImportType.FBXIT_ANIMATION
    o.import_as_skeletal=True;o.import_mesh=False;o.import_animations=True;o.import_materials=False;o.import_textures=False;o.skeleton=skeleton
    data=o.anim_sequence_import_data;data.convert_scene=True;data.convert_scene_unit=True;data.import_uniform_scale=1.
    data.set_editor_property('use_default_sample_rate',False);data.set_editor_property('custom_sample_rate',60)
    data.set_editor_property('animation_length',u.FBXAnimationLengthImportType.FBXALIT_EXPORTED_TIME)
    clip=import_asset(ROOT/'Exports/A_M09_CrownClaw_V15.fbx',PATH,o)
    clip.set_editor_property('enable_root_motion',False);clip.set_editor_property('force_root_lock',True)
    clip.set_editor_property('loop',False);clip.set_editor_property('rate_scale',1.);clip.set_preview_skeletal_mesh(mesh)
    A.set_metadata_tag(clip,'M09AnimationRevision','CrownClawV15 supported forward/downward paired rake')
    A.set_metadata_tag(clip,'M09ClawDonor','Attack_D contact pacing; bespoke M09 whole-arm choreography')
    save(clip)
    if skeleton.get_outermost().is_dirty():save(skeleton)
    report.update({'complete':True,'duration':1.1,'contact':[.35,.55],
        'physics_retained':physics.get_path_name(),'skeleton_reused':skeleton.get_path_name(),
        'other_animations_modified':False,'AI_damage_cooldown_unchanged':True,
        'offline_inspection':'CrownClawV15/Inspection; authored mesh poses, not PIE acceptance'})
    receipt();print('M09_CROWN_CLAW_V15_SAVED '+clip.get_path_name())
except Exception:
    report['error']=traceback.format_exc();receipt();raise
