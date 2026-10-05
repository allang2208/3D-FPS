"""Import the six-turn attack and save the existing monster's defaults."""
from pathlib import Path
import unreal as u
import json, shutil, traceback
PROJECT=Path('D:/FPS3D/FPSGAME');ROOT=PROJECT/'SourceAssets/SpiralPillarM14Meshy20261004/ProductionV12'
DEST='/Game/Monsters/SpiralPillarM14';E=u.EditorAssetLibrary
report={'complete':False,'saved':[],'tested':False,'rendered':False}

def record():(ROOT/'Records/ue_revision.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf8')

def save(asset):
    if not E.save_loaded_asset(asset,False):raise RuntimeError('Could not save '+asset.get_path_name())
    report['saved'].append(asset.get_path_name());record()

def main():
    backup=ROOT/'Before/BP_SpiralPillarM14.uasset';backup.parent.mkdir(parents=True,exist_ok=True)
    if not backup.exists():shutil.copy2(PROJECT/'Content/Monsters/SpiralPillarM14/BP_SpiralPillarM14.uasset',backup)
    bp=u.load_asset(DEST+'/BP_SpiralPillarM14');cdo=u.get_default_object(bp.generated_class())
    try:cdo.get_editor_property('whirlwind_clip');native_ready=True
    except Exception:native_ready=False
    mesh=cdo.get_editor_property('visual_mesh')
    report['mesh']=mesh.get_path_name()
    report['preserved']={key:cdo.get_editor_property(key).get_path_name() for key in (
        'move_clip','turn_left_clip','turn_right_clip','bite_clip','spit_clip','trunk_slam_clip','death_clip',
        'corpse_physics_asset','mucus_material','mucus_core_material')}
    name='A_M14_Whirlwind_v12';path=DEST+'/Animations/'+name
    old=u.SystemLibrary.get_console_variable_bool_value('Interchange.FeatureFlags.Import.FBX')
    try:
        u.SystemLibrary.execute_console_command(None,'Interchange.FeatureFlags.Import.FBX 0')
        task=u.AssetImportTask();task.filename=str(ROOT/'Exports'/(name+'.fbx'))
        task.destination_path=DEST+'/Animations';task.destination_name=name
        task.automated=True;task.save=False;task.replace_existing=True;task.factory=u.FbxFactory()
        options=u.FbxImportUI();options.automated_import_should_detect_type=False
        options.import_as_skeletal=True;options.mesh_type_to_import=u.FBXImportType.FBXIT_ANIMATION
        options.import_mesh=False;options.import_animations=True;options.import_materials=False;options.import_textures=False
        options.skeleton=mesh.skeleton;data=options.anim_sequence_import_data
        data.convert_scene=True;data.convert_scene_unit=True;data.import_uniform_scale=1.
        data.set_editor_property('use_default_sample_rate',False);data.set_editor_property('custom_sample_rate',60)
        data.set_editor_property('animation_length',u.FBXAnimationLengthImportType.FBXALIT_EXPORTED_TIME)
        task.options=options;u.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
    finally:u.SystemLibrary.execute_console_command(None,'Interchange.FeatureFlags.Import.FBX '+('1' if old else '0'))
    clip=u.load_asset(path)
    if not clip:raise RuntimeError('Whirlwind was not imported')
    clip.set_editor_property('enable_root_motion',False);clip.set_editor_property('force_root_lock',True)
    clip.set_editor_property('loop',False);clip.set_preview_skeletal_mesh(mesh);save(clip);save(mesh.skeleton)
    report['attack']=clip.get_path_name();report['clip_saved']=True
    if not native_ready:
        report['pending']='Regular Editor native build and blueprint binding after the loaded module is released'
        record();print('M14_V12_ANIMATION_SAVED_NATIVE_BINDING_PENDING');return
    cdo.set_editor_property('whirlwind_clip',clip)
    settings={'whirlwind_cooldown':12.,'whirlwind_trigger_range':190.,'whirlwind_damage_multiplier':2.4,'whirlwind_knockback':250.}
    for key,value in settings.items():cdo.set_editor_property(key,value)
    u.BlueprintEditorLibrary.compile_blueprint(bp);save(bp)
    report.update(complete=True,attack=clip.get_path_name(),settings=settings,user_testing_pending=True)
    record();print('M14_V12_WHirlwind_SAVED')
try:main()
except Exception:
    report['error']=traceback.format_exc();record();raise
