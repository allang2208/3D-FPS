import bpy
import json
from pathlib import Path
from mathutils import Matrix, Vector

SOURCE = Path(r"E:\3d\akm-classic-staging\akm-classic-unified.blend")
OUT_DIR = Path(r"D:\FPS3D\FPSGAME\SourceAssets\AKM")
BLEND_OUT = OUT_DIR / "SK_AKM_Viewmodel_Source.blend"
MESH_FBX = OUT_DIR / "SK_AKM_Viewmodel.fbx"
REPORT_OUT = OUT_DIR / "akm_ue_export_report.json"
CLIPS = ("idle", "aim", "fire", "aim_fire", "reload", "reload_empty", "draw", "holster", "inspect")


def action_slot_for(action, object_name):
    wanted = f"OB{object_name}"
    for slot in action.slots:
        if slot.identifier == wanted:
            return slot
    raise RuntimeError(f"Action {action.name} has no slot for {object_name}")


def assign_source_action(obj, action):
    if obj.animation_data is None:
        obj.animation_data_create()
    obj.animation_data.action = action
    obj.animation_data.action_slot = action_slot_for(action, obj.name)


def build_combined_rig(source_rigs):
    rig_data = bpy.data.armatures.new("SK_AKM_Viewmodel_Skeleton")
    rig = bpy.data.objects.new("SK_AKM_Viewmodel", rig_data)
    bpy.context.collection.objects.link(rig)
    # Keep the source armature object transform (notably its 0.01 scale).
    # Edit bones cannot faithfully absorb object-level scale into their rest
    # matrices, so baking everything into world space breaks skinning.
    rig.matrix_world = source_rigs[0].matrix_world.copy()
    target_from_world = rig.matrix_world.inverted()
    bpy.context.view_layer.objects.active = rig
    rig.select_set(True)
    bpy.ops.object.mode_set(mode="EDIT")

    vm_root = rig.data.edit_bones.new("VM_Root")
    vm_root.head = Vector((0.0, 0.0, 0.0))
    vm_root.tail = Vector((0.0, 0.0, 5.0))
    name_maps = {}

    for source in source_rigs:
        prefix = "" if source.name == "ArmsRig" else "WPN_"
        name_map = {bone.name: f"{prefix}{bone.name}" for bone in source.data.bones}
        name_maps[source.name] = name_map
        for bone in source.data.bones:
            edit_bone = rig.data.edit_bones.new(name_map[bone.name])
            source_to_target = target_from_world @ source.matrix_world
            edit_bone.head = source_to_target @ bone.head_local
            edit_bone.tail = source_to_target @ bone.tail_local
            if edit_bone.length < 0.25:
                edit_bone.tail = edit_bone.head + Vector((0.0, 0.25, 0.0))
            source_z = bone.matrix_local.to_3x3().col[2]
            edit_bone.align_roll((source_to_target.to_3x3() @ source_z).normalized())
            edit_bone.use_deform = bone.use_deform
        for bone in source.data.bones:
            edit_bone = rig.data.edit_bones[name_map[bone.name]]
            edit_bone.parent = rig.data.edit_bones[name_map[bone.parent.name]] if bone.parent else vm_root
            edit_bone.use_connect = False

    bpy.ops.object.mode_set(mode="OBJECT")
    rig.select_set(False)
    return rig, name_maps


def duplicate_bound_meshes(source_rigs, target_rig, name_maps):
    exported = []
    for obj in list(bpy.data.objects):
        if obj.type != "MESH":
            continue
        source_rig = None
        preserve_volume = False
        for modifier in obj.modifiers:
            if modifier.type == "ARMATURE" and modifier.object in source_rigs:
                source_rig = modifier.object
                preserve_volume = modifier.use_deform_preserve_volume
                break
        if source_rig is None:
            continue

        duplicate = obj.copy()
        duplicate.data = obj.data.copy()
        duplicate.name = obj.name
        bpy.context.collection.objects.link(duplicate)
        world = obj.matrix_world.copy()
        duplicate.parent = target_rig
        duplicate.matrix_world = world

        for modifier in list(duplicate.modifiers):
            if modifier.type == "ARMATURE":
                duplicate.modifiers.remove(modifier)
        modifier = duplicate.modifiers.new(name="Armature", type="ARMATURE")
        modifier.object = target_rig
        modifier.use_deform_preserve_volume = preserve_volume

        mapping = name_maps[source_rig.name]
        for group in duplicate.vertex_groups:
            if group.name in mapping:
                group.name = mapping[group.name]
        exported.append(duplicate)

        obj.hide_set(True)
        obj.hide_render = True
    return exported


def bake_action(target_rig, source_rigs, name_maps, source_action):
    for source in source_rigs:
        assign_source_action(source, source_action)
    frame_start = int(round(source_action.frame_range[0]))
    frame_end = int(round(source_action.frame_range[1]))

    action = bpy.data.actions.new(f"AKM_{source_action.name}")
    slot = action.slots.new(id_type="OBJECT", name=target_rig.name)
    target_rig.animation_data_create()
    target_rig.animation_data.action = action
    target_rig.animation_data.action_slot = slot

    for pose_bone in target_rig.pose.bones:
        pose_bone.rotation_mode = "QUATERNION"
        pose_bone.matrix_basis = Matrix.Identity(4)
    bpy.context.view_layer.update()

    for frame in range(frame_start, frame_end + 1):
        bpy.context.scene.frame_set(frame)
        bpy.context.view_layer.update()
        sampled = {}
        target_from_world = target_rig.matrix_world.inverted()
        for source in source_rigs:
            for pose_bone in source.pose.bones:
                sampled[name_maps[source.name][pose_bone.name]] = (
                    target_from_world @ source.matrix_world @ pose_bone.matrix
                )
        # Convert the desired armature-space pose to matrix_basis explicitly.
        # Assigning PoseBone.matrix in data-bone order is parent-order dependent
        # and caused the two-frame idle/aim poses to become singular.
        for pose_bone in target_rig.pose.bones:
            if pose_bone.name == "VM_Root":
                pose_bone.matrix_basis = Matrix.Identity(4)
                continue
            parent = pose_bone.parent
            if parent.name == "VM_Root":
                parent_matrix = parent.bone.matrix_local
            else:
                parent_matrix = sampled[parent.name]
            pose_bone.matrix_basis = pose_bone.bone.convert_local_to_pose(
                sampled[pose_bone.name],
                pose_bone.bone.matrix_local,
                parent_matrix=parent_matrix,
                parent_matrix_local=parent.bone.matrix_local,
                invert=True,
            )
        bpy.context.view_layer.update()
        for pose_bone in target_rig.pose.bones:
            pose_bone.keyframe_insert("location", frame=frame, group=pose_bone.name)
            pose_bone.keyframe_insert("rotation_quaternion", frame=frame, group=pose_bone.name)
            pose_bone.keyframe_insert("scale", frame=frame, group=pose_bone.name)

    action.use_fake_user = True
    return action, frame_start, frame_end


def select_only(objects):
    bpy.ops.object.select_all(action="DESELECT")
    for obj in objects:
        obj.hide_set(False)
        obj.select_set(True)
    bpy.context.view_layer.objects.active = objects[0]


def export_fbx(path, rig, meshes, bake_anim, all_actions=False):
    select_only([rig, *meshes])
    bpy.ops.export_scene.fbx(
        filepath=str(path),
        use_selection=True,
        object_types={"ARMATURE", "MESH"},
        apply_scale_options="FBX_SCALE_ALL",
        apply_unit_scale=True,
        use_space_transform=True,
        axis_forward="-Y",
        axis_up="Z",
        add_leaf_bones=False,
        use_armature_deform_only=False,
        bake_anim=bake_anim,
        bake_anim_use_all_bones=True,
        bake_anim_use_nla_strips=False,
        bake_anim_use_all_actions=all_actions,
        bake_anim_force_startend_keying=True,
        bake_anim_step=1.0,
        bake_anim_simplify_factor=0.0,
        path_mode="COPY",
        embed_textures=True,
        mesh_smooth_type="FACE",
        use_tspace=True,
    )


OUT_DIR.mkdir(parents=True, exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=str(SOURCE))
bpy.context.scene.render.fps = 24
source_rigs = [bpy.data.objects["ArmsRig"], bpy.data.objects["WeaponRig"]]
for source in source_rigs:
    if source.animation_data:
        for track in source.animation_data.nla_tracks:
            track.mute = True

target_rig, name_maps = build_combined_rig(source_rigs)
meshes = duplicate_bound_meshes(source_rigs, target_rig, name_maps)

baked = []
for clip_name in CLIPS:
    source_action = bpy.data.actions[clip_name]
    action, frame_start, frame_end = bake_action(target_rig, source_rigs, name_maps, source_action)
    baked.append({
        "source": clip_name,
        "action": action.name,
        "frame_start": frame_start,
        "frame_end": frame_end,
        "duration_seconds": (frame_end - frame_start) / bpy.context.scene.render.fps,
    })

target_rig.animation_data.action = bpy.data.actions["AKM_idle"]
bpy.context.scene.frame_start = 1
bpy.context.scene.frame_end = 2
bpy.context.scene.frame_set(1)

for source in source_rigs:
    source.hide_set(True)
    source.hide_render = True

bpy.ops.wm.save_as_mainfile(filepath=str(BLEND_OUT))
export_fbx(MESH_FBX, target_rig, meshes, bake_anim=False)

for clip in baked:
    action = bpy.data.actions[clip["action"]]
    target_rig.animation_data.action = action
    target_rig.animation_data.action_slot = action.slots[0]
    bpy.context.scene.frame_start = clip["frame_start"]
    bpy.context.scene.frame_end = clip["frame_end"]
    animation_path = OUT_DIR / f"A_AKM_{clip['source']}.fbx"
    export_fbx(animation_path, target_rig, [], bake_anim=True, all_actions=False)
    clip["fbx"] = str(animation_path)

report = {
    "source": str(SOURCE),
    "blend": str(BLEND_OUT),
    "mesh_fbx": str(MESH_FBX),
    "fps": bpy.context.scene.render.fps,
    "rig": target_rig.name,
    "bone_count": len(target_rig.data.bones),
    "root_bones": [bone.name for bone in target_rig.data.bones if bone.parent is None],
    "meshes": [{"name": obj.name, "vertices": len(obj.data.vertices), "polygons": len(obj.data.polygons)} for obj in meshes],
    "clips": baked,
    "socket_bones": [name for name in target_rig.data.bones.keys() if "SOCKET_" in name or name in {"RearSight", "FrontSight"}],
}
REPORT_OUT.write_text(json.dumps(report, indent=2), encoding="utf-8")
print(json.dumps(report, indent=2))
