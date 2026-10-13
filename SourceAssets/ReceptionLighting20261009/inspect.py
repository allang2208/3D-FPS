"""Requested per-lamp inspection of the production reception, without playing it."""
from pathlib import Path
import json
import unreal as u

ROOT = Path(__file__).resolve().parent
ROOT.joinpath('Receipts').mkdir(parents=True, exist_ok=True)
TARGET = '/Game/GameMaps/L_Dungeon_Randomized'
def vec(v): return [v.x, v.y, v.z]
def path(v): return v.get_path_name() if v else None
editor = u.get_editor_subsystem(u.UnrealEditorSubsystem)
world = (u.EditorLoadingAndSavingUtils.load_map(TARGET)
    if '-run=pythonscript' in u.SystemLibrary.get_command_line().lower() else u.load_asset(TARGET))
editor_world = editor.get_editor_world() if editor else None
game_world = editor.get_game_world() if editor else None
generators = u.GameplayStatics.get_all_actors_of_class(world, u.AuthoredDungeonGenerator)
if len(generators) != 1: raise RuntimeError('Expected one production generator')
g = generators[0]
catalog = json.loads(g.get_editor_property('module_catalog_json'))
ROOT.joinpath('Receipts/catalog-before.json').write_text(json.dumps(catalog, ensure_ascii=False, indent=2), encoding='utf8')
module = next(m for m in catalog['modules'] if m['id'] == 'FacilityReceptionHall')
report = dict(map=TARGET, module=module, editor_world=path(editor_world),
    game_world=path(game_world), dirty_maps=[p.get_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_map_packages()],
    dirty_content=[p.get_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()], meshes=[], worlds=[])
for suffix in ('LightFixtures', 'LightDiffusers', 'LightHangers'):
    mesh = u.load_asset('/Game/Dungeons/ReceptionHall20261006/Meshes/SM_Reception_' + suffix)
    item = dict(path=path(mesh), sections=[])
    for section in range(mesh.get_num_sections(0)):
        vertices, triangles, normals, uvs, tangents = u.ProceduralMeshLibrary.get_section_from_static_mesh(mesh, 0, section)
        item['sections'].append(dict(vertices=[vec(v) for v in vertices], triangles=list(triangles)))
    report['meshes'].append(item)
for kind, w in [('saved', world), ('editor', editor_world), ('game', game_world)]:
    if not w: continue
    entry = dict(kind=kind, path=path(w), lights=[], fixtures=[], generators=[])
    for actor in u.GameplayStatics.get_all_actors_of_class(w, u.Actor):
        tags = [str(t) for t in actor.tags]
        if isinstance(actor, u.AuthoredDungeonGenerator):
            entry['generators'].append(dict(path=path(actor), manifest=actor.get_editor_property('layout_manifest_json')))
        for light in actor.get_components_by_class(u.LocalLightComponent):
            entry['lights'].append(dict(label=actor.get_actor_label(), path=path(actor), tags=tags,
                type=light.get_class().get_name(), position=vec(light.get_world_location()), forward=vec(light.get_forward_vector()),
                rotation=str(light.get_world_rotation()), intensity=light.intensity, radius=light.attenuation_radius,
                shadows=light.cast_shadows, visible=light.is_visible(), function=path(light.light_function_material)))
        for c in actor.get_components_by_class(u.StaticMeshComponent):
            if c.static_mesh and c.static_mesh.get_name() in ('SM_Reception_LightFixtures', 'SM_Reception_LightDiffusers'):
                row=dict(mesh=path(c.static_mesh), tags=tags, transform=str(c.get_world_transform()), materials=[path(c.get_material(i)) for i in range(c.get_num_materials())])
                if isinstance(c, u.InstancedStaticMeshComponent):
                    row['instances']=[str(c.get_instance_transform(i, True)) for i in range(c.get_instance_count())]
                entry['fixtures'].append(row)
    report['worlds'].append(entry)
ROOT.joinpath('Receipts/inspection-before.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf8')
print('RECEPTION_INSPECTED', json.dumps(dict(lights=len(module['lights']), meshes=[dict(path=m['path'], vertices=sum(len(s['vertices']) for s in m['sections'])) for m in report['meshes']], worlds=[dict(kind=w['kind'], path=w['path'], lights=len(w['lights']), fixtures=len(w['fixtures'])) for w in report['worlds']], dirty_maps=report['dirty_maps'], game_world=report['game_world']), ensure_ascii=False))
