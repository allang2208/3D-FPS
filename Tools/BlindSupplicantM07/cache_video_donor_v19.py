"""Cache existing CC0 locomotion donors as production input for M-07 V19.

Run with Blender 5.1 in background. This does not edit the source GLB, create
M-07 motion, render previews, or open Unreal. Cached matrices use Blender
world space, metres, Z-up, nested row-major 4x4 arrays acting on column vectors.
The three complete source action spans retain both loop endpoints.
"""

from __future__ import annotations

import json
import math
import statistics
import struct
from pathlib import Path

import bpy
from mathutils import Vector


PROJECT = Path("D:/FPS3D/FPSGAME")
SOURCE_ROOT = PROJECT / "SourceAssets/FatZombieMeshy20260913"
SOURCE = SOURCE_ROOT / "sources/human-base-animations.glb"
OUT = PROJECT / "SourceAssets/BlindSupplicantM07Meshy20261001/VideoLocomotionV19/Donor"
FPS = 30
CLIPS = ("Jog", "Walk", "Sprint")
MAIN_ROLES = (
    "root", "pelvis", "spine_01", "spine_02", "spine_03", "neck_01", "head",
    "clavicle_l", "upperarm_l", "lowerarm_l", "hand_l",
    "clavicle_r", "upperarm_r", "lowerarm_r", "hand_r",
    "thigh_l", "calf_l", "foot_l", "ball_l",
    "thigh_r", "calf_r", "foot_r", "ball_r",
)


def matrix_rows(value):
    return [[round(float(c), 9) for c in row] for row in value]


def xyz(value):
    return [round(float(c), 9) for c in value]


def read_gltf():
    raw = SOURCE.read_bytes()
    offset = 12
    document, binary = None, None
    while offset < len(raw):
        length, kind = struct.unpack_from("<II", raw, offset)
        offset += 8
        payload = raw[offset:offset + length]
        offset += length
        if kind == 0x4E4F534A:
            document = json.loads(payload)
        elif kind == 0x004E4942:
            binary = payload
    if document is None or binary is None:
        raise RuntimeError("Expected glTF JSON and embedded binary source chunks")
    return document, binary


def accessor_times(document, binary, accessor_index):
    accessor = document["accessors"][accessor_index]
    if accessor["componentType"] != 5126 or accessor["type"] != "SCALAR":
        raise RuntimeError("Unexpected source time accessor")
    view = document["bufferViews"][accessor["bufferView"]]
    offset = view.get("byteOffset", 0) + accessor.get("byteOffset", 0)
    stride = view.get("byteStride", 4)
    return [struct.unpack_from("<f", binary, offset + i * stride)[0]
            for i in range(accessor["count"])]


def animation_metadata(document, binary, clip):
    source = next(item for item in document["animations"] if item["name"] == clip)
    times = [accessor_times(document, binary, item["input"])
             for item in source["samplers"]]
    start = min(values[0] for values in times)
    end = max(values[-1] for values in times)
    # Constant glTF tracks often contain only the two endpoints. FPS is an
    # inference from dense tracks, because glTF itself stores seconds, not FPS.
    dense = max(times, key=len)
    deltas = [b - a for a, b in zip(dense, dense[1:]) if b - a > 1e-6]
    median_dt = statistics.median(deltas) if len(dense) > 2 else None
    return {
        "gltf_start_seconds": start,
        "gltf_end_seconds": end,
        "source_duration_seconds": end - start,
        "source_key_sample_fps_inferred": 1 / median_dt if median_dt else None,
        "source_key_sample_fps_basis": "Median interval of the densest glTF time track; source format has no declared FPS",
        "dense_source_key_times_seconds": dense,
        "gltf_channel_count": len(source["channels"]),
        "gltf_sampler_count": len(source["samplers"]),
    }


def activate(rig, action):
    rig.animation_data_create()
    rig.animation_data.action = action
    if action.slots:
        suitable = [slot for slot in action.slots if slot.target_id_type == "OBJECT"]
        rig.animation_data.action_slot = suitable[0] if suitable else action.slots[0]
    for track in rig.animation_data.nla_tracks:
        track.mute = True
    rig.data.pose_position = "POSE"
    bpy.context.view_layer.update()


def locate_action(name):
    exact = bpy.data.actions.get(name)
    if exact:
        return exact
    matches = [action for action in bpy.data.actions
               if action.name.startswith(name + ".") or action.name.endswith("|" + name)]
    if len(matches) != 1:
        raise RuntimeError(f"Source action {name!r} is unavailable or ambiguous")
    return matches[0]


def stance_intervals(times, contact):
    result, beginning = [], None
    for index, flag in enumerate(contact):
        if flag and beginning is None:
            beginning = times[index]
        if beginning is not None and (not flag or index == len(contact) - 1):
            ending = times[index] if flag else times[max(0, index - 1)]
            result.append([round(beginning, 9), round(ending, 9)])
            beginning = None
    return result


def support_trajectories(samples, forward, up):
    times = [sample["time_seconds"] for sample in samples]
    result = {}
    for side in ("l", "r"):
        foot, toe, pelvis = [], [], []
        for sample in samples:
            matrices = sample["world_matrices"]
            foot.append(Vector([matrices["foot_" + side][j][3] for j in range(3)]))
            toe.append(Vector([matrices["ball_" + side][j][3] for j in range(3)]))
            pelvis.append(Vector([matrices["pelvis"][j][3] for j in range(3)]))
        heights = [point.dot(up) for point in toe]
        ground = min(heights)
        heights_above_low = [value - ground for value in heights]
        derivatives = []
        for i in range(len(samples)):
            a, b = max(0, i - 1), min(len(samples) - 1, i + 1)
            dt = max(1e-8, times[b] - times[a])
            derivatives.append((toe[b] - toe[a]) / dt)
        # This is a source trajectory aid, not an IK/contact acceptance check.
        # In-place locomotion normally has moving world-space support feet.
        # A low toe with backward horizontal travel is a coarse stance hint.
        contact = [height <= 0.045 and velocity.dot(forward) <= 0.10
                   for height, velocity in zip(heights_above_low, derivatives)]
        result[side] = {
            "ankle_role": "foot_" + side,
            "toe_role": "ball_" + side,
            "toe_lowest_world_height_m": round(ground, 9),
            "ankle_world_positions_m": [xyz(point) for point in foot],
            "toe_world_positions_m": [xyz(point) for point in toe],
            "toe_pelvis_relative_positions_m": [xyz(point - center) for point, center in zip(toe, pelvis)],
            "toe_height_above_source_low_m": [round(value, 9) for value in heights_above_low],
            "toe_velocity_world_m_s": [xyz(velocity) for velocity in derivatives],
            "toe_fore_aft_world_m": [round(point.dot(forward), 9) for point in toe],
            "coarse_stance_hint": contact,
            "coarse_stance_intervals_seconds": stance_intervals(times, contact),
            "coarse_stance_rule": "Toe within 4.5cm of clip-local lowest toe and source-forward velocity <= 0.10m/s; an authoring hint only",
        }
    return result


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    document, binary = read_gltf()
    provenance = json.loads((SOURCE_ROOT / "source_manifest.json").read_text(encoding="utf-8-sig"))
    source_entry = next(item for item in provenance["downloads"]
                        if Path(item["path"]).name == SOURCE.name)
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    scene.render.fps, scene.render.fps_base = FPS, 1.0
    scene.unit_settings.system = "METRIC"
    scene.unit_settings.scale_length = 1.0
    bpy.ops.import_scene.gltf(filepath=str(SOURCE))
    rig = next(obj for obj in bpy.data.objects if obj.type == "ARMATURE")
    rig.data.pose_position = "POSE"
    ordered = sorted(rig.data.bones, key=lambda bone: len(bone.parent_recursive))
    rest = {bone.name: rig.matrix_world @ bone.matrix_local for bone in ordered}
    role_map = {name: name for name in MAIN_ROLES if name in rest}
    finger_roles = {name: name for name in rest
                    if name.startswith(("thumb_", "index_", "middle_", "ring_", "pinky_"))
                    and "leaf" not in name}
    role_map.update(finger_roles)
    bone_to_role = {source: role for role, source in role_map.items()}
    up = Vector((0, 0, 1))
    toe_direction = sum((rest["ball_" + side].translation - rest["foot_" + side].translation
                         for side in ("l", "r")), Vector())
    toe_direction.z = 0
    forward = toe_direction.normalized()
    left = rest["thigh_l"].translation - rest["thigh_r"].translation
    left.z = 0
    left.normalize()
    reference = {
        "object_name": rig.name,
        "object_matrix_world": matrix_rows(rig.matrix_world),
        "bone_order": [bone.name for bone in ordered],
        "bone_parents": {bone.name: bone.parent.name if bone.parent else None for bone in ordered},
        "bone_world_rest_matrices": {name: matrix_rows(value) for name, value in rest.items()},
        "bone_armature_local_rest_matrices": {bone.name: matrix_rows(bone.matrix_local) for bone in ordered},
        "bone_local_parent_rest_matrices": {
            bone.name: matrix_rows(bone.parent.matrix_local.inverted() @ bone.matrix_local
                                   if bone.parent else bone.matrix_local)
            for bone in ordered
        },
        "bone_rest_world_heads_m": {bone.name: xyz(rig.matrix_world @ bone.head_local) for bone in ordered},
        "bone_rest_world_tails_m": {bone.name: xyz(rig.matrix_world @ bone.tail_local) for bone in ordered},
        "role_to_source_bone": role_map,
        "source_bone_to_role": bone_to_role,
        "world_axes": {
            "up": xyz(up), "forward_from_rest_ankle_to_toe": xyz(forward),
            "character_left_from_rest_thighs": xyz(left),
            "original_glTF_up": "+Y", "imported_Blender_up": "+Z",
            "linear_unit": "metres", "scene_scale_length": scene.unit_settings.scale_length,
            "matrix_convention": "4x4 nested row-major; transform column vectors; translation in column 3",
        },
    }
    reference_path = OUT / "donor_reference.json"
    reference_path.write_text(json.dumps(reference, ensure_ascii=False, indent=2), encoding="utf-8")
    manifest = {
        "purpose": "Production donor input for video-guided M-07 V19 authoring; no claim of video matching or M-07 visual acceptance",
        "source": str(SOURCE), "source_manifest": str(SOURCE_ROOT / "source_manifest.json"),
        "source_license": provenance["animation_license"],
        "license_file": str(SOURCE_ROOT / "sources/LICENSE-CC0.MD"),
        "repository": provenance["animation_repository"], "commit": provenance["commit"],
        "source_download_url": source_entry["url"],
        "recorded_source_sha256": source_entry["sha256"],
        "reference_file": str(reference_path),
        "sample_fps": FPS,
        "units": "metres in Blender world space",
        "source_motion_usage": "Complete mature Walk and Jog spans; Sprint retained only as an optional donor. These are not the referenced Yummy Games motion files.",
        "clips": {},
    }
    for clip in CLIPS:
        action = locate_action(clip)
        activate(rig, action)
        metadata = animation_metadata(document, binary, clip)
        action_start, action_end = (float(value) for value in action.frame_range)
        duration = metadata["source_duration_seconds"]
        count = int(math.floor(duration * FPS + 1e-5))
        times = [index / FPS for index in range(count + 1)]
        if abs(times[-1] - duration) <= 1e-5:
            times[-1] = duration
        else:
            times.append(duration)
        samples = []
        for index, time in enumerate(times):
            source_frame = action_start + time * FPS
            scene.frame_set(math.floor(source_frame), subframe=source_frame % 1.0)
            bpy.context.view_layer.update()
            evaluated = rig.evaluated_get(bpy.context.evaluated_depsgraph_get())
            world = evaluated.matrix_world
            samples.append({
                "index": index, "time_seconds": time,
                "phase": time / duration if duration else 0.0,
                "source_blender_frame": source_frame,
                "object_matrix_world": matrix_rows(world),
                "world_matrices": {bone.name: matrix_rows(world @ evaluated.pose.bones[bone.name].matrix)
                                   for bone in ordered},
            })
        support = support_trajectories(samples, forward, up)
        cache = {
            "clip": clip, "blender_action_name": action.name,
            **metadata,
            "source_fps": metadata["source_key_sample_fps_inferred"],
            "sample_fps": FPS,
            "source_action_frame_range": [action_start, action_end],
            "imported_blender_fps": scene.render.fps / scene.render.fps_base,
            "sample_count": len(samples),
            "complete_cycle_span": "Full named source action, including original first and last samples; source loop endpoints have not been changed",
            "reference_file": str(reference_path),
            "role_to_source_bone": role_map,
            "source_bone_to_role": bone_to_role,
            "world_axes": reference["world_axes"],
            "samples": samples,
            "foot_support_trajectories": support,
        }
        cache_path = OUT / (clip + "_world_30fps.json")
        cache_path.write_text(json.dumps(cache, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
        manifest["clips"][clip] = {
            "cache": str(cache_path), "action": action.name,
            "sample_count": len(samples), "duration_seconds": duration,
            "source_fps_inferred": metadata["source_key_sample_fps_inferred"],
            "source_frame_range": [action_start, action_end],
        }
        print(f"M07_V19_DONOR_CACHED {clip} {len(samples)} samples {duration:.6f}s {cache_path}", flush=True)
    (OUT / "donor_cache_manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"M07_V19_DONOR_MANIFEST {OUT / 'donor_cache_manifest.json'}", flush=True)


if __name__ == "__main__":
    main()
