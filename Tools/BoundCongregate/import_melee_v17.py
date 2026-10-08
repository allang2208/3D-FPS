"""Import two authored animations and bind only their combat fields on the live BP."""
from pathlib import Path
import unreal as u
import json, shutil

PROJECT=Path('D:/FPS3D/FPSGAME')
OUT=PROJECT/'SourceAssets/BoundCongregateMeshy20261006/MeleeV17'
BASE='/Game/Monsters/BoundCongregate'
DEST=BASE+'/MeleeV17'
E=u.EditorAssetLibrary
AT=u.AssetToolsHelpers.get_asset_tools()
report={'saved':False,'assets':[],'gameplay_tested':False,'revision':'MeleeV17'}

def record():
    (OUT/'delivery.json').write_text(json.dumps(report,indent=2),encoding='utf8')

def save(asset):
    if not asset or not E.save_loaded_asset(asset,False):raise RuntimeError('Save failed '+str(asset))
    report['assets'].append(asset.get_path_name())
    record()

try:
    if u.get_editor_subsystem(u.UnrealEditorSubsystem).get_game_world():raise RuntimeError('PIE is active; preserve it.')
    dirty={p.get_path_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()}
    if any(p.startswith(DEST) or p==BASE+'/BP_BoundCongregate' for p in dirty):raise RuntimeError('Unsaved owned assets retained.')
    bp=u.load_asset(BASE+'/BP_BoundCongregate')
    cdo=u.get_default_object(bp.generated_class())
    mesh=cdo.get_editor_property('visual_mesh')
    report['visual_mesh']=mesh.get_path_name()
    report['previous_bite']=cdo.get_editor_property('bite_clip').get_path_name()
    backup=OUT/'before'
    backup.mkdir(exist_ok=True)
    source=PROJECT/'Content/Monsters/BoundCongregate/BP_BoundCongregate.uasset'
    if not (backup/source.name).exists():shutil.copy2(source,backup/source.name)
    u.SystemLibrary.execute_console_command(None,'Interchange.FeatureFlags.Import.FBX 0')
    u.SystemLibrary.execute_console_command(None,'Editor.AsyncSkinnedAssetCompilation 0')
    manifest=json.loads((OUT/'motion_manifest.json').read_text())
    contract=json.loads((OUT/'motion_contract.json').read_text())
    clips={}
    for role,entry in manifest['clips'].items():
        options=u.FbxImportUI()
        options.automated_import_should_detect_type=False
        options.mesh_type_to_import=u.FBXImportType.FBXIT_ANIMATION
        options.import_as_skeletal=True
        options.import_mesh=False
        options.import_animations=True
        options.import_materials=options.import_textures=options.create_physics_asset=False
        options.skeleton=mesh.skeleton
        data=options.anim_sequence_import_data
        data.convert_scene=data.convert_scene_unit=True
        data.force_front_x_axis=False
        data.import_uniform_scale=1
        data.set_editor_property('use_default_sample_rate',False)
        data.set_editor_property('custom_sample_rate',manifest['fps'])
        data.set_editor_property('animation_length',u.FBXAnimationLengthImportType.FBXALIT_EXPORTED_TIME)
        task=u.AssetImportTask()
        task.filename=entry['file'];task.destination_name=entry['name'];task.destination_path=DEST
        task.factory=u.FbxFactory();task.options=options
        task.automated=task.replace_existing=task.replace_existing_settings=True
        task.save=False
        AT.import_asset_tasks([task])
        clip=u.load_asset(DEST+'/'+entry['name'])
        if not clip:raise RuntimeError('Animation import failed '+role)
        clip.set_editor_property('loop',False)
        clip.set_editor_property('enable_root_motion',False)
        clip.set_editor_property('force_root_lock',True)
        clip.set_editor_property('root_motion_root_lock',u.RootMotionRootLock.REF_POSE)
        clip.set_preview_skeletal_mesh(mesh)
        E.set_metadata_tag(clip,'MotionRevision','MeleeV17-phased-120fps')
        save(clip);clips[role]=clip
    save(mesh.skeleton)
    cdo.set_editor_property('bite_clip',clips['Bite'])
    cdo.set_editor_property('flurry_clip',clips['Flurry'])
    cdo.set_editor_property('bite_contact_seconds',contract['bite']['contact'])
    cdo.set_editor_property('bite_trigger_range',280.)
    cdo.set_editor_property('bite_reach',125.)
    cdo.set_editor_property('flurry_range',280.)
    cdo.set_editor_property('flurry_damage',18.)
    cdo.set_editor_property('flurry_finisher_damage',32.)
    cdo.set_editor_property('flurry_cooldown',4.5)
    cdo.set_editor_property('flurry_palm_radius',45.)
    sound=u.load_asset('/Game/Audio/WeaponHit20260916/S_MeleeHit_Quick')
    if sound:cdo.set_editor_property('flurry_sound',sound)
    u.BlueprintEditorLibrary.compile_blueprint(bp)
    save(bp)
    report.update(saved=True,blueprint=bp.get_path_name(),clips={k:v.get_path_name() for k,v in clips.items()},
        timings=contract,kept='current visual mesh, cloth, skeleton topology, whip 120-degree cone / 2-second cooldown and F escape')
    record()
    print('BOUND_CONGREGATE_MELEE_V17_SAVED',flush=True)
except Exception as error:
    report['error']=str(error);record();raise
