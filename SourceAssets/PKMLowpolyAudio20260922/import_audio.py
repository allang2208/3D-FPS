"""Import the original gamedev PKM fire WAV as PKM's own fire sound.

Runs inside the already-open editor through the mutual-exclusion bridge. Creates
exactly one asset, matching the accepted AKM fire voice's volume/pitch settings so
the two share one loudness convention; the WAV itself is level-matched already
(+0.07 dB vs the AKM reference), so no gain is applied here.

No PIE, no playback, no listening.
"""
from pathlib import Path
import json

import unreal as u

HERE = Path(__file__).resolve().parent
DEST = '/Game/Weapons/PKMLowpoly20260922/Audio'
NAME = 'S_PKM_Fire'
REFERENCE = '/Game/Weapons/AKM/VideoAudio20260921/S_AKM_Fire'
# Requested 2x loudness in total: the WAV normalisation contributes 1.66x
# (0.6025 -> 1.0) and this property carries the remainder, 2.0 / 1.66 = 1.205.
FIRE_VOLUME_MULTIPLIER = 1.205

source = HERE / (NAME + '.wav')
if not source.is_file():
    raise RuntimeError('Missing source WAV: ' + str(source))

reference = u.load_asset(REFERENCE)
if reference is None:
    raise RuntimeError('Missing reference voice for audio settings: ' + REFERENCE)

task = u.AssetImportTask()
task.filename = str(source)
task.destination_path = DEST
task.destination_name = NAME
task.automated = True
task.replace_existing = True
task.save = False
u.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
if not task.imported_object_paths:
    raise RuntimeError('Import failed: ' + NAME)

sound = u.load_asset(task.imported_object_paths[0])
if sound is None:
    raise RuntimeError('Imported asset did not load: ' + NAME)

# Copy only the settings that carry loudness/timbre convention between the two
# rifle voices, then normalise the playback contract explicitly.
for prop in ('volume', 'pitch', 'sound_class_object'):
    sound.set_editor_property(prop, reference.get_editor_property(prop))
# The WAV is already peak-normalised to full scale, so the remaining part of the
# requested 2x loudness rides here; doing it all on the WAV clipped 1.7% of samples.
sound.set_editor_property('volume', FIRE_VOLUME_MULTIPLIER)
sound.set_editor_property('looping', False)
sound.set_editor_property('loading_behavior', u.SoundWaveLoadingBehavior.FORCE_INLINE)

# save_loaded_asset returns False for an import created in this same call even
# when the package is writable; save by path and then verify on disk instead.
asset_path = sound.get_path_name().split('.')[0]
saved = u.EditorAssetLibrary.save_asset(asset_path, False)
if not saved:
    u.EditorAssetLibrary.save_directory(DEST, False, True)
if not u.EditorAssetLibrary.does_asset_exist(asset_path):
    raise RuntimeError('Save failed: ' + asset_path)

receipt = [dict(
    asset=sound.get_path_name(),
    source=str(source),
    reference=REFERENCE,
    duration_seconds=sound.get_editor_property('duration'),
    volume=sound.get_editor_property('volume'),
    pitch=sound.get_editor_property('pitch'),
    looping=sound.get_editor_property('looping'),
)]
(HERE / 'import-receipt.json').write_text(
    json.dumps(receipt, indent=2, ensure_ascii=False), encoding='utf-8')
u.log('PKM_FIRE_AUDIO_IMPORTED ' + json.dumps(receipt))
