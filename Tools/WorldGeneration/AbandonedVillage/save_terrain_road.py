"""Move the placed village road projector onto the two terrain materials."""
import hashlib
import json
from pathlib import Path
import runpy

import unreal as u

root = Path(u.Paths.convert_relative_path_to_full(u.Paths.project_dir()))
base = '/Game/WorldGeneration/TemperateHills/'
level = base + 'AbandonedVillage/L_AbandonedVillage'
road = base + 'AbandonedVillage/M_VillageMudRoad.M_VillageMudRoad'
plan = json.loads((root/'SourceAssets/TemperateHillsVillage/layout.json').read_text(encoding='utf-8'))
apply_layer = runpy.run_path(str(Path(__file__).with_name('terrain_road_layer.py')))['add_to_ground']

def disk_digest(package, extension):
    path = root/'Content'/(package.removeprefix('/Game/') + extension)
    return hashlib.sha256(path.read_bytes()).digest()

for material_path in (base + 'M_TemperateGround', base + 'PebbleShore/M_PebbleShoreGround'):
    before = disk_digest(material_path, '.uasset')
    material = u.load_asset(material_path)
    if not material:
        raise RuntimeError('Cannot load ' + material_path)
    if apply_layer(material, plan):
        errors = u.MaterialEditingLibrary.recompile_material(material)
        if errors:
            raise RuntimeError(str(errors))
        if before != disk_digest(material_path, '.uasset'):
            raise RuntimeError('Terrain material changed on disk during authoring: ' + material_path)
        if not u.EditorAssetLibrary.save_loaded_asset(material, False):
            raise RuntimeError('Cannot save ' + material_path)
        u.log('Saved terrain road on ' + material_path)

before = disk_digest(level, '.umap')
world = u.EditorLoadingAndSavingUtils.load_map(level)
if not world:
    raise RuntimeError('Cannot load ' + level)
actors = u.get_editor_subsystem(u.EditorActorSubsystem)
removed = 0
for actor in u.GameplayStatics.get_all_actors_of_class(world, u.DecalActor):
    if actor.get_path_name().startswith(level + '.'):
        component = actor.get_component_by_class(u.DecalComponent)
        material = component.get_editor_property('decal_material')
        if material and material.get_path_name() == road:
            if not actors.destroy_actor(actor):
                raise RuntimeError('Cannot remove the village road projector')
            removed += 1
if removed:
    if before != disk_digest(level, '.umap'):
        raise RuntimeError('Village level changed on disk during authoring')
    if not u.EditorLoadingAndSavingUtils.save_map(world, level):
        raise RuntimeError('Cannot save the village level')
u.log('VILLAGE_TERRAIN_ROAD_SAVED removed_projectors=' + str(removed))
