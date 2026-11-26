"""Install HorseGaitsR47 anatomical zero-twist Canter & Walk motions and hoof contacts into UE5."""
import gzip
import json
import os
from pathlib import Path
import sys

import unreal as ue

sys.path.insert(0, str(Path(__file__).resolve().parent))
from import_hoofsteps import AUDIO, GAITS, HORSES, LIB, bind_contacts, save


def install_clip(gait_key, clip_name, data_path, fit_tag_name):
    with gzip.open(data_path, "rt", encoding="utf-8") as stream:
        motion = json.load(stream)
    package = HORSES + "/Animations/" + clip_name
    clip = ue.load_asset(package)
    mesh = ue.load_asset(HORSES + "/SK_StableWarhorse")
    if not isinstance(clip, ue.AnimSequence) or clip.get_editor_property("skeleton") != mesh.skeleton:
        raise RuntimeError(f"Missing Warhorse {clip_name} or skeleton")
    if any(p.get_name() == package for p in ue.EditorLoadingAndSavingUtils.get_dirty_content_packages()):
        raise RuntimeError(f"Package {package} has unsaved changes")
    waves = [ue.load_asset(AUDIO + f"/SW_Hoof_{gait_key}_{i:02}") for i in range(1, 5)]
    if not all(waves):
        raise RuntimeError(f"Missing hoof sounds for {gait_key}")

    pose = mesh.skeleton.get_reference_pose()
    api = ue.AnimPoseExtensions
    model = clip.get_editor_property("data_model_interface")
    data = motion["bones"]
    skeleton_bones = {str(name) for name in api.get_bone_names(pose)}
    if not data.keys() <= skeleton_bones:
        raise RuntimeError(f"{clip_name} source and resident horse bones differ")

    world = {b: api.get_bone_pose(pose, b, ue.AnimPoseSpaces.WORLD) for b in data}
    keys = {}
    for name, values in data.items():
        rest = api.get_bone_pose(pose, name, ue.AnimPoseSpaces.LOCAL)
        parent = world.get(values["parent"])
        basis = parent.rotation if parent is not None else ue.Quat(0, 0, 0, 1)
        undo = basis.inversed()
        right = basis * rest.rotation
        turns = [undo * ue.Quat(*q) * right for q in values["rotation"]]
        positions = [rest.translation] * len(turns)
        if "translation_cm" in values:
            positions = [
                rest.translation + basis.unrotate_vector(ue.Vector(*p)) / parent.scale3d
                for p in values["translation_cm"]
            ]
        keys[name] = (positions, turns, [rest.scale3d] * len(turns))

    controller = clip.get_editor_property("controller")
    controller.open_bracket(f"Install {motion['source']} into {clip_name}", False)
    try:
        controller.set_frame_rate(ue.FrameRate(numerator=int(motion["rate"]), denominator=1), False)
        controller.set_number_of_frames(ue.FrameNumber(value=int(motion["frames"])), False)
        for name, (positions, rotations, scales) in keys.items():
            if not model.is_valid_bone_track_name(name) and not controller.add_bone_curve(name, False):
                raise RuntimeError("Failed to create track " + name)
            if not controller.set_bone_track_keys(name, positions, rotations, scales, False):
                raise RuntimeError("Failed to write track " + name)
    finally:
        controller.close_bracket(False)

    expected = float(motion["frames"]) / float(motion["rate"])
    if abs(clip.get_play_length() - expected) > 0.0005:
        raise RuntimeError(f"Duration mismatch on {clip_name}: got {clip.get_play_length()}, expected {expected}")

    clip.set_editor_property("rate_scale", float(motion["rate_scale"]))
    period, _, contacts = GAITS[gait_key]
    rev_contacts = motion.get("reverse_contacts") or None
    bind_contacts(clip, waves, period, contacts, motion["contacts"], rev_contacts)
    LIB.set_metadata_tag(clip, "StableHoofPhases", json.dumps(motion["contacts"]))
    if rev_contacts:
        LIB.set_metadata_tag(clip, "StableHoofReversePhases", json.dumps(rev_contacts))
    LIB.set_metadata_tag(clip, fit_tag_name, motion["source"])
    LIB.set_metadata_tag(clip, "StableHorseMotion", motion["source"])
    save(clip)

    return dict(
        package=package,
        motion=motion["source"],
        frames=motion["frames"],
        rate=motion["rate"],
        raw_period_s=round(expected, 4),
        rate_scale=round(float(motion["rate_scale"]), 4),
        stride_m=round(float(motion["stride_m"]), 3),
        contact_phases=motion["contacts"],
        reverse_contact_phases=rev_contacts or {},
    )


def main():
    batch = Path(os.environ.get("HORSE_GAITS_R47_DIR", r"F:\FPSGAMEData\ArtProduction\HillsVillageStable\HorseGaitsR47-20261126"))
    receipt = dict(
        Canter=install_clip("Canter", "A_Warhorse_Canter", batch / "coastal_gallop_r47.json.gz", "StableCanterFit"),
        Walk=install_clip("Walk", "A_Warhorse_Walk", batch / "lateral_walk_r47.json.gz", "StableWalkFit"),
    )
    out = batch / "ue_install_receipt.json"
    out.write_text(json.dumps(receipt, indent=2), encoding="utf-8")
    ue.log("HORSE_GAITS_R47_INSTALLED " + json.dumps(receipt))


if __name__ == "__main__":
    main()
