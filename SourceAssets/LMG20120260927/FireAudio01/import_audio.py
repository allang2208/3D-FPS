"""Import and save only the 201 fire bank. No playback or game launch."""
from pathlib import Path
import json
import unreal as u

ROOT = Path(__file__).resolve().parent
DEST = '/Game/Weapons/LMG201/FireAudio01'
if u.get_editor_subsystem(u.UnrealEditorSubsystem).get_game_world():
    raise RuntimeError('Active game session; preserve it and import after play ends')
source = json.loads((ROOT / 'provenance.json').read_text(encoding='utf-8'))
original = u.load_asset('/Game/Weapons/AKM/VideoAudio20260921/S_AKM_Fire')
if not original:
    raise RuntimeError('Missing current 201 fire settings source')
receipt = []
dirty = {p.get_path_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()}
for row in source['cues']:
    name = row['name']
    target = DEST + '/' + name
    if target in dirty:
        raise RuntimeError('Unsaved target: ' + target)
    task = u.AssetImportTask()
    task.filename = str(ROOT / row['file'])
    task.destination_path = DEST
    task.destination_name = name
    task.automated = True
    task.replace_existing = True
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
    receipt.append({
        'asset': sound.get_path_name(), 'source': task.filename, 'saved': True,
        'volume': sound.get_editor_property('volume'), 'pitch': sound.get_editor_property('pitch'),
        'sound_class': str(sound.get_editor_property('sound_class_object')),
        'compression': 'PCM', 'loading': 'ForceInline',
    })
    (ROOT / 'import_receipt.json').write_text(json.dumps(receipt, indent=2), encoding='utf-8')
print('LMG201_FIRE_AUDIO_IMPORTED_SAVED', len(receipt))
