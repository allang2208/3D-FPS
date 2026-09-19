import unreal
E=unreal.LevelSequenceEditorBlueprintLibrary
seq=E.get_current_level_sequence();assert seq.get_name()=='LS_M4_Vertical_Idle_IK_Edit'
A=unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
grip=A.spawn_actor_from_class(unreal.StaticMeshActor,unreal.Vector(),transient=True)
assert grip
grip.static_mesh_component.set_mobility(unreal.ComponentMobility.MOVABLE)
grip.static_mesh_component.set_static_mesh(unreal.load_asset('/Game/Weapons/M4VerticalGripCompact75/SM_VerticalForegrip'))
mod=unreal.SkeletonModifier();assert mod.set_skeletal_mesh(unreal.load_asset('/Game/Weapons/M4HK416Replica/SK_M4_FoldingSights_HK416'))
root=mod.get_bone_transform('WPN_root',True);rear=mod.get_bone_transform('WPN_RearSight',True);front=mod.get_bone_transform('WPN_FrontSight',True)
forward=(front.translation-rear.translation).normal();up=rear.rotation.rotate_vector(unreal.Vector(0,0,1))
mount=unreal.Transform(location=rear.translation+forward*27-up*8.05,rotation=unreal.MathLibrary.make_rot_from_xz(forward,up),scale=[1,1,1])
relative=unreal.MathLibrary.make_relative_transform(mount,root)
arm=next(b for b in seq.get_bindings() if any(isinstance(t,unreal.MovieSceneControlRigParameterTrack) for t in b.get_tracks()))
comp=grip.static_mesh_component
p=relative.translation;r=relative.rotation.rotator();s=relative.scale3d
binding=seq.add_spawnable_from_instance(grip);binding.set_name('Vertical Grip - Exact Game Mount')
spawn=binding.add_track(unreal.MovieSceneSpawnTrack).add_section();spawn.set_range(0,360)
for ch in spawn.get_all_channels():ch.set_default(True)
attach=binding.add_track(unreal.MovieScene3DAttachTrack).add_section();attach.set_range(0,360)
bid=unreal.MovieSceneObjectBindingID();bid.set_editor_property('guid',arm.get_id());attach.set_constraint_binding_id(bid)
attach.set_editor_property('attach_socket_name','WPN_root')
for prop in ['attachment_location_rule','attachment_rotation_rule','attachment_scale_rule']:attach.set_editor_property(prop,unreal.AttachmentRule.KEEP_RELATIVE)
section=binding.add_track(unreal.MovieScene3DTransformTrack).add_section();section.set_range(0,360)
for ch,v in zip(section.get_all_channels(),[p.x,p.y,p.z,r.roll,r.pitch,r.yaw,s.x,s.y,s.z]):ch.set_default(v)
A.destroy_actor(grip)
E.refresh_current_level_sequence();E.set_current_time(1)
assert unreal.EditorAssetLibrary.save_loaded_asset(seq,False)
