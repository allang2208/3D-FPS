"""Import the nine prepared one-shots with their original SoundWave playback settings."""
import json
from pathlib import Path
import unreal as u

here = Path(__file__).resolve().parent
rows = json.loads((here/"masters.json").read_text(encoding="utf-8"))
lib = u.EditorAssetLibrary
dirty = {p.get_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()}
if any(r["package"] in dirty for r in rows):
    raise RuntimeError("An affected SoundWave has unsaved edits")
if "-run=pythonscript" not in u.SystemLibrary.get_command_line().lower():
    if u.get_editor_subsystem(u.LevelEditorSubsystem).is_in_play_in_editor():
        raise RuntimeError("The editor is in PIE")
for row in rows:
    donor = u.load_asset(row["donor"])
    if not isinstance(donor,u.SoundWave):
        raise RuntimeError("Missing previous shot settings: "+row["donor"])
    dest, name = row["package"].rsplit("/",1)
    task = u.AssetImportTask()
    task.filename = str(here/row["wav"])
    task.destination_name = name
    task.destination_path = dest
    task.automated = True
    task.replace_existing = True
    task.save = False
    task.factory = u.SoundFactory()
    u.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
    wave = u.load_asset(row["package"])
    if not task.imported_object_paths or not isinstance(wave,u.SoundWave):
        raise RuntimeError("Failed importing "+name)
    for prop in ("volume","pitch","sound_class_object","compression_quality"):
        wave.set_editor_property(prop,donor.get_editor_property(prop))
    wave.set_editor_property("looping",False)
    wave.set_editor_property("loading_behavior",u.SoundWaveLoadingBehavior.FORCE_INLINE)
    wave.set_sound_asset_compression_type(u.SoundAssetCompressionType.PCM)
    lib.set_metadata_tag(wave,"SuppressedSource",row["donor"])
    lib.set_metadata_tag(wave,"AudioSourceAttribution", "Game sound design derived from the existing project recording; original source rights retained.")
    if not lib.save_loaded_asset(wave, False):
        raise RuntimeError("Failed saving "+name)
    u.log("SNIPER_WARM_WAVE "+wave.get_path_name())
u.log("SNIPER_WARM_SAVED "+str(len(rows)))
