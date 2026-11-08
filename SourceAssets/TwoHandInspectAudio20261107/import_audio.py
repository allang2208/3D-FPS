"""Run with system Python to decode the two takes, then UE Python to import."""
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
SOURCE = Path("D:/FPS3D/资产/音效")
DEST = "/Game/Audio/TwoHandInspect"
TAKES = [(SOURCE / f"武器划过空气-{i}.mp3", HERE / f"S_TwoHandInspect_Air_0{i}.wav")
         for i in (1, 2)]


def decode():
    import numpy as np
    import soundfile as sf

    for source, wav in TAKES:
        audio, rate = sf.read(source, always_2d=True)
        window = rate // 100
        level = [np.mean(audio[i:i + window] ** 2) for i in range(0, len(audio), window)]
        # Both takes then reach their loudest 10 ms at 0.15 s on the cue clock.
        trim = int(np.argmax(level)) * window - round(0.15 * rate)
        if trim > 0:
            audio = audio[trim:].copy()
            fade = round(0.005 * rate)
            audio[:fade] *= np.linspace(0, 1, fade)[:, None]
        elif trim < 0:
            audio = np.pad(audio, ((-trim, 0), (0, 0)))
        sf.write(wav, audio, rate, subtype="PCM_16")


def import_waves():
    import unreal as u

    tools = u.AssetToolsHelpers.get_asset_tools()
    baseline = u.load_asset("/Game/Audio/WeaponHit20260916/S_MeleeHit_Quick")
    for source, wav in TAKES:
        task = u.AssetImportTask()
        task.filename = str(wav)
        task.destination_path = DEST
        task.destination_name = wav.stem
        task.automated = True
        task.replace_existing = True
        tools.import_asset_tasks([task])
        if not task.imported_object_paths:
            raise RuntimeError(f"Failed to import {wav}")
        wave = u.load_asset(task.imported_object_paths[0])
        wave.set_editor_property("looping", False)
        wave.set_editor_property("loading_behavior", u.SoundWaveLoadingBehavior.FORCE_INLINE)
        wave.set_sound_asset_compression_type(u.SoundAssetCompressionType.PCM)
        if baseline:
            wave.set_editor_property("sound_class_object", baseline.get_editor_property("sound_class_object"))
        u.EditorAssetLibrary.set_metadata_tag(wave, "AudioSource", str(source))
        if not u.EditorLoadingAndSavingUtils.save_packages([wave.get_outermost()], False):
            raise RuntimeError(f"Failed to save {wave.get_path_name()}")
        u.log(f"TWO_HAND_INSPECT_SAVED {wave.get_path_name()}")


if "--decode" in sys.argv:
    decode()
else:
    import_waves()
