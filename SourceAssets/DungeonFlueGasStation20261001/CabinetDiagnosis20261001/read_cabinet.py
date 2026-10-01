"""Read current cabinet geometry/collision and the last traversal query; no mutations."""
import json
from pathlib import Path
import unreal as u

OUT=Path(__file__).resolve().parent
PATH='/Game/Dungeons/FacilityScenes20260927/Meshes/SM_Facility_PowerCabinet'
report={'asset':PATH,'errors':[]}
def vec(v):return [round(v.x,3),round(v.y,3),round(v.z,3)]
def attempt(key,fn):
    try:report[key]=fn()
    except Exception as e:report['errors'].append(key+': '+str(e))
mesh=u.load_asset(PATH)
attempt('mesh_bounds',lambda:str(mesh.get_bounds()))
body=mesh.get_editor_property('body_setup')
attempt('collision_trace_flag',lambda:str(body.get_editor_property('collision_trace_flag')))
def hulls():
    agg=body.get_editor_property('agg_geom');out=[]
    for hull in agg.get_editor_property('convex_elems'):
        points=[vec(v) for v in hull.get_editor_property('vertex_data')]
        out.append({'points':points})
    return out
attempt('convex_hulls',hulls)
world=u.get_editor_subsystem(u.UnrealEditorSubsystem).get_game_world()
if not world:world=u.get_editor_subsystem(u.UnrealEditorSubsystem).get_editor_world()
report['world']=world.get_path_name() if world else None
if world:
    actors=[]
    for a in u.GameplayStatics.get_all_actors_of_class(world,u.StaticMeshActor):
        c=a.static_mesh_component
        if c.static_mesh==mesh:
            actors.append({'path':a.get_path_name(),'location':vec(a.get_actor_location()),
                'transform':str(a.get_actor_transform()),'local_bounds':str(c.get_local_bounds()),
                'profile':str(c.get_collision_profile_name()),'collision':str(c.get_collision_enabled()),
                'pawn_response':str(c.get_collision_response_to_channel(u.CollisionChannel.ECC_PAWN)),
                'actor_tags':[str(t) for t in a.tags]})
    report['actors']=actors
    player=u.GameplayStatics.get_player_character(world,0)
    if player:
        capsule=player.get_capsule_component()
        report['player']={'path':player.get_path_name(),'location':vec(player.get_actor_location()),
            'radius':capsule.get_scaled_capsule_radius(),'half_height':capsule.get_scaled_capsule_half_height(),
            'profile':str(capsule.get_collision_profile_name()),'view':str(player.get_control_rotation())}
        traversal=player.get_component_by_class(u.FPSTraversalComponent)
        if traversal:
            attempt('last_jump_target',lambda:str(traversal.get_editor_property('last_jump_target')))
            attempt('current_target',lambda:str(traversal.find_target(True,True)))
report['line_trace_api']=u.SystemLibrary.line_trace_single_by_profile.__doc__
report['capsule_trace_api']=u.SystemLibrary.capsule_trace_single_by_profile.__doc__
(OUT/'read_cabinet.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(report,ensure_ascii=False))
