"""Import and save only the M14 extended-bite revision in the existing editor or a commandlet."""
from pathlib import Path
import json, traceback
import unreal as u

ROOT=Path('D:/FPS3D/FPSGAME/SourceAssets/SpiralPillarM14Meshy20261004/ProductionV03')
DEST='/Game/Monsters/SpiralPillarM14'
LIB=u.EditorAssetLibrary
report={'complete':False,'saved':[],'tested':False,'rendered':False,'native_code_changed':False}
REPORT=ROOT/'Records/ue_revision.json'

def record():REPORT.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
def save(asset):
    if not LIB.save_loaded_asset(asset,False):raise RuntimeError('Could not save '+asset.get_path_name())
    report['saved'].append(asset.get_path_name());record()

def main():
    bp=u.load_asset(DEST+'/BP_SpiralPillarM14')
    cdo=u.get_default_object(bp.generated_class())
    previous=cdo.get_editor_property('bite_clip')
    report['previous_bite']=previous.get_path_name() if previous else None
    report['preserved_death']=cdo.get_editor_property('death_clip').get_path_name()
    report['preserved_walk_speed']=float(cdo.get_editor_property('walk_speed'))
    # Keep this revision scoped to the source action the user asked to extend.
    allowed={DEST+'/Animations/A_M14_Bite.A_M14_Bite',DEST+'/Animations/A_M14_Bite_v03.A_M14_Bite_v03'}
    if report['previous_bite'] not in allowed:raise RuntimeError('The active bite was changed outside this revision: '+str(report['previous_bite']))
    mesh=cdo.get_editor_property('visual_mesh')
    path=DEST+'/Animations/A_M14_Bite_v03'
    clip=u.load_asset(path) if LIB.does_asset_exist(path) else None
    if not clip:
        old_fbx=u.SystemLibrary.get_console_variable_bool_value('Interchange.FeatureFlags.Import.FBX')
        try:
            u.SystemLibrary.execute_console_command(None,'Interchange.FeatureFlags.Import.FBX 0')
            task=u.AssetImportTask();task.filename=str(ROOT/'Exports/A_M14_Bite_v03.fbx')
            task.destination_path=DEST+'/Animations';task.destination_name='A_M14_Bite_v03'
            task.automated=True;task.save=False;task.factory=u.FbxFactory()
            options=u.FbxImportUI();options.automated_import_should_detect_type=False
            options.import_as_skeletal=True;options.mesh_type_to_import=u.FBXImportType.FBXIT_ANIMATION
            options.import_mesh=False;options.import_animations=True;options.import_materials=False;options.import_textures=False
            options.skeleton=mesh.skeleton;data=options.anim_sequence_import_data
            data.convert_scene=True;data.convert_scene_unit=True;data.import_uniform_scale=1.
            data.set_editor_property('use_default_sample_rate',False);data.set_editor_property('custom_sample_rate',30)
            data.set_editor_property('animation_length',u.FBXAnimationLengthImportType.FBXALIT_EXPORTED_TIME)
            task.options=options;u.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
            clip=u.load_asset(path)
            if not clip:raise RuntimeError('Extended bite was not imported')
        finally:u.SystemLibrary.execute_console_command(None,'Interchange.FeatureFlags.Import.FBX '+('1' if old_fbx else '0'))
    clip.set_editor_property('enable_root_motion',False);clip.set_editor_property('force_root_lock',True)
    clip.set_editor_property('loop',False);clip.set_preview_skeletal_mesh(mesh);save(clip);save(mesh.skeleton)
    cdo.set_editor_property('bite_clip',clip)
    u.BlueprintEditorLibrary.compile_blueprint(bp);save(bp)
    report.update(complete=True,bite_animation=clip.get_path_name(),outward_displacement_multiplier=1.5,
        duration_seconds=1.9,contact_seconds=.86,hit_anchor='mouth_socket',hit_anchor_follows_animation=True,
        user_testing_pending=True)
    record();print('M14_V03_BITE_SAVED')

try:main()
except Exception:
    report['error']=traceback.format_exc();record();raise
