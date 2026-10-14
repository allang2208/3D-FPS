"""Save the user-retained staff-living test route from saved production modules.

Authoring only. Shared assets are referenced, and only the new map is saved.
"""
import hashlib
import json
import traceback
from datetime import datetime
from pathlib import Path

import unreal as u

ROOT = Path(__file__).resolve().parents[1]
PROJECT = ROOT.parents[1]
STAFF = PROJECT / 'SourceAssets/DungeonStaffLiving20261002'
TARGET = '/Game/GameMaps/Design/L_StaffLiving_Theme_Subject'
PRODUCTION = '/Game/GameMaps/L_Dungeon_Randomized'
CHEST_CLASS = '/Game/Dungeons/StationWorkshop20261003/RefineV2/Blueprints/BP_StationUpperTreasure'
PLACEMENTS = [
    dict(id='StaffDormitory', position=[0, 0, 0]),
    dict(id='StaffChangingShowers', position=[3400, 0, 0]),
    dict(id='StaffRecreation', position=[6900, -600, 0]),
]


def write(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding='utf8')


def main():
    for folder in ('Config', 'Receipts'):
        (ROOT / folder).mkdir(parents=True, exist_ok=True)
    if Path(u.Paths.project_dir()).resolve() != PROJECT.resolve():
        raise RuntimeError('Wrong project for staff-living subject')
    existing_editor = globals().get('STAFF_TEST_EXISTING_EDITOR', False)
    if '-run=pythonscript' not in u.SystemLibrary.get_command_line().lower() and not existing_editor:
        raise RuntimeError('Background commandlet or existing editor bridge required')
    editor = u.get_editor_subsystem(u.UnrealEditorSubsystem)
    if editor and editor.get_game_world():
        raise RuntimeError('Preserve active PIE session; finish playing before saving the new map')
    dirty_maps = [p.get_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_map_packages()]
    if dirty_maps:
        raise RuntimeError('Preserve unsaved maps: ' + str(dirty_maps))
    previous_world = editor.get_editor_world().get_path_name().split('.')[0] if editor and editor.get_editor_world() else ''
    receipt = ROOT / 'Receipts/install.json'
    if u.EditorAssetLibrary.does_asset_exist(TARGET):
        if receipt.exists() and json.loads(receipt.read_text('utf8')).get('stage') == 'map_saved':
            print('STAFF_LIVING_TEST_ALREADY_SAVED ' + TARGET, flush=True)
            return
        raise RuntimeError('Preserve pre-existing staff-living subject map')

    actors = u.get_editor_subsystem(u.EditorActorSubsystem) or u.new_object(u.EditorActorSubsystem)
    production_world = u.EditorLoadingAndSavingUtils.load_map(PRODUCTION)
    if not production_world:
        raise RuntimeError('Saved production world unavailable')
    generators = u.GameplayStatics.get_all_actors_of_class(production_world, u.AuthoredDungeonGenerator)
    if len(generators) != 1:
        raise RuntimeError('Saved production generator unavailable')
    source_json = generators[0].get_editor_property('module_catalog_json')
    by_id = {m['id']: m for m in json.loads(source_json)['modules']}
    modules = [by_id[p['id']] for p in PLACEMENTS]
    outline = json.loads((STAFF / 'Config/modules-draft.json').read_text('utf8'))['container_outline']
    report = dict(stage='authoring', map=TARGET, source_map=PRODUCTION,
                  source_catalog_sha256=hashlib.sha256(source_json.encode('utf8')).hexdigest(),
                  retained_for_user_testing=True, tests_run=False, rendered=False,
                  game_run=False, editor_opened=False,
                  save_mode='existing_editor_bridge' if existing_editor else 'background_commandlet')
    write(receipt, report)
    write(ROOT / 'Config/modules.json', dict(source_map=PRODUCTION, modules=modules,
          placements=PLACEMENTS, container_outline=outline, retained_for_user_testing=True))

    # Loading the production map above only reads its serialized descriptors.
    # Switch worlds before authoring; never save the source map or shared assets.
    world = u.EditorLoadingAndSavingUtils.new_blank_map(False)
    if not world:
        raise RuntimeError('New staff-living world unavailable')
    world.get_world_settings().set_editor_property('default_game_mode',
        u.load_class(None, '/Script/FPSGAME.FPSGAMEGameMode'))
    counts = dict(static_meshes=0, lights=0, scene_containers=0, treasure_chests=0,
                  layout_managers=0, layout_furniture=0)
    cache = {}

    def asset(path):
        if path not in cache:
            cache[path] = u.load_asset(path)
            if not cache[path]:
                raise RuntimeError('Missing shared staff asset: ' + path)
        return cache[path]

    def spawn(cls, spec, pose, label, tags=()):
        local = spec.get('position', [0, 0, 0])
        location = u.Vector(*(local[i] + pose['position'][i] for i in range(3)))
        rotation = u.Rotator(pitch=spec.get('pitch', 0), yaw=spec.get('yaw', 0), roll=spec.get('roll', 0))
        actor = actors.spawn_actor_from_class(cls, location, rotation)
        if not actor:
            raise RuntimeError('Cannot create staff actor: ' + label)
        actor.set_actor_label('StaffTest_' + label)
        actor.set_folder_path('StaffLivingTest/' + pose['id'])
        actor.set_editor_property('tags', [u.Name('StaffLivingTest.Subject'), u.Name(pose['id']),
                                           *(u.Name(t) for t in tags)])
        actor.set_actor_scale3d(u.Vector(*spec.get('scale', [1, 1, 1])))
        return actor

    def static(spec, pose, label):
        slot = spec.get('layout_slot')
        tags = ['StaffDormitory.LayoutSlot.' + slot] if slot else []
        if spec.get('guardrail_drop'):
            tags.append('Traversal.GuardrailDrop')
        actor = spawn(u.StaticMeshActor, spec, pose, label, tags)
        component = actor.static_mesh_component
        component.set_mobility(u.ComponentMobility.MOVABLE if slot else u.ComponentMobility.STATIC)
        component.set_static_mesh(asset(spec['mesh']))
        component.set_collision_profile_name('BlockAll' if spec.get('collision', True) else 'NoCollision')
        component.set_cast_shadow(spec.get('cast_shadow', True))
        for index, path in enumerate(spec.get('materials', [])):
            if path:
                component.set_material(index, asset(path))
        counts['static_meshes'] += 1
        return actor

    def light(spec, pose, label):
        actor = spawn(u.PointLight, spec, pose, label, ['Dungeon.Light.' + spec.get('role', 'path')])
        component = actor.get_component_by_class(u.PointLightComponent)
        component.set_mobility(u.ComponentMobility.MOVABLE)
        component.set_editor_property('intensity_units', u.LightUnits.LUMENS)
        component.set_intensity(spec['intensity'])
        component.set_editor_property('attenuation_radius', spec.get('optimized_radius_cm', spec['radius']))
        component.set_editor_property('cast_shadows', spec.get('cast_shadows', True))
        component.set_editor_property('max_draw_distance', spec.get('max_draw_distance_cm', 2600))
        component.set_editor_property('max_distance_fade_range', spec.get('fade_range_cm', 550))
        component.set_editor_property('indirect_lighting_intensity', spec.get('indirect_lighting_intensity', .65))
        for key in ('source_radius', 'source_length', 'volumetric_scattering_intensity'):
            if key in spec:
                component.set_editor_property(key, spec[key])
        component.set_light_color(u.LinearColor(*spec['color'], 1))
        counts['lights'] += 1

    container_class = u.load_class(None, '/Script/FPSGAME.ColdSteelSceneContainer')
    layout_class = u.load_class(None, '/Script/FPSGAME.StaffDormitoryLayout')
    if not container_class or not layout_class:
        raise RuntimeError('Existing staff gameplay classes unavailable')

    def container(spec, pose, layout_slots):
        identity = spec['container_id']
        slot = spec.get('layout_slot', identity.split('.', 1)[-1])
        tags = ['ColdSteel.SceneContainer']
        if slot in layout_slots:
            tags.append('StaffDormitory.LayoutSlot.' + slot)
        if spec.get('initial_random_open'):
            tags.append(spec.get('random_open_tag', 'ColdSteel.SceneContainer.RandomOpen'))
        actor = spawn(container_class, spec, pose, identity, tags)
        actor.set_editor_property('container_id', 'StaffLivingTest.' + identity)
        for key in ('caption', 'storage_pages', 'opened_yaw', 'opened_roll', 'initial_open_fraction'):
            if key in spec:
                actor.set_editor_property(key, spec[key])
        motion = dict(Swing='SWING', Drawer='DRAWER', OpenShelf='OPEN_SHELF', Lid='LID')
        actor.set_editor_property('opening_motion', getattr(u.ColdSteelContainerMotion, motion[spec.get('opening_motion', 'Swing')]))
        if 'drawer_travel' in spec:
            actor.set_editor_property('drawer_travel', u.Vector(*spec['drawer_travel']))
        actor.body.set_static_mesh(asset(spec['body']))
        actor.door.set_static_mesh(asset(spec['door']) if spec.get('door') else None)
        actor.door_hinge.set_relative_location(u.Vector(*spec.get('hinge', [0, 0, 0])), False, False)
        actor.door_hinge.set_mobility(u.ComponentMobility.MOVABLE)
        actor.body.set_collision_profile_name('BlockAll')
        actor.door.set_collision_profile_name('NoCollision')
        for component, key in ((actor.body, 'body_materials'), (actor.door, 'door_materials')):
            component.set_mobility(u.ComponentMobility.MOVABLE)
            component.set_render_custom_depth(False)
            component.set_custom_depth_stencil_value(201)
            for index, path in enumerate(spec.get(key, [])):
                if path:
                    component.set_material(index, asset(path))
        counts['scene_containers'] += 1
        return actor, slot

    def treasure(spec, pose, index):
        # Reuse the saved skeletal chest Blueprint: its box belongs to the
        # chest actor, so the existing interaction trace hits the correct owner.
        cls = u.EditorAssetLibrary.load_blueprint_class(CHEST_CLASS)
        if not cls:
            raise RuntimeError('Shared treasure Blueprint unavailable')
        identity = spec.get('identity', pose['id'] + '_' + str(index))
        actor = spawn(cls, spec, pose, pose['id'] + '_Treasure_' + str(index),
                      ['DungeonTreasureChest', 'FutureTreasureLoot', 'DungeonChestClaim.StaffLivingTest.' + identity])
        component = actor.get_component_by_class(u.SkeletalMeshComponent)
        component.set_mobility(u.ComponentMobility.MOVABLE)
        component.set_skeletal_mesh_asset(asset(spec['skeletal_mesh']))
        component.set_collision_profile_name('NoCollision')
        for index in range(component.get_num_materials()):
            material = component.get_material(index)
            path = spec.get('material_overrides', {}).get(material.get_name() if material else '')
            if path:
                component.set_material(index, asset(path))
        closed = asset(spec['closed_animation'])
        component.override_animation_data(closed, False, False, closed.get_editor_property('sequence_length'), 0.)
        collision = actor.get_component_by_class(u.BoxComponent)
        collision.set_box_extent(u.Vector(*spec['collision_extent']), False)
        collision.set_relative_location(u.Vector(*spec['collision_center']), False, False)
        collision.set_collision_profile_name('BlockAll')
        counts['treasure_chests'] += 1

    for pose, module in zip(PLACEMENTS, modules):
        layouts = [module[key] for key in ('layout_variants', 'recreation_chair_layout_variants') if key in module]
        slots = {p['id'] for layout in layouts for room in layout['rooms']
                 for variant in room['variants'] for p in variant['placements']}
        movable = []
        for index, spec in enumerate(module['parts']):
            actor = static(spec, pose, pose['id'] + '_Part_' + str(index))
            if spec.get('layout_slot') in slots:
                movable.append(actor)
        for spec in module.get('scene_containers', []):
            actor, slot = container(spec, pose, slots)
            if slot in slots:
                movable.append(actor)
        for index, spec in enumerate(module['lights']):
            light(spec, pose, pose['id'] + '_Light_' + str(index))
        for index, spec in enumerate(module.get('props', [])):
            treasure(spec, pose, index)
        for index, layout in enumerate(layouts):
            manager = spawn(layout_class, {}, pose, pose['id'] + '_Layout_' + str(index))
            manager.set_editor_property('layout_json', json.dumps(layout, ensure_ascii=False, separators=(',', ':')))
            manager.set_editor_property('layout_actors', movable)
            manager.set_editor_property('random_seed', -1)
            counts['layout_managers'] += 1
        counts['layout_furniture'] += len(movable)

    base = '/Game/Dungeons/StaffLiving20261002'
    link_parts = [dict(mesh=base + '/Meshes/SM_Staff_Link_' + kind, collision=True)
                  for kind in ('Floors', 'Paving', 'Walls', 'Roof')]
    link_parts += [dict(mesh=base + '/IntactTilesV4/Meshes/SM_Staff_Link_Tiles_V4', collision=False),
                   dict(mesh=base + '/RefinementV3/Meshes/SM_Staff_Link_Carpet_V3', collision=False)]
    for x in (1600, 4800):
        pose = dict(id='Links', position=[x, 0, 0])
        for index, spec in enumerate(link_parts):
            static(spec, pose, 'Link_' + str(x) + '_' + str(index))
        static(dict(mesh=base + '/ScenePolishV4/Meshes/SM_Staff_Link_CarpetEdges_V4', collision=False),
               pose, 'LinkCarpetEdges_' + str(x))
    environment = dict(id='Environment', position=[0, 0, 0])
    for x in (-1600, 8600):
        static(dict(mesh='/Engine/BasicShapes/Cube', position=[x, 0, 140], scale=[.13, 3, 2.8],
                    collision=True, materials=[base + '/Materials/M_Staff_OlivePaint']), environment, 'EndCap_' + str(x))
    spawn(u.PlayerStart, dict(position=[-1500, 0, 105]), environment, 'PlayerStart')

    pp_spec = next(s for s in modules[0]['runtime_actors'] if s['type'] == 'post_process')
    pp = spawn(u.PostProcessVolume, {}, environment, 'ExposureAndContainerOutline', ['ColdSteel.SceneContainer.Outline'])
    pp.set_editor_property('unbound', True)
    settings = pp.get_editor_property('settings')
    values = dict(auto_exposure_min_brightness=pp_spec['exposure_ev'],
                  auto_exposure_max_brightness=pp_spec['exposure_ev'], auto_exposure_bias=pp_spec['exposure_bias'],
                  indirect_lighting_intensity=pp_spec['indirect_intensity'], bloom_intensity=pp_spec['bloom'],
                  vignette_intensity=pp_spec['vignette'],
                  color_saturation=u.Vector4(pp_spec['saturation'], pp_spec['saturation'], pp_spec['saturation'], 1),
                  color_contrast=u.Vector4(pp_spec['contrast'], pp_spec['contrast'], pp_spec['contrast'], 1))
    for key, value in values.items():
        settings.set_editor_property('override_' + key, True)
        settings.set_editor_property(key, value)
    blend = u.WeightedBlendable()
    blend.set_editor_property('weight', 1.)
    blend.set_editor_property('object', asset(outline))
    blends = u.WeightedBlendables()
    blends.set_editor_property('array', [blend])
    settings.set_editor_property('weighted_blendables', blends)
    pp.set_editor_property('settings', settings)

    if not u.EditorLoadingAndSavingUtils.save_map(world, TARGET):
        raise RuntimeError('Staff-living test map save failed')
    report.update(stage='map_saved', saved_at=datetime.now().isoformat(timespec='seconds'), counts=counts,
                  sequence=[p['id'] for p in PLACEMENTS], placements=PLACEMENTS,
                  player_start_cm=[-1500, 0, 105], shared_treasure_blueprint=CHEST_CLASS,
                  open_command='open ' + TARGET, return_command='open /Game/GameMaps/DayNight_Lighting')
    write(receipt, report)
    print('STAFF_LIVING_TEST_MAP_SAVED ' + TARGET + ' ' + json.dumps(counts), flush=True)
    if existing_editor and previous_world.startswith('/Game/') and previous_world != TARGET:
        u.EditorLoadingAndSavingUtils.load_map(previous_world)


try:
    main()
except Exception:
    (ROOT / 'Receipts').mkdir(parents=True, exist_ok=True)
    (ROOT / 'Receipts/error.txt').write_text(traceback.format_exc(), encoding='utf8')
    raise
