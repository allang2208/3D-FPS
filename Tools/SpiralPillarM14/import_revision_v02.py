"""Save the M14 speed/death revision in UE; no PIE, rendering or acceptance tests."""
from pathlib import Path
import json, shutil, traceback
import unreal as u

PROJECT=Path('D:/FPS3D/FPSGAME')
ROOT=PROJECT/'SourceAssets/SpiralPillarM14Meshy20261004/ProductionV02'
DEST='/Game/Monsters/SpiralPillarM14'
LIB=u.EditorAssetLibrary;AT=u.AssetToolsHelpers.get_asset_tools()
REPORT=ROOT/'Records/ue_revision.json'
report={'complete':False,'saved':[],'tested':False,'rendered':False}

def record():REPORT.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
def save(asset):
    if not LIB.save_loaded_asset(asset,False):raise RuntimeError('Could not save '+asset.get_path_name())
    report['saved'].append(asset.get_path_name());record()

def main():
    u.SystemLibrary.execute_console_command(None,'Interchange.FeatureFlags.Import.FBX 0')
    source=PROJECT/'Content/Monsters/SpiralPillarM14/BP_SpiralPillarM14.uasset'
    backup=ROOT/'Before/BP_SpiralPillarM14.uasset'
    backup.parent.mkdir(parents=True,exist_ok=True)
    if not backup.exists():shutil.copy2(source,backup)
    mesh=u.load_asset(DEST+'/SK_M14')
    name='A_M14_Death_v02';clip=u.load_asset(DEST+'/Animations/'+name) if LIB.does_asset_exist(DEST+'/Animations/'+name) else None
    if not clip:
        task=u.AssetImportTask();task.filename=str(ROOT/'Exports/A_M14_Death_v02.fbx')
        task.destination_path=DEST+'/Animations';task.destination_name=name;task.automated=True;task.save=False
        task.factory=u.FbxFactory()
        options=u.FbxImportUI();options.automated_import_should_detect_type=False
        options.import_as_skeletal=True;options.mesh_type_to_import=u.FBXImportType.FBXIT_ANIMATION
        options.import_mesh=False;options.import_animations=True;options.import_materials=False;options.import_textures=False
        options.skeleton=mesh.skeleton;data=options.anim_sequence_import_data
        data.convert_scene=True;data.convert_scene_unit=True;data.import_uniform_scale=1.
        data.set_editor_property('use_default_sample_rate',False);data.set_editor_property('custom_sample_rate',30)
        data.set_editor_property('animation_length',u.FBXAnimationLengthImportType.FBXALIT_EXPORTED_TIME)
        task.options=options;AT.import_asset_tasks([task])
        clip=u.load_asset(DEST+'/Animations/'+name)
        if not clip:raise RuntimeError('Death animation was not imported')
    clip.set_editor_property('enable_root_motion',False);clip.set_editor_property('force_root_lock',True)
    clip.set_editor_property('loop',False);clip.set_preview_skeletal_mesh(mesh);save(clip);save(mesh.skeleton)
    name='PA_M14_Corpse_v02';path=DEST+'/'+name
    # The PhysicsAsset factory opens an interactive generation dialog. Duplicate
    # the existing query package, then replace only the duplicate's bodies below.
    corpse=u.load_asset(path) if LIB.does_asset_exist(path) else LIB.duplicate_asset(mesh.physics_asset.get_path_name(),path)
    if not u.SpiralPillarM14.build_corpse_physics(mesh,mesh.physics_asset,corpse):raise RuntimeError('Corpse compound creation failed')
    save(corpse)
    bp=u.load_asset(DEST+'/BP_SpiralPillarM14');u.BlueprintEditorLibrary.compile_blueprint(bp)
    cdo=u.get_default_object(bp.generated_class())
    cdo.set_editor_property('walk_speed',56.)
    # Existing 2.4 s source cycle plays at 2x at 56 cm/s. Do not double this denominator.
    cdo.set_editor_property('animation_walk_speed',28.)
    cdo.set_editor_property('death_clip',clip);cdo.set_editor_property('corpse_physics_asset',corpse)
    cdo.get_editor_property('character_movement').set_editor_property('max_walk_speed',56.)
    u.BlueprintEditorLibrary.compile_blueprint(bp);save(bp)
    report.update(complete=True,display_name='螺柱 M-14',walk_speed_cm_s=56.,animation_source_speed_cm_s=28.,
        full_speed_animation_rate=2.,full_speed_cycle_seconds=1.2,death_animation=clip.get_path_name(),
        corpse_asset=corpse.get_path_name(),corpse_body_count=1,independent_corpse_joints=0,
        alive_physics_asset=mesh.physics_asset.get_path_name(),handoff_seconds=1.8,
        user_testing_pending=True)
    record();print('M14_V02_UE_SAVED')

try:main()
except Exception:
    report['error']=traceback.format_exc();record();raise
