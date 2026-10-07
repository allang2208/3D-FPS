"""Import the eight authored S_M10_* waves and bind them on BP_M10Mawcrawler."""
from pathlib import Path
import json, sys, traceback
import unreal as u
ROOT = Path(__file__).resolve().parent; PROJECT = ROOT.parents[2]
DEST = '/Game/Monsters/M10Mawcrawler/Audio/AudioV1'; REV = 'M10AudioV1_20261004'
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
    if lib.get_metadata_tag(asset, 'M10.AudioRevision') != REV:
        raise RuntimeError('Preserving unowned asset ' + path)
    return asset
def save(asset):
    lib.set_metadata_tag(asset, 'M10.AudioRevision', REV)
    if not lib.save_loaded_asset(asset, False):
        raise RuntimeError('Save failed ' + asset.get_path_name())
    report['saved'].append(asset.get_path_name()); receipt()

if Path(u.Paths.project_dir()).resolve() != PROJECT.resolve():
    raise RuntimeError('Wrong project')
editor = u.get_editor_subsystem(u.UnrealEditorSubsystem)
if editor and editor.get_game_world():
    raise RuntimeError('PIE session active; no asset changed')
if any(p.get_name().startswith('/Game/Monsters/M10Mawcrawler') for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()):
    raise RuntimeError('Preserving unsaved M10 content')
try:
    lib.make_directory(DEST)
    sounds = {}
    for name, looping in [('S_M10_Idle', True), ('S_M10_Crawl', True), ('S_M10_Bite', False), ('S_M10_Howl', False),
                          ('S_M10_Gas', False), ('S_M10_Hit', False), ('S_M10_Death', False), ('S_M10_Threat', False)]:
        path = DEST + '/' + name
        sound = owned(path)
        if sound is None:
            task = u.AssetImportTask(); task.filename = str(ROOT / 'Wav' / (name + '.wav'))
            task.destination_path = DEST; task.destination_name = name
            task.automated = True; task.save = False; task.replace_existing = False
            tools.import_asset_tasks([task])
            sound = load(path)
        sound.set_editor_property('looping', looping)
        sound.set_editor_property('loading_behavior', u.SoundWaveLoadingBehavior.FORCE_INLINE)
        save(sound); sounds[name] = sound
    bp = load('/Game/Monsters/M10Mawcrawler/BP_M10Mawcrawler')
    u.BlueprintEditorLibrary.compile_blueprint(bp)
    cdo = u.get_default_object(bp.generated_class())
    for key, value in {'idle_sound': sounds['S_M10_Idle'], 'crawl_sound': sounds['S_M10_Crawl'],
                       'bite_sound': sounds['S_M10_Bite'], 'hit_sound': sounds['S_M10_Hit'],
                       'death_sound': sounds['S_M10_Death'], 'threat_sound': sounds['S_M10_Threat'],
                       'gas_sound': sounds['S_M10_Gas'], 'howl_sound': sounds['S_M10_Howl'],
                       'threat_cooldown': 18.0}.items():
        cdo.set_editor_property(key, value)
    save(bp)
    report.update(stage='assets_saved', blueprint=bp.get_path_name(), sounds=list(sounds))
    receipt(); u.log('M10_AUDIO_V1_SAVED')
except Exception:
    report.update(stage='production_failed', error=traceback.format_exc()); receipt(); raise
