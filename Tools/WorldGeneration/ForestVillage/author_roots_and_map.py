"""Update the two forest PCG graphs, their placed trees, region planting and cartography."""
import json
import os
from pathlib import Path
import unreal as u

batch = Path(os.environ['FPS_ROOTS_BATCH'])
directory = Path(os.environ['FPS_REFERENCE_HILL_SOURCE'])
study = '/Game/ForestPathStudy/Maps/L_ForestPathForest'
village = '/Game/GameMaps/L_ForestPathVillage'
actors = u.get_editor_subsystem(u.EditorActorSubsystem)
save = u.EditorLoadingAndSavingUtils
report = {}

def meshes(actor):
    return actor.get_components_by_class(u.InstancedStaticMeshComponent)

def positions(groups):
    return {(round(t.translation.x, 1), round(t.translation.y, 1), g.static_mesh.get_name()): t.translation.z
            for g in groups for i in range(g.get_instance_count())
            for t in [g.get_instance_transform(i, world_space=True)]}

world = save.load_map(study)
if not world:
    raise RuntimeError('Forest sublevel could not be loaded')
for layer in ('Canopy', 'Hazel'):
    volume = next(a for a in actors.get_all_level_actors() if isinstance(a, u.PCGVolume)
                  and a.get_actor_label() == 'Forest path - ' + layer)
    groups = meshes(volume)
    initial = positions(groups)
    graph = u.load_asset('/Game/ForestPathStudy/PCG/PCG_ForestPath' + layer)
    nodes = graph.get_editor_property('nodes')
    pose = next(n for n in nodes if isinstance(n.get_settings(), u.PCGTransformPointsSettings))
    spawn = next(n for n in nodes if isinstance(n.get_settings(), u.PCGStaticMeshSpawnerSettings))
    profiles = {g.static_mesh.get_name(): u.ForestRootFitSettings.measure_root(g.static_mesh) for g in groups}
    existing = next((n for n in nodes if isinstance(n.get_settings(), u.ForestRootFitSettings)), None)
    if existing:
        settings = existing.get_settings()
    else:
        graph.remove_edge(pose, 'Out', spawn, 'In')
        node, settings = graph.add_node_of_type(u.ForestRootFitSettings)
        node.set_node_position(1940, 160)
        if not graph.add_edge(pose, 'Out', node, 'In') or not graph.add_edge(node, 'Out', spawn, 'In'):
            raise RuntimeError('Cannot connect root fit for ' + layer)
    settings.set_editor_property('root_radius', max(p.x for p in profiles.values()))
    settings.set_editor_property('root_collar_z', max(p.y for p in profiles.values()))
    if not u.EditorAssetLibrary.save_loaded_asset(graph, False):
        raise RuntimeError('Cannot save ' + layer)
    pcg = volume.get_component_by_class(u.PCGComponent)
    if not u.ForestRootFitSettings.regenerate_trees(pcg):
        raise RuntimeError('Tree PCG failed for ' + layer)
    final = positions(meshes(volume))
    shared = initial.keys() & final.keys()
    if not final or len(shared) != len(initial) or len(final) != len(initial):
        raise RuntimeError(f'{layer} placement layout changed: {len(initial)}, {len(final)}, {len(shared)} shared')
    shifts = sorted(initial[k] - final[k] for k in shared)
    report[layer] = dict(instances=len(final), lowered=sum(d > .1 for d in shifts),
                         median_lower_cm=round(shifts[len(shifts)//2], 2), max_lower_cm=round(shifts[-1], 2),
                         profiles={k:[round(p.x,2),round(p.y,2)] for k,p in profiles.items()})
    u.log('Forest root bake ' + json.dumps(report[layer]))
if not save.save_map(world, study):
    raise RuntimeError('Could not save the forest sublevel')
world = save.load_map(village)
if not world:
    raise RuntimeError('Could not load main village')
scene = actors.get_all_level_actors()
region = next(a for a in scene if isinstance(a, u.ForestVillageRegion) and a.get_path_name().startswith(village+'.'))
templates = [g for a in scene if isinstance(a,u.PCGVolume) and '/L_ForestPathForest.' in a.get_path_name() for g in meshes(a)]
def regional_trees():
    return positions([g for g in meshes(region) if g.static_mesh and
                      g.static_mesh.get_name().startswith(('SM_EuropeanHornbeam_', 'SM_CommonHazel_'))])
old = regional_trees()
if not region.bake_map_roads(str(directory)):
    raise RuntimeError('Could not sample road surface layers')
if not region.bake_vegetation(str(directory/'Grass'/'planting.bin'),templates):
    raise RuntimeError('Could not bake regional planting')
new = regional_trees()
if not new or new.keys() != old.keys():
    raise RuntimeError('Regional tree layout changed')
dz = sorted(old[k]-new[k] for k in old)
report['regional'] = dict(instances=len(dz), lowered=sum(d>.1 for d in dz), median_lower_cm=round(dz[len(dz)//2],2),
                          max_lower_cm=round(dz[-1],2))
if not save.save_map(world,village):
    raise RuntimeError('Could not save village')
(batch/'baked.json').write_text(json.dumps(report,indent=2),encoding='utf8')
