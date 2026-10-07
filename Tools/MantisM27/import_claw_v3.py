"""Import the two new attack clips; preserve the V2 mesh, rig and other clips."""
from pathlib import Path
import json
import unreal as u

ROOT=Path('D:/FPS3D/FPSGAME/SourceAssets/MantisM27/ClawV3')
SOURCE=ROOT/'Delivery';DEST='/Game/Monsters/MantisM27/ClawV3/Animations'
REPORT=ROOT/'ue_claw_receipt.json'
manifest=json.loads((SOURCE/'motion_manifest.json').read_text(encoding='utf-8'))
LIB=u.EditorAssetLibrary

def connect():
    report=json.loads(REPORT.read_text(encoding='utf-8'))
    if '-run=pythonscript' not in u.SystemLibrary.get_command_line().lower():
        if u.get_editor_subsystem(u.LevelEditorSubsystem).is_in_play_in_editor():
            raise RuntimeError('M27 ClawV3 connection requires ending PIE; editor can remain open.')
    if not report['assets_saved']:raise RuntimeError('M27 ClawV3 import incomplete.')
    u.AssetRegistryHelpers.get_asset_registry().scan_paths_synchronous([DEST],True)
    clips={role:u.load_asset(path) for role,path in report['clips'].items()}
    bp=u.load_asset('/Game/Monsters/MantisM27/BP_MantisM27')
    if not all(clips.values()) or not bp:raise RuntimeError('M27 attack packages unavailable.')
    defaults=u.get_default_object(bp.generated_class())
    if defaults.get_editor_property('visual_mesh').get_path_name()!=report['mesh']:
        raise RuntimeError('M27 mesh binding changed during production; preserve the current Blueprint.')
    previous={}
    for prop in ['left_slash_clip','right_slash_clip','attack_clip','contact_time','contact_end','recovery_time']:
        value=defaults.get_editor_property(prop)
        previous[prop]=value.get_path_name() if isinstance(value,u.Object) else value
    defaults.set_editor_property('left_slash_clip',clips['LeftSlash'])
    defaults.set_editor_property('right_slash_clip',clips['RightSlash'])
    defaults.set_editor_property('attack_clip',clips['LeftSlash'])
    defaults.set_editor_property('contact_time',manifest['contact_window_seconds'][0])
    defaults.set_editor_property('contact_end',manifest['contact_window_seconds'][1])
    defaults.set_editor_property('recovery_time',manifest['recovery_time_seconds'])
    LIB.set_metadata_tag(bp,'AttackRevision','ClawV3: native Mutant3/Khaimera body motion, long-scythe fitting, 0.70 s attacks')
    if not LIB.save_loaded_asset(bp,False):raise RuntimeError('Could not save the existing M27 F6 Blueprint.')
    report.update(saved=True,blueprint_connected=True,blueprint=bp.get_path_name(),f6_entry='MantisM27',previous=previous,
                  contact_window_seconds=manifest['contact_window_seconds'],recovery_time_seconds=manifest['recovery_time_seconds'])
    REPORT.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    print('M27_CLAW_V3_CONNECTED_AND_SAVED '+str(REPORT),flush=True)

def run():
    mesh=u.load_asset('/Game/Monsters/MantisM27/BindingV2/SK_MantisM27_BindingV2')
    report={'revision':'ClawV3','mesh':mesh.get_path_name(),'assets_saved':False,'blueprint_connected':False,
            'saved':False,'tested':False,'runtime_tested':False,'rendered':False,'user_review_pending':True,'clips':{}}
    try:
        for role,info in manifest['clips'].items():
            name=Path(info['file']).stem
            options=u.FbxImportUI();options.automated_import_should_detect_type=False
            options.mesh_type_to_import=u.FBXImportType.FBXIT_ANIMATION
            options.import_mesh=False;options.import_as_skeletal=True;options.import_animations=True
            options.import_materials=False;options.import_textures=False;options.skeleton=mesh.skeleton
            data=options.anim_sequence_import_data
            data.set_editor_property('convert_scene',True);data.set_editor_property('convert_scene_unit',True)
            data.set_editor_property('import_uniform_scale',1.)
            data.set_editor_property('use_default_sample_rate',False);data.set_editor_property('custom_sample_rate',60)
            data.set_editor_property('animation_length',u.FBXAnimationLengthImportType.FBXALIT_EXPORTED_TIME)
            data.set_editor_property('preserve_local_transform',True)
            task=u.AssetImportTask();task.filename=str(SOURCE/info['file']);task.destination_path=DEST;task.destination_name=name
            task.automated=True;task.save=False;task.replace_existing=True;task.replace_existing_settings=True
            task.options=options;task.factory=u.FbxFactory()
            u.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
            clip=u.load_asset(DEST+'/'+name)
            if not clip or not task.imported_object_paths:raise RuntimeError('Could not import '+name)
            clip.set_preview_skeletal_mesh(mesh);clip.set_editor_property('enable_root_motion',False)
            clip.set_editor_property('force_root_lock',False)
            LIB.set_metadata_tag(clip,'SourceAnimation',info['source'])
            LIB.set_metadata_tag(clip,'Authoring','ClawV3; native whole-body retarget; M27 scythe clearance; nonlinear timing; no runtime test')
            if not LIB.save_loaded_asset(clip,False):raise RuntimeError('Could not save '+name)
            report['clips'][role]=clip.get_path_name()
        report.update(assets_saved=True,duration_seconds=manifest['duration_seconds'],fps=60)
        REPORT.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
        print('M27_CLAW_V3_ASSETS_SAVED',flush=True)
        if '-m27connectclawv3' in u.SystemLibrary.get_command_line().lower():connect()
    except Exception as error:
        report['error']=str(error)
        REPORT.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
        raise

if __name__=='__main__':run()
