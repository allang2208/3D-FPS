"""User-requested diagnosis of the hospital map's missing containers and fixture references."""
import json
from pathlib import Path
import unreal as u
ROOT=Path(__file__).resolve().parents[1]
(ROOT/'Receipts').mkdir(parents=True,exist_ok=True)
editor=u.get_editor_subsystem(u.UnrealEditorSubsystem)
report={'worlds':{},'dirty_maps':[p.get_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_map_packages()]}
worlds={'editor':editor.get_editor_world(),'game':editor.get_game_world(),
    'saved_hospital':u.load_asset('/Game/GameMaps/Design/L_Hospital_Theme_Subject')}
for role,world in worlds.items():
    if not world:continue
    containers=u.GameplayStatics.get_all_actors_of_class(world,u.ColdSteelSceneContainer)
    beds=u.GameplayStatics.get_all_actors_of_class(world,u.WardBedScatter)
    meshes=[]
    for actor in u.GameplayStatics.get_all_actors_of_class(world,u.StaticMeshActor):
        component=actor.static_mesh_component;mesh=component.get_editor_property('static_mesh')
        if mesh and any(word in mesh.get_path_name().lower() for word in ('pump','spare','sink')):
            meshes.append(dict(actor=actor.get_name(),label=actor.get_actor_label(),mesh=mesh.get_path_name(),
                location=str(actor.get_actor_location()),rotation=str(actor.get_actor_rotation())))
    report['worlds'][role]=dict(world=world.get_path_name(),containers=[dict(actor=a.get_name(),id=a.get_editor_property('container_id'),
        body=a.body.get_editor_property('static_mesh').get_path_name() if a.body.get_editor_property('static_mesh') else None,
        door=a.door.get_editor_property('static_mesh').get_path_name() if a.door.get_editor_property('static_mesh') else None,
        location=str(a.get_actor_location()),body_transform=str(a.body.get_world_transform()),
        body_bounds=str(a.body.get_editor_property('static_mesh').get_bounding_box()) if a.body.get_editor_property('static_mesh') else None,
        visible=a.body.get_editor_property('visible'),hidden=a.get_editor_property('hidden')) for a in containers],
        beds=[dict(actor=a.get_name(),mesh=str(a.get_editor_property('bed_mesh')),
            bedside_body=str(a.get_editor_property('bedside_containers').get_editor_property('body_mesh'))) for a in beds],fixtures=meshes)
path=ROOT/'Receipts/hospital-diagnosis.json';path.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf8')
print(json.dumps({'receipt':str(path),'worlds':{k:dict(world=v['world'],containers=len(v['containers']),beds=len(v['beds'])) for k,v in report['worlds'].items()},'dirty_maps':report['dirty_maps']},ensure_ascii=False),flush=True)
