"""Import M14 secondary-motion loops and save only their locomotion bindings."""
from pathlib import Path
import json, shutil, traceback
import unreal as u

PROJECT=Path('D:/FPS3D/FPSGAME')
ROOT=PROJECT/'SourceAssets/SpiralPillarM14Meshy20261004/ProductionV07'
DEST='/Game/Monsters/SpiralPillarM14'
LIB=u.EditorAssetLibrary
REPORT=ROOT/'Records/ue_revision.json'
report={'complete':False,'saved':[],'tested':False,'rendered':False}

def record():REPORT.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
def save(asset):
    if not LIB.save_loaded_asset(asset,False):raise RuntimeError('Could not save '+asset.get_path_name())
    report['saved'].append(asset.get_path_name());record()

def main():
    source=PROJECT/'Content/Monsters/SpiralPillarM14/BP_SpiralPillarM14.uasset'
    backup=ROOT/'Before/BP_SpiralPillarM14.uasset';backup.parent.mkdir(parents=True,exist_ok=True)
    if not backup.exists():shutil.copy2(source,backup)
    bp=u.load_asset(DEST+'/BP_SpiralPillarM14');u.BlueprintEditorLibrary.compile_blueprint(bp)
    cdo=u.get_default_object(bp.generated_class());mesh=cdo.get_editor_property('visual_mesh')
    actions={'move_clip':'Move','turn_left_clip':'TurnLeft','turn_right_clip':'TurnRight'}
    report['previous']={prop:cdo.get_editor_property(prop).get_path_name() for prop in actions}
    report['preserved']={prop:cdo.get_editor_property(prop).get_path_name() for prop in
        ('visual_mesh','idle_clip','bite_clip','spit_clip','sweep_positive_clip','sweep_negative_clip','death_clip','corpse_physics_asset')}
    report['preserved'].update({prop:float(cdo.get_editor_property(prop)) for prop in
        ('walk_speed','animation_walk_speed','bite_trigger_range','mouth_reach','death_physics_fraction')})
    previous_flag=u.SystemLibrary.get_console_variable_bool_value('Interchange.FeatureFlags.Import.FBX')
    try:
        u.SystemLibrary.execute_console_command(None,'Interchange.FeatureFlags.Import.FBX 0')
        tasks=[]
        for role in actions.values():
            name='A_M14_'+role+'_v07'
            if LIB.does_asset_exist(DEST+'/Animations/'+name):continue
            task=u.AssetImportTask();task.filename=str(ROOT/'Exports'/(name+'.fbx'))
            task.destination_path=DEST+'/Animations';task.destination_name=name
            task.automated=True;task.save=False;task.factory=u.FbxFactory()
            options=u.FbxImportUI();options.automated_import_should_detect_type=False
            options.import_as_skeletal=True;options.mesh_type_to_import=u.FBXImportType.FBXIT_ANIMATION
            options.import_mesh=False;options.import_animations=True
            options.import_materials=False;options.import_textures=False;options.skeleton=mesh.skeleton
            data=options.anim_sequence_import_data
            data.convert_scene=True;data.convert_scene_unit=True;data.import_uniform_scale=1.
            data.set_editor_property('use_default_sample_rate',False);data.set_editor_property('custom_sample_rate',30)
            data.set_editor_property('animation_length',u.FBXAnimationLengthImportType.FBXALIT_EXPORTED_TIME)
            task.options=options;tasks.append(task)
        if tasks:u.AssetToolsHelpers.get_asset_tools().import_asset_tasks(tasks)
    finally:
        u.SystemLibrary.execute_console_command(None,'Interchange.FeatureFlags.Import.FBX '+('1' if previous_flag else '0'))
    bound={}
    for prop,role in actions.items():
        clip=u.load_asset(DEST+'/Animations/A_M14_'+role+'_v07')
        if not clip:raise RuntimeError('Missing imported action '+role)
        clip.set_editor_property('enable_root_motion',False);clip.set_editor_property('force_root_lock',True)
        clip.set_editor_property('loop',True);clip.set_preview_skeletal_mesh(mesh);save(clip)
        cdo.set_editor_property(prop,clip);bound[prop]=clip.get_path_name()
    save(mesh.skeleton)
    u.BlueprintEditorLibrary.compile_blueprint(bp);save(bp)
    report.update(complete=True,bindings=bound,source_duration_seconds=2.4,source_fps=30,
        full_speed_cycle_seconds=1.2,native_code_changed=False,user_testing_pending=True)
    record();print('M14_V07_LOCOMOTION_SAVED')

try:main()
except Exception:
    report['error']=traceback.format_exc();record();raise
