"""Import the new SUPER90 cue without playing it or changing the normal cue."""
from pathlib import Path
import json
import unreal as u
O=Path(__file__).parent
recipe=json.loads((O/'audio_provenance.json').read_text(encoding='utf-8'))
reference=u.load_asset(recipe['normal_asset'])
if not reference:raise RuntimeError('Missing SUPER90 normal sound')
settings={key:reference.get_editor_property(key) for key in ('volume','pitch','sound_class_object')}
task=u.AssetImportTask();task.filename=recipe['output']
task.destination_path,task.destination_name=recipe['asset'].rsplit('/',1)
task.automated=True;task.replace_existing=False;task.save=False;task.factory=u.SoundFactory()
u.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
sound=u.load_asset(recipe['asset'])
if not task.imported_object_paths or not isinstance(sound,u.SoundWave):raise RuntimeError('Sound import failed')
for key,value in settings.items():sound.set_editor_property(key,value)
sound.set_editor_property('looping',False)
sound.set_editor_property('loading_behavior',u.SoundWaveLoadingBehavior.FORCE_INLINE)
sound.set_sound_asset_compression_type(u.SoundAssetCompressionType.PCM)
u.EditorAssetLibrary.set_metadata_tag(sound,'AudioSourceRights',recipe['license_note'])
u.EditorAssetLibrary.set_metadata_tag(sound,'AudioSourceRecipe',str(O/'audio_provenance.json'))
sound.modify()
if not u.EditorAssetLibrary.save_loaded_asset(sound,False):raise RuntimeError('Sound save failed')
(O/'audio_import_receipt.json').write_text(json.dumps({'complete':True,'asset':sound.get_path_name(),
    'volume':settings['volume'],'pitch':settings['pitch'],'auditioned':False,'runtime_tested':False},indent=2),encoding='utf-8')
print('SUPER90_SUPPRESSED_SOUND_SAVED')
