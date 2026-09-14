"""Write one complete reference pose for the multipart skin and animation FBXs.

Blender's individual mesh poses omit the other meshes driven by the same bones.
The complete pose preserves the authored rest transforms for UE's FBX importer.
This patches only the current Blender export process, not the installed add-on.
"""
from io_scene_fbx import export_fbx_bin as fbx


def install():
    original = fbx.fbx_data_armature_elements

    def with_complete_pose(root, arm_obj, scene_data):
        original(root, arm_obj, scene_data)
        bones = [bone for bone in arm_obj.bones if bone in scene_data.objects]
        deformers = scene_data.data_deformers_skin.get(arm_obj, {})
        meshes = [entry[1] for entry in deformers.values()]
        objects = [arm_obj] + bones + meshes
        key = fbx.get_blender_bindpose_key(arm_obj.bdata, arm_obj.bdata)
        pose = fbx.elem_data_single_int64(root, b"Pose", fbx.get_fbx_uuid_from_key(key))
        pose.add_string(fbx.fbx_name_class(b"DW715_CompleteReference", b"Pose"))
        pose.add_string(b"BindPose")
        fbx.elem_data_single_string(pose, b"Type", b"BindPose")
        fbx.elem_data_single_int32(pose, b"Version", fbx.FBX_POSE_BIND_VERSION)
        fbx.elem_data_single_int32(pose, b"NbPoseNodes", len(objects))
        for obj in objects:
            matrix = obj.fbx_object_matrix(scene_data, rest=obj in bones, global_space=True)
            node = fbx.elem_empty(pose, b"PoseNode")
            fbx.elem_data_single_int64(node, b"Node", obj.fbx_uuid)
            fbx.elem_data_single_float64_array(node, b"Matrix", fbx.matrix4_to_array(matrix))

    fbx.fbx_data_armature_elements = with_complete_pose
