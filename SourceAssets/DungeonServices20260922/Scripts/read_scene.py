"""Requested light/ceiling and structural-service clearance inspection inputs."""
import json
from pathlib import Path
import unreal as u
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'Sources';OUT.mkdir(parents=True,exist_ok=True)
UE=u.get_editor_subsystem(u.UnrealEditorSubsystem);AA=u.get_editor_subsystem(u.EditorActorSubsystem)
if not UE or Path(u.Paths.project_dir()).resolve()!=ROOT.parents[1].resolve():raise RuntimeError('Requires FPSGAME editor')
world=UE.get_editor_world()
if world.get_path_name().split('.')[0]!='/Game/GameMaps/L_Dungeon_Prototype':raise RuntimeError('Dungeon not loaded')
def vec(v):return list(v.to_tuple())
def read(c,name):
    try:
        v=c.get_editor_property(name)
        if isinstance(v,(float,int,bool,str)):return v
        if hasattr(v,'to_tuple'):return list(v.to_tuple())
        return str(v)
    except Exception:return None
data=dict(world=world.get_path_name(),gameplay=bool(UE.get_game_world()),actors=[],lights=[],dirty_maps=[p.get_path_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_map_packages()])
for a in AA.get_all_level_actors():
    label=a.get_actor_label()
    if not label.startswith('DGN_'):continue
    light_components=a.get_components_by_class(u.LightComponent)
    relevant=any(w in label.lower() for w in ('ceiling','pipe','support','fixture','tray','light','conduit','cable','workbenchkit','vault'))
    if not relevant and not light_components:continue
    row=dict(label=label,path=a.get_path_name(),location=vec(a.get_actor_location()),rotation=vec(a.get_actor_rotation()),
             scale=vec(a.get_actor_scale3d()),hidden=a.is_hidden_ed(),components=[])
    for c in a.get_components_by_class(u.StaticMeshComponent):
        if not c.static_mesh:continue
        origin,extent=c.get_local_bounds()
        row['components'].append(dict(name=c.get_name(),mesh=c.static_mesh.get_path_name(),
             transform=str(c.get_world_transform()),location=vec(c.get_world_location()),rotation=vec(c.get_world_rotation()),scale=vec(c.get_world_scale()),
             local_min=vec(origin),local_max=vec(extent),visible=c.is_visible(),
             materials=[c.get_material(i).get_path_name() if c.get_material(i) else None for i in range(c.get_num_materials())]))
    for c in light_components:
        data['lights'].append(dict(actor=label,component=c.get_name(),class_name=c.get_class().get_name(),
             location=vec(c.get_world_location()),rotation=vec(c.get_world_rotation()),forward=vec(c.get_forward_vector()),
             properties={p:read(c,p) for p in ('visible','intensity','intensity_units','attenuation_radius','source_radius','source_length',
              'source_width','source_height','cast_shadows','cast_dynamic_shadows','cast_raytraced_shadow','indirect_lighting_intensity',
              'use_temperature','temperature','light_color','inner_cone_angle','outer_cone_angle','barn_door_angle','barn_door_length')}))
    data['actors'].append(row)
(OUT/globals().get('SCENE_SNAPSHOT','scene-before.json')).write_text(json.dumps(data,indent=2),encoding='utf-8')
print(json.dumps(dict(actors=[r['label'] for r in data['actors']],lights=data['lights'],dirty_maps=data['dirty_maps'])))
