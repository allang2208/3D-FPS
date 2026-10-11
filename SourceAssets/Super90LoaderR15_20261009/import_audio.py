"""Import seven reference cuts only into the Super90 loader audio namespace."""
from pathlib import Path
import json
import unreal as u
O=Path(__file__).parent
recipe=json.loads((O/'audio_provenance.json').read_text())
receipt=dict(completed=False,saved=[],auditioned=False,game_tested=False)
template=u.load_asset('/Game/Weapons/Super90/GameDevAudio20261007/S_Super90_Reload')
for row in recipe['audio']:
    target=row['asset']
    task=u.AssetImportTask();task.filename=row['output']
    task.destination_path,task.destination_name=target.rsplit('/',1)
    task.automated=True;task.replace_existing=True;task.replace_existing_settings=False;task.save=False
    u.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
    sound=u.load_asset(target)
    if not task.imported_object_paths or not isinstance(sound,u.SoundWave):raise RuntimeError('Import failed '+target)
    sound.set_editor_property('volume',1.0);sound.set_editor_property('pitch',1.0)
    if template:sound.set_editor_property('sound_class_object',template.get_editor_property('sound_class_object'))
    sound.set_editor_property('looping',False)
    sound.set_editor_property('loading_behavior',u.SoundWaveLoadingBehavior.FORCE_INLINE)
    sound.set_sound_asset_compression_type(u.SoundAssetCompressionType.PCM)
    for key,value in dict(AudioSourceSHA256=recipe['source_sha256'],AudioSourceRecipe=str(O/'audio_provenance.json'),
                          AudioSourceRights=recipe['license_note'],AudioSourceKind=recipe['source_kind']).items():
        u.EditorAssetLibrary.set_metadata_tag(sound,key,value)
    if not u.EditorLoadingAndSavingUtils.save_packages([sound.get_outermost()],False):raise RuntimeError('Save failed '+target)
    receipt['saved'].append(dict(role=row['role'],asset=sound.get_path_name(),duration_seconds=row['duration_seconds']))
    (O/'audio_import_receipt.json').write_text(json.dumps(receipt,indent=2))
receipt['completed']=True
(O/'audio_import_receipt.json').write_text(json.dumps(receipt,indent=2))
print('SUPER90_LOADER_REFERENCE_AUDIO_SAVED',len(receipt['saved']),flush=True)
