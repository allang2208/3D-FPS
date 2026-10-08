import unreal as u
cdo=u.get_default_object(u.load_asset('/Game/Monsters/BoundCongregate/BP_BoundCongregate').generated_class())
mesh=cdo.get_editor_property('visual_mesh');comp=cdo.get_editor_property('mesh')
print('mesh',mesh.get_bounds(),'component',comp.get_editor_property('relative_scale3d'))
options=u.AnimPoseEvaluationOptions();options.optional_skeletal_mesh=mesh
options.incorporate_root_motion_into_pose=False
for role in ('idle_clip','move_clip'):
    clip=cdo.get_editor_property(role)
    pose=u.AnimPoseExtensions.get_anim_pose_at_time(clip,0,options)
    for name in ('root','body','leg_L1_upper','leg_L1_lower','leg_L1_foot'):
        print(role,name,'pose',u.AnimPoseExtensions.get_bone_pose(pose,name,u.AnimPoseSpaces.WORLD),'ref',u.AnimPoseExtensions.get_ref_bone_pose(pose,name,u.AnimPoseSpaces.WORLD))
