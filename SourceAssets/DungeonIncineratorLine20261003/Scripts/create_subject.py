"""Save three treatment rooms from the live production catalog, without playing them."""
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
TARGET = '/Game/GameMaps/Design/L_Incinerator_Theme_Subject'
PRODUCTION = '/Game/GameMaps/L_Dungeon_Randomized'
SEQUENCE = ['ShoredBreach', 'AbandonedIncineratorHall', 'AbandonedFlueGasStation']
SEED = 20261003
SUBJECT_TAG = 'IncineratorLine.Subject'
BLOOD_TAG = 'IncineratorLine.BloodReceiver'


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding='utf8')


def main():
    if Path(u.Paths.project_dir()).resolve() != PROJECT.resolve():
        raise RuntimeError('Wrong project for incinerator line authoring')
    existing_editor = globals().get('INCINERATOR_LINE_EXISTING_EDITOR', False)
    if '-run=pythonscript' not in u.SystemLibrary.get_command_line().lower() and not existing_editor:
        raise RuntimeError('Commandlet or existing editor bridge required')
    editor = u.get_editor_subsystem(u.UnrealEditorSubsystem)
    if editor and editor.get_game_world():
        raise RuntimeError('Preserve active game session')
    dirty = [p.get_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_map_packages()]
    if dirty:
        raise RuntimeError('Preserve unsaved maps: ' + str(dirty))
    receipt = ROOT / 'Receipts/install.json'
    if u.EditorAssetLibrary.does_asset_exist(TARGET):
        if receipt.exists() and json.loads(receipt.read_text('utf8')).get('stage') == 'map_saved':
            print('INCINERATOR_LINE_ALREADY_SAVED ' + TARGET, flush=True)
            return
        raise RuntimeError('Preserve existing incinerator subject map')
    original = editor.get_editor_world().get_path_name().split('.')[0] if editor and editor.get_editor_world() else ''
    actors = u.get_editor_subsystem(u.EditorActorSubsystem) or u.new_object(u.EditorActorSubsystem)
    report = dict(stage='authoring', map=TARGET, tests_run=False, rendered=False,
                  game_run=False, editor_opened=False, seed=SEED)
    write(receipt, report)
    counts = dict(mesh_actors=0, lights=0, runtime_actors={})
    cache = {}

    def asset(path):
        if path not in cache:
            cache[path] = u.load_asset(path)
            if not cache[path]:
                raise RuntimeError('Missing production asset: ' + path)
        return cache[path]

    def vector(values):
        return u.Vector(*values)

    def struct(cls, **properties):
        result = cls()
        for key, value in properties.items():
            result.set_editor_property(key, value)
        return result

    def transform(position, pose):
        angle = math.radians(pose['yaw'])
        x, y, z = position
        origin = pose['position']
        return [x * math.cos(angle) - y * math.sin(angle) + origin[0],
                x * math.sin(angle) + y * math.cos(angle) + origin[1], z + origin[2]]

    def spawn(cls, spec, pose, label, extra=()):
        actor = actors.spawn_actor_from_class(cls, vector(transform(spec.get('position', [0, 0, 0]), pose)),
            u.Rotator(pitch=spec.get('pitch', 0), yaw=pose['yaw'] + spec.get('yaw', 0), roll=spec.get('roll', 0)))
        if not actor:
            raise RuntimeError('Actor creation failed: ' + label)
        room = pose.get('name', pose['id'])
        actor.set_actor_label('IncineratorLine_' + label)
        actor.set_folder_path('IncineratorLine/' + room)
        actor.set_editor_property('tags', [u.Name(SUBJECT_TAG), u.Name(room), *(u.Name(t) for t in extra)])
        return actor

    def static(spec, pose, label):
        tags = []
        if spec.get('treatment_container_fixed'):
            tags.append('TreatmentContainers.Preview')
        if spec.get('guardrail_drop'):
            tags.append('Traversal.GuardrailDrop')
        if spec.get('blood_receiver'):
            tags.append(BLOOD_TAG)
        if spec.get('wall_art'):
            tags.append('DungeonWallArt')
        actor = spawn(u.StaticMeshActor, spec, pose, label, tags)
        component = actor.static_mesh_component
        component.set_mobility(u.ComponentMobility.MOVABLE if spec.get('fluid') else u.ComponentMobility.STATIC)
        component.set_static_mesh(asset(spec['mesh']))
        component.set_collision_profile_name('BlockAll' if spec.get('collision', True) else 'NoCollision')
        default_shadow = not spec['mesh'].endswith(('_Fixtures', '_Debris'))
        component.set_cast_shadow(spec.get('cast_shadow', default_shadow) and not spec.get('fluid') and not spec.get('wall_art'))
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
        counts['mesh_actors'] += 1

    def light(spec, pose, label, role, cells):
        # Same optimized role, cone, reach and authored overrides as the production generator.
        spot = spec.get('type', 'spot' if role in ('corridor', 'fill') else 'point') == 'spot'
        light_spec = dict(spec)
        if spot:
            light_spec['pitch'] = -90
        actor = spawn(u.SpotLight if spot else u.PointLight, light_spec, pose, label, ['DungeonLight.' + role])
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
            clearance = max([0, *(min(p[0] - c['min'][0], c['max'][0] - p[0],
                                     p[1] - c['min'][1], c['max'][1] - p[1]) - 35 for c in cells)])
            shadows = (radius * math.sin(math.radians(outer)) if spot else radius) > clearance
        component.set_intensity(intensity)
        component.set_editor_property('attenuation_radius', max(1, radius))
        component.set_editor_property('cast_shadows', spec.get('cast_shadows', shadows))
        component.set_editor_property('max_draw_distance', spec.get('max_draw_distance_cm', 1400 if role == 'fill' else 1800 if role == 'corridor' else 2400))
        component.set_editor_property('max_distance_fade_range', spec.get('fade_range_cm', 400 if role == 'fill' else 500))
        for key, default in (('source_radius', 5), ('source_length', 0 if spot else 60),
                             ('indirect_lighting_intensity', 1), ('volumetric_scattering_intensity', 1)):
            component.set_editor_property(key, spec.get(key, default))
        component.set_light_color(u.LinearColor(*spec['color'], 1))
        if spec.get('light_function'):
            component.set_light_function_material(asset(spec['light_function']))
            component.set_editor_property('light_function_fade_distance', spec.get('light_function_fade_distance', 2700))
            component.set_editor_property('disabled_brightness', spec.get('disabled_brightness', 1))
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

    def exposure_class():
        path = '/Game/Dungeons/IncineratorLine20261003/Blueprints/BP_IncineratorLineExposure'
        if not u.EditorAssetLibrary.does_asset_exist(path):
            factory = u.BlueprintFactory()
            factory.set_editor_property('parent_class', u.Actor)
            blueprint = u.AssetToolsHelpers.get_asset_tools().create_asset(
                'BP_IncineratorLineExposure', path.rsplit('/', 1)[0], u.Blueprint, factory)
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
            component('RoomExposure', u.PostProcessComponent, bounds_handle)
            u.BlueprintEditorLibrary.compile_blueprint(blueprint)
            if not u.EditorAssetLibrary.save_asset(path, only_if_is_dirty=False):
                raise RuntimeError('Incinerator exposure Blueprint save failed')
        result = u.EditorAssetLibrary.load_blueprint_class(path)
        if not result:
            raise RuntimeError('Incinerator exposure Blueprint unavailable')
        report['exposure_blueprint'] = path
        return result

    def runtime(spec, pose, label, index):
        kind = spec['type']
        if kind == 'decal':
            actor = spawn(u.DecalActor, spec, pose, label)
            component = actor.get_component_by_class(u.DecalComponent)
            component.set_decal_material(asset(spec['material']))
            component.set_editor_property('decal_size', vector(spec['decal_size']))
            component.set_sort_order(spec['sort_order'])
            component.set_fade_screen_size(spec['fade_screen_size'])
        elif kind == 'blood':
            actor = spawn(u.DungeonBloodScatter, spec, pose, label)
            actor.set_editor_property('receiver_tag', u.Name(BLOOD_TAG))
            actor.set_editor_property('blood_material', asset(spec['material']))
            for key in ('floor_count', 'wall_count', 'floor_size_scale'):
                actor.set_editor_property(key, spec[key])
            actor.set_editor_property('scanned_size_range_cm', u.Vector2D(*spec['scanned_size_range_cm']))
            actor.set_editor_property('surfaces', [struct(u.DungeonBloodSurface, center=vector(s['center']),
                normal=vector(s['normal']), axis_u=vector(s['axis_u']),
                half_size=u.Vector2D(*s['half_size']), wall=s['wall']) for s in spec['surfaces']])
            actor.set_editor_property('seed', SEED + index + 1)
            actor.set_editor_property('randomize_on_begin_play', False)
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
            raise RuntimeError('Production treatment actor requires authoring support: ' + kind)
        counts['runtime_actors'][kind] = counts['runtime_actors'].get(kind, 0) + 1

    try:
        source_world = u.EditorLoadingAndSavingUtils.load_map(PRODUCTION)
        generators = u.GameplayStatics.get_all_actors_of_class(source_world, u.AuthoredDungeonGenerator)
        if len(generators) != 1:
            raise RuntimeError('Production dungeon catalog unavailable')
        source_text = generators[0].get_editor_property('module_catalog_json')
        catalog = json.loads(source_text)
        route = next(r for r in catalog['themed_routes']['routes'] if r['id'] == 'treatment')
        if route['sequence'] != SEQUENCE:
            raise RuntimeError('Treatment route changed; preserve descriptors before adapting placement')
        modules = {m['id']: m for m in catalog['modules']}
        selected = [modules[m] for m in ['Transit', 'Threshold', *SEQUENCE]]
        write(ROOT / 'Config/source-modules.json', dict(source_map=PRODUCTION,
            source_catalog_sha256=hashlib.sha256(source_text.encode()).hexdigest(), route=route, modules=selected))
        layout = runpy.run_path(str(ROOT / 'Scripts/subject_layout.py'))
        placements = layout['placements'](modules, SEQUENCE)
        for module in selected:
            groups=module.get('warehouse_containers',{}).get('groups',[])
            if module.get('scene_recipes') or any(not p.get('flue_under_platform_chest') for p in module.get('props',[])) or module.get('progression_gate') or any(not g['id'].startswith('Treatment.') for g in groups):
                raise RuntimeError('Treatment module gained assembly requirements: ' + module['id'])
            if any(s['type'] not in ('decal', 'blood', 'post_process') for s in module.get('runtime_actors', [])):
                raise RuntimeError('Treatment module gained interactive actors: ' + module['id'])
        world = u.EditorLoadingAndSavingUtils.new_blank_map(False)
        if not world:
            raise RuntimeError('New incinerator subject world unavailable')
        world.get_world_settings().set_editor_property('default_game_mode', u.load_class(None, '/Script/FPSGAME.FPSGAMEGameMode'))
        for pose in placements:
            module = copy.deepcopy(modules[pose['id']])
            prefix = pose.get('name', pose['id'])
            for index, spec in enumerate(module['parts']):
                static(spec, pose, prefix + '_' + str(index))
            brightest = sorted(range(len(module['lights'])), key=lambda i: -module['lights'][i]['intensity'])[:2]
            for index, spec in enumerate(module['lights']):
                role = spec.get('role', 'corridor' if pose['id'] == 'Transit' else 'key' if index in brightest else 'fill')
                light(spec, pose, prefix + '_Light_' + str(index), role, module.get('cells', []))
            for index, spec in enumerate(module.get('runtime_actors', [])):
                runtime(spec, pose, prefix + '_Runtime_' + str(index), index)
            if module.get('props'):
                chest_source=PROJECT/'SourceAssets/FlueUnderPlatformChest20261003'
                chest_rules=runpy.run_path(str(chest_source/'Scripts/extend_catalog.py'))['rules']()
                chest_helpers=runpy.run_path(str(chest_source/'Scripts/unreal_helpers.py'))
                for spec in module['props']:
                    chest_helpers['spawn_preview_chest'](actors,spec,pose,asset,chest_rules['preview_blueprint'])
            groups=module.get('warehouse_containers',{}).get('groups',[])
            if groups:
                container_source=PROJECT/'SourceAssets/IncineratorContainers20261003'
                rules=runpy.run_path(str(container_source/'Scripts/catalog_rules.py'))
                helpers=runpy.run_path(str(container_source/'Scripts/unreal_helpers.py'))
                offset=SEQUENCE.index(pose['id'])
                for spec in rules['choose'](groups,SEED+offset):helpers['spawn_container'](actors,spec,pose,asset)
        environment = dict(id='Environment', position=[0, 0, 0], yaw=0)
        first = modules[SEQUENCE[0]]['ports'][0]
        last = modules[SEQUENCE[-1]]['ports'][1]
        for name, port, pose in [('StartCap', first, placements[0]), ('EndCap', last, placements[-1])]:
            position = transform(port['position'], pose)
            position[2] += port['height'] * .5
            normal = port['normal']
            yaw = pose['yaw'] + math.degrees(math.atan2(normal[1], normal[0]))
            static(dict(mesh='/Engine/BasicShapes/Cube', position=position, yaw=yaw,
                scale=[.12, port['width'] / 100, port['height'] / 100], collision=True,
                materials=['/Game/Dungeons/WallUpgrade20260924/Materials/MI_WallConcrete']), environment, name)
        entry = transform(first['position'], placements[0])
        player_start = [entry[0] - first['normal'][0] * 140, entry[1] - first['normal'][1] * 140, entry[2] + 105]
        facing = math.degrees(math.atan2(-first['normal'][1], -first['normal'][0]))
        spawn(u.PlayerStart, dict(position=player_start, yaw=facing), environment, 'PlayerStart')
        pp = spawn(u.PostProcessVolume, dict(position=[0, 0, 0]), environment, 'GlobalExposure')
        pp.set_editor_property('unbound', True)
        pp.set_editor_property('priority', 0)
        exposure(pp, dict(exposure_ev=.7, exposure_bias=-.05, indirect_intensity=1,
                          saturation=1, contrast=1, vignette=.3, bloom=.25))
        container_rule=next((m['warehouse_containers'] for m in selected if m.get('warehouse_containers')),None)
        if container_rule:
            helper=PROJECT/'SourceAssets/IncineratorContainers20261003/Scripts/unreal_helpers.py'
            runpy.run_path(str(helper))['ensure_outline'](actors,container_rule['outline'],'IncineratorLine_ContainerOutline',asset,True)
        if not u.EditorLoadingAndSavingUtils.save_map(world, TARGET):
            raise RuntimeError('Incinerator subject map save failed')
        write(ROOT / 'Config/line.json', dict(map=TARGET, sequence=SEQUENCE, placements=placements,
            player_start=player_start, source_map=PRODUCTION, source_catalog_sha256=hashlib.sha256(source_text.encode()).hexdigest(),
            seed=SEED, blood_generation='native BeginPlay, fixed seeds for repeatable refinement',
            monster_spawning=False, encounter_gates=False, return_map='/Game/GameMaps/DayNight_Lighting',
            keep_maps=['/Game/GameMaps/Design/L_Hospital_Theme_Subject', '/Game/GameMaps/Design/L_FreightTransit_Theme_Subject'],
            layout_revision=layout['REVISION']))
        report.update(stage='map_saved', counts=counts, source_map=PRODUCTION,
            source_catalog_sha256=hashlib.sha256(source_text.encode()).hexdigest(),
            original_map=original, monster_spawning=False, encounter_gates=False)
        write(receipt, report)
        print('INCINERATOR_LINE_SUBJECT_SAVED ' + TARGET, flush=True)
    except Exception:
        report.update(stage='authoring_failed', error=traceback.format_exc())
        write(receipt, report)
        raise
    finally:
        if existing_editor and original and original != TARGET and u.EditorAssetLibrary.does_asset_exist(original):
            u.EditorLoadingAndSavingUtils.load_map(original)


main()
