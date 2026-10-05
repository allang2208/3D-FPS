"""Import the bite animation and save the existing monster's independent melee channel."""
from pathlib import Path
import json, sys, traceback
import unreal as u
ROOT=Path(__file__).resolve().parent
PROJECT=ROOT.parents[2]
DEST='/Game/Monsters/VortexCofferM25'
REV='M25Bite20261004V1'
LIB=u.EditorAssetLibrary
record=dict(revision=REV,stage='started',saved=[],runtime_tested=False,rendered=False)
sys.path.insert(0,str(PROJECT/'Tools/InfectedDog'))
from meshy_animation_units import match_bind_root_scale

def receipt():
    (ROOT/'asset_receipt.json').write_text(json.dumps(record,ensure_ascii=False,indent=2),encoding='utf-8')
def load(path):
    asset=u.load_asset(path)
    if asset is None: raise RuntimeError('Missing asset: '+path)
    return asset
def save(asset):
    LIB.set_metadata_tag(asset,'M25.BiteRevision',REV)
    if not LIB.save_loaded_asset(asset,False): raise RuntimeError('Save failed: '+asset.get_path_name())
    record['saved'].append(asset.get_path_name());receipt()
def main():
    if Path(u.Paths.project_dir()).resolve()!=PROJECT.resolve(): raise RuntimeError('Wrong project')
    if '-run=pythonscript' not in u.SystemLibrary.get_command_line().lower():
        editor=u.get_editor_subsystem(u.UnrealEditorSubsystem)
        if editor and editor.get_game_world(): raise RuntimeError('Stop PIE before saving the bite')
    if not hasattr(u,'M25BiteComponent'): raise RuntimeError('Regular native Editor build required')
    if any(p.get_name().startswith(DEST) for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()):
        raise RuntimeError('Preserving unsaved M25 packages')
    mesh=load(DEST+'/SK_M25_VortexCoffer')
    skeleton=mesh.get_editor_property('skeleton')
    path=DEST+'/Animations/A_M25_Bite_V01'
    if LIB.does_asset_exist(path):
        clip=load(path)
        if LIB.get_metadata_tag(clip,'M25.BiteRevision')!=REV: raise RuntimeError('Preserving unowned bite asset')
    else:
        cvar='Interchange.FeatureFlags.Import.FBX'
        old=u.SystemLibrary.get_console_variable_int_value(cvar)
        u.SystemLibrary.execute_console_command(None,cvar+' 0')
        try:
            op=u.FbxImportUI()
            op.automated_import_should_detect_type=False
            op.mesh_type_to_import=u.FBXImportType.FBXIT_ANIMATION
            op.import_as_skeletal=True;op.import_mesh=False;op.import_animations=True
            op.import_materials=False;op.import_textures=False;op.skeleton=skeleton
            data=op.anim_sequence_import_data
            data.set_editor_property('use_default_sample_rate',False)
            data.set_editor_property('custom_sample_rate',30)
            data.set_editor_property('animation_length',u.FBXAnimationLengthImportType.FBXALIT_EXPORTED_TIME)
            data.set_editor_property('remove_redundant_keys',False)
            task=u.AssetImportTask()
            task.filename=str(ROOT/'A_M25_Bite_V01.fbx')
            task.destination_path=DEST+'/Animations';task.destination_name='A_M25_Bite_V01'
            task.options=op;task.automated=True;task.save=False;task.replace_existing=False
            u.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
            clip=load(path)
        finally:
            u.SystemLibrary.execute_console_command(None,cvar+' '+str(old))
    clip.set_editor_property('enable_root_motion',False)
    clip.set_editor_property('force_root_lock',False)
    clip.set_editor_property('rate_scale',1.)
    clip.set_preview_skeletal_mesh(mesh)
    record['root_units']=match_bind_root_scale(clip,mesh)
    save(clip)
    save(skeleton)
    bp=load(DEST+'/BP_VortexCofferM25')
    u.BlueprintEditorLibrary.compile_blueprint(bp)
    cdo=u.get_default_object(bp.generated_class())
    cdo.set_editor_property('bite_clip',clip)
    bite=cdo.get_editor_property('bite')
    if bite is None: raise RuntimeError('BiteExecution native component missing')
    settings=dict(bite_enabled=True,physical_attack=65.,bite_cooldown=2.5,trigger_reach=85.,
        half_angle=40.,contact_radius=55.,contact_start=.60,contact_end=.76,playback_rate=1.)
    for key,value in settings.items():bite.set_editor_property(key,value)
    save(bp)
    record.update(stage='assets_saved',animation=clip.get_path_name(),duration=clip.get_play_length(),
        component=bite.get_path_name(),settings=settings,channels='independent_physical_bite_and_magic',
        priority='front_melee_first_at_shared_BT_dispatch',simultaneous_cast_and_bite=True)
    receipt()
    u.log('M25_BITE_ANIMATION_AND_BLUEPRINT_SAVED')
try:
    main()
except Exception:
    record.update(stage='production_failed',error=traceback.format_exc());receipt();raise
