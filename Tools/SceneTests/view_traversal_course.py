import unreal
api=unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
# Hide the existing oversized editor-only title for this inspection only.
for a in api.get_all_level_actors():
 if a.get_actor_label()=='TextRenderActor': a.set_is_temporarily_hidden_in_editor(True)
eye=unreal.Vector(250,150,500)
unreal.EditorLevelLibrary.set_level_viewport_camera_info(eye,unreal.MathLibrary.find_look_at_rotation(eye,unreal.Vector(1150,1100,75)))
