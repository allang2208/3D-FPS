"""Replace only the three pounce animations in the running editor."""
import unreal as u
import json, shutil, os
from pathlib import Path

ROOT=Path(__file__).parent
PROJECT=ROOT.parents[2]
DEST='/Game/Monsters/Mutant3Meshy/KhaimeraV2'
contract=json.loads((ROOT/'animation_contract.json').read_text())
lib=u.EditorAssetLibrary
targets=[DEST+'/Animations/A_Mutant3_'+r for r in contract['clips']]
skel_path=DEST+'/SK_Mutant3_Claw_Skeleton'
HEADLESS=os.environ.get('MUTANT3_POUNCE_COMMANDLET')=='1'

def install():
    dirty=set() if HEADLESS else {p.get_path_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()}
    conflicts=[p for p in targets+[skel_path] if p in dirty]
    if conflicts:raise RuntimeError('Unsaved changes on target assets; no import performed: '+str(conflicts))
    if not HEADLESS and u.get_editor_subsystem(u.UnrealEditorSubsystem).get_game_world():
        u.get_editor_subsystem(u.LevelEditorSubsystem).editor_request_end_play()
        (ROOT/'import_state.json').write_text(json.dumps({'state':'PIE end requested; no assets changed'}),encoding='utf-8')
        u.log('POUNCE_REFERENCE_RAKE_WAITING_FOR_PIE_END')
        return
    for asset in targets+[skel_path]:
        relative=Path(asset.removeprefix('/Game/'))
        for suffix in ['.uasset','.uexp','.ubulk']:
            file=PROJECT/'Content'/relative.with_suffix(suffix)
            backup=ROOT/'before_content'/relative.with_suffix(suffix)
            if file.exists() and not backup.exists():
                backup.parent.mkdir(parents=True,exist_ok=True)
                shutil.copy2(file,backup)
    skeleton=u.load_asset(skel_path)
    mesh=u.load_asset(DEST+'/SK_Mutant3_Claw')
    state={'state':'importing','saved':[]}
    def save(asset):
        if not lib.save_loaded_asset(asset,False):raise RuntimeError('Save failed: '+asset.get_path_name())
        state['saved'].append(asset.get_path_name())
        (ROOT/'import_state.json').write_text(json.dumps(state,indent=2),encoding='utf-8')
    flag='Interchange.FeatureFlags.Import.FBX'
    previous=u.SystemLibrary.get_console_variable_int_value(flag)
    u.SystemLibrary.execute_console_command(None,flag+' 0')
    try:
        for role,info in contract['clips'].items():
            name='A_Mutant3_'+role
            options=u.FbxImportUI();options.automated_import_should_detect_type=False
            options.mesh_type_to_import=u.FBXImportType.FBXIT_ANIMATION
            options.import_mesh=False;options.import_as_skeletal=True;options.import_animations=True
            options.import_materials=False;options.import_textures=False;options.skeleton=skeleton
            data=options.anim_sequence_import_data
            data.set_editor_property('use_default_sample_rate',False)
            data.set_editor_property('custom_sample_rate',60)
            data.set_editor_property('convert_scene_unit',True)
            data.set_editor_property('animation_length',u.FBXAnimationLengthImportType.FBXALIT_EXPORTED_TIME)
            task=u.AssetImportTask()
            task.filename=str(ROOT/'animations'/(name+'.fbx'))
            task.destination_path=DEST+'/Animations';task.destination_name=name
            task.options=options;task.automated=True;task.save=False
            task.replace_existing=True;task.replace_existing_settings=True
            u.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
            if not task.imported_object_paths:raise RuntimeError('No import result: '+name)
            clip=u.load_asset(DEST+'/Animations/'+name)
            clip.set_preview_skeletal_mesh(mesh)
            clip.set_editor_property('loop',False)
            clip.set_editor_property('enable_root_motion',False)
            clip.set_editor_property('force_root_lock',True)
            lib.set_metadata_tag(clip,'PounceRevision','Native coherent Khaimera torso and arm chain; late-flight downstroke 2026-09-23')
            save(clip)
        save(skeleton)
        state['state']=('Three pounce animations saved in isolated authoring project; installation pending' if HEADLESS else
            'Three pounce animations imported and saved; requested offline arm comparison completed; no gameplay test')
        (ROOT/'import_state.json').write_text(json.dumps(state,indent=2),encoding='utf-8')
        contract['state']=state['state']
        (ROOT/'animation_contract.json').write_text(json.dumps(contract,indent=2),encoding='utf-8')
        u.log(('MUTANT3_POUNCE_REFERENCE_RAKE_STAGED' if HEADLESS else 'MUTANT3_POUNCE_REFERENCE_RAKE_SAVED')+' 3 animations')
    finally:
        u.SystemLibrary.execute_console_command(None,flag+' '+str(previous))

install()
