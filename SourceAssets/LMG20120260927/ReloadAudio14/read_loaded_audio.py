"""Read-only investigation of the already-running editor's PKM sound objects."""
import hashlib
import json
from pathlib import Path
import unreal as u

OUT = Path(__file__).parent / 'HistoryInvestigation'
OUT.mkdir(exist_ok=True)
world = u.get_editor_subsystem(u.UnrealEditorSubsystem).get_game_world()
result = {'pie': bool(world), 'sounds': [], 'mechanical_components': []}
for name in ('CoverOpen', 'CoverClose'):
    path = '/Game/Weapons/PKMLowpoly20260922/ReloadAudio22/S_PKM_' + name
    sound = u.load_asset(path)
    if sound is None:
        raise RuntimeError('Missing current PKM sound: ' + path)
    row = {'asset': sound.get_path_name(),
           'source': list(sound.get_editor_property('asset_import_data').extract_filenames()),
           'duration': sound.get_editor_property('duration'),
           'volume': sound.get_editor_property('volume'),
           'pitch': sound.get_editor_property('pitch')}
    export = u.AssetExportTask()
    export.object = sound
    export.exporter = u.SoundExporterWAV()
    export.filename = str(OUT / (sound.get_name() + '.wav'))
    export.automated = True
    export.prompt = False
    export.replace_identical = True
    row['exported'] = bool(u.Exporter.run_asset_export_task(export))
    row['wav_sha256'] = hashlib.sha256(Path(export.filename).read_bytes()).hexdigest()
    result['sounds'].append(row)

if world:
    pawn = u.GameplayStatics.get_player_pawn(world, 0)
    if pawn:
        result['pawn'] = pawn.get_path_name()
        for component in pawn.get_components_by_class(u.AudioComponent):
            sound = component.get_editor_property('sound')
            if sound and any(part in sound.get_path_name() for part in ('PKM', 'LMG201', 'S_AKM_Charge', 'S_AKM_Mag')):
                result['mechanical_components'].append({
                    'component': component.get_name(), 'sound': sound.get_path_name(),
                    'playing': component.is_playing(),
                    'volume': component.get_editor_property('volume_multiplier'),
                    'pitch': component.get_editor_property('pitch_multiplier')})

(OUT / 'loaded_audio.json').write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding='utf-8')
print('201_AUDIO_HISTORY_READ ' + json.dumps(result, ensure_ascii=False))
