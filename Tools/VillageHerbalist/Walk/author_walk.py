"""Fit Mesh2Motion's unarmed walk to Lin Zhi's own legs, feet and relaxed arms."""
import json
import sys
from pathlib import Path

import numpy as np
from scipy.spatial.transform import Rotation


PROJECT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(PROJECT / "Tools/VillageTavernKeeper/Idle"))
from retarget_idle import body_frame, forward_kinematics, rotation, swing, unit

DONOR = PROJECT / "SourceAssets/BlindSupplicantM07Meshy20261001/VideoLocomotionV19/Donor"
RIG = PROJECT / "SourceAssets/VillageHerbalist/FullBody/UEAuthoringR1"
SPEED = 60.0  # Centimetres per second at play rate one.


def smooth(start, end, x):
    t = np.clip((x - start) / (end - start), 0, 1)
    return t * t * (3 - 2 * t)


def mix(a, b, t):
    return a + (b - a) * t


def fit_walk():
    read = lambda path: json.loads(path.read_text(encoding="utf-8"))
    reference = read(RIG / "idle_reference.json")
    idle = read(RIG / "idle_motion.json")
    clip = read(DONOR / "Walk_world_30fps.json")
    source_ref = {k: np.array(v) for k, v in read(DONOR / "donor_reference.json")["bone_world_rest_matrices"].items()}
    samples = [{k: np.array(v) for k, v in row["world_matrices"].items()} for row in clip["samples"][:-1]]
    count, rate = len(samples), clip["sample_fps"]
    duration = count / rate
    names, parents = reference["names"], reference["parents"]
    indices = {name: i for i, name in enumerate(names)}
    native = np.array(reference["reference"])
    rest = forward_kinematics(native, parents)
    relaxed = forward_kinematics(np.array([idle["tracks"].get(n, [row])[0] for n, row in zip(names, native)]), parents)
    across, forward, up = body_frame(rest[:, :3, 3], indices["upperarm_l"], indices["upperarm_r"],
                                    [indices["foot_l"], indices["foot_r"]], [indices["ball_l"], indices["ball_r"]]).T
    axes = clip["world_axes"]
    to_target = (np.array([across, forward, up]).T
                 @ np.array([axes["character_left_from_rest_thighs"], axes["forward_from_rest_ankle_to_toe"], axes["up"]]))

    def delta(source_rot, amount):
        return Rotation.from_matrix(to_target @ Rotation.from_rotvec(source_rot.as_rotvec() * amount).as_matrix() @ to_target.T)

    pelvis = indices["pelvis"]
    upper = [n for n in names if n in source_ref and not n.startswith(("thigh_", "calf_", "foot_", "ball_"))]
    mean = {n: Rotation.from_quat([rotation(s[n]).as_quat() for s in samples]).mean() for n in upper}
    pelvis_pos = np.array([s["pelvis"][:3, 3] for s in samples])
    pelvis_center = pelvis_pos.mean(axis=0)
    pelvis_center[2] = pelvis_pos[:, 2].max()

    # The low, backward-moving ball of the donor foot identifies the flat
    # support speed independently of its swing arc or the character's height.
    support_speeds = []
    for side in ("l", "r"):
        toes = np.array([s[f"ball_{side}"][:3, 3] for s in samples])
        speed = -np.diff(toes, axis=0) @ axes["forward_from_rest_ankle_to_toe"] * rate
        support_speeds.extend(speed[(toes[:-1, 2] < toes[:, 2].min() + .014) & (speed > .1)])
    step_scale = SPEED / np.median(support_speeds)
    legs = {}
    for side, heel_time in (("l", 0), ("r", count // 2)):
        thigh, calf, foot, toe = (f"{part}_{side}" for part in ("thigh", "calf", "foot", "ball"))
        joint, knee, ankle, ball = (rest[indices[n], :3, 3] for n in (thigh, calf, foot, toe))
        heel_offset = -forward * 4. - up * ankle[2]
        toe_offset = forward * 3. - up * ball[2]
        foot_rot, toe_rot, swing_targets, offsets = [], [], [], []
        origin = np.mean([s[foot][:3, 3] for s in samples], axis=0)
        for sample in samples:
            fd = delta(rotation(sample[foot]) * rotation(source_ref[foot]).inv(), .75)
            td = delta(rotation(sample[toe]) * rotation(source_ref[toe]).inv(), .75)
            foot_rot.append(fd * rotation(rest[indices[foot]]))
            toe_rot.append(td * rotation(rest[indices[toe]]))
            heel = fd.apply(heel_offset)
            tip = fd.apply(ball - ankle) + td.apply(toe_offset)
            offsets.append((heel, tip))
            target = ankle + to_target @ (sample[foot][:3, 3] - origin) * step_scale
            swing_targets.append(target)
        # Ground-space heel and forefoot anchors stay fixed while the body
        # advances. During rollover, the toes get the ground anchor.
        heel_anchor = swing_targets[heel_time] + offsets[heel_time][0]
        heel_anchor[2] = 0.
        flat = (heel_time + round(.18 * count)) % count
        toe_anchor = heel_anchor + offsets[flat][1] - offsets[flat][0]
        toe_anchor[2] = 0.
        lowest_toe = min(s[toe][2, 3] for s in samples)
        lowest_heel = min(s[foot][2, 3] for s in samples)
        for i, sample in enumerate(samples):
            phase = ((i - heel_time) % count) / count
            # Use the following heel strike on the approach to the ground.
            stance_phase = phase if phase < .8 else phase - 1.
            heel, tip = offsets[i]
            heel_target = heel_anchor - heel - forward * (SPEED * duration * stance_phase)
            toe_target = toe_anchor - tip - forward * (SPEED * duration * stance_phase)
            grounded = mix(heel_target, toe_target, smooth(.07, .23, stance_phase))
            grounded[2] = -min(heel[2], tip[2])
            foot_clearance = min(sample[toe][2, 3] - lowest_toe, sample[foot][2, 3] - lowest_heel)
            airborne = swing_targets[i]
            airborne[2] = grounded[2] + max(0., foot_clearance) * 53.
            swing_weight = smooth(.55, .69, phase) * (1. - smooth(.87, 1., phase))
            swing_targets[i] = mix(grounded, airborne, swing_weight)
        lengths = (np.linalg.norm(knee - joint), np.linalg.norm(ankle - knee))
        legs[side] = (thigh, calf, foot, toe, lengths, foot_rot, toe_rot, swing_targets)

    frames = []
    for index, sample in enumerate(samples):
        frame = native.copy()
        sway = to_target @ (pelvis_pos[index] - pelvis_center)
        frame[pelvis, :3] += across * np.dot(sway, across) * 45. + forward * np.dot(sway, forward) * 45.
        frame[pelvis, 2] += sway[2] * 60. - 1.4
        world = forward_kinematics(frame, parents)

        def set_rotation(name, desired):
            i = indices[name]
            parent = parents[i]
            frame[i, 3:7] = ((rotation(world[parent]).inv() * desired) if parent >= 0 else desired).as_quat()
            return forward_kinematics(frame, parents)

        for name in upper:
            # A low-amplitude swing around her existing idle preserves her
            # hand clearance and avoids importing the donor's bind pose.
            strength = .67 if name.startswith(("upperarm", "lowerarm", "hand")) else .5
            relative = rotation(sample[name]) * mean[name].inv()
            world = set_rotation(name, delta(relative, strength) * rotation(relaxed[indices[name]]))

        # Both feet share a pelvis, so lower it once if either contact would
        # otherwise demand a straightened leg beyond its actual bone length.
        lower = 0.
        for thigh, _, _, _, lengths, _, _, targets in legs.values():
            hip = world[indices[thigh], :3, 3]
            vector = hip - targets[index]
            reach = sum(lengths) - .25
            lower = max(lower, vector[2] - np.sqrt(max(0., reach**2 - vector[:2] @ vector[:2])))
        frame[pelvis, 2] -= lower
        world = forward_kinematics(frame, parents)
        for thigh, calf, foot, toe, (shin, shank), foot_rot, toe_rot, targets in legs.values():
            hip = world[indices[thigh], :3, 3]
            target = targets[index]
            direction = unit(target - hip)
            distance = np.linalg.norm(target - hip)
            along = (shin**2 - shank**2 + distance**2) / (2 * distance)
            bend = np.sqrt(max(0., shin**2 - along**2))
            source_axis = unit(sample[foot][:3, 3] - sample[thigh][:3, 3])
            source_knee = sample[calf][:3, 3] - sample[thigh][:3, 3]
            pole = to_target @ (source_knee - np.dot(source_knee, source_axis) * source_axis)
            pole = forward + .22 * unit(pole)
            knee_target = hip + direction * along + unit(pole - np.dot(pole, direction) * direction) * bend
            for name, child, goal in ((thigh, calf, knee_target), (calf, foot, target)):
                origin = world[indices[name], :3, 3]
                aim = swing(world[indices[child], :3, 3] - origin, goal - origin)
                world = set_rotation(name, aim * rotation(world[indices[name]]))
            world = set_rotation(foot, foot_rot[index])
            world = set_rotation(toe, toe_rot[index])
        frames.append(frame)
    tracks = {}
    for i, name in enumerate(names):
        keys = np.array([f[i] for f in [*frames, frames[0]]])
        for a, b in zip(keys, keys[1:]):
            if a[3:7] @ b[3:7] < 0:
                b[3:7] *= -1
        tracks[name] = (keys[:1] if np.allclose(keys, keys[0], atol=1e-6) else keys).round(8).tolist()
    return dict(rate=rate, frames=count, duration=duration, speed_cm_s=SPEED, stride_cm=duration*SPEED,
                contacts={"LeftFoot": 0., "RightFoot": duration/2.}, source="Mesh2Motion CC0 Walk",
                tracks=tracks)


if __name__ == "__main__":
    result = fit_walk()
    Path(sys.argv[1]).write_text(json.dumps(result, separators=(",", ":")), encoding="utf-8")
