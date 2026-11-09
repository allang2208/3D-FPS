"""Import and save the M249 SoundWaves with the project's rifle mixer settings."""
import json
from pathlib import Path
import unreal as u

root = Path(__file__).resolve().parent
recipe = json.loads((root / "source.json").read_text(encoding="utf8"))
reference = u.load_asset("/Game/Weapons/LMG201/FireAudio01/S_LMG201_Fire_01")
target = "/Game/Weapons/M249/Audio"
tasks = []
for name in recipe["files"]:
    task = u.AssetImportTask()
    task.filename = str(root / name)
    task.destination_name = Path(name).stem
    task.destination_path = target
    task.automated = True
    task.replace_existing = True
    task.save = False
    tasks.append(task)
u.AssetToolsHelpers.get_asset_tools().import_asset_tasks(tasks)
packages = []
for task in tasks:
    if not task.imported_object_paths:
        raise RuntimeError("Failed to import " + task.filename)
    wave = u.load_asset(target + "/" + task.destination_name)
    for key in ("volume", "pitch", "sound_class_object"):
        wave.set_editor_property(key, reference.get_editor_property(key))
    wave.set_editor_property("looping", False)
    wave.set_editor_property("loading_behavior", u.SoundWaveLoadingBehavior.FORCE_INLINE)
    wave.set_sound_asset_compression_type(u.SoundAssetCompressionType.PCM)
    u.EditorAssetLibrary.set_metadata_tag(wave, "SourceRecording", "M249.mp3")
    u.EditorAssetLibrary.set_metadata_tag(wave, "SourceRecordingSHA256", recipe["sha256"])
    packages.append(wave.get_outermost())
if not u.EditorLoadingAndSavingUtils.save_packages(packages, False):
    raise RuntimeError("Failed to save the M249 SoundWaves")
print("M249_FIRE_SAVED", [p.get_name() for p in packages], flush=True)
