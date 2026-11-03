"""Import the six selected recording cuts and author their continuous random player."""
from pathlib import Path
import json
import unreal as u

P = Path(__file__).resolve().parent
D = '/Game/Weapons/ThunderGodHammer20261028/JiLeiRecordedCurrentV2'
NAME = 'MS_JiLei_CurrentRandom'
recipe = json.loads((P/'audio_manifest.json').read_text(encoding='utf-8'))
targets = {D+'/'+NAME} | {D+'/'+r['name'] for r in recipe['clips']}
for package in u.EditorLoadingAndSavingUtils.get_dirty_content_packages():
    if package.get_path_name() in targets:
        raise RuntimeError('Preserving unsaved target: '+package.get_path_name())
receipt = dict(complete=False, revision=recipe['revision'], waves=[], metasound=None, gameplay_tested=False)
def record():
    (P/'import_receipt.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2),encoding='utf-8')
def save(asset):
    asset.modify()
    if not u.EditorAssetLibrary.save_loaded_asset(asset,False):
        raise RuntimeError('Save failed: '+asset.get_path_name())
record()
waves=[]
for row in recipe['clips']:
    wave = u.load_asset(D+'/'+row['name'])
    if wave is None:
        task = u.AssetImportTask()
        task.filename = str(P/row['file'])
        task.destination_path = D
        task.destination_name = row['name']
        task.automated = True
        task.save = False
        task.replace_existing = False
        u.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
        wave = u.load_asset(D+'/'+row['name'])
    if not isinstance(wave,u.SoundWave):
        raise RuntimeError('Import failed: '+row['name'])
    wave.set_editor_property('looping',False)
    wave.set_editor_property('loading_behavior',u.SoundWaveLoadingBehavior.FORCE_INLINE)
    wave.set_sound_asset_compression_type(u.SoundAssetCompressionType.PCM)
    u.EditorAssetLibrary.set_metadata_tag(wave,'AudioSourceAttribution',recipe['provenance'])
    u.EditorAssetLibrary.set_metadata_tag(wave,'AudioSourceSHA256',recipe['source_sha256'])
    u.EditorAssetLibrary.set_metadata_tag(wave,'AudioCutSeconds',str(row['start_seconds'])+':'+str(row['end_seconds']))
    save(wave)
    waves.append(wave)
    receipt['waves'].append(dict(asset=wave.get_path_name(),seconds=row['seconds'],source=row['file']))
    record()

def good(result, operation):
    if result != u.MetaSoundBuilderResult.SUCCEEDED:
        raise RuntimeError(operation+': '+str(result))
def value(pair, operation):
    val, result = pair
    good(result,operation)
    return val

sub = u.get_engine_subsystem(u.MetaSoundBuilderSubsystem)
builder,on_play,on_finished,audio_out,result = sub.create_source_builder(
    'JiLeiRecordedCurrentV2',u.MetaSoundOutputAudioFormat.STEREO,False)
good(result,'CreateSourceBuilder')
def node(namespace,name,variant=''):
    cls = u.MetasoundFrontendClassName(namespace=namespace,name=name,variant=variant)
    return value(builder.add_node_by_class_name(cls,1),'Add '+name)
def inp(handle,name):
    return value(builder.find_node_input_by_name(handle,name),'Input '+name)
def out(handle,name):
    return value(builder.find_node_output_by_name(handle,name),'Output '+name)
def link(a,b):
    good(builder.connect_nodes(a,b),'Connect')
def default(handle,name,literal):
    good(builder.set_node_input_default(inp(handle,name),literal),'Default '+name)

wave_player = node('UE','Wave Player','Stereo')
random = node('Array','Random Get','WaveAsset:Array')
trigger_any = node('TriggerAny','Trigger Any (2)')
default(random,'In Array',sub.create_object_array_meta_sound_literal(waves))
default(random,'Seed',sub.create_int_meta_sound_literal(-1)[0])
default(random,'No Repeats',sub.create_int_meta_sound_literal(2)[0])
default(random,'Enable Shared State',sub.create_bool_meta_sound_literal(False)[0])
default(wave_player,'Loop',sub.create_bool_meta_sound_literal(False)[0])
default(wave_player,'Pitch Shift',sub.create_float_meta_sound_literal(0.)[0])

# The wave announces completion one audio block early. A delayed trigger
# variable advances that event by one block, scheduling the next random cut
# exactly at completion without a game-thread tick or SoundCue-loop gap.
good(builder.add_graph_variable('NextClip','Trigger',sub.create_bool_meta_sound_literal(False)[0]),'Add trigger variable')
set_next = value(builder.add_graph_variable_set_node('NextClip'),'Set trigger variable')
get_next = value(builder.add_graph_variable_get_delayed_node('NextClip'),'Delayed trigger variable')
link(on_play,inp(trigger_any,'In 0'))
link(out(get_next,'Value'),inp(trigger_any,'In 1'))
link(out(trigger_any,'Out'),inp(random,'Next'))
link(out(random,'Value'),inp(wave_player,'Wave Asset'))
link(out(random,'On Next'),inp(wave_player,'Play'))
link(out(wave_player,'On Nearly Finished'),inp(set_next,'Value'))
link(out(wave_player,'Out Left'),audio_out[0])
link(out(wave_player,'Out Right'),audio_out[1])

editor = u.get_editor_subsystem(u.MetaSoundEditorSubsystem)
asset = value(editor.build_to_asset(builder,'FPSGAME',NAME,D),'Build MetaSound asset')
asset.set_editor_property('volume',1.)
asset.set_editor_property('pitch',1.)
u.EditorAssetLibrary.set_metadata_tag(asset,'AudioSourceSHA256',recipe['source_sha256'])
u.EditorAssetLibrary.set_metadata_tag(asset,'AuthoringRevision',recipe['revision'])
save(asset)
receipt['metasound'] = dict(asset=asset.get_path_name(),segments=6,no_repeat_previous=2,
    pitch_semitones=0,continuous=True,source_sha256=recipe['source_sha256'],
    scheduling='On Nearly Finished -> delayed trigger variable -> Random Get -> Wave Player')
receipt['complete'] = True
record()
print('JI_LEI_RECORDED_RANDOM_CURRENT_SAVED',asset.get_path_name())
