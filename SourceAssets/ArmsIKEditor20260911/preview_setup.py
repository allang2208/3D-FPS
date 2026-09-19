import unreal,json,runpy
from pathlib import Path
O=Path(__file__).parent
E=unreal.LevelSequenceEditorBlueprintLibrary
seq=E.get_current_level_sequence()
assert seq.get_name()=='LS_M4_Vertical_Idle_IK_Edit'
A=unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
rig=unreal.ControlRigSequencerLibrary.get_control_rigs(seq)[0].control_rig
comp=rig.get_bound_actor() if hasattr(rig,'get_bound_actor') else None
objects=[]
for binding in seq.get_bindings():
 bid=unreal.MovieSceneObjectBindingID();bid.set_editor_property('guid',binding.get_id())
 objects.extend(E.get_bound_objects(bid))
actors=[x for x in objects if isinstance(x,unreal.SkeletalMeshActor)]
assert len(actors)==1,objects
actor=actors[0];A.set_selected_level_actors([actor])
runpy.run_path('D:/FPS3D/FPSGAME/Tools/AssetPipeline/preview_vertical_grip.py',run_name='__main__')
center=actor.skeletal_mesh_component.get_socket_location('hand_l')
camera=center+unreal.Vector(80,-100,35)
unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).set_level_viewport_camera_info(camera,unreal.MathLibrary.find_look_at_rotation(camera,center))
(O/'preview_probe.json').write_text(json.dumps({'center':center.to_tuple(),'attach_docs':unreal.MovieScene3DAttachSection.__doc__},indent=2))
