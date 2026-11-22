"""Migrate only the three repaired interiors in the current production village."""
import json
import os
from pathlib import Path
import shutil
import sys

import unreal as u

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path[:0] = [str(HERE), str(HERE.parent/'VillageBlacksmith'), str(HERE.parent/'VillageCarpenter')]
from author_shop import pose
from carpenter_pendant import replace_hand_lantern
from shop_pendants import BAKERY, HAND, LANTERN, LOFT, TAVERN, hang, light_settings, remove_components

LEVEL = '/Game/WorldGeneration/TemperateHills/AbandonedVillage/L_AbandonedVillage'


def remove_table_lamp(actor, frame, spec, pivot, source):
    body_position = u.MathLibrary.transform_location(frame,u.Vector(*pivot))
    light_position = u.MathLibrary.transform_location(frame,u.Vector(*source))
    bodies, lights, instances = [], [], []
    for part in actor.get_components_by_class(u.SceneComponent):
        tags = list(map(str,part.component_tags))
        if spec.state not in tags or spec.name in tags:
            continue
        if isinstance(part,u.PointLightComponent) and not isinstance(part,u.SpotLightComponent):
            if (part.get_world_location()-light_position).length() < 2.:
                lights.append(part)
        elif isinstance(part,u.StaticMeshComponent) and part.static_mesh and part.static_mesh.get_name()==LANTERN.rsplit('/',1)[1]:
            if isinstance(part,u.InstancedStaticMeshComponent):
                for i in range(part.get_instance_count()):
                    if (part.get_instance_transform(i,True).translation-body_position).length() < 2.:
                        instances.append((part,i))
            elif (part.get_world_location()-body_position).length() < 2.:
                bodies.append(part)

    counts = (len(bodies)+len(instances),len(lights))
    installed = any(spec.name in map(str,l.component_tags) for l in actor.get_components_by_class(u.PointLightComponent))
    if counts != (1,1) and not (installed and counts == (0,0)):
        raise RuntimeError(f'{spec.name}: expected the table fixture and its source, found {counts}')
    actor.modify()
    remove_components(actor,bodies+lights)
    for part,i in instances:
        part.modify()
        if not part.remove_instance(i):
            raise RuntimeError('Could not remove the table lantern from '+part.get_path_name())
    return dict(removed_bodies=counts[0],removed_point_lights=counts[1])


def fit(out):
    store = u.EditorLoadingAndSavingUtils
    editor = u.get_editor_subsystem(u.UnrealEditorSubsystem)
    if (editor and editor.get_game_world()) or store.get_dirty_map_packages():
        raise RuntimeError('The editor has an active game or unsaved map changes')
    package = ROOT/('Content/'+LEVEL.removeprefix('/Game/')+'.umap')
    stamp = package.stat().st_mtime_ns
    backup = out/'Before'/('L_AbandonedVillage.'+str(stamp)+'.umap')
    backup.parent.mkdir(parents=True,exist_ok=True)
    if not backup.exists():
        shutil.copy2(package,backup)
    plan = json.loads((ROOT/'SourceAssets/TemperateHillsVillage/layout.json').read_text(encoding='utf-8'))
    house = next(h for h in plan['houses'] if h[0] == plan['carpenter']['house'])
    world = store.load_map(LEVEL)
    if not world:
        raise RuntimeError('Could not load '+LEVEL)
    subsystem = u.get_editor_subsystem(u.EditorActorSubsystem) or u.new_object(u.EditorActorSubsystem)
    actors = list(subsystem.get_all_level_actors())
    bakery, = [a for a in actors if 'VillageBakery.Site' in map(str,a.tags)]
    tavern, = [a for a in actors if 'VillageTavern.Site' in map(str,a.tags)]
    carpenter, = [a for a in actors if a.get_actor_label()=='Village_Carpenter_Repaired']
    kitchen_frame = bakery.get_actor_transform()
    workshop_frame = pose(house,0,0)
    bake_old = remove_table_lamp(bakery,kitchen_frame,BAKERY,(60,587,112.5),(60,587,110.8))
    loft_old = remove_table_lamp(carpenter,workshop_frame,LOFT,(237.1,-274,451.5),(237,-274,458))
    changes = {
        BAKERY.name: {**bake_old, **hang(bakery,kitchen_frame,BAKERY)},
        LOFT.name: {**loft_old, **hang(carpenter,workshop_frame,LOFT)},
        TAVERN.name: hang(tavern,tavern.get_actor_transform(),TAVERN),
    }
    existing = [p for p in carpenter.get_components_by_class(u.PointLightComponent) if HAND.name in map(str,p.component_tags)]
    if existing:
        lamp, = existing
        lamp.modify()
        light_settings(lamp,workshop_frame,HAND)
        changes[HAND.name] = dict(existing_mount=True,task_light_lumens=lamp.get_editor_property('intensity'))
    else:
        changes[HAND.name] = replace_hand_lantern(house,carpenter)
    if package.stat().st_mtime_ns != stamp:
        raise RuntimeError('Village was edited on disk during the refit')
    if not store.save_map(world,LEVEL):
        raise RuntimeError('Could not save '+LEVEL)
    receipt = dict(level=LEVEL,saved_file=str(package.resolve()),backup=str(backup),changes=changes)
    (out/'level-saved.json').write_text(json.dumps(receipt,indent=2),encoding='utf-8')
    u.log('SHOP_PENDANTS_SAVED '+LEVEL)


if __name__ == '__main__':
    fit(Path(os.environ['SHOP_PENDANT_RUN']))
