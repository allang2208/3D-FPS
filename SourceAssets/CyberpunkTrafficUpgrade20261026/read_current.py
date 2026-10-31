from pathlib import Path
import unreal as u,json
R=Path(__file__).resolve().parent
editor=u.get_editor_subsystem(u.UnrealEditorSubsystem)
w=editor.get_editor_world()
level=u.get_editor_subsystem(u.LevelEditorSubsystem)
data=dict(world=w.get_path_name(),pie=level.is_in_play_in_editor(),actors=[],collections={})
for a in u.GameplayStatics.get_all_actors_of_class(w,u.Actor):
 if a.get_actor_label() in ['AP16_Traffic_Coupe','AP16_Traffic_Shuttle','AP16_Traffic_Freight']:
  c=a.static_mesh_component
  data['actors'].append(dict(label=a.get_actor_label(),mesh=c.static_mesh.get_path_name(),position=list(a.get_actor_location().to_tuple()),rotation=str(a.get_actor_rotation()),scale=list(a.get_actor_scale3d().to_tuple()),materials=[m.get_path_name() for m in c.get_materials()]))
for path in ['/Game/Weather/Materials/MPC_FPS_Weather','/Game/Props/CyberpunkApartmentRebuild20261022/RefinementV21/MPC_ApartmentClock']:
 asset=u.load_asset(path)
 if asset:data['collections'][path]=dict(scalars=[str(x.parameter_name) for x in asset.get_editor_property('scalar_parameters')],vectors=[str(x.parameter_name) for x in asset.get_editor_property('vector_parameters')])
(R/'current_scene.json').write_text(json.dumps(data,indent=2),encoding='utf8')
print(json.dumps(data))
