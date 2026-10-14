"""Inspect actual editor/play light components without changing their state."""
from pathlib import Path
import json,math
import unreal as u
ROOT=Path(__file__).resolve().parent
(ROOT/'Receipts').mkdir(parents=True,exist_ok=True)
ed=u.get_editor_subsystem(u.UnrealEditorSubsystem)
def path(x):return x.get_path_name() if x else None
def vec(v):return [v.x,v.y,v.z]
def rot(r):return [r.pitch,r.yaw,r.roll]
report=dict(worlds=[],dirty_maps=[p.get_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_map_packages()])
for kind,world in [('editor',ed.get_editor_world()),('game',ed.get_game_world())]:
    if not world:continue
    row=dict(kind=kind,path=path(world),lights=[],cameras=[],generators=[])
    if kind=='game':
        cam=u.GameplayStatics.get_player_camera_manager(world,0)
        if cam:row['cameras'].append(dict(position=vec(cam.get_camera_location()),rotation=rot(cam.get_camera_rotation()),fov=cam.get_fov_angle()))
    else:
        loc,r=u.EditorLevelLibrary.get_level_viewport_camera_info()
        row['cameras'].append(dict(position=vec(loc),rotation=rot(r)))
    for a in u.GameplayStatics.get_all_actors_of_class(world,u.Actor):
        if isinstance(a,u.AuthoredDungeonGenerator):
            row['generators'].append(dict(label=a.get_actor_label(),manifest=a.get_editor_property('layout_manifest_json')))
            (ROOT/'Receipts'/('catalog-'+kind+'.json')).write_text(a.get_editor_property('module_catalog_json'),encoding='utf8')
        for c in a.get_components_by_class(u.LocalLightComponent):
            item=dict(actor=a.get_actor_label(),name=path(c),type=c.get_class().get_name(),tags=[str(t) for t in a.tags],
                position=vec(c.get_world_location()),forward=vec(c.get_forward_vector()),rotation=rot(c.get_world_rotation()),
                actor_rotation=rot(a.get_actor_rotation()),relative_rotation=rot(c.get_editor_property('relative_rotation')),
                intensity=c.intensity,units=str(c.intensity_units),radius=c.attenuation_radius,shadows=c.cast_shadows,
                visible=c.is_visible(),function=path(c.light_function_material),indirect=c.indirect_lighting_intensity)
            if isinstance(c,u.SpotLightComponent):item.update(inner=c.inner_cone_angle,outer=c.outer_cone_angle)
            if isinstance(c,u.RectLightComponent):item.update(width=c.source_width,height=c.source_height)
            if isinstance(c,u.PointLightComponent):item.update(source_radius=c.source_radius,source_length=c.source_length)
            row['lights'].append(item)
    report['worlds'].append(row)
(ROOT/'Receipts/live-state.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf8')
print('LIGHT_DIRECTION_STATE',[(w['kind'],w['path'],len(w['lights']),w['cameras']) for w in report['worlds']],'dirty maps',report['dirty_maps'])
