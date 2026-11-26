import json,os,unreal as u
from pathlib import Path
src=Path(os.environ['FPS_FOREST_REFERENCE_SOURCE'])
batch=Path(os.environ['FPS_FOREST_REFERENCE_BATCH'])
target='/Game/GameMaps/L_ForestPathVillage'
world=u.EditorLoadingAndSavingUtils.load_map(target)
actors=u.get_editor_subsystem(u.EditorActorSubsystem).get_all_level_actors()
region=next(a for a in actors if isinstance(a,u.ForestVillageRegion))
templates=[c for a in actors if isinstance(a,u.PCGVolume) and '/L_ForestPathForest.' in a.get_path_name() for c in a.get_components_by_class(u.InstancedStaticMeshComponent)]
hills=next(a for a in actors if isinstance(a,u.TemperateHillsWorld))
assets=hills.get_editor_property('assets')
trees=[m.get_path_name() for m in list(assets.get_editor_property('trees'))[:8]]
names=[n.rsplit('.',1)[-1] for n in trees]
if names!=['SK_BlackPoplarPCG_'+s for s in 'ABCD']+['SK_Beech_'+s for s in 'ABCD']:
    raise RuntimeError('Unexpected harvest palette '+str(names))
site=json.loads((src/'hill.json').read_text())
if not region.install_hill_site(str(src/'Turf'),u.IntPoint(*site['site_min_m']),site['village_datum_cm']):raise RuntimeError('Could not install town heightfield')
if not region.bake_vegetation(str(src/'Grass/planting.bin'),templates):raise RuntimeError('Forest pool bake failed')
counts={}
for c in region.get_components_by_class(u.InstancedStaticMeshComponent):
    if c.static_mesh and '/VillageRegion/Granite/' in c.static_mesh.get_path_name():
        name=c.static_mesh.get_path_name()
        counts[name]=counts.get(name,0)+c.get_instance_count()
expected=json.loads((src/'variation.json').read_text())
if len(counts)!=expected['granite_meshes'] or sum(counts.values())!=expected['granite_sites']:raise RuntimeError('Incomplete baked granite '+str(counts))
if not u.EditorLoadingAndSavingUtils.save_map(world,target):raise RuntimeError('Map save failed')
(batch/'baked.json').write_text(json.dumps(dict(map=target,trees=trees,granite=counts,layout=expected),indent=2))
