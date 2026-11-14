"""Save the warehouse / station environmental detail into the existing design subject."""
from collections import Counter
from datetime import datetime
from pathlib import Path
import json
import shutil
import traceback
import unreal as u

ROOT = Path(__file__).resolve().parent
PROJECT = ROOT.parents[1]
PLAN = json.loads((ROOT / 'Config/layout.json').read_text('utf8'))
INPUTS = json.loads((ROOT / 'inputs.json').read_text('utf8'))
TARGET = PLAN['map']
TAG = PLAN['tag']
RECEIPT = ROOT / 'Receipts/install.json'
SHARED = '/Game/SceneTests/FreightWarehouseDerelictPass20261111/Materials/'
DEST = '/Game/SceneTests/FreightStationUnifiedPatina20261111/Materials/'
ASSETS = u.EditorAssetLibrary
MATERIALS = u.MaterialEditingLibrary


def load(path):
    asset = u.load_asset(path)
    if not asset:
        raise RuntimeError('Asset unavailable: ' + path)
    return asset


def author_materials():
    previous = ROOT.parent / 'FreightWarehouseDerelictPass20261111/Receipts/install.json'
    material_paths = json.loads(previous.read_text('utf8'))['materials']
    result = {role: load(path) for role, path in material_paths.items()}
    # Each variant keeps the warehouse decal mask, UV orientation and PBR response.
    # Only opacity, roughness and noise phase change with its receiving surface.
    roles = {
        'DustEdge': ('Dust', .30, .82, .97, (.31, .74)),
        'DustFine': ('Dust', .20, .79, .93, (.72, .17)),
        'DustWall': ('Dust', .26, .78, .94, (.27, .58)),
        'LeakSoft': ('Leak', .17, .59, .88, (.64, .13)),
        'ScuffWall': ('Scuff', .32, .55, .79, (.38, .87)),
        'DampWall': ('Damp', .20, .60, .85, (.93, .34)),
    }
    for role, (parent, density, low, high, offset) in roles.items():
        path = DEST + 'MI_' + role
        if ASSETS.does_asset_exist(path):
            instance = load(path)
            if str(ASSETS.get_metadata_tag(instance, 'FreightStation.Owner')) != TAG:
                raise RuntimeError('An unrelated asset uses ' + path)
        else:
            instance = ASSETS.duplicate_asset(result[parent].get_path_name(), path)
        if not instance:
            raise RuntimeError('Material instance creation failed: ' + path)
        instance.modify()
        ASSETS.set_metadata_tag(instance, 'FreightStation.Owner', TAG)
        for name, value in [('Density', density), ('RoughMin', low), ('RoughMax', high)]:
            MATERIALS.set_material_instance_scalar_parameter_value(instance, name, value)
        MATERIALS.set_material_instance_vector_parameter_value(instance, 'Offset', u.LinearColor(*offset, 0, 0))
        MATERIALS.update_material_instance(instance)
        if not ASSETS.save_loaded_asset(instance, False):
            raise RuntimeError('Could not save ' + path)
        result[role] = instance
    return result


def back_up_target():
    relative = TARGET.removeprefix('/Game/')
    content = PROJECT / 'Content'
    backup = ROOT / 'Backups' / datetime.now().strftime('%Y%m%d-%H%M%S-%f')
    sources = [content / (relative + '.umap')]
    sources.extend(content / folder / relative for folder in ('__ExternalActors__', '__ExternalObjects__'))
    for source in sources:
        if not source.exists():
            continue
        dest = backup / source.relative_to(PROJECT)
        dest.parent.mkdir(parents=True, exist_ok=True)
        if source.is_dir():
            shutil.copytree(source, dest)
        else:
            shutil.copy2(source, dest)
    return str(backup)


def require_current_receivers(world_actors):
    current = {actor.get_name(): actor for actor in world_actors}
    receivers = {c['mesh'] for row in INPUTS['actors'] for c in row['components']
                 if INPUTS['meshes'][c['mesh']].get('geometry')}
    warehouse = {'StaticMeshActor_' + str(i) for i in (21, 22, 23, 29, 32)}
    for row in INPUTS['actors']:
        if row['name'] not in warehouse and not any(c['mesh'] in receivers for c in row['components']):
            continue
        actor = current.get(row['name'])
        if not actor or actor.get_actor_label() != row['label']:
            raise RuntimeError('Receiving geometry changed: ' + row['label'])
        components = {c.get_name(): c for c in actor.get_components_by_class(u.StaticMeshComponent)}
        for saved in row['components']:
            component = components.get(saved['name'])
            if not component or not component.static_mesh or component.static_mesh.get_path_name() != saved['mesh']:
                raise RuntimeError('Receiving mesh changed: ' + row['label'])
            transform = component.get_world_transform()
            for actual, expected in [(transform.translation.to_tuple(), saved['position']),
                                     (transform.rotation.rotator().to_tuple(), saved['rotation']),
                                     (transform.scale3d.to_tuple(), saved['scale'])]:
                if any(abs(a-b) > .02 for a, b in zip(actual, expected)):
                    raise RuntimeError('Receiving surface moved: ' + row['label'])
            bindings = [component.get_material(i).get_path_name() if component.get_material(i) else None
                        for i in range(component.get_num_materials())]
            if bindings != saved['materials']:
                raise RuntimeError('Receiving material changed: ' + row['label'])


def save_subject(world, external_prefixes):
    external = [p for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()
                if p.get_name().lower().startswith(external_prefixes)]
    if external and not u.EditorLoadingAndSavingUtils.save_packages(external, False):
        raise RuntimeError('Could not save subject external packages')
    if not u.EditorLoadingAndSavingUtils.save_map(world, TARGET):
        raise RuntimeError('Could not save the station subject')
    return [TARGET] + [p.get_name() for p in external]


def main():
    if Path(u.Paths.project_dir()).resolve() != PROJECT.resolve():
        raise RuntimeError('Wrong project')
    if RECEIPT.exists() and json.loads(RECEIPT.read_text('utf8')).get('stage') == 'map_saved':
        print('FREIGHT_STATION_UNIFIED_ALREADY_SAVED', flush=True)
        return
    relative = TARGET.removeprefix('/Game/').lower()
    external_prefixes = tuple('/game/' + folder + '/' + relative + '/'
                              for folder in ('__externalactors__', '__externalobjects__'))
    editor = u.get_editor_subsystem(u.UnrealEditorSubsystem)
    if editor and editor.get_game_world():
        raise RuntimeError('Preserve active gameplay')
    if u.EditorLoadingAndSavingUtils.get_dirty_map_packages() or any(
            p.get_name().lower().startswith(external_prefixes) for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()):
        raise RuntimeError('Preserve unsaved map edits')
    prior_world = editor.get_editor_world() if editor else None
    prior_path = prior_world.get_path_name().split('.')[0] if prior_world else ''
    world = u.EditorLoadingAndSavingUtils.load_map(TARGET)
    if not world or world.get_path_name().split('.')[0] != TARGET:
        raise RuntimeError('Could not load the specified subject')
    existing = list(u.GameplayStatics.get_all_actors_of_class(world, u.Actor))
    require_current_receivers(existing)
    if any(TAG in [str(t) for t in actor.tags] for actor in existing):
        raise RuntimeError('This decoration layer already exists in the scene')
    actor_api = u.get_editor_subsystem(u.EditorActorSubsystem) or u.new_object(u.EditorActorSubsystem)
    report = {'target': TARGET, 'entry_command': 'open ' + TARGET, 'backup': back_up_target(), 'stage': 'authoring',
              'game_run': False, 'rendered': False, 'tests_run': False}
    RECEIPT.parent.mkdir(exist_ok=True)

    def record():
        RECEIPT.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf8')

    added = []
    def spawn(row, actor_type):
        pitch, yaw, roll = row['rotation']
        point = u.Vector(*row['position'])
        rotation = u.Rotator(pitch=pitch, yaw=yaw, roll=roll)
        actor = actor_api.spawn_actor_from_class(actor_type, point, rotation)
        if not actor:
            raise RuntimeError('Spawn failed: ' + row['id'])
        added.append(actor)
        actor.set_actor_location(point, False, True)
        actor.set_actor_rotation(rotation, True)
        actor.set_actor_label('FreightStation_' + row['id'])
        actor.set_folder_path('StationLine/FreightStationPatina/' + row['group'])
        actor.set_editor_property('tags', [u.Name(TAG), u.Name('StationLine.Subject')])
        return actor

    record()
    try:
        materials = author_materials()
        meshes = {path: load(path) for path in {r['mesh'] for r in PLAN['parts']}}
        for row in PLAN['parts']:
            actor = spawn(row, u.StaticMeshActor)
            component = actor.static_mesh_component
            component.set_static_mesh(meshes[row['mesh']])
            actor.set_actor_scale3d(u.Vector(*row['scale']))
            component.set_mobility(u.ComponentMobility.STATIC)
            component.set_collision_profile_name(row['collision'])
            component.set_cast_shadow(row['shadow'])
            component.set_editor_property('ld_max_draw_distance', row['draw_distance'])
            for slot in range(component.get_num_materials()):
                source = component.get_material(slot)
                if source and source.get_path_name().startswith('/Game/UndergroundTunnel/Materials/MI_Prop_'):
                    for state in ('Settled', 'Handled'):
                        variant = SHARED + source.get_name() + '_' + state
                        if ASSETS.does_asset_exist(variant):
                            component.set_material(slot, load(variant))
                            break
        for row in PLAN['decals']:
            actor = spawn(row, u.DecalActor)
            component = actor.get_component_by_class(u.DecalComponent)
            component.set_decal_material(materials[row['material']])
            component.set_editor_property('decal_size', u.Vector(*row['size']))
            component.set_editor_property('sort_order', 4 if row['material'] == 'Damage' else 2)
            component.set_editor_property('fade_screen_size', .0015)
        packages = save_subject(world, external_prefixes)
        report.update(stage='map_saved', saved_packages=packages, added_meshes=len(PLAN['parts']),
                      added_decals=len(PLAN['decals']), added_materials=sorted(m.get_path_name() for m in materials.values()
                                                                             if m.get_path_name().startswith(DEST)),
                      by_area=dict(Counter(r['group'] for r in PLAN['parts'] + PLAN['decals'])),
                      original_actors_edited=0, new_blocking_actors=0)
        record()
        print('FREIGHT_STATION_UNIFIED_MAP_SAVED ' + TARGET, flush=True)
    except Exception:
        if report['stage'] != 'map_saved':
            for actor in reversed(added):
                actor_api.destroy_actor(actor)
        report['error'] = traceback.format_exc()
        record()
        raise
    finally:
        if prior_path and prior_path != TARGET and not prior_path.startswith('/Temp/'):
            u.EditorLoadingAndSavingUtils.load_map(prior_path)


main()
