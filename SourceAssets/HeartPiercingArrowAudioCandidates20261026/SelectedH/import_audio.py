"""Import the user-selected combined H release; save one SoundWave without playback."""
from pathlib import Path
import hashlib
import json
import unreal as u

HERE = Path(__file__).resolve().parent
SOURCE = HERE / "S_HeartPiercingArrow_Release.wav"
DEST = "/Game/Skills/HeartPiercingArrow/Audio20261026"
NAME = "S_HeartPiercingArrow_Release"
if "-run=pythonscript" not in u.SystemLibrary.get_command_line().lower():
    # LevelEditor can exist in a commandlet without its interactive module state.
    level_editor = u.get_editor_subsystem(u.LevelEditorSubsystem)
    if level_editor and level_editor.is_in_play_in_editor():
        raise RuntimeError("End Play mode before importing; do not modify or stop the user's running session")
if any(str(p.get_path_name()) == DEST + "/" + NAME for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()):
    raise RuntimeError("Preserve unsaved release sound edits before reimporting")
selection = json.loads((HERE / "selection.json").read_text(encoding="utf-8"))
revision = selection.get("revision", "CombinedV3")

task = u.AssetImportTask()
task.filename = str(SOURCE)
task.destination_path = DEST
task.destination_name = NAME
task.automated = True
task.replace_existing = True
task.save = False
u.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
if not task.imported_object_paths:
    raise RuntimeError("Heart-piercing arrow sound import failed")
sound = u.load_asset(task.imported_object_paths[0])
if not isinstance(sound, u.SoundWave):
    raise RuntimeError("Import did not return a SoundWave")
sound.set_editor_property("volume", 1.)
sound.set_editor_property("pitch", 1.)
sound.set_editor_property("looping", False)
sound.set_editor_property("compression_quality", 100)
sound.set_editor_property("loading_behavior", u.SoundWaveLoadingBehavior.FORCE_INLINE)
sound.set_sound_asset_compression_type(u.SoundAssetCompressionType.PCM)
u.EditorAssetLibrary.set_metadata_tag(sound, "HeartPiercingArrowSelection", "H / E+F+G " + revision + "; user-directed integration")
u.EditorAssetLibrary.set_metadata_tag(sound, "AudioSourceLicense", "CC0-1.0; artisticdude and Still North Media sources; see SelectedH/README.md")
if not u.EditorAssetLibrary.save_loaded_asset(sound, False):
    raise RuntimeError("Heart-piercing arrow sound save failed")
receipt = {
    "candidate": "H / " + revision, "asset": sound.get_path_name(),
    "source": str(SOURCE), "source_sha256": hashlib.sha256(SOURCE.read_bytes()).hexdigest(),
    "saved": True, "looping": False, "volume": 1., "pitch": 1.,
    "compression": "PCM", "loading_behavior": "ForceInline",
    "runtime_tested": False, "played": False,
}
(HERE / "import-receipt.json").write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
u.log("HEART_PIERCING_AUDIO_SAVED " + json.dumps(receipt))
