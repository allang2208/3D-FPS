"""Capture the accepted archive, then incrementally save its production generator.

Authoring/save only: does not generate a dungeon, start play or render.
"""
import copy
import hashlib
import json
import runpy
from pathlib import Path
import unreal as u

ROOT = Path(__file__).resolve().parents[1]
HALL = ROOT.parent
PROJECT = HALL.parents[1]
SAMPLE = '/Game/GameMaps/Design/L_AbandonedDataArchive_Subject'
TARGET = '/Game/GameMaps/L_Dungeon_Randomized'
if Path(u.Paths.project_dir()).resolve() != PROJECT.resolve():
    raise RuntimeError('Wrong project')
if '-run=pythonscript' not in u.SystemLibrary.get_command_line().lower():
    raise RuntimeError('Background save only; never replace an open editor world')
for folder in ('Config', 'Backup', 'Receipts'):
    (ROOT / folder).mkdir(exist_ok=True)

def read(p):
    return json.loads(p.read_text(encoding='utf-8'))

def write(p, value):
    p.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding='utf-8')

def vec(v):
    return [v.x, v.y, v.z]

def asset_path(o):
    return o.get_path_name().split('.')[0]

def point(v):
    return [v[0] * 100, -v[1] * 100, v[2] * 100]

def box(lo, hi):
    a, b = point(lo), point(hi)
    return dict(min=[min(a[i], b[i]) for i in range(3)], max=[max(a[i], b[i]) for i in range(3)])

hall = read(HALL / 'Config/room.json')
module_file = ROOT / 'Config/module.json'
if not module_file.exists():
    world = u.EditorLoadingAndSavingUtils.load_map(SAMPLE)
    if not world:
        raise RuntimeError('Cannot capture accepted sample before retirement')
    pieces, lights, runtime = [], [], []
    mood = None
    for actor in u.get_editor_subsystem(u.EditorActorSubsystem).get_all_level_actors():
        label = actor.get_actor_label()
        tags = [str(t) for t in actor.tags]
        rotation = actor.get_actor_rotation()
        transform = dict(position=vec(actor.get_actor_location()), yaw=rotation.yaw,
                         pitch=rotation.pitch, roll=rotation.roll)
        if isinstance(actor, u.StaticMeshActor):
            c = actor.static_mesh_component
            mesh = c.static_mesh
            if not mesh or 'DataArchive.SampleOnly' in tags or 'SamplePortCaps' in mesh.get_name():
                continue
            collision = c.get_collision_enabled() != u.CollisionEnabled.NO_COLLISION
            pieces.append(dict(**transform, mesh=asset_path(mesh), scale=vec(actor.get_actor_scale3d()),
                collision=collision, affects_navigation=collision, fluid=False,
                materials=[asset_path(c.get_material(i)) if c.get_material(i) else '' for i in range(c.get_num_materials())],
                cast_shadow=c.get_editor_property('cast_shadow'), source_label=label))
        elif isinstance(actor, u.PointLight):
            c = actor.point_light_component
            if not c.get_editor_property('visible') or c.intensity <= 0:
                continue
            color = c.get_light_color()
            spec = dict(**transform, type='point', source_label=label,
                role='path' if 'DataArchive.Role.path' in tags else 'key',
                intensity=c.intensity, radius=c.attenuation_radius, optimized_radius_cm=c.attenuation_radius,
                color=[color.r, color.g, color.b], cast_shadows=c.cast_shadows,
                max_draw_distance_cm=c.max_draw_distance, fade_range_cm=c.max_distance_fade_range,
                source_radius=c.source_radius, source_length=c.source_length,
                indirect_lighting_intensity=c.indirect_lighting_intensity,
                volumetric_scattering_intensity=c.volumetric_scattering_intensity)
            material = c.get_editor_property('light_function_material')
            if material:
                spec.update(light_function=asset_path(material), light_function_fade_distance=c.light_function_fade_distance,
                            disabled_brightness=c.disabled_brightness)
            lights.append(spec)
        elif isinstance(actor, u.PostProcessVolume) and label == 'DataArchive_Exposure':
            settings = actor.get_editor_property('settings')
            mood = dict(exposure_ev=settings.auto_exposure_min_brightness, exposure_bias=settings.auto_exposure_bias,
                indirect_intensity=settings.indirect_lighting_intensity, saturation=settings.color_saturation.x,
                contrast=settings.color_contrast.x, vignette=settings.vignette_intensity, bloom=settings.bloom_intensity)
    if mood is None:
        raise RuntimeError('Accepted room exposure is missing')

    # Cover the octagon in strips, not a huge rectangular blocker over its cut corners.
    cells = [box([-12.2, -8.2, -.95], [12.2, 8.2, 6.42])]
    for low, high, width in ((8, 9.2, 12.2), (9, 10.2, 11.3), (10, 11.2, 10.3), (11, 12.2, 9.3)):
        cells += [box([-width, low, -.95], [width, high, 6.42]),
                  box([-width, -high, -.95], [width, -low, 6.42])]
    cells += [box([-14.2, -2.5, -.35], [-11.8, 2.5, 3.72]),
              box([11.8, -2.5, -.35], [14.2, 2.5, 3.72])]
    # Bound the former sample-wide exposure to the hall and its two vestibules.
    # Identical settings in overlapping strips preserve the approved appearance.
    for cell in cells:
        lo, hi = cell['min'], cell['max']
        runtime.append(dict(type='post_process', position=[(lo[i] + hi[i]) / 2 for i in range(3)],
            yaw=0, extent=[(hi[i] - lo[i]) / 2 for i in range(3)], blend_radius=40, priority=10, **mood))
    centre = [(-3.7,-3.7),(0,-3.7),(3.7,-3.7),(-3.7,3.7),(0,3.7),(3.7,3.7),(-3.7,0),(3.7,0)]
    ring = [(-9,-4),(-9,4),(9,-4),(9,4),(-4,-9),(4,-9),(-4,9),(4,9)]
    anchors = [dict(position=point([x,y,z]), role='archive_combat')
               for locations,z in ((centre,-.55),(ring,.05)) for x,y in locations]
    walk = [box([-5.75,-5.75,-.65],[5.75,5.75,2.2]),
            box([-10.4,-7.8,-.05],[-6.25,7.8,2.8]), box([6.25,-7.8,-.05],[10.4,7.8,2.8]),
            box([-7.8,-10.4,-.05],[7.8,-6.25,2.8]), box([-7.8,6.25,-.05],[7.8,10.4,2.8]),
            box([-14,-1.45,-.65],[-5.7,1.45,2.8]), box([5.7,-1.45,-.65],[14,1.45,2.8]),
            box([-1.45,-10.1,-.65],[1.45,-5.7,2.8]), box([-1.45,5.7,-.65],[1.45,10.1,2.8])]
    module = dict(id='AbandonedDataArchive', family_id='AbandonedDataArchive', role='room',
        encounter_role='special_combat', revision='archive_accepted_v2_pool_20261001',
        min=[-1420,-1220,-95], max=[1420,1220,642], cells=cells,
        ports=[dict(id=p['id'], position=point(p['position']), normal=[p['normal'][0],-p['normal'][1],p['normal'][2]],
                    width=p['width']*100, height=p['height']*100) for p in hall['ports']],
        port_pairs=[[0,1]], parts=pieces, lights=lights, runtime_actors=runtime, anchors=anchors, walk_mask=walk,
        walk_polyline=[[-1400,0,5],[-850,0,5],[-810,0,-10],[-750,0,-25],[-690,0,-40],[-630,0,-55],
                       [630,0,-55],[690,0,-40],[750,0,-25],[810,0,-10],[850,0,5],[1400,0,5]],
        selection=dict(chance_per_run=.3, max_per_run=1, route='Approach'))
    write(module_file, module)
else:
    module = read(module_file)

world = u.EditorLoadingAndSavingUtils.load_map(TARGET)
if not world:
    raise RuntimeError('Cannot load production map')
generators = u.GameplayStatics.get_all_actors_of_class(world, u.AuthoredDungeonGenerator)
if len(generators) != 1:
    raise RuntimeError('Expected one production generator')
g = generators[0]
before = g.get_editor_property('module_catalog_json')
catalog = json.loads(before)
backup = ROOT / 'Backup' / ('catalog-' + hashlib.sha256(before.encode()).hexdigest()[:12] + '.json')
if not backup.exists():
    backup.write_text(before, encoding='utf-8')
spawn = copy.deepcopy(next(m for m in catalog['modules'] if m['id']=='FreightTransfer')['spawn'])
spawn.update(source='DungeonDataArchive20260930', count=[4,6], anchor_roles=['archive_combat'],
             theme='abandoned_data_archive', sealed_encounter=True)
module['spawn'] = spawn
helpers = runpy.run_path(str(ROOT / 'Scripts/extend_catalog.py'))
assets = {a.get_path_name(): a for a in g.get_editor_property('module_assets') if a}
for item in sorted(set(helpers['asset_paths'](module))):
    asset = u.load_class(None, item) if item.startswith('/Script/') or item.endswith('_C') else u.load_asset(item)
    if not asset:
        raise RuntimeError('Missing production dependency ' + item)
    assets[asset.get_path_name()] = asset
module['runtime_assets'] = sorted(set(helpers['asset_paths'](module['runtime_actors'])))
catalog = helpers['extend'](catalog, module)
g.modify()
g.set_editor_property('module_catalog_json', json.dumps(catalog, ensure_ascii=False))
g.set_editor_property('module_assets', list(assets.values()))
dirty = list(u.EditorLoadingAndSavingUtils.get_dirty_map_packages()) + list(u.EditorLoadingAndSavingUtils.get_dirty_content_packages())
packages = [p for p in dirty if 'gamemaps/l_dungeon_randomized' in p.get_name().lower()]
if not packages or not u.EditorLoadingAndSavingUtils.save_packages(packages, False):
    raise RuntimeError('Cannot save production generator packages')
write(PROJECT / 'SourceAssets/DungeonRoutes20260922/Config/catalog.json', catalog)
write(module_file, module)
write(ROOT / 'Receipts/install.json', dict(stage='map_saved', map=TARGET, module=module['id'],
    room_ids=catalog['room_ids'], saved_packages=[p.get_name() for p in packages],
    parts=len(module['parts']), lights=len(module['lights']), runtime_actors=len(module['runtime_actors']),
    anchors=len(module['anchors']), selection=module['selection'], spawn_count=spawn['count'],
    sample_port_caps_included=False, tests_run=False, rendered=False))
print('DATA_ARCHIVE_POOL_MAP_SAVED ' + TARGET, flush=True)
