import unreal,json
from pathlib import Path
E=unreal.LevelSequenceEditorBlueprintLibrary;seq=E.get_current_level_sequence()
out=[];actors=[]
for b in seq.get_bindings():
 bid=unreal.MovieSceneObjectBindingID();bid.set_editor_property('guid',b.get_id())
 for obj in E.get_bound_objects(bid):
  if not isinstance(obj,unreal.Actor):continue
  actors.append(obj)
  out.append({'binding':str(b.get_name()),'actor':obj.get_path_name(),'location':obj.get_actor_location().to_tuple(),'parent':str(obj.get_attach_parent_actor()),'socket':str(obj.get_attach_parent_socket_name())})
unreal.get_editor_subsystem(unreal.EditorActorSubsystem).set_selected_level_actors([x for x in actors if isinstance(x,unreal.SkeletalMeshActor)])
rig=unreal.ControlRigSequencerLibrary.get_control_rigs(seq)[0].control_rig
rig.clear_control_selection();rig.select_control('hand_l_ik_ctrl',True)
center=next(x for x in actors if isinstance(x,unreal.SkeletalMeshActor)).skeletal_mesh_component.get_socket_location('hand_l')
cam=center+unreal.Vector(65,-65,25)
unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).set_level_viewport_camera_info(cam,unreal.MathLibrary.find_look_at_rotation(cam,center))
(Path(__file__).parent/'preview_check.json').write_text(json.dumps(out,indent=2))
