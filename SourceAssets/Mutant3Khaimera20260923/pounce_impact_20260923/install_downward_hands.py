"""Import in memory, copy only hand rotations, and save the two production clips."""
import unreal as u
import json, shutil
from pathlib import Path

ROOT = Path(__file__).parent
PROJECT = ROOT.parents[2]
DEST = '/Game/Monsters/Mutant3Meshy/KhaimeraV2'
WORKING = DEST+'/Authoring/PounceHands20260923'
lib = u.EditorAssetLibrary
contract = json.loads((ROOT/'animation_contract.json').read_text())
roles = list(contract['clips'])
targets = [DEST+'/Animations/A_Mutant3_'+role for role in roles]
state = {'state': 'preparing', 'saved': [], 'gameplay_tested': False, 'visual_tested': False,
         'scope': 'Only wrist/finger rotation tracks in flight and landing; no mesh/material/skeleton replacement'}

def record():
    (ROOT/'install_state.json').write_text(json.dumps(state, indent=2), encoding='utf-8')

def install():
    if not hasattr(u.Mutant3, 'apply_pounce_hand_tracks'):
        raise RuntimeError('Compile the current native modules before installing hand tracks')
    if u.get_editor_subsystem(u.UnrealEditorSubsystem).get_game_world():
        raise RuntimeError('Stop PIE before changing animation assets')
    dirty = {p.get_path_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()}
    if any(path in dirty for path in targets):
        raise RuntimeError('Unsaved changes on a target pounce animation; assets left untouched')
    for asset in targets:
        relative = Path(asset.removeprefix('/Game/'))
        for suffix in ['.uasset','.uexp','.ubulk']:
            file = PROJECT/'Content'/relative.with_suffix(suffix)
            backup = ROOT/'before_content'/relative.with_suffix(suffix)
            if file.exists() and not backup.exists():
                backup.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(file, backup)
    skeleton = u.load_asset(DEST+'/SK_Mutant3_Claw_Skeleton')
    if not skeleton: raise RuntimeError('Missing production claw skeleton')
    flag = 'Interchange.FeatureFlags.Import.FBX'
    previous = u.SystemLibrary.get_console_variable_int_value(flag)
    u.SystemLibrary.execute_console_command(None, flag+' 0')
    state['state'] = 'importing temporary animation objects'
    record()
    try:
        authored = {}
        for role in roles:
            name = 'A_Mutant3_'+role
            options = u.FbxImportUI()
            options.automated_import_should_detect_type = False
            options.mesh_type_to_import = u.FBXImportType.FBXIT_ANIMATION
            options.import_mesh = False
            options.import_as_skeletal = True
            options.import_animations = True
            options.import_materials = False
            options.import_textures = False
            options.skeleton = skeleton
            data = options.anim_sequence_import_data
            data.set_editor_property('use_default_sample_rate', False)
            data.set_editor_property('custom_sample_rate', 60)
            data.set_editor_property('convert_scene_unit', True)
            data.set_editor_property('animation_length', u.FBXAnimationLengthImportType.FBXALIT_EXPORTED_TIME)
            task = u.AssetImportTask()
            task.filename = str(ROOT/'animations'/(name+'.fbx'))
            task.destination_path = WORKING
            task.destination_name = name+'_HandsSource'
            task.options = options
            task.automated = True
            task.save = False
            task.replace_existing = True
            task.replace_existing_settings = True
            u.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
            clips = [u.load_asset(path) for path in task.imported_object_paths]
            clips = [clip for clip in clips if isinstance(clip, u.AnimSequence)]
            if len(clips) != 1: raise RuntimeError('Expected one animation from '+name)
            authored[role] = clips[0]
        # The native helper preserves every non-hand track and original local
        # translation/scale. No source mesh or skeleton package is saved here.
        for role, path in zip(roles, targets):
            target = u.load_asset(path)
            if not u.Mutant3.apply_pounce_hand_tracks(target, authored[role]):
                raise RuntimeError('Could not apply hand tracks to '+path)
            lib.set_metadata_tag(target, 'PounceHandRevision',
                'Downward wrist swing and open finger rake; 32 rotation tracks only; 2026-09-23')
            if not lib.save_loaded_asset(target, False):
                raise RuntimeError('Could not save '+path)
            state['saved'].append(target.get_path_name())
            record()
        state['state'] = 'Two production pounce animations saved; gameplay and visual testing left to user'
        contract['state'] = state['state']
        (ROOT/'animation_contract.json').write_text(json.dumps(contract, indent=2), encoding='utf-8')
        record()
        u.log('MUTANT3_POUNCE_HANDS_SAVED '+str(len(state['saved']))+' production clips')
    finally:
        u.SystemLibrary.execute_console_command(None, flag+' '+str(previous))

try:
    install()
except Exception as error:
    state['state'] = 'installation interrupted'
    state['error'] = str(error)
    record()
    raise
