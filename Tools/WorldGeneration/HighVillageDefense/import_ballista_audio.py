"""Import one siege engine sound set into its isolated staging project."""
import json
import os
from pathlib import Path
import unreal

batch = Path(os.environ['VILLAGE_SIEGE_AUDIO_RUN'])
destination = '/Game/WorldGeneration/TemperateHills/HighVillageDefense/SiegeEngines/Audio'
receipt = []
family = os.environ.get('VILLAGE_SIEGE_AUDIO_FAMILY', 'Ballista')
roles = {'Ballista': ('Tension', 'Release', 'Windlass'),
         'Trebuchet': ('Windup', 'Release', 'Reload', 'Impact')}[family]
tools = unreal.AssetToolsHelpers.get_asset_tools()
if family == 'Trebuchet':
    name = 'SA_TrebuchetImpact'
    path = destination + '/' + name
    if unreal.EditorAssetLibrary.does_asset_exist(path):
        attenuation = unreal.load_asset(path)
    else:
        attenuation = tools.create_asset(name, destination, unreal.SoundAttenuation, unreal.SoundAttenuationFactory())
    settings = attenuation.get_editor_property('attenuation')
    settings.set_editor_property('attenuation_shape_extents', unreal.Vector(430., 0., 0.))
    settings.set_editor_property('falloff_distance', 7600.)
    attenuation.set_editor_property('attenuation', settings)
    if not unreal.EditorAssetLibrary.save_loaded_asset(attenuation, False):
        raise RuntimeError('Failed to save ' + name)
    receipt.append({'package': attenuation.get_path_name()})

for role in roles:
    name = 'S_' + family + role
    source = batch / 'Wav' / (name + '.wav')
    task = unreal.AssetImportTask()
    task.filename = str(source)
    task.destination_path = destination
    task.destination_name = name
    task.automated = True
    task.replace_existing = True
    tools.import_asset_tasks([task])
    if not task.imported_object_paths:
        raise RuntimeError('Failed to import ' + name)
    sound = unreal.load_asset(task.imported_object_paths[0])
    sound.set_editor_property('looping', False)
    sound.set_editor_property('compression_quality', 100)
    sound.set_editor_property('loading_behavior', unreal.SoundWaveLoadingBehavior.FORCE_INLINE)
    if family == 'Trebuchet' and role == 'Impact':
        sound.set_editor_property('attenuation_settings', attenuation)
    if not unreal.EditorAssetLibrary.save_loaded_asset(sound, False):
        raise RuntimeError('Failed to save ' + name)
    receipt.append({'package': sound.get_path_name(), 'source': str(source)})
(batch / 'Import' / 'saved.json').write_text(json.dumps(receipt, indent=2), encoding='utf-8')
