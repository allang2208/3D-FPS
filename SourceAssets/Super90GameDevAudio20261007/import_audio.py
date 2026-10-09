"""Import this Super90 sound set through the existing UE batch or commandlet."""
from pathlib import Path
import json
import unreal as u

O = Path(__file__).parent
recipe = json.loads((O / 'provenance.json').read_text(encoding='utf-8'))
templates = {
    'Fire': '/Game/Weapons/Super90/Cransh20261006/Audio/S_Super90_Fire_01',
    'Reload': '/Game/Weapons/M4HK416Audio/S_HK416_MagInsert',
    'Bolt': '/Game/Weapons/M4HK416Audio/S_HK416_ChargeRelease',
}
receipt = {'saved': [], 'auditioned': False, 'game_tested': False}
for role, row in recipe['audio'].items():
    target = row['asset']
    previous = u.load_asset(target) if u.EditorAssetLibrary.does_asset_exist(target) else u.load_asset(templates[role])
    settings = {key: previous.get_editor_property(key) for key in ('volume', 'pitch', 'sound_class_object')} if previous else {}
    task = u.AssetImportTask()
    task.filename = row['output']
    task.destination_path, task.destination_name = target.rsplit('/', 1)
    task.automated = True
    task.replace_existing = True
    task.replace_existing_settings = False
    task.save = False
    u.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
    sound = u.load_asset(target)
    if not task.imported_object_paths or not isinstance(sound, u.SoundWave):
        raise RuntimeError('Failed to import ' + target)
    for key, value in settings.items():
        sound.set_editor_property(key, value)
    sound.set_editor_property('looping', False)
    sound.set_editor_property('loading_behavior', u.SoundWaveLoadingBehavior.FORCE_INLINE)
    sound.set_sound_asset_compression_type(u.SoundAssetCompressionType.PCM)
    u.EditorAssetLibrary.set_metadata_tag(sound, 'AudioSourceProject', recipe['source_project'])
    u.EditorAssetLibrary.set_metadata_tag(sound, 'AudioSourceSHA256', row['source_sha256'])
    u.EditorAssetLibrary.set_metadata_tag(sound, 'AudioSourceRecipe', str(O / 'provenance.json'))
    u.EditorAssetLibrary.set_metadata_tag(sound, 'AudioSourceRights', recipe['license_note'])
    if not u.EditorLoadingAndSavingUtils.save_packages([sound.get_outermost()], False):
        raise RuntimeError('Failed to save ' + target)
    receipt['saved'].append({'role': role, 'asset': sound.get_path_name(), 'source': row['source'],
        'duration_seconds': row['duration_seconds']})
    (O / 'import_receipt.json').write_text(json.dumps(receipt, ensure_ascii=False, indent=2), encoding='utf-8')
print('SUPER90_GAMEDEV_AUDIO_SAVED', len(receipt['saved']))
