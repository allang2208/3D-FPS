import unreal as u,json
from pathlib import Path
R=Path(__file__).parent/'SpawnRepair'
e=u.get_editor_subsystem(u.UnrealEditorSubsystem)
g=e.get_game_world();w=g or e.get_editor_world()
def v(p):return [p.x,p.y,p.z]
data={'world':str(w),'game':bool(g),'dirty_maps':[p.get_path_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_map_packages()]}
pawn=u.GameplayStatics.get_player_character(g,0) if g else None
if pawn:
    data['pawn']={'name':pawn.get_name(),'location':v(pawn.get_actor_location()),'scale':v(pawn.get_actor_scale3d()),'velocity':v(pawn.get_velocity()),'components':[]}
    for c in pawn.get_components_by_class(u.SceneComponent):
        if isinstance(c,(u.CameraComponent,u.CapsuleComponent)) or c.get_name()=='StairVisualRoot':
            data['pawn']['components'].append({'name':c.get_name(),'location':v(c.get_world_location()),'relative':v(c.relative_location),'scale':v(c.get_world_scale())})
    mv=pawn.get_component_by_class(u.CharacterMovementComponent);data['pawn']['movement_mode']=str(mv.movement_mode)
    data['pawn']['floor']=str(mv.get_editor_property('current_floor'))
    cap=pawn.get_component_by_class(u.CapsuleComponent)
    data['pawn']['capsule_half_height']=cap.get_scaled_capsule_half_height()
data['static_components']=[]
for a in u.GameplayStatics.get_all_actors_of_class(w,u.Actor):
    for c in a.get_components_by_class(u.StaticMeshComponent):
        m=c.static_mesh
        if not m:continue
        b=m.get_bounding_box();t=c.get_world_transform();center=t.transform_location((b.min+b.max)*.5);ex=(b.max-b.min)*.5*c.get_world_scale()
        if abs(center.x+1100)>abs(ex.x)+500 or abs(center.y+5100)>abs(ex.y)+500:continue
        data['static_components'].append({'actor':a.get_name(),'label':a.get_actor_label(),'component':c.get_name(),'mesh':m.get_path_name(),'location':v(c.get_world_location()),'bounds':[v(b.min),v(b.max)],'world_center':v(center),'world_extent':v(ex),'collision':str(c.get_collision_enabled()),'visible':c.is_visible()})
(R/'live-spawn-issue.json').write_text(json.dumps(data,indent=2),encoding='utf8')
print(json.dumps(data,ensure_ascii=False))
