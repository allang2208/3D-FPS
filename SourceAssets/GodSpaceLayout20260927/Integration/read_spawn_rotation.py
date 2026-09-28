import unreal as u,json
from pathlib import Path
e=u.get_editor_subsystem(u.UnrealEditorSubsystem);g=e.get_game_world();ew=e.get_editor_world();data={}
def tr(c):return {'name':c.get_name(),'world':str(c.get_world_transform()),'relative_rotation':str(c.relative_rotation)}
if g:
    p=u.GameplayStatics.get_player_character(g,0)
    data['pawn']={'transform':str(p.get_actor_transform()),'control_rotation':str(p.get_control_rotation()),'components':[tr(c) for c in p.get_components_by_class(u.SceneComponent) if c.get_name() in ['CollisionCylinder','StairVisualRoot','FirstPersonCamera']]}
data['starts']=[{'transform':str(a.get_actor_transform()),'label':a.get_actor_label()} for a in u.GameplayStatics.get_all_actors_of_class(ew,u.PlayerStart)]
data['constructor_positional']=str(u.Rotator(0,45,0));data['constructor_named']=str(u.Rotator(pitch=0,yaw=45,roll=0))
data['architecture']=[{'label':a.get_actor_label(),'rotation':str(a.get_actor_rotation())} for a in u.GameplayStatics.get_all_actors_of_class(ew,u.Actor) if a.get_actor_label() in ['GodSpace_HillsPortalAnchor','GodSpace_WarehouseAnchor','GodSpace_ExpeditionAltar']]
(Path(__file__).parent/'SpawnRepair/rotation-cause.json').write_text(json.dumps(data,indent=2))
print(json.dumps(data))
