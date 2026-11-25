"""Install spatial one-shots and hoof-contact events onto the placed residents' gait clips."""
import json
import os
from pathlib import Path

import unreal as ue

ROOT = Path(ue.Paths.convert_relative_path_to_full(ue.Paths.project_dir()))
MASTERS = ROOT / "SourceAssets/HillsVillageStable/HoofAudioR11/Masters"
HORSES = "/Game/WorldGeneration/TemperateHills/VillageStable/Horses"
AUDIO = HORSES + "/Audio"
TRACK = "StableHoofContacts"
LIB = ue.EditorAssetLibrary
ANIM = ue.AnimationLibrary
TOOLS = ue.AssetToolsHelpers.get_asset_tools()

# Frames in the source 30 Hz loop. On reverse playback contact occurs at forward lift-off.
GAITS = {
    "Walk": (36, 2100, [
        (0, "toe_L", .65, False), (9, "finger_R", .75, False),
        (18, "toe_R", .67, False), (27, "finger_L", .73, False),
        (1, "toe_R", .60, True), (7, "finger_L", .67, True),
        (19, "toe_L", .60, True), (25, "finger_R", .67, True)]),
    "Canter": (20, 3600, [
        (1, "toe_R", .93, False), (6, "finger_R", .76, False),
        (7, "toe_L", .66, False), (11, "finger_L", 1.0, False)]),
}


def require_asset(name, cls, factory):
    path = AUDIO + "/" + name
    asset = ue.load_asset(path) if LIB.does_asset_exist(path) else TOOLS.create_asset(name, AUDIO, cls, factory)
    if not isinstance(asset, cls):
        raise RuntimeError("Cannot create " + path)
    return asset


def save(asset):
    if not LIB.save_loaded_asset(asset, only_if_is_dirty=False):
        raise RuntimeError("Cannot save " + asset.get_path_name())


def bind_contacts(clip, waves, period, contacts, phases=None):
    if ANIM.is_valid_anim_notify_track_name(clip, TRACK):
        ANIM.remove_animation_notify_track(clip, TRACK)
    ANIM.add_animation_notify_track(clip, TRACK)
    for frame, bone, gain, reverse in contacts:
        phase = phases[bone] if phases is not None else frame/period
        notify = ANIM.add_animation_notify_event(clip, TRACK, clip.get_play_length()*phase,
                                                 ue.StableHoofstepNotify)
        if not notify:
            raise RuntimeError(f"Cannot bind {clip.get_name()}/{bone} at phase {phase}")
        notify.set_editor_property("hoof_bone", bone)
        notify.set_editor_property("variations", waves)
        notify.set_editor_property("gain", gain)
        notify.set_editor_property("reverse_only", reverse)


def install():
    LIB.make_directory(AUDIO)
    limit = require_asset("CON_StableHooves", ue.SoundConcurrency, ue.SoundConcurrencyFactory())
    settings = limit.get_editor_property("concurrency")
    settings.set_editor_property("max_count", 5)
    settings.set_editor_property("limit_to_owner", True)
    settings.set_editor_property("resolution_rule", ue.MaxConcurrentResolutionRule.STOP_OLDEST)
    limit.set_editor_property("concurrency", settings)
    save(limit)
    clips = []
    receipt = {}
    for gait, (period, falloff, contacts) in GAITS.items():
        clip = ue.load_asset(HORSES + "/Animations/A_Warhorse_" + gait)
        if not isinstance(clip, ue.AnimSequence):
            raise RuntimeError("Missing resident gait " + gait)
        attenuation = require_asset("ATT_StableHoof_" + gait, ue.SoundAttenuation, ue.SoundAttenuationFactory())
        spatial = attenuation.get_editor_property("attenuation")
        spatial.set_editor_property("attenuate", True)
        spatial.set_editor_property("spatialize", True)
        spatial.set_editor_property("attenuation_shape_extents", ue.Vector(150, 0, 0))
        spatial.set_editor_property("falloff_distance", falloff)
        attenuation.set_editor_property("attenuation", spatial)
        save(attenuation)
        waves = []
        for i in range(1, 5):
            name = f"SW_Hoof_{gait}_{i:02}"
            task = ue.AssetImportTask()
            task.filename = str(MASTERS / (name + ".wav"))
            task.destination_path = AUDIO
            task.destination_name = name
            task.automated = True
            task.replace_existing = True
            task.save = False
            TOOLS.import_asset_tasks([task])
            if not task.imported_object_paths:
                raise RuntimeError("Import failed for " + name)
            sound = ue.load_asset(task.imported_object_paths[0])
            sound.set_editor_property("looping", False)
            sound.set_editor_property("attenuation_settings", attenuation)
            sound.set_editor_property("override_concurrency", False)
            sound.set_editor_property("concurrency_set", {limit})
            sound.set_editor_property("loading_behavior", ue.SoundWaveLoadingBehavior.FORCE_INLINE)
            save(sound)
            waves.append(sound)
        encoded = LIB.get_metadata_tag(clip, "StableHoofPhases")
        phases = json.loads(encoded) if encoded else None
        bind_contacts(clip, waves, period, contacts, phases)
        clips.append(clip)
        receipt[gait] = dict(clip=clip.get_path_name(), sounds=[w.get_path_name() for w in waves],
                             contacts=contacts, period_frames=period)
        if phases is not None:
            receipt[gait]["contact_phases"] = phases
    for clip in clips:
        save(clip)
    Path(os.environ["STABLE_HOOF_RECEIPT"]).write_text(json.dumps(receipt, indent=2), encoding="utf-8")


if __name__ == "__main__":
    install()
