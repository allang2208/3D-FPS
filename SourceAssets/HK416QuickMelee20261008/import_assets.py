"""Publish only HK416 quick melee and its current grip-profile entries."""
import json
import shutil
from pathlib import Path
import unreal as u

O = Path(__file__).parent
P = O.parents[1]
H = '/Game/Weapons/HK416/Reworked20260930'
D = '/Game/Weapons/AnimationProfiles20261001/ue_hk416'
if Path(u.Paths.convert_relative_path_to_full(u.Paths.project_content_dir())).resolve() != (P/'Content').resolve():
    raise RuntimeError('Wrong content mount')
headless = '-run=pythonscript' in u.SystemLibrary.get_command_line().lower()
if not headless:
    editor = u.get_editor_subsystem(u.UnrealEditorSubsystem)
    if editor and editor.get_game_world():
        raise RuntimeError('PIE is active; preserve the session')
source = json.loads((O/'animations.json').read_text(encoding='utf-8'))
families = ('base','drum','angled','vertical','canted','prism')
targets = {H+'/Animations/'+f+'/A_HK416_'+f+'_quick_melee' for f in families}
profiles = {D+'/DA_'+f for f in families}
mesh = u.load_asset(H+'/SK_HK416_Manny')
skeleton = mesh.get_editor_property('skeleton')
dirty = {p.get_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()}
if dirty & (targets | profiles | {skeleton.get_outermost().get_name()}):
    raise RuntimeError('Preserve unsaved HK416 animation/profile edits')
for path in targets | profiles:
    file = P/'Content'/(path.removeprefix('/Game/')+'.uasset')
    backup = O/'Before'/file.relative_to(P/'Content')
    if file.exists() and not backup.exists():
        backup.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(file, backup)
receipt = dict(animations={}, profiles={}, complete=False, runtime_tested=False)


def record():
    (O/'import_receipt.json').write_text(json.dumps(receipt, indent=2), encoding='utf-8')


def save(asset):
    if not u.EditorLoadingAndSavingUtils.save_packages([asset.get_outermost()], False):
        raise RuntimeError('Save failed '+asset.get_path_name())


tools = u.AssetToolsHelpers.get_asset_tools()
flag = 'Interchange.FeatureFlags.Import.FBX'
previous = u.SystemLibrary.get_console_variable_int_value(flag)
u.SystemLibrary.execute_console_command(None, flag+' 0')
try:
    for family in families:
        clip = source['clips'][family]
        path = H+'/Animations/'+family+'/'+clip['name']
        old = u.load_asset(path)
        if not old:
            raise RuntimeError('Missing current HK416 clip '+path)
        before_length = old.get_play_length()
        compression = old.get_editor_property('bone_compression_settings')
        opt = u.FbxImportUI()
        opt.automated_import_should_detect_type = False
        opt.mesh_type_to_import = u.FBXImportType.FBXIT_ANIMATION
        opt.import_mesh = False
        opt.import_animations = True
        opt.import_materials = False
        opt.import_textures = False
        opt.skeleton = skeleton
        opt.anim_sequence_import_data.set_editor_property('use_default_sample_rate', False)
        opt.anim_sequence_import_data.set_editor_property('custom_sample_rate', source['playback_fps'])
        task = u.AssetImportTask()
        task.filename = clip['file']
        task.destination_path = H+'/Animations/'+family
        task.destination_name = clip['name']
        task.automated = True
        task.replace_existing = True
        task.save = False
        task.options = opt
        tools.import_asset_tasks([task])
        anim = u.load_asset(path)
        anim.set_editor_property('bone_compression_settings', compression)
        anim.set_editor_property('rate_scale', 1.)
        u.EditorAssetLibrary.set_metadata_tag(anim, 'HK416QuickMeleeSource',
            '20261008 compact M4 N trajectory; HK416 native grip; 0.6s baked at 180Hz; travel .70, rotation .90')
        save(anim)
        receipt['animations'][family] = dict(asset=anim.get_path_name(), saved=True,
            previous_duration=before_length, duration=anim.get_play_length(), source=clip['file'])
        record()
finally:
    u.SystemLibrary.execute_console_command(None, flag+' '+str(previous))

base = u.load_asset(H+'/Animations/base/A_HK416_base_quick_melee')
for family in families:
    path = D+'/DA_'+family
    if not u.EditorAssetLibrary.does_asset_exist(path):
        continue
    profile = u.load_asset(path)
    authored = u.load_asset(H+'/Animations/'+family+'/A_HK416_'+family+'_quick_melee')
    # BakeClip updates this base entry only; preserve all reload/inspect/sprint
    # layers. Drum uses its actual held pose, not the empty-reload helper rule.
    if not profile.bake_clip(base, authored):
        raise RuntimeError('Cannot bake current HK416 grip '+family)
    u.EditorAssetLibrary.set_metadata_tag(profile, 'HK416QuickMeleeSource',
        '20261008 compact M4 N; native '+family+' grip; 0.6s; quick_melee entry only')
    save(profile)
    receipt['profiles'][family] = dict(asset=profile.get_path_name(), saved=True,
        base=base.get_path_name(), authored=authored.get_path_name(), duration=base.get_play_length())
    record()
receipt['complete'] = True
record()
print('HK416_QUICK_MELEE_SAVED',len(receipt['animations']),len(receipt['profiles']),flush=True)
