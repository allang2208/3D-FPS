"""Background commandlet: import and save eight PKM reload contact WAVs."""
from pathlib import Path
import json
import unreal as u

HERE = Path(__file__).resolve().parent
DEST = '/Game/Weapons/PKMLowpoly20260922/ReloadAudio22'
manifest = json.loads((HERE/'audio_manifest.json').read_text(encoding='utf-8'))
rows = []
for contact in manifest['contacts']:
    reference = u.load_asset(contact['settings_reference'])
    if reference is None:
        raise RuntimeError('Missing audio settings reference: '+contact['settings_reference'])
    task = u.AssetImportTask()
    task.filename = str(HERE/contact['wav'])
    task.destination_path = DEST
    task.destination_name = contact['asset_name']
    task.automated = True
    task.replace_existing = True
    task.save = False
    u.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
    if not task.imported_object_paths:
        raise RuntimeError('Import failed: '+contact['asset_name'])
    sound = u.load_asset(task.imported_object_paths[0])
    for prop in ('volume', 'sound_class_object'):
        sound.set_editor_property(prop, reference.get_editor_property(prop))
    # Retain the reference recording's pitch; timing adjustments were authored
    # with a pitch-preserving tempo filter, not runtime pitch multiplication.
    sound.set_editor_property('pitch', 1.)
    sound.set_editor_property('looping', False)
    sound.set_editor_property('loading_behavior', u.SoundWaveLoadingBehavior.FORCE_INLINE)
    path = sound.get_path_name().split('.')[0]
    if not u.EditorAssetLibrary.save_asset(path, False):
        raise RuntimeError('Could not save imported contact: '+path)
    rows.append({'asset':sound.get_path_name(), 'source':task.filename,
        'saved':True, 'duration':sound.get_editor_property('duration'),
        'volume':sound.get_editor_property('volume'), 'pitch':1.})
    u.log('PKM_RELOAD22_SAVED '+path)
(HERE/'import_receipt.json').write_text(json.dumps(rows, indent=2), encoding='utf-8')
u.log('PKM_RELOAD22_IMPORTED '+str(len(rows))+' saved contacts')
