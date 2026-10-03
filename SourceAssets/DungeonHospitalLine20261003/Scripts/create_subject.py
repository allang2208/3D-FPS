"""Save an editable medical-route sample using the production room descriptors.

Authoring only: no PIE, rendering, monster spawning, or gameplay verification.
Native bed/blood actors populate normally when the user enters the saved map.
"""
import copy
import hashlib
import json
import math
import runpy
import traceback
from pathlib import Path

import unreal as u

ROOT = Path(__file__).resolve().parents[1]
PROJECT = ROOT.parents[1]
TARGET = '/Game/GameMaps/Design/L_Hospital_Theme_Subject'
PRODUCTION = '/Game/GameMaps/L_Dungeon_Randomized'
SEED = 20261003


def write(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding='utf8')


def main():
    for folder in ('Config', 'Receipts'):
        (ROOT / folder).mkdir(parents=True, exist_ok=True)
    if Path(u.Paths.project_dir()).resolve() != PROJECT.resolve():
        raise RuntimeError('Wrong project for hospital line authoring')
    existing_editor = globals().get('HOSPITAL_LINE_EXISTING_EDITOR', False)
    if '-run=pythonscript' not in u.SystemLibrary.get_command_line().lower() and not existing_editor:
        raise RuntimeError('Commandlet or existing editor bridge required')
    editor = u.get_editor_subsystem(u.UnrealEditorSubsystem)
    if editor and editor.get_game_world():
        raise RuntimeError('Preserve active game session')
    dirty = [p.get_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_map_packages()]
    if dirty:
        raise RuntimeError('Preserve unsaved maps: ' + str(dirty))
    if u.EditorAssetLibrary.does_asset_exist(TARGET):
        receipt = ROOT / 'Receipts/install.json'
        if receipt.exists() and json.loads(receipt.read_text('utf8')).get('stage') == 'map_saved':
            print('HOSPITAL_LINE_ALREADY_SAVED ' + TARGET, flush=True)
            return
        raise RuntimeError('Preserve existing hospital subject map')
    original = editor.get_editor_world().get_path_name().split('.')[0] if editor and editor.get_editor_world() else ''
    actors = u.get_editor_subsystem(u.EditorActorSubsystem) or u.new_object(u.EditorActorSubsystem)
    report = dict(stage='authoring', map=TARGET, tests_run=False, rendered=False,
                  game_run=False, editor_opened=False, seed=SEED)
    receipt = ROOT / 'Receipts/install.json'
    write(receipt, report)
    cache = {}

    def asset(path):
        if path not in cache:
            cache[path] = u.load_asset(path)
            if not cache[path]:
                raise RuntimeError('Missing production asset: ' + path)
        return cache[path]

    def vector(values):
        return u.Vector(*values)

    def box(spec):
        return u.Box(min=vector(spec['min']), max=vector(spec['max']))

    def struct(cls, **properties):
        value = cls()
        for key, item in properties.items():
            value.set_editor_property(key, item)
        return value

    def location(position, pose):
        angle = math.radians(pose['yaw'])
        x, y, z = position
        origin = pose['position']
        return u.Vector(x * math.cos(angle) - y * math.sin(angle) + origin[0],
                        x * math.sin(angle) + y * math.cos(angle) + origin[1], z + origin[2])

    def rotation(spec, pose):
        return u.Rotator(pitch=spec.get('pitch', 0), yaw=pose['yaw'] + spec.get('yaw', 0),
                         roll=spec.get('roll', 0))

    def named(actor, label, pose, extra=()):
        if not actor:
            raise RuntimeError('Actor creation failed: ' + label)
        room = pose.get('name', pose['id'])
        actor.set_actor_label('HospitalLine_' + label)
        actor.set_folder_path('HospitalLine/' + room)
        actor.set_editor_property('tags', [u.Name('HospitalLine.Subject'), u.Name(room),
                                          *(u.Name(t) for t in extra)])
        return actor

    def spawn(cls, spec, pose, label, extra=()):
        return named(actors.spawn_actor_from_class(cls, location(spec.get('position', [0, 0, 0]), pose),
                                                   rotation(spec, pose)), label, pose, extra)

    counts = dict(mesh_actors=0, hazard_actors=0, lights=0, runtime_actors={})
    container_root = PROJECT / 'SourceAssets/HospitalContainers20261003'
    container_helpers = runpy.run_path(str(container_root / 'Scripts/unreal_helpers.py'))
    container_rules = runpy.run_path(str(container_root / 'Scripts/catalog_rules.py'))

    def exposure_class():
        path = '/Game/Dungeons/HospitalLine20261003/Blueprints/BP_HospitalLineExposure'
        if not u.EditorAssetLibrary.does_asset_exist(path):
            factory = u.BlueprintFactory()
            factory.set_editor_property('parent_class', u.Actor)
            blueprint = u.AssetToolsHelpers.get_asset_tools().create_asset(
                'BP_HospitalLineExposure', path.rsplit('/', 1)[0], u.Blueprint, factory)
            subsystem = u.get_engine_subsystem(u.SubobjectDataSubsystem)
            functions = u.SubobjectDataBlueprintFunctionLibrary
            handles = subsystem.k2_gather_subobject_data_for_blueprint(blueprint)
            root = next(h for h in handles if functions.is_root_component(functions.get_data(h)))

            def component(name, cls, parent):
                handle, reason = subsystem.add_new_subobject(u.AddNewSubobjectParams(
                    parent_handle=parent, new_class=cls, blueprint_context=blueprint))
                if not functions.is_handle_valid(handle):
                    raise RuntimeError('Exposure component creation: ' + str(reason))
                subsystem.rename_subobject(handle, u.Text(name))
                return handle, functions.get_object(functions.get_data(handle))

            bounds_handle, bounds = component('RoomExposureBounds', u.BoxComponent, root)
            bounds.set_collision_profile_name('NoCollision')
            bounds.set_editor_property('generate_overlap_events', False)
            bounds.set_hidden_in_game(True)
            _, postprocess = component('RoomExposure', u.PostProcessComponent, bounds_handle)
            postprocess.set_editor_property('unbound', False)
            postprocess.set_editor_property('blend_weight', 1)
            u.BlueprintEditorLibrary.compile_blueprint(blueprint)
            if not u.EditorAssetLibrary.save_asset(path, only_if_is_dirty=False):
                raise RuntimeError('Hospital exposure Blueprint save failed')
        cls = u.EditorAssetLibrary.load_blueprint_class(path)
        if not cls:
            raise RuntimeError('Hospital exposure Blueprint unavailable')
        report['exposure_blueprint'] = path
        return cls

    def static(spec, pose, label):
        extra = []
        if spec.get('guardrail_drop'):
            extra.append('Traversal.GuardrailDrop')
        if spec.get('blood_receiver'):
            extra.append('HospitalLine.WardBlood')
        if spec.get('wall_art'):
            extra.append('DungeonWallArt')
        if 'half_size' in spec:
            if spec.get('radial'):
                extra.append('PusRadialFootprint')
            actor = spawn(u.DungeonPusChannel, spec, pose, label, extra)
            actor.set_editor_property('half_size', u.Vector2D(*spec['half_size']))
            component = actor.get_editor_property('surface')
            counts['hazard_actors'] += 1
        else:
            actor = spawn(u.StaticMeshActor, spec, pose, label, extra)
            component = actor.static_mesh_component
            counts['mesh_actors'] += 1
        component.set_mobility(u.ComponentMobility.MOVABLE if spec.get('fluid') else u.ComponentMobility.STATIC)
        component.set_static_mesh(asset(spec['mesh']))
        component.set_collision_profile_name('BlockAll' if spec.get('collision', True) else 'NoCollision')
        component.set_cast_shadow(spec.get('cast_shadow', True) and not spec.get('fluid') and not spec.get('wall_art'))
        if spec.get('wall_art'):
            component.set_editor_property('receives_decals', False)
        if spec.get('fluid'):
            component.set_editor_property('evaluate_world_position_offset', True)
            component.set_editor_property('visible_in_ray_tracing', False)
            component.set_editor_property('affect_distance_field_lighting', False)
        for index, path in enumerate(spec.get('materials', [])):
            if path:
                component.set_material(index, asset(path))
        actor.set_actor_scale3d(vector(spec.get('scale', [1, 1, 1])))

    def light(spec, pose, label, role, cells):
        kind = spec.get('type', 'spot' if role in ('corridor', 'fill') else 'point')
        spot = kind == 'spot'
        light_spec = dict(spec)
        if spot:
            light_spec['pitch'] = -90
        actor = spawn(u.SpotLight if spot else u.PointLight, light_spec, pose, label)
        component = actor.get_component_by_class(u.PointLightComponent)
        component.set_mobility(u.ComponentMobility.MOVABLE)
        component.set_editor_property('intensity_units', u.LightUnits.LUMENS)
        outer = max(10, min(85, spec.get('outer_cone_degrees', 80 if role == 'corridor' else 65)))
        intensity = spec['intensity']
        if spot:
            component.set_editor_property('outer_cone_angle', outer)
            component.set_editor_property('inner_cone_angle', max(0, outer - 15))
            intensity *= .5 * (1 - math.cos(math.radians(outer)))
        radius = spec.get('optimized_radius_cm', min(spec['radius'] * .8, 300) if role == 'fill' else spec['radius'])
        shadows = True
        if role == 'fill':
            p = spec['position']
            clearance = max([0, *(min(p[0] - cell['min'][0], cell['max'][0] - p[0],
                                     p[1] - cell['min'][1], cell['max'][1] - p[1]) - 35 for cell in cells)])
            shadows = (radius * math.sin(math.radians(outer)) if spot else radius) > clearance
        component.set_intensity(intensity)
        component.set_editor_property('attenuation_radius', max(1, radius))
        component.set_editor_property('cast_shadows', spec.get('cast_shadows', shadows))
        component.set_editor_property('max_draw_distance', spec.get('max_draw_distance_cm', 1400 if role == 'fill' else 1800 if role == 'corridor' else 2400))
        component.set_editor_property('max_distance_fade_range', spec.get('fade_range_cm', 400 if role == 'fill' else 500))
        for key, default in (('source_radius', 5), ('source_length', 0 if spot else 60),
                             ('indirect_lighting_intensity', .7), ('volumetric_scattering_intensity', 1)):
            component.set_editor_property(key, spec.get(key, default))
        component.set_light_color(u.LinearColor(*spec['color'], 1))
        if spec.get('light_function'):
            component.set_light_function_material(asset(spec['light_function']))
        counts['lights'] += 1

    def exposure(component, spec):
        settings = component.get_editor_property('settings')
        values = dict(auto_exposure_min_brightness=spec['exposure_ev'],
                      auto_exposure_max_brightness=spec['exposure_ev'], auto_exposure_bias=spec['exposure_bias'],
                      indirect_lighting_intensity=spec['indirect_intensity'],
                      color_saturation=u.Vector4(spec['saturation'], spec['saturation'], spec['saturation'], 1),
                      color_contrast=u.Vector4(spec['contrast'], spec['contrast'], spec['contrast'], 1),
                      vignette_intensity=spec['vignette'], bloom_intensity=spec['bloom'])
        for key, value in values.items():
            settings.set_editor_property('override_' + key, True)
            settings.set_editor_property(key, value)
        component.set_editor_property('settings', settings)

    def runtime(spec, pose, label):
        kind = spec['type']
        if kind in ('glass_door', 'glass_window'):
            actor = spawn(u.WardGlassDoor if kind == 'glass_door' else u.WardGlassWindow, spec, pose, label)
            if kind == 'glass_door':
                components = {c.get_name(): c for c in actor.get_components_by_class(u.SceneComponent)}
                frame, leaf, hinge = (components[n] for n in ('DoorFrame', 'DoorLeaf', 'DoorHinge'))
                frame.set_static_mesh(None)
                frame.set_collision_profile_name('NoCollision')
                frame.set_visibility(False)
                mesh = asset(spec['leaf'])
                leaf.set_static_mesh(mesh)
                leaf.set_relative_rotation(u.Rotator(pitch=0, yaw=180 if spec['positive_hinge'] else 0, roll=0), False, True)
                for key, value in dict(hinge_on_positive_y=spec['positive_hinge'], open_angle_degrees=85,
                                       open_seconds=spec['open_seconds'], auto_close_seconds=spec['auto_close_seconds']).items():
                    actor.set_editor_property(key, value)
                # Same bounds/pivot alignment as ColdSteelDoor::ConfigureStandaloneLeaf.
                bounds = mesh.get_bounding_box()
                center = (bounds.min + bounds.max) * .5
                extent = (bounds.max - bounds.min) * .5
                sign = 1 if spec['positive_hinge'] else -1
                hinge.set_relative_location(u.Vector(0, sign * extent.y, 0), False, True)
                leaf.set_relative_location(u.Vector(-center.x, -sign * extent.y - center.y, extent.z - center.z), False, True)
            pane = actor.get_editor_property('glass_pane')
            pane.set_static_mesh(asset(spec['pane']))
            for key, source in (('fracture_mesh', 'fracture'), ('fracture_material', 'fracture_material'),
                                ('impact_particles', 'impact_particles'), ('break_sound', 'sound')):
                pane.set_editor_property(key, asset(spec[source]))
            pane.set_editor_property('pane_dimensions', vector(spec['dimensions_cm']))
        elif kind == 'beds':
            actor = spawn(u.WardBedScatter, spec, pose, label)
            actor.set_editor_property('bed_mesh', asset(spec['mesh']))
            for key in ('min_beds_per_room', 'max_beds_per_room', 'wall_clearance', 'bed_clearance'):
                actor.set_editor_property(key, spec[key])
            actor.set_editor_property('rooms', [struct(u.WardBedRoom, room_id=u.Name(s['id']), bounds=box(s)) for s in spec['rooms']])
            actor.set_editor_property('poses', [struct(u.WardBedPose, pose_id=u.Name(s['id']), bounds=box(s), weight=s['weight'],
                                                             rotation=u.Rotator(pitch=s['pitch'], yaw=0, roll=s['roll'])) for s in spec['poses']])
            actor.set_editor_property('keep_clear', [box(s) for s in spec['keep_clear']])
            actor.set_editor_property('room_props', [struct(u.WardRoomProp, type_id=u.Name(s['id']), mesh=asset(s['mesh']),
                                        min_per_room=s['min_per_room'], max_per_room=s['max_per_room'],
                                        clearance=s['clearance'], blocking=s['blocking']) for s in spec['room_props']])
            actor.set_editor_property('seed', SEED)
            actor.set_editor_property('randomize_on_begin_play', False)
            container_helpers['configure_bedside'](actor, spec, asset)
        elif kind == 'scene_container':
            container_helpers['spawn_container'](actors, spec, pose, asset)
        elif kind == 'blood':
            actor = spawn(u.DungeonBloodScatter, spec, pose, label)
            actor.set_editor_property('receiver_tag', u.Name('HospitalLine.WardBlood'))
            actor.set_editor_property('blood_material', asset(spec['material']))
            for key in ('floor_count', 'wall_count', 'floor_size_scale'):
                actor.set_editor_property(key, spec[key])
            actor.set_editor_property('scanned_size_range_cm', u.Vector2D(*spec['scanned_size_range_cm']))
            actor.set_editor_property('surfaces', [struct(u.DungeonBloodSurface, center=vector(s['center']), normal=vector(s['normal']),
                      axis_u=vector(s['axis_u']), half_size=u.Vector2D(*s['half_size']), wall=s['wall']) for s in spec['surfaces']])
            actor.set_editor_property('seed', SEED + 1)
            actor.set_editor_property('randomize_on_begin_play', False)
        elif kind == 'decal':
            actor = spawn(u.DecalActor, spec, pose, label)
            component = actor.get_component_by_class(u.DecalComponent)
            component.set_decal_material(asset(spec['material']))
            component.set_editor_property('decal_size', vector(spec['decal_size']))
            component.set_sort_order(spec['sort_order'])
            component.set_fade_screen_size(spec['fade_screen_size'])
        elif kind == 'post_process':
            actor = spawn(exposure_class(), spec, pose, label)
            bounds = actor.get_component_by_class(u.BoxComponent)
            bounds.set_box_extent(vector(spec['extent']), False)
            bounds.set_collision_enabled(u.CollisionEnabled.NO_COLLISION)
            bounds.set_editor_property('generate_overlap_events', False)
            bounds.set_hidden_in_game(True)
            component = actor.get_component_by_class(u.PostProcessComponent)
            component.set_editor_property('unbound', False)
            component.set_editor_property('priority', spec['priority'])
            component.set_editor_property('blend_radius', spec['blend_radius'])
            component.set_editor_property('blend_weight', 1)
            exposure(component, spec)
        else:
            raise RuntimeError('Production hospital actor requires authoring support: ' + kind)
        counts['runtime_actors'][kind] = counts['runtime_actors'].get(kind, 0) + 1

    try:
        source_world = u.EditorLoadingAndSavingUtils.load_map(PRODUCTION)
        generators = u.GameplayStatics.get_all_actors_of_class(source_world, u.AuthoredDungeonGenerator)
        if len(generators) != 1:
            raise RuntimeError('Production dungeon catalog unavailable')
        source_text = generators[0].get_editor_property('module_catalog_json')
        catalog = json.loads(source_text)
        write(ROOT / 'Config/production-catalog-snapshot.json', catalog)
        modules = {m['id']: m for m in catalog['modules']}
        route = next(r for r in catalog['themed_routes']['routes'] if r['id'] == 'medical')
        sequence = route['sequence']
        if sequence != ['Drainage', 'AbandonedIsolationWard', 'AbandonedAnatomyTheatre']:
            raise RuntimeError('Medical route changed; preserve latest descriptors before adapting placement')
        drainage = modules['Drainage']
        end = next(p for p in drainage['ports'] if p['id'] == 'exit')['position']
        x, y, z = end
        placements = [dict(id='Drainage', position=[0, 0, 0], yaw=0),
                      dict(id='Transit', name='DrainageWardLink', position=[x, y, z], yaw=90),
                      dict(id='AbandonedIsolationWard', position=[x + 400 + 3300, y, z], yaw=0),
                      dict(id='Transit', name='WardTheatreLink', position=[x + 400 + 6600, y, z], yaw=90),
                      dict(id='AbandonedAnatomyTheatre', position=[x + 800 + 6600 + 1600, y - 1000, z], yaw=0)]
        world = u.EditorLoadingAndSavingUtils.new_blank_map(False)
        if not world:
            raise RuntimeError('New hospital subject world unavailable')
        world.get_world_settings().set_editor_property('default_game_mode', u.load_class(None, '/Script/FPSGAME.FPSGAMEGameMode'))
        hospital_container_index = 0
        hospital_selections = {}
        for pose in placements:
            module = copy.deepcopy(modules[pose['id']])
            prefix = pose.get('name', pose['id'])
            if module.get('scene_recipes'):
                recipe = next(r for r in module['scene_recipes'] if r['id'] == 'pump_service')
                state = next(s for s in recipe['states'] if s['id'] == 'maintenance')
                module['parts'].extend(recipe.get('parts', []) + state.get('parts', []))
                pose['scene_recipe_id'], pose['scene_state_id'] = recipe['id'], state['id']
                for spec in module['lights']:
                    spec['intensity'] *= state.get('light_intensity_scale', 1)
            for index, spec in enumerate(module['parts']):
                static(spec, pose, prefix + '_' + str(index))
            brightest = sorted(range(len(module['lights'])), key=lambda i: -module['lights'][i]['intensity'])[:2]
            for index, spec in enumerate(module['lights']):
                role = spec.get('role', 'corridor' if pose['id'] == 'Transit' else 'key' if index in brightest else 'fill')
                light(spec, pose, prefix + '_Light_' + str(index), role, module.get('cells', []))
            for index, spec in enumerate(module.get('runtime_actors', [])):
                runtime(spec, pose, prefix + '_Runtime_' + str(index))
            groups = [g for g in module.get('warehouse_containers', {}).get('groups', []) if g['id'].startswith('Hospital.')]
            if groups:
                selected = container_rules['choose'](groups, SEED + hospital_container_index)
                hospital_container_index += 1
                hospital_selections[pose['id']] = len(selected)
                for index, spec in enumerate(selected):
                    runtime(spec, pose, prefix + '_Search_' + str(index))
            if module.get('props') or module.get('progression_gate'):
                raise RuntimeError('Medical module gained progression/prop requirements: ' + pose['id'])
        environment = dict(id='Environment', position=[0, 0, 0], yaw=0)
        entry = next(p for p in drainage['ports'] if p['id'] == 'entry')['position']
        exit_spec = next(p for p in modules['AbandonedAnatomyTheatre']['ports'] if p['id'] == 'Service')
        exit_position = location(exit_spec['position'], placements[-1])
        for label, position, scale in (('StartCap', [entry[0], entry[1], entry[2] + 140], [3, .12, 2.8]),
                                        ('EndCap', [exit_position.x, exit_position.y, exit_position.z + 140], [.12, 3, 2.8])):
            static(dict(mesh='/Engine/BasicShapes/Cube', position=position, scale=scale, collision=True,
                        materials=['/Game/Dungeons/WallUpgrade20260924/Materials/MI_WallConcrete']), environment, label)
        player_start = [entry[0], entry[1] - 140, entry[2] + 105]
        spawn(u.PlayerStart, dict(position=player_start, yaw=-90), environment, 'PlayerStart')
        pp = spawn(u.PostProcessVolume, dict(position=[0, 0, 0]), environment, 'GlobalExposure')
        pp.set_editor_property('unbound', True)
        pp.set_editor_property('priority', 0)
        exposure(pp, dict(exposure_ev=.7, exposure_bias=-.05, indirect_intensity=1,
                          saturation=1, contrast=1, vignette=.3, bloom=.25))
        if hospital_selections:
            container_helpers['ensure_outline'](actors, container_rules['rules']()['outline'],
                                                  'HospitalLine_ContainerOutline', asset, True)
        if not u.EditorLoadingAndSavingUtils.save_map(world, TARGET):
            raise RuntimeError('Hospital subject map save failed')
        write(ROOT / 'Config/line.json', dict(map=TARGET, sequence=sequence, placements=placements,
                     player_start=player_start, source_map=PRODUCTION, source_catalog_sha256=hashlib.sha256(source_text.encode()).hexdigest(),
                     seed=SEED, bed_blood_generation='native BeginPlay, fixed seeds for repeatable visual refinement',
                     monster_spawning=False, return_map='/Game/GameMaps/DayNight_Lighting',
                     hospital_container_revision=catalog.get('hospital_container_revision', 0),
                     hospital_authored_container_count=sum(hospital_selections.values()),
                     hospital_bedside_requested=[2, 3] if hospital_selections else [], container_rewards_deferred=True))
        report.update(stage='map_saved', counts=counts, source_map=PRODUCTION,
                      source_catalog_sha256=hashlib.sha256(source_text.encode()).hexdigest(),
                      monster_spawning=False, original_map=original)
        write(receipt, report)
        print('HOSPITAL_LINE_SUBJECT_SAVED ' + TARGET, flush=True)
    except Exception:
        report.update(stage='authoring_failed', error=traceback.format_exc())
        write(receipt, report)
        raise
    finally:
        if existing_editor and original and original != TARGET and u.EditorAssetLibrary.does_asset_exist(original):
            u.EditorLoadingAndSavingUtils.load_map(original)


main()
