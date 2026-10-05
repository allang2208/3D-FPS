"""Save the faster M14 bite with its matching hit clock and engagement range."""
from pathlib import Path
import json, shutil, traceback
import unreal as u

PROJECT=Path('D:/FPS3D/FPSGAME')
ROOT=PROJECT/'SourceAssets/SpiralPillarM14Meshy20261004/ProductionV08'
DEST='/Game/Monsters/SpiralPillarM14';LIB=u.EditorAssetLibrary
REPORT=ROOT/'Records/ue_revision.json'
report={'complete':False,'saved':[],'tested':False,'rendered':False,'native_code_changed':False}

def record():REPORT.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
def save(asset):
    if not LIB.save_loaded_asset(asset,False):raise RuntimeError('Could not save '+asset.get_path_name())
    report['saved'].append(asset.get_path_name());record()

def main():
    source=PROJECT/'Content/Monsters/SpiralPillarM14/BP_SpiralPillarM14.uasset'
    backup=ROOT/'Before/BP_SpiralPillarM14.uasset';backup.parent.mkdir(parents=True,exist_ok=True)
    if not backup.exists():shutil.copy2(source,backup)
    bp=u.load_asset(DEST+'/BP_SpiralPillarM14')
    cdo=u.get_default_object(bp.generated_class());mesh=cdo.get_editor_property('visual_mesh')
    report['previous']={key:float(cdo.get_editor_property(key)) for key in
        ('bite_contact_seconds','mouth_reach','bite_trigger_range','bite_cooldown')}
    report['previous']['bite_clip']=cdo.get_editor_property('bite_clip').get_path_name()
    report['preserved']={key:cdo.get_editor_property(key).get_path_name() for key in
        ('visual_mesh','death_clip','move_clip','turn_left_clip','turn_right_clip','spit_clip','sweep_positive_clip','sweep_negative_clip')}
    path=DEST+'/Animations/A_M14_Bite_v08'
    if not LIB.does_asset_exist(path):
        old=u.SystemLibrary.get_console_variable_bool_value('Interchange.FeatureFlags.Import.FBX')
        try:
            u.SystemLibrary.execute_console_command(None,'Interchange.FeatureFlags.Import.FBX 0')
            task=u.AssetImportTask();task.filename=str(ROOT/'Exports/A_M14_Bite_v08.fbx')
            task.destination_path=DEST+'/Animations';task.destination_name='A_M14_Bite_v08'
            task.automated=True;task.save=False;task.factory=u.FbxFactory()
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
    if not clip:raise RuntimeError('Bite V08 was not imported')
    clip.set_editor_property('enable_root_motion',False);clip.set_editor_property('force_root_lock',True)
    clip.set_editor_property('loop',False);clip.set_preview_skeletal_mesh(mesh);save(clip);save(mesh.skeleton)
    settings={'bite_contact_seconds':.43,'mouth_reach':125.,'bite_trigger_range':260.}
    cdo.set_editor_property('bite_clip',clip)
    for key,value in settings.items():cdo.set_editor_property(key,value)
    u.BlueprintEditorLibrary.compile_blueprint(bp);save(bp)
    report.update(complete=True,bite_animation=clip.get_path_name(),settings=settings,
        duration_seconds=.95,speed_multiplier=2.,extra_maw_thrust_cm=5.,derived_stop_range_cm=245.,
        cooldown_changed=False,damage_changed=False,user_testing_pending=True)
    record();print('M14_V08_BITE_SAVED')

try:main()
except Exception:
    report['error']=traceback.format_exc();record();raise
