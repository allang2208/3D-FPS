"""Import three M14 actions and save only their configured monster blueprint."""
from pathlib import Path
import json, shutil, traceback
import unreal as u

PROJECT = Path('D:/FPS3D/FPSGAME')
ROOT = PROJECT/'SourceAssets/SpiralPillarM14Meshy20261004/ProductionV05'
DEST = '/Game/Monsters/SpiralPillarM14'
LIB = u.EditorAssetLibrary
REPORT = ROOT/'Records/ue_revision.json'
report = {'complete':False, 'saved':[], 'tested':False, 'rendered':False}

def record():
    REPORT.write_text(json.dumps(report, ensure_ascii=False, indent=2)+'\n', encoding='utf8')

def save(asset):
    if not LIB.save_loaded_asset(asset, False):
        raise RuntimeError('Could not save '+asset.get_path_name())
    report['saved'].append(asset.get_path_name())
    record()

def main():
    source = PROJECT/'Content/Monsters/SpiralPillarM14/BP_SpiralPillarM14.uasset'
    backup = ROOT/'Before/BP_SpiralPillarM14.uasset'
    backup.parent.mkdir(parents=True, exist_ok=True)
    if not backup.exists():
        shutil.copy2(source, backup)
    bp = u.load_asset(DEST+'/BP_SpiralPillarM14')
    u.BlueprintEditorLibrary.compile_blueprint(bp)
    cdo = u.get_default_object(bp.generated_class())
    mesh = cdo.get_editor_property('visual_mesh')
    report['preserved'] = {key:cdo.get_editor_property(key).get_path_name()
        for key in ('bite_clip','death_clip','corpse_physics_asset','move_clip')}
    report['preserved'].update({key:float(cdo.get_editor_property(key))
        for key in ('bite_trigger_range','mouth_reach','walk_speed','animation_walk_speed')})
    actions = {'spit_clip':'Spit','sweep_positive_clip':'RootSweep_PosX','sweep_negative_clip':'RootSweep_NegX'}
    old_fbx = u.SystemLibrary.get_console_variable_bool_value('Interchange.FeatureFlags.Import.FBX')
    try:
        u.SystemLibrary.execute_console_command(None, 'Interchange.FeatureFlags.Import.FBX 0')
        tasks = []
        for role in actions.values():
            name = 'A_M14_'+role+'_v05'
            task = u.AssetImportTask()
            task.filename = str(ROOT/'Exports'/(name+'.fbx'))
            task.destination_path = DEST+'/Animations'
            task.destination_name = name
            task.automated = True
            task.save = False
            task.replace_existing = True
            task.factory = u.FbxFactory()
            options = u.FbxImportUI()
            options.automated_import_should_detect_type = False
            options.import_as_skeletal = True
            options.mesh_type_to_import = u.FBXImportType.FBXIT_ANIMATION
            options.import_mesh = False
            options.import_animations = True
            options.import_materials = False
            options.import_textures = False
            options.skeleton = mesh.skeleton
            data = options.anim_sequence_import_data
            data.convert_scene = True
            data.convert_scene_unit = True
            data.import_uniform_scale = 1.
            data.set_editor_property('use_default_sample_rate', False)
            data.set_editor_property('custom_sample_rate', 30)
            data.set_editor_property('animation_length', u.FBXAnimationLengthImportType.FBXALIT_EXPORTED_TIME)
            task.options = options
            tasks.append(task)
        u.AssetToolsHelpers.get_asset_tools().import_asset_tasks(tasks)
    finally:
        u.SystemLibrary.execute_console_command(None, 'Interchange.FeatureFlags.Import.FBX '+('1' if old_fbx else '0'))
    for prop, role in actions.items():
        clip = u.load_asset(DEST+'/Animations/A_M14_'+role+'_v05')
        if not clip:
            raise RuntimeError('Missing imported action: '+role)
        clip.set_editor_property('enable_root_motion', False)
        clip.set_editor_property('force_root_lock', True)
        clip.set_editor_property('loop', False)
        clip.set_preview_skeletal_mesh(mesh)
        save(clip)
        cdo.set_editor_property(prop, clip)
    save(mesh.skeleton)
    for prop, name in [('mucus_material','M_VenomBody'),('mucus_core_material','M_VenomCore')]:
        material = u.load_asset('/Game/Fluids/VenomProjectiles20260924/'+name)
        if not material:
            raise RuntimeError('Shared liquid material is missing: '+name)
        cdo.set_editor_property(prop, material)
    settings = dict(spit_min_range=400., spit_max_range=1000., spit_aim_lock_seconds=.65,
        spit_release_seconds=1.10, spit_cooldown=7., spit_speed=1000., spit_travel_range=1100.,
        spit_damage_multiplier=.75, spit_slow_percent=.25, spit_slow_seconds=2.5,
        sweep_trigger_range=250., sweep_start_seconds=.80, sweep_end_seconds=1.20,
        sweep_cooldown=4.8, sweep_damage_multiplier=.9, sweep_radius=18.)
    for key, value in settings.items():
        cdo.set_editor_property(key, value)
    u.BlueprintEditorLibrary.compile_blueprint(bp)
    save(bp)
    report.update(complete=True, settings=settings, attack_selection='shared BT, M14 ChooseAttack',
        mucus_fx='existing shared liquid fragment/impact pool', poison=False, damaging_pool=False,
        user_testing_pending=True)
    record()
    print('M14_V05_ATTACKS_SAVED')

try:
    main()
except Exception:
    report['error'] = traceback.format_exc()
    record()
    raise
