import math
import random
import struct
import wave
from pathlib import Path

import unreal


DESTINATION = "/Game/Weapons/AKM/Audio"
PROJECT_ROOT = Path(unreal.Paths.project_dir())
CLICK_SOURCE = PROJECT_ROOT / "SourceAssets" / "AKM" / "S_AKM_DryClick.wav"


def make_godot_dry_click():
    CLICK_SOURCE.parent.mkdir(parents=True, exist_ok=True)
    random.seed(122)
    rate = 22050
    frames = int(rate * 0.05)
    pcm = bytearray()
    for index in range(frames):
        envelope = 0.6 * (1.0 - index / frames)
        sample = random.uniform(-1.0, 1.0) * envelope
        pcm.extend(struct.pack("<h", int(max(-1.0, min(1.0, sample)) * 32767.0)))
    with wave.open(str(CLICK_SOURCE), "wb") as output:
        output.setnchannels(1)
        output.setsampwidth(2)
        output.setframerate(rate)
        output.writeframes(pcm)


def import_sound(source, destination_name):
    task = unreal.AssetImportTask()
    task.filename = str(source)
    task.destination_path = DESTINATION
    task.destination_name = destination_name
    task.automated = True
    task.replace_existing = True
    task.save = True
    unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
    if not task.imported_object_paths:
        raise RuntimeError(f"Audio import failed: {source}")
    unreal.log(f"AKM_AUDIO_IMPORTED {destination_name} <- {source}")


make_godot_dry_click()
sources = [
    (r"E:\3d\3-dfps\assets\sfx\akm_burst.mp3", "S_AKM_Fire"),
    (r"E:\3d\3-dfps\assets\sfx\akm\equip.mp3", "S_AKM_Equip"),
    (r"E:\3d\3-dfps\assets\sfx\akm_classic\mechanics\mag_out.wav", "S_AKM_MagOut"),
    (r"E:\3d\3-dfps\assets\sfx\akm_classic\mechanics\mag_insert.wav", "S_AKM_MagInsert"),
    (r"E:\3d\3-dfps\assets\sfx\akm_classic\mechanics\mag_seat.wav", "S_AKM_MagSeat"),
    (r"E:\3d\3-dfps\assets\sfx\m16\mechanics\charge_pull.wav", "S_AKM_ChargePull"),
    (r"E:\3d\3-dfps\assets\sfx\m16\mechanics\charge_release.wav", "S_AKM_ChargeRelease"),
    (r"E:\3d\3-dfps\assets\sfx\criticalhit.mp3", "S_AKM_CriticalHit"),
    (CLICK_SOURCE, "S_AKM_DryClick"),
]
for filename, asset_name in sources:
    import_sound(Path(filename), asset_name)

unreal.EditorAssetLibrary.save_directory(DESTINATION, only_if_is_dirty=False, recursive=True)
unreal.log("AKM_AUDIO_IMPORT_COMPLETE count=9")
