"""Save the seam-consistent mesh, revised slam and requested ranged tuning."""
from pathlib import Path
import unreal as u
import json, shutil, traceback
PROJECT=Path('D:/FPS3D/FPSGAME');ROOT=PROJECT/'SourceAssets/SpiralPillarM14Meshy20261004/ProductionV13'
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
    report['preserved']={key:cdo.get_editor_property(key).get_path_name() for key in (
        'move_clip','turn_left_clip','turn_right_clip','bite_clip','spit_clip','whirlwind_clip','death_clip',
        'corpse_physics_asset','mucus_material','mucus_core_material')}
    path=DEST+'/SK_M14_HardwareSeams_v13'
    mesh=u.load_asset(path) if E.does_asset_exist(path) else E.duplicate_asset(DEST+'/SK_M14_HardwareSeparated_v11',path)
    bones=json.loads((ROOT/'Exports/hardware_bones.json').read_text(encoding='utf8'))
    if not u.SpiralPillarM14.apply_hardware_skin(mesh,str(ROOT/'Exports/hardware_skin.bin'),[u.Name(b) for b in bones]):
        raise RuntimeError('Hardware seam repair could not be applied')
    save(mesh)
    name='A_M14_TrunkSlam_v13';path=DEST+'/Animations/'+name
    if not E.does_asset_exist(path):
        old=u.SystemLibrary.get_console_variable_bool_value('Interchange.FeatureFlags.Import.FBX')
        try:
            u.SystemLibrary.execute_console_command(None,'Interchange.FeatureFlags.Import.FBX 0')
            task=u.AssetImportTask();task.filename=str(ROOT/'Exports'/(name+'.fbx'))
            task.destination_path=DEST+'/Animations';task.destination_name=name
            task.automated=True;task.save=False;task.factory=u.FbxFactory()
            options=u.FbxImportUI();options.automated_import_should_detect_type=False
            options.import_as_skeletal=True;options.mesh_type_to_import=u.FBXImportType.FBXIT_ANIMATION
            options.import_mesh=False;options.import_animations=True;options.import_materials=False;options.import_textures=False
            options.skeleton=mesh.skeleton;data=options.anim_sequence_import_data
            data.convert_scene=True;data.convert_scene_unit=True;data.import_uniform_scale=1.
            data.set_editor_property('use_default_sample_rate',False);data.set_editor_property('custom_sample_rate',30)
            data.set_editor_property('animation_length',u.FBXAnimationLengthImportType.FBXALIT_EXPORTED_TIME)
            task.options=options;u.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
        finally:u.SystemLibrary.execute_console_command(None,'Interchange.FeatureFlags.Import.FBX '+('1' if old else '0'))
    clip=u.load_asset(path)
    if not clip:raise RuntimeError('Updated trunk slam was not imported')
    clip.set_editor_property('enable_root_motion',False);clip.set_editor_property('force_root_lock',True)
    clip.set_editor_property('loop',False);clip.set_preview_skeletal_mesh(mesh);save(clip);save(mesh.skeleton)
    cdo.set_editor_property('visual_mesh',mesh);cdo.get_editor_property('mesh').set_skeletal_mesh_asset(mesh)
    cdo.set_editor_property('trunk_slam_clip',clip)
    settings={'spit_cooldown':3.5,'spit_max_range':2000.,'spit_travel_range':2200.,'aggro_radius':2200.}
    for key,value in settings.items():cdo.set_editor_property(key,value)
    u.BlueprintEditorLibrary.compile_blueprint(bp);save(bp)
    report.update(complete=True,mesh=mesh.get_path_name(),attack=clip.get_path_name(),settings=settings,
        poison_layers_per_hit=1,lead='locked velocity snapshot, remaining windup plus linear interception',user_testing_pending=True)
    record();print('M14_V13_HARDWARE_SPIT_SAVED')
try:main()
except Exception:
    report['error']=traceback.format_exc();record();raise
