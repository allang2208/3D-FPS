"""Import and save only the six new SVD sounds; no playback or PIE."""
import json
from pathlib import Path
import unreal as u

ROOT = Path(__file__).resolve().parent
DEST = '/Game/Weapons/SVDDragunov20260922/VideoAudio20260923'
if u.get_editor_subsystem(u.UnrealEditorSubsystem).get_game_world():
    raise RuntimeError('Active play session: preserve state, no audio import')
dirty = {p.get_path_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()}
source = json.loads((ROOT / 'provenance.json').read_text(encoding='utf-8'))
receipt = []
for record in source['cues']:
    name = record['name']
    target = DEST + '/' + name
    if target in dirty:
        raise RuntimeError('Unsaved target: ' + target)
    if u.EditorAssetLibrary.does_asset_exist(target):
        raise RuntimeError('Target already exists; preserve it: ' + target)
for record in source['cues']:
    name, cue = record['name'], record['cue']
    original_path = (
        '/Game/Weapons/SVDDragunov20260922/Complete20260923/Audio/S_SVD_Fire_01'
        if cue == 'Fire_01' else '/Game/Weapons/AKM/Audio/S_AKM_' + cue
    )
    original = u.load_asset(original_path)
    if original is None:
        raise RuntimeError('Missing audio settings source: ' + original_path)
    task = u.AssetImportTask()
    task.filename = str(ROOT / record['file'])
    task.destination_path = DEST
    task.destination_name = name
    task.automated = True
    task.replace_existing = False
    task.save = False
    u.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
    if not task.imported_object_paths:
        raise RuntimeError('Import failed: ' + name)
    sound = u.load_asset(task.imported_object_paths[0])
    for prop in ('volume', 'pitch', 'sound_class_object'):
        sound.set_editor_property(prop, original.get_editor_property(prop))
    sound.set_editor_property('looping', False)
    sound.set_editor_property('loading_behavior', u.SoundWaveLoadingBehavior.FORCE_INLINE)
    sound.set_sound_asset_compression_type(u.SoundAssetCompressionType.PCM)
    if not u.EditorAssetLibrary.save_loaded_asset(sound, False):
        raise RuntimeError('Save failed: ' + name)
    receipt.append({'asset': sound.get_path_name(), 'source': task.filename,
                    'compression': 'PCM', 'saved': True})
    (ROOT / 'import_receipt.json').write_text(json.dumps(receipt, indent=2), encoding='utf-8')
u.log('SVD_AUDIO_IMPORTED_SAVED ' + json.dumps(receipt))
