"""Replace the existing door SoundWave with the user's local audio; do not play it."""
from pathlib import Path
import json
import shutil
import wave
import unreal as u

HERE = Path(__file__).resolve().parent
PROJECT = HERE.parents[2]
DEST = "/Game/Audio/Interactions/DoorPush20261002"
NAME = "S_DoorPushImpact"
ASSET = DEST + "/" + NAME + "." + NAME
receipt = {
    "status": "import_started",
    "source": str(HERE / (NAME + ".wav")),
    "asset": ASSET,
    "audio_auditioned": False,
    "game_tested": False,
}

def write_receipt():
    (HERE / "import-receipt.json").write_text(
        json.dumps(receipt, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

try:
    write_receipt()
    if u.get_editor_subsystem(u.UnrealEditorSubsystem).get_game_world() is not None:
        raise RuntimeError("Stop PIE before replacing the loaded door SoundWave")
    sound = u.load_asset(ASSET)
    if sound is None:
        raise RuntimeError("Existing door SoundWave missing; preserving replacement scope")
    properties = ("sound_class_object", "volume", "pitch", "looping",
                  "compression_quality", "loading_behavior")
    settings = {key: sound.get_editor_property(key) for key in properties}
    backup = HERE / "BeforeAsset"
    backup.mkdir(exist_ok=True)
    disk_asset = PROJECT / "Content/Audio/Interactions/DoorPush20261002" / NAME
    for suffix in (".uasset", ".ubulk", ".uexp"):
        source = disk_asset.with_suffix(suffix)
        target = backup / source.name
        if source.exists() and not target.exists():
            shutil.copy2(source, target)
    receipt["backup"] = str(backup)

    task = u.AssetImportTask()
    task.filename = receipt["source"]
    task.destination_path = DEST
    task.destination_name = NAME
    task.automated = True
    task.replace_existing = True
    task.replace_existing_settings = False
    task.save = False
    u.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
    if ASSET not in task.imported_object_paths:
        raise RuntimeError("Import did not return the intended door SoundWave")
    sound = u.load_asset(ASSET)
    for key, value in settings.items():
        sound.set_editor_property(key, value)
    if not u.EditorAssetLibrary.save_loaded_asset(sound, False):
        raise RuntimeError("Replacement SoundWave save failed")
    with wave.open(receipt["source"], "rb") as wav:
        receipt.update(sample_rate_hz=wav.getframerate(), channels=wav.getnchannels(),
                       bit_depth=wav.getsampwidth() * 8)
    receipt.update(
        status="imported_and_saved",
        duration_seconds=sound.get_editor_property("duration"),
        sound_class=settings["sound_class_object"].get_path_name()
            if settings["sound_class_object"] is not None else None,
        volume=settings["volume"], pitch=settings["pitch"], looping=settings["looping"],
        compression_quality=settings["compression_quality"],
        loading_behavior=str(settings["loading_behavior"]),
        imported_object_paths=list(task.imported_object_paths),
        playback_trigger_changed=False,
        runtime_volume_multiplier=0.85,
        contact_seconds=0.36,
    )
    write_receipt()
    u.log("DOOR_PUSH_USER_AUDIO_SAVED " + json.dumps(receipt, ensure_ascii=False))
except Exception as error:
    receipt.update(status="failed", error=str(error))
    write_receipt()
    raise
