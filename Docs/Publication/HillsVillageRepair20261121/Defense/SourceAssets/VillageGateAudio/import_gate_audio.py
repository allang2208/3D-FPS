"""Import the two original game-dev gate cues as mono, positional SoundWaves.

The source MP3s come from assets/sounds/environment in the World-122 project.
wall-gate.js uses gate.mp3 on open and close. defense-system.js uses
gate_iron.mp3 on open and close for both iron grilles. PCM masters retain the
full original durations and sample rates, with stereo averaged to mono.
"""
from pathlib import Path
import unreal as ue

source = Path(__file__).resolve().parent
folder = '/Game/WorldGeneration/TemperateHills/VillageDefenses/GateAudio'
library = ue.EditorAssetLibrary
asset_tools = ue.AssetToolsHelpers.get_asset_tools()
library.make_directory(folder)

def save(obj):
    if not obj or not library.save_loaded_asset(obj, only_if_is_dirty=False):
        raise RuntimeError('Failed to save gate audio: '+str(obj))

mix_name = 'ATT_VillageGate'
mix = library.load_asset(folder+'/'+mix_name) if library.does_asset_exist(folder+'/'+mix_name) else (
    asset_tools.create_asset(mix_name,folder,ue.SoundAttenuation,ue.SoundAttenuationFactory()))
settings = mix.get_editor_property('attenuation')
settings.set_editor_property('spatialize',True)
settings.set_editor_property('attenuate',True)
settings.set_editor_property('attenuation_shape_extents',ue.Vector(220,0,0))
settings.set_editor_property('falloff_distance',3400.)
mix.set_editor_property('attenuation',settings)
save(mix)

for original, name in [('gate','S_VillageTimberGate'),('gate_iron','S_VillageIronGate')]:
    task = ue.AssetImportTask()
    task.filename = str(source/(original+'.wav'))
    task.destination_path = folder
    task.destination_name = name
    task.automated = True
    task.replace_existing = True
    task.factory = ue.SoundFactory()
    asset_tools.import_asset_tasks([task])
    if not task.imported_object_paths:
        raise RuntimeError('Failed to import '+task.filename)
    wave = library.load_asset(folder+'/'+name)
    wave.set_editor_property('attenuation_settings',mix)
    wave.set_editor_property('loading_behavior',ue.SoundWaveLoadingBehavior.FORCE_INLINE)
    wave.set_editor_property('looping',False)
    library.set_metadata_tag(wave,'OriginalSource','game-dev/assets/sounds/environment/'+original+'.mp3')
    save(wave)
