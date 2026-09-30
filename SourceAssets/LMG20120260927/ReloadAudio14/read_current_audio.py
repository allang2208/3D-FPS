"""Read the installed PKM contacts used by the 201 reload; no asset changes."""
import json
from pathlib import Path
import unreal as u

OUT = Path(__file__).parent
(OUT / 'CurrentPKM').mkdir(exist_ok=True)
rows = []
for folder, names in [
    ('ReloadAudio22', ['CoverOpen', 'BeltLift', 'BoxOut', 'BoxInsert', 'BeltSeat', 'CoverClose']),
    ('ChargeAudio35', ['ChargePullMove', 'ChargeRearStop', 'ChargePushMove', 'ChargeFrontStop']),
]:
    for name in names:
        path = '/Game/Weapons/PKMLowpoly20260922/' + folder + '/S_PKM_' + name
        sound = u.load_asset(path)
        if sound is None:
            raise RuntimeError('Missing installed PKM contact: ' + path)
        row = {'asset': sound.get_path_name(), 'source': list(sound.get_editor_property('asset_import_data').extract_filenames())}
        for prop in ['volume', 'pitch', 'duration', 'looping', 'loading_behavior', 'sample_rate', 'num_channels',
                     'sound_class_object', 'attenuation_settings', 'sound_submix_object', 'concurrency_set', 'compression_quality']:
            try:
                row[prop] = str(sound.get_editor_property(prop))
            except Exception as exc:
                row[prop] = str(exc)
        task = u.AssetExportTask()
        task.object = sound
        task.exporter = u.SoundExporterWAV()
        task.filename = str(OUT / 'CurrentPKM' / (sound.get_name() + '.wav'))
        task.automated = True
        task.prompt = False
        task.replace_identical = True
        row['exported'] = bool(u.Exporter.run_asset_export_task(task))
        rows.append(row)

clips = []
for path in [
    '/Game/Weapons/PKMLowpoly20260922/Animations/A_PKM_reload',
    '/Game/Weapons/PKMLowpoly20260922/Animations/A_PKM_reload_empty',
    '/Game/Weapons/LMG201/Reload11/A_LMG201_reload_belt',
    '/Game/Weapons/LMG201/Reload11/A_LMG201_reload_belt_empty',
]:
    clip = u.load_asset(path)
    row = {'asset': path, 'duration': clip.get_play_length()}
    row['notifies'] = [str(x) for x in u.AnimationLibrary.get_animation_notify_events(clip)]
    clips.append(row)

(OUT / 'current_audio.json').write_text(json.dumps({'sounds': rows, 'clips': clips}, indent=2, ensure_ascii=False), encoding='utf-8')
print('201_CURRENT_PKM_AUDIO_READ', len(rows), flush=True)
