"""Import the nine authored S_M25_* waves and bind them on BP_VortexCofferM25."""
from pathlib import Path
import json, sys, traceback
import unreal as u
ROOT = Path(__file__).resolve().parent; PROJECT = ROOT.parents[2]
DEST = '/Game/Monsters/VortexCofferM25/Audio/AudioV1'; REV = 'M25AudioV1_20261005'
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
    if lib.get_metadata_tag(asset, 'M25.AudioRevision') != REV:
        raise RuntimeError('Preserving unowned asset ' + path)
    return asset
def save(asset):
    lib.set_metadata_tag(asset, 'M25.AudioRevision', REV)
    if not lib.save_loaded_asset(asset, False):
        raise RuntimeError('Save failed ' + asset.get_path_name())
    report['saved'].append(asset.get_path_name()); receipt()

if Path(u.Paths.project_dir()).resolve() != PROJECT.resolve():
    raise RuntimeError('Wrong project')
editor = u.get_editor_subsystem(u.UnrealEditorSubsystem)
if editor and editor.get_game_world():
    raise RuntimeError('PIE session active; no asset changed')
if any(p.get_name().startswith('/Game/Monsters/VortexCofferM25') for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()):
    raise RuntimeError('Preserving unsaved M25 content')
try:
    lib.make_directory(DEST)
    # V2 realism pass: every wav was re-authored from recorded sources, so each
    # previously imported cue is deleted (ownership checked) and re-imported.
    for name in ['S_M25_Idle', 'S_M25_Crawl', 'S_M25_Crackle', 'S_M25_Bite', 'S_M25_Charge',
                 'S_M25_LanceCharge', 'S_M25_LanceRelease', 'S_M25_Hit', 'S_M25_Death']:
        stale = DEST + '/' + name
        if owned(stale) is not None:
            if not lib.delete_asset(stale):
                raise RuntimeError('Delete failed ' + stale)
            report.setdefault('deleted', []).append(stale); receipt()
    sounds = {}
    for name, looping in [('S_M25_Idle', True), ('S_M25_Crawl', True), ('S_M25_Crackle', True),
                          ('S_M25_Bite', False), ('S_M25_Charge', False), ('S_M25_LanceCharge', False),
                          ('S_M25_LanceRelease', False), ('S_M25_Hit', False), ('S_M25_Death', False)]:
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
    bp = load('/Game/Monsters/VortexCofferM25/BP_VortexCofferM25')
    u.BlueprintEditorLibrary.compile_blueprint(bp)
    cdo = u.get_default_object(bp.generated_class())
    # Lance audio reuses the player thunder-lance cues (full visual+audio recipe reuse);
    # the monster-authored lance waves stay on disk as a restore path.
    lance_charge = load('/Game/Skills/ElectricMagic/S_ThunderLanceCharge')
    lance_release = load('/Game/Skills/ElectricMagic/S_ThunderLanceDischarge')
    for key, value in {'idle_sound': sounds['S_M25_Idle'], 'crawl_sound': sounds['S_M25_Crawl'],
                       'bite_sound': sounds['S_M25_Bite'], 'hit_sound': sounds['S_M25_Hit'],
                       'death_sound': sounds['S_M25_Death'], 'crackle_sound': sounds['S_M25_Crackle'],
                       'charge_sound': sounds['S_M25_Charge'], 'lance_charge_sound': lance_charge,
                       'lance_release_sound': lance_release}.items():
        cdo.set_editor_property(key, value)
    save(bp)
    report.update(stage='assets_saved', blueprint=bp.get_path_name(), sounds=list(sounds),
                  lance_audio=['/Game/Skills/ElectricMagic/S_ThunderLanceCharge',
                               '/Game/Skills/ElectricMagic/S_ThunderLanceDischarge',
                               '/Game/Skills/ElectricMagic/S_ElectricCast1'])
    receipt(); u.log('M25_AUDIO_V1_SAVED')
except Exception:
    report.update(stage='production_failed', error=traceback.format_exc()); receipt(); raise
