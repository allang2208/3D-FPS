"""Import edited mono masters and assign the hills wildlife spatial mix."""
from pathlib import Path
import json
import unreal as ue

project = Path(ue.Paths.convert_relative_path_to_full(ue.Paths.project_dir()))
masters = project / "SourceAssets/HillsWildlifeAudio/Masters"
edits = json.loads((masters.parent / "edits.json").read_text(encoding="utf-8"))
dest = "/Game/Monsters/Wildlife/Audio"
library = ue.EditorAssetLibrary
tools = ue.AssetToolsHelpers.get_asset_tools()
library.make_directory(dest)


def asset(name, kind, factory):
    path = f"{dest}/{name}"
    if library.does_asset_exist(path):
        return ue.load_asset(path)
    return tools.create_asset(name, dest, kind, factory)


def save(obj):
    if not library.save_loaded_asset(obj, only_if_is_dirty=False):
        raise RuntimeError(f"Cannot save {obj.get_path_name()}")


def make_mix(name, inner_radius, falloff, max_count):
    attenuation = asset("ATT_Hills" + name, ue.SoundAttenuation, ue.SoundAttenuationFactory())
    spatial = attenuation.get_editor_property("attenuation")
    spatial.set_editor_property("attenuate", True)
    spatial.set_editor_property("spatialize", True)
    spatial.set_editor_property("attenuation_shape_extents", ue.Vector(inner_radius, 0, 0))
    spatial.set_editor_property("falloff_distance", falloff)
    attenuation.set_editor_property("attenuation", spatial)
    save(attenuation)

    concurrency = asset("CON_Hills" + name, ue.SoundConcurrency, ue.SoundConcurrencyFactory())
    limits = concurrency.get_editor_property("concurrency")
    limits.set_editor_property("max_count", max_count)
    limits.set_editor_property("resolution_rule", ue.MaxConcurrentResolutionRule.STOP_FARTHEST_THEN_OLDEST)
    limits.set_editor_property("voice_steal_release_time", 0.04)
    concurrency.set_editor_property("concurrency", limits)
    save(concurrency)
    return attenuation, concurrency


mixes = {
    "Alarm": make_mix("Alarm", 180, 4700, 7),
    "Hurt": make_mix("Hurt", 160, 3300, 8),
    "Death": make_mix("Death", 170, 3600, 8),
    "Hoof": make_mix("Hoof", 100, 2600, 14),
    "Wings": make_mix("Wings", 95, 2100, 8),
}
for name in edits:
    path = f"{dest}/{name}"
    task = ue.AssetImportTask()
    task.filename = str(masters / (name + ".wav"))
    task.destination_path = dest
    task.destination_name = name
    task.factory = ue.SoundFactory()
    task.automated = True
    task.replace_existing = True
    task.save = False
    tools.import_asset_tasks([task])
    if not task.imported_object_paths:
        raise RuntimeError(f"Cannot import {task.filename}")
    sound = ue.load_asset(path)
    role = name.split("_")[-2]
    attenuation, concurrency = mixes[role]
    sound.set_editor_property("looping", False)
    sound.set_editor_property("attenuation_settings", attenuation)
    sound.set_editor_property("override_concurrency", False)
    sound.set_editor_property("concurrency_set", {concurrency})
    sound.set_editor_property("loading_behavior", ue.SoundWaveLoadingBehavior.FORCE_INLINE)
    library.set_metadata_tag(sound, "WildlifeAudioRole", role)
    save(sound)
ue.log(f"Saved {len(edits)} hills wildlife waves and {len(mixes)} spatial/concurrency pairs.")
