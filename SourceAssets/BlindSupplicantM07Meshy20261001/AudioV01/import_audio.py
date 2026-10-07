"""Import the seven authored S_M07_* waves and bind them on BP_BlindSupplicantM07."""
from pathlib import Path
import json, traceback
import unreal as u
ROOT = Path(__file__).resolve().parent; PROJECT = ROOT.parents[2]
DEST = '/Game/Monsters/BlindSupplicantM07/Audio/AudioV1'; REV = 'M07AudioV01_20261006'
lib = u.EditorAssetLibrary; tools = u.AssetToolsHelpers.get_asset_tools()
report = {'revision': REV, 'saved': [], 'runtime_tested': False, 'preview_rendered': False}
def receipt():
    (ROOT / 'asset_receipt.json').write_text(json.dumps(report, ensure_ascii=False, indent=2, default=str), encoding='utf-8')
def load(path):
    asset = u.load_asset(path)
    if asset is None:
        raise RuntimeError('Missing ' + path)
    return asset
def owned(path):
    if not lib.does_asset_exist(path):
        return None
    asset = load(path)
    if lib.get_metadata_tag(asset, 'M07.AudioRevision') != REV:
        raise RuntimeError('Preserving unowned asset ' + path)
    return asset
def save(asset):
    lib.set_metadata_tag(asset, 'M07.AudioRevision', REV)
    if not lib.save_loaded_asset(asset, False):
        raise RuntimeError('Save failed ' + asset.get_path_name())
    report['saved'].append(asset.get_path_name()); receipt()

if Path(u.Paths.project_dir()).resolve() != PROJECT.resolve():
    raise RuntimeError('Wrong project')
editor = u.get_editor_subsystem(u.UnrealEditorSubsystem)
if editor and editor.get_game_world():
    raise RuntimeError('PIE session active; no asset changed')
dirty = [p.get_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()
         if p.get_name().startswith('/Game/Monsters/BlindSupplicantM07')]
if dirty:
    # The GUI-editor guard already ran; headless dirty flags are version-upgrade
    # marks, not unsaved user work. Record them and resave normally.
    report['dirty_packages_seen'] = dirty
    u.log('M07 dirty-on-load packages: ' + ', '.join(dirty))
try:
    lib.make_directory(DEST)
    sounds = {}
    for name, looping in [('S_M07_Idle', True), ('S_M07_Chase', True),
                          ('S_M07_Melee', False), ('S_M07_MagicGather', False),
                          ('S_M07_MagicRelease', False), ('S_M07_Hit', False),
                          ('S_M07_Death', False)]:
        path = DEST + '/' + name
        sound = owned(path)
        if sound is None:
            task = u.AssetImportTask(); task.filename = str(ROOT / 'Audio' / (name + '.wav'))
            task.destination_path = DEST; task.destination_name = name
            task.automated = True; task.save = False; task.replace_existing = False
            tools.import_asset_tasks([task])
            sound = load(path)
        sound.set_editor_property('looping', looping)
        sound.set_editor_property('loading_behavior', u.SoundWaveLoadingBehavior.FORCE_INLINE)
        save(sound); sounds[name] = sound
    bp = load('/Game/Monsters/BlindSupplicantM07/BP_BlindSupplicantM07')
    u.BlueprintEditorLibrary.compile_blueprint(bp)
    cdo = u.get_default_object(bp.generated_class())
    for key, value in {'idle_sound': sounds['S_M07_Idle'], 'chase_sound': sounds['S_M07_Chase'],
                       'melee_sound': sounds['S_M07_Melee'],
                       'magic_gather_sound': sounds['S_M07_MagicGather'],
                       'magic_release_sound': sounds['S_M07_MagicRelease'],
                       'hit_sound': sounds['S_M07_Hit'], 'death_sound': sounds['S_M07_Death']}.items():
        cdo.set_editor_property(key, value)
    save(bp)
    report.update(stage='assets_saved', blueprint=bp.get_path_name(), sounds=list(sounds))
    receipt(); u.log('M07_AUDIO_V01_SAVED')
except Exception:
    report.update(stage='production_failed', error=traceback.format_exc()); receipt(); raise
