"""Bake a dense tall-grass map. Authoring only: no PIE, audit or screenshots."""
import datetime
import json
import pathlib
import random
import shutil

import unreal as u

ROOT = pathlib.Path(u.Paths.project_dir()).resolve()
LEVEL = '/Game/GameMaps/L_GrassDeformDenseTest'
DEST = '/Game/WorldGeneration/GrassDeform/DenseTest'
SEED = 20260926
HALF_SIZE = 3200.0
SPACING = 40.0
OWNED = 'GrassDenseTest.Authored'
STAMP = datetime.datetime.now().strftime('%Y%m%d-%H%M%S')
OUT = ROOT / 'SourceAssets' / 'GrassDenseTest20260926'
OUT.mkdir(parents=True, exist_ok=True)
eal = u.EditorAssetLibrary
mel = u.MaterialEditingLibrary
actors = u.get_editor_subsystem(u.EditorActorSubsystem)
levels = u.get_editor_subsystem(u.LevelEditorSubsystem)


def required(path):
    asset = eal.load_asset(path)
    if asset is None:
        raise RuntimeError('Missing authoring dependency: ' + path)
    return asset


def backup(package, extension):
    source = ROOT / 'Content' / (package.removeprefix('/Game/') + extension)
    if source.exists():
        target = OUT / ('Before-' + STAMP) / source.relative_to(ROOT / 'Content')
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)


def spawn(cls, label, position=(0, 0, 0), rotation=(0, 0, 0)):
    actor = actors.spawn_actor_from_class(cls, u.Vector(*position), u.Rotator(*rotation))
    if actor is None:
        raise RuntimeError('Could not author ' + label)
    actor.set_actor_label(label)
    actor.set_editor_property('tags', [OWNED])
    return actor


def ground_material():
    path = DEST + '/M_GrassTestGround'
    backup(path, '.uasset')
    material = eal.load_asset(path) if eal.does_asset_exist(path) else None
    if material is None:
        material = u.AssetToolsHelpers.get_asset_tools().create_asset(
            'M_GrassTestGround', DEST, u.Material, u.MaterialFactoryNew())
        color = mel.create_material_expression(material, u.MaterialExpressionConstant3Vector, -260, 0)
        color.set_editor_property('constant', u.LinearColor(.055, .067, .022, 1))
        mel.connect_material_property(color, '', u.MaterialProperty.MP_BASE_COLOR)
        rough = mel.create_material_expression(material, u.MaterialExpressionConstant, -260, 100)
        rough.set_editor_property('r', .95)
        mel.connect_material_property(rough, '', u.MaterialProperty.MP_ROUGHNESS)
    errors = mel.recompile_material(material)
    if errors:
        raise RuntimeError('Ground material compile failed: ' + str(errors))
    if not eal.save_loaded_asset(material, only_if_is_dirty=False):
        raise RuntimeError('Ground material was not saved')
    return material


mesh_paths = [
    '/Game/WorldGeneration/TemperateHills/Grass/SM_Meadow_grass_03_08_mesh',
    '/Game/WorldGeneration/TemperateHills/Grass/SM_Meadow_grass_05_03_mesh',
]
meshes = [required(path) for path in mesh_paths]
cube = required('/Engine/BasicShapes/Cube')
ground = ground_material()
backup(LEVEL, '.umap')
if eal.does_asset_exist(LEVEL):
    if not levels.load_level(LEVEL):
        raise RuntimeError('Cannot open authored grass level')
    for actor in actors.get_all_level_actors():
        if OWNED in [str(tag) for tag in actor.get_editor_property('tags')]:
            actors.destroy_actor(actor)
elif not levels.new_level(LEVEL):
    raise RuntimeError('Cannot create grass level')

world = u.get_editor_subsystem(u.UnrealEditorSubsystem).get_editor_world()
world.get_world_settings().set_editor_property('default_game_mode', u.FPSGAMEGameMode)
floor = spawn(u.StaticMeshActor, 'Grass test ground', (0, 0, -50))
floor.set_actor_scale3d(u.Vector(200, 200, 1))
floor_component = floor.static_mesh_component
floor_component.set_static_mesh(cube)
floor_component.set_material(0, ground)
floor_component.set_mobility(u.ComponentMobility.STATIC)
floor_component.set_collision_profile_name('BlockAll')
floor_component.set_collision_enabled(u.CollisionEnabled.QUERY_AND_PHYSICS)

field = spawn(u.GrassDeformTestField, 'Dense tall grass - 64m field')
components = [field.get_editor_property('tall_grass_a'), field.get_editor_property('tall_grass_b')]
mesh_bounds = [mesh.get_bounding_box() for mesh in meshes]
transforms = [[], []]
rng = random.Random(SEED)
side = int(HALF_SIZE * 2 / SPACING)
for row in range(side):
    for col in range(side):
        x = -HALF_SIZE + (col + .5) * SPACING + rng.uniform(-12, 12)
        y = -HALF_SIZE + (row + .5) * SPACING + rng.uniform(-12, 12)
        # One small clear patch connects PlayerStart to the return portal at (-3500, 0).
        if x < -2770 and abs(y) < 190:
            continue
        which = rng.randrange(2)
        bounds = mesh_bounds[which]
        height = rng.uniform(130, 170)
        z_scale = height / (bounds.max.z - bounds.min.z)
        xy_scale = rng.uniform(1.25, 1.6)
        z = -bounds.min.z * z_scale
        transform = u.Transform(
            location=u.Vector(x, y, z),
            rotation=u.Rotator(0, rng.uniform(-180, 180), 0),
            scale=u.Vector(xy_scale, xy_scale, z_scale))
        transforms[which].append(transform)

for index, component in enumerate(components):
    component.set_static_mesh(meshes[index])
    component.add_instances(transforms[index], False, False, False)

spawn(u.PlayerStart, 'Grass test spawn - face into field', (-3070, 0, 110))
sun = spawn(u.DirectionalLight, 'Grass test sun', (0, 0, 10000), (-38, -30, 0))
sun.light_component.set_mobility(u.ComponentMobility.MOVABLE)
sun.light_component.set_editor_property('intensity', 5.0)
sun.light_component.set_editor_property('atmosphere_sun_light', True)
sun.light_component.set_editor_property('light_source_angle', 1.4)
spawn(u.SkyAtmosphere, 'Grass test atmosphere')
sky = spawn(u.SkyLight, 'Grass test skylight', (0, 0, 5000))
sky.light_component.set_mobility(u.ComponentMobility.MOVABLE)
sky.light_component.set_editor_property('real_time_capture', True)
sky.light_component.set_editor_property('intensity', .9)
sky.light_component.set_editor_property('lower_hemisphere_is_black', False)
fog = spawn(u.ExponentialHeightFog, 'Grass test horizon haze')
fog.component.set_editor_property('fog_density', .005)
fog.component.set_editor_property('fog_height_falloff', .2)
fog.component.set_editor_property('fog_inscattering_luminance', u.LinearColor(.42, .58, .78, 1))
weather = spawn(u.FPSWeatherManager, 'Grass test clear weather')
weather.set_editor_property('automatic_schedule', False)
post = spawn(u.PostProcessVolume, 'Grass test fixed exposure')
post.set_editor_property('unbound', True)
settings = post.get_editor_property('settings')
for key, value in [('override_auto_exposure_min_brightness', True),
                   ('override_auto_exposure_max_brightness', True),
                   ('auto_exposure_min_brightness', 1.0), ('auto_exposure_max_brightness', 1.0)]:
    settings.set_editor_property(key, value)
post.set_editor_property('settings', settings)

if not levels.save_current_level():
    raise RuntimeError('Grass level was not saved')
receipt = dict(map=LEVEL, seed=SEED, dimensions_m=[64, 64], height_cm=[130, 170],
               spacing_cm=SPACING, meshes=mesh_paths, instance_counts=[len(items) for items in transforms],
               total_instances=sum(len(items) for items in transforms),
               material_function='/Game/WorldGeneration/GrassDeform/MF_GrassDeform',
               entry='Hub/hills: 600cm left of spawn; E within 200cm',
               return_portal_cm=[-3500, 0, .5], runtime_tested=False)
(OUT / ('authored-' + STAMP + '.json')).write_text(json.dumps(receipt, indent=2), encoding='utf-8')
u.log('GRASS_DENSE_TEST_SAVED ' + json.dumps(receipt))
