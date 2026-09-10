import json
from pathlib import Path
import unreal

OUTPUT = Path(r"D:\FPS3D\FPSGAME\SourceAssets\AKM\akm_unreal_pose_report.json")
CLIPS = ("idle", "aim", "fire", "aim_fire", "reload", "reload_empty", "draw", "holster", "inspect")
BONES = (
    "VM_Root", "root", "hand_l", "hand_r", "WPN_root", "WPN_magazine",
    "WPN_bolt", "WPN_SOCKET_Muzzle",
)


def transform_dict(transform):
    location = transform.translation
    rotation = transform.rotation.rotator()
    scale = transform.scale3d
    return {
        "location": [location.x, location.y, location.z],
        "rotation": [rotation.roll, rotation.pitch, rotation.yaw],
        "scale": [scale.x, scale.y, scale.z],
    }


report = {}
for clip in CLIPS:
    animation = unreal.load_asset(f"/Game/Weapons/AKM/A_AKM_{clip}")
    keys = int(animation.get_editor_property("number_of_sampled_keys"))
    frames = sorted(set((0, max(0, (keys - 1) // 2), max(0, keys - 1))))
    samples = {}
    for frame in frames:
        samples[str(frame)] = {
            bone: transform_dict(unreal.AnimationLibrary.get_bone_pose_for_frame(
                animation, bone, frame, False
            ))
            for bone in BONES
        }
    report[clip] = {"sampled_keys": keys, "samples": samples}

OUTPUT.write_text(json.dumps(report, indent=2), encoding="utf-8")
unreal.log("AKM_UNREAL_POSE_REPORT_WRITTEN")
