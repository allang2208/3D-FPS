"""Read source pose/clip and mesh metadata for player-body diagnosis."""
import json
from pathlib import Path
import unreal as u

root = Path(u.Paths.project_dir()).resolve()
if root != Path("D:/FPS3D/FPSGAME").resolve():
    raise RuntimeError("Unexpected project")
config = json.loads((root / "Content/ColdSteelData/player_body.json").read_text(encoding="utf-8"))
options = u.AnimPoseEvaluationOptions()
options.optional_skeletal_mesh = u.load_asset(config["body_mesh"])
report = {}
for family in ("Unarmed", "Rifle", "Pistol"):
    for suffix in (key[len(family) + 1:] for key in config["clips"]
                   if key.startswith(family + ".Walk.") or key.startswith(family + ".Jog.")):
        key = family + "." + suffix
        clip = u.load_asset(config["clips"][key])
        length = clip.get_play_length()
        samples = []
        for index in (range(33) if suffix.endswith(".Fwd") or (family == "Rifle" and suffix.startswith("Jog.")) else ()):
            pose = u.AnimPoseExtensions.get_anim_pose_at_time(clip, length * index / 32, options)
            bones = {}
            for bone in ("root", "pelvis", "foot_l", "foot_r"):
                transform = u.AnimPoseExtensions.get_bone_pose(pose, bone, u.AnimPoseSpaces.WORLD)
                v = transform.translation
                bones[bone] = [round(v.x, 3), round(v.y, 3), round(v.z, 3)]
            samples.append({"phase": index / 32, "bones": bones})
        report[key] = {"path": clip.get_path_name(), "length": length, "samples": samples,
                       "enable_root_motion": clip.get_editor_property("enable_root_motion"),
                       "force_root_lock": clip.get_editor_property("force_root_lock"),
                       "markers": [{"name": str(marker.marker_name), "time": marker.time}
                                   for marker in u.AnimationLibrary.get_animation_sync_markers(clip)]}
destination = root / "Saved/PlayerBodyFix20260921/source-poses.json"
destination.parent.mkdir(parents=True, exist_ok=True)
destination.write_text(json.dumps(report, indent=2), encoding="utf-8")
print(str(destination))
print(json.dumps({key: {k: v for k, v in data.items() if k not in ("path", "samples")}
                  for key, data in report.items() if key.endswith(".Fwd")}))
