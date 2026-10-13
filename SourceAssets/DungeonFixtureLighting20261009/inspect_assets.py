"""Read the saved dungeon catalog and fixture materials without starting play."""
from pathlib import Path
import json
import unreal as u

ROOT=Path(__file__).resolve().parent
PROJECT=ROOT.parents[1]
(ROOT/'Receipts').mkdir(parents=True,exist_ok=True)
catalog=json.loads((PROJECT/'SourceAssets/DungeonFacilityFlow20261007/Config/catalog.json').read_text('utf8'))
def path(o):return o.get_path_name() if o else None
def v(p):return [p.x,p.y,p.z]
def meshes(value):
    if isinstance(value,dict):
        if value.get('mesh','').startswith('/Game/'):yield value['mesh']
        for child in value.values():yield from meshes(child)
    elif isinstance(value,list):
        for child in value:yield from meshes(child)
editor=u.get_editor_subsystem(u.UnrealEditorSubsystem)
report=dict(editor_world=path(editor.get_editor_world()) if editor else None,
    game_world=path(editor.get_game_world()) if editor else None,
    dirty_maps=[p.get_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_map_packages()],meshes=[],fixed=[])
paths=set(meshes(catalog['modules']))|set(meshes(catalog['facility_flow'].get('route_portal_variants',{})))
for name in sorted(paths):
    mesh=u.load_asset(name)
    if not isinstance(mesh,u.StaticMesh):continue
    materials=[dict(slot=str(s.material_slot_name),path=path(s.material_interface)) for s in mesh.static_materials]
    relevant=any(k in name.lower() for k in ('fixture','lamp','diffus','sconce','lumin','routeramp'))
    relevant=relevant or any(any(k in str(m).lower() for k in ('glow','emiss','diffus','lamp')) for m in materials)
    if relevant:
        report['meshes'].append(dict(path=name,materials=materials,sections=mesh.get_num_sections(0),bounds=str(mesh.get_bounds())))
world=u.load_asset('/Game/GameMaps/L_Dungeon_Randomized')
actors=u.GameplayStatics.get_all_actors_of_class(world,u.Actor)
for a in actors:
    if a.actor_has_tag('DungeonRouteGenerated'):continue
    local=a.get_component_by_class(u.LocalLightComponent)
    comps=a.get_components_by_class(u.StaticMeshComponent)
    if local or any(c.static_mesh and any(k in c.static_mesh.get_name().lower() for k in ('lamp','fixture','light','workbench')) for c in comps):
        report['fixed'].append(dict(label=a.get_actor_label(),path=path(a),position=v(a.get_actor_location()),rotation=str(a.get_actor_rotation()),
            light=dict(type=local.get_class().get_name(),intensity=local.intensity,position=v(local.get_world_location()),forward=v(local.get_forward_vector()),shadows=local.cast_shadows) if local else None,
            meshes=[dict(mesh=path(c.static_mesh),transform=str(c.get_world_transform())) for c in comps if c.static_mesh]))
(ROOT/'Receipts/asset-inventory.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf8')
print('DUNGEON_FIXTURE_INVENTORY',len(report['meshes']),'candidate meshes;',len(report['fixed']),'fixed actors; game=',report['game_world'],'dirty_maps=',report['dirty_maps'])
