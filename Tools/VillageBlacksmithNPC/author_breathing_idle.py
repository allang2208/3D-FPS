"""Bake the smith's standing breath on his own Jason skeleton."""
import math
import unreal as ue


FOLDER = "/Game/Characters/VillageBlacksmithNPC20261118"
BASE = "/Game/Characters/JasonPlayer20261003/Animations/J_MM_Idle"
NAME = "A_Smith_StandingBreath"
RATE = 30
FRAME_COUNT = 12 * RATE

# Local offsets are specified in the standing mesh's anatomical axes.
# Values are peak rotation in degrees and peak rise in cm.
SPINE = {
    "spine_02": (0.055, 0.00),
    "spine_03": (0.11, 0.045),
    "spine_04": (0.20, 0.10),
    "spine_05": (0.16, 0.055),
}
MOVING = set(SPINE) | {"clavicle_l", "clavicle_r", "neck_01", "head"}


def turn(axis, degrees):
    half = math.radians(degrees) * 0.5
    s = math.sin(half)
    return ue.Quat(axis.x * s, axis.y * s, axis.z * s, math.cos(half))


def breathing_keys(name, rest, world):
    # Convert lateral and forward mesh axes to this bone's authored frame.
    right = world.rotation.unrotate_vector(ue.Vector(1, 0, 0))
    forward = world.rotation.unrotate_vector(ue.Vector(0, 1, 0))
    parent_rotation = world.rotation * rest.rotation.inversed()
    up = parent_rotation.unrotate_vector(ue.Vector(0, 0, 1))
    positions, rotations, scales = [], [], []
    for frame in range(FRAME_COUNT):
        phase = math.tau * frame / FRAME_COUNT
        breath = ((math.sin(3 * phase) + 0.14 * math.sin(6 * phase - 0.35))
                  * (1 + 0.06 * math.sin(phase + 0.6)))
        pitch = roll = rise = 0.0
        scale = rest.scale3d
        if name in SPINE:
            angle, height = SPINE[name]
            pitch, rise = angle * breath, height * breath
            if name == "spine_04":
                # Expand mostly through the depth of the rib cage.
                gain = 0.0035 * breath
                scale = ue.Vector(*(v * (1 + gain * (f*f + 0.40*r*r)) for v, f, r in zip(
                    (scale.x, scale.y, scale.z), (forward.x, forward.y, forward.z), (right.x, right.y, right.z))))
        elif name.startswith("clavicle"):
            shoulder = (math.sin(3 * phase - 0.12) + 0.10 * math.sin(6 * phase - 0.6))
            roll = (0.14 if name.endswith("_l") else -0.14) * shoulder
            rise = 0.055 * shoulder
        elif name == "neck_01":
            pitch = -0.16 * breath
        else:
            pitch = -0.055 * breath
            roll = 0.045 * math.sin(phase + 0.5)
        positions.append(rest.translation + up * rise)
        rotations.append(rest.rotation * turn(right, pitch) * turn(forward, roll))
        scales.append(scale)
    for keys in (positions, rotations, scales):
        keys.append(keys[0])
    return positions, rotations, scales


def author():
    body = ue.load_asset(FOLDER + "/SK_Smith_Body")
    idle = ue.load_asset(BASE)
    if not body or not idle or body.skeleton != idle.get_editor_property("skeleton"):
        raise RuntimeError("The smith and his standing pose require the same Jason skeleton")
    options = ue.AnimPoseEvaluationOptions()
    options.optional_skeletal_mesh = body
    options.evaluation_type = ue.AnimDataEvalType.RAW
    options.should_retarget = False
    pose = ue.AnimPoseExtensions.get_anim_pose_at_time(idle, 0.0, options)
    pose_names = {str(n) for n in ue.AnimPoseExtensions.get_bone_names(pose)}
    if not MOVING.issubset(pose_names):
        raise RuntimeError("Missing breathing bones: " + ", ".join(sorted(MOVING - pose_names)))
    tracks = {str(n) for n in ue.AnimationLibrary.get_animation_track_names(idle)} & pose_names
    if not {"pelvis", "foot_l", "foot_r"}.issubset(tracks):
        raise RuntimeError("Cannot sample the grounded Jason standing pose")

    folder = FOLDER + "/Animations"
    if ue.EditorAssetLibrary.does_asset_exist(folder + "/" + NAME):
        raise RuntimeError("Destination animation already exists")
    factory = ue.AnimSequenceFactory()
    factory.set_editor_property("target_skeleton", body.skeleton)
    factory.set_editor_property("preview_skeletal_mesh", body)
    clip = ue.AssetToolsHelpers.get_asset_tools().create_asset(NAME, folder, ue.AnimSequence, factory)
    ctl = clip.get_editor_property("controller")
    ctl.open_bracket("Blacksmith standing breath", False)
    try:
        ctl.set_frame_rate(ue.FrameRate(RATE, 1), False)
        ctl.set_number_of_frames(ue.FrameNumber(FRAME_COUNT), False)
        for name in sorted(tracks | MOVING):
            rest = ue.AnimPoseExtensions.get_bone_pose(pose, name, ue.AnimPoseSpaces.LOCAL)
            if name in MOVING:
                world = ue.AnimPoseExtensions.get_bone_pose(pose, name, ue.AnimPoseSpaces.WORLD)
                keys = breathing_keys(name, rest, world)
            else:
                keys = ([rest.translation], [rest.rotation], [rest.scale3d])
            ctl.add_bone_curve(name, False)
            if not ctl.set_bone_track_keys(name, *keys, False):
                raise RuntimeError("Cannot author " + name)
    finally:
        ctl.close_bracket(False)
    clip.set_editor_property("enable_root_motion", False)
    clip.set_editor_property("force_root_lock", True)
    clip.set_editor_property("root_motion_root_lock", ue.RootMotionRootLock.REF_POSE)
    if not ue.EditorAssetLibrary.save_loaded_asset(clip, False):
        raise RuntimeError("Could not save the blacksmith animation")
    ue.log("SMITH_BREATH_SAVED " + clip.get_path_name())


author()
