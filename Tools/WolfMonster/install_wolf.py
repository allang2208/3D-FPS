"""Author the playable wolf's assets. No level loading, PIE or acceptance run."""
import json
import math
from pathlib import Path
import unreal as u

PROJECT = Path(__file__).resolve().parents[2]
OUT = PROJECT / 'SourceAssets/WolfMonster'
DEST = '/Game/Monsters/Wolf'
SOURCE = '/Game/AnimalVarietyPack/Wolf/Meshes'
TEMPLATE = '/Game/Monsters/QuadrupedTemplates/WolfV1'
lib = u.EditorAssetLibrary
assets = u.AssetToolsHelpers.get_asset_tools()
motion = json.loads((OUT / 'reference_motion.json').read_text(encoding='utf-8'))
created_paths = []
preserved_paths = []

def save(asset):
    if not lib.save_loaded_asset(asset, False):
        raise RuntimeError('Could not save ' + asset.get_path_name())

def duplicate(source, name):
    path = DEST + '/' + name
    if lib.does_asset_exist(path):
        preserved_paths.append(path)
        return u.load_asset(path)
    result = lib.duplicate_asset(source, path)
    if result is None:
        raise RuntimeError('Could not duplicate ' + source)
    created_paths.append(path)
    return result

def initialized(asset):
    return lib.get_metadata_tag(asset, 'Wolf.GameplayVersion') == '1'

def finish(asset):
    lib.set_metadata_tag(asset, 'Wolf.GameplayVersion', '1')
    save(asset)

def source_speed(role):
    row = motion['clips'][role]
    first, last = row['samples'][0], row['samples'][-1]
    a, b = first['bones']['root'], last['bones']['root']
    return math.hypot(b[0] - a[0], b[1] - a[1]) / row['seconds']

physics = duplicate(SOURCE + '/SK_Wolf_PhysicsAsset', 'PA_Wolf_Gameplay')
mesh = duplicate(SOURCE + '/SK_Wolf', 'SK_Wolf_Gameplay')
if not initialized(mesh) or not initialized(physics):
    mesh.set_editor_property('physics_asset', physics)
    if not u.WolfMonster.prepare_combat_physics(mesh):
        raise RuntimeError('Could not author wolf gameplay physics')
    finish(physics)
    finish(mesh)

dataset = duplicate(TEMPLATE + '/DA_QP_Wolf_AnimationSet', 'DA_Wolf_AnimationSet')
contacts = {'AttackBite': [6 / 30, 11 / 30], 'AttackPounce': [10 / 30, 16 / 30]}
walk_speed, run_speed = source_speed('Walk_RM'), source_speed('Run_RM')
if not initialized(dataset):
    dataset.set_editor_property('reference_mesh', mesh)
    dataset.set_editor_property('walk_speed', walk_speed)
    dataset.set_editor_property('run_speed', run_speed)
    actions = dataset.get_editor_property('actions')
    for role, window in contacts.items():
        entry = actions[role]
        entry.set_editor_property('contact_start_seconds', window[0])
        entry.set_editor_property('contact_end_seconds', window[1])
        actions[role] = entry
    dataset.set_editor_property('actions', actions)
    finish(dataset)

bp_path = DEST + '/BP_WolfMonster'
if lib.does_asset_exist(bp_path):
    blueprint = u.load_asset(bp_path)
    preserved_paths.append(bp_path)
else:
    factory = u.BlueprintFactory()
    factory.set_editor_property('parent_class', u.WolfMonster)
    blueprint = assets.create_asset('BP_WolfMonster', DEST, u.Blueprint, factory)
    if blueprint is None:
        raise RuntimeError('Could not create ' + bp_path)
    created_paths.append(bp_path)

if not initialized(blueprint):
    # Blueprint compilation constructs the deliverable; it does not run the game.
    u.BlueprintEditorLibrary.compile_blueprint(blueprint)
    defaults = u.get_default_object(blueprint.generated_class())
    defaults.set_editor_property('animation_set', dataset)
    ai_class = u.load_class(None, '/Game/Monsters/AI/BP_MonsterAIController.BP_MonsterAIController_C')
    if ai_class is None:
        raise RuntimeError('The shared monster Behavior Tree controller is required')
    defaults.set_editor_property('ai_controller_class', ai_class)
    component = defaults.get_editor_property('mesh')
    component.set_skeletal_mesh_asset(mesh)
    component.set_anim_instance_class(u.QuadrupedTemplateAnimInstance.static_class())
    # Named fields avoid the Python Rotator constructor's pitch/yaw/roll ordering.
    rotation = u.Rotator()
    rotation.yaw = -90.0
    component.set_editor_property('relative_rotation', rotation)
    bottom = motion['bounds_origin'][2] - motion['bounds_extent'][2]
    component.set_editor_property('relative_location', u.Vector(0, 0, -60.0 - bottom))
    finish(blueprint)

report = {
    'version': 1,
    'source_listing': 'https://www.fab.com/listings/2dd7964c-a601-4264-a53d-465dcae1644c',
    'stage': 'gameplay assets authored; user runtime testing pending',
    'runtime_tested': False,
    'rendered_or_visually_accepted': False,
    'entry': bp_path,
    'animation_set': dataset.get_path_name(),
    'mesh': mesh.get_path_name(),
    'physics': physics.get_path_name(),
    'native_actor': '/Script/FPSGAME.WolfMonster',
    'native_animation': '/Script/FPSGAME.QuadrupedTemplateAnimInstance',
    'f6_id': 'Wolf',
    'f6_display_name': '野狼',
    'contact_source_seconds_half_open': contacts,
    'contact_basis': 'initial windows authored from existing 30 fps bone motion samples; no visual acceptance',
    'source_speed_cm_s': {'walk': walk_speed, 'run': run_speed},
    'initial_balance': {'health': 220, 'physical_defense': 12, 'magic_defense': 8,
                        'critical_resistance': 5, 'experience': 180,
                        'bite_damage': 22, 'pounce_damage': 36,
                        'walk_cm_s': 100, 'chase_cm_s': 380},
    'death_animation_fraction': 0.6,
    'created_this_run': created_paths,
    'already_present_this_run': preserved_paths,
    'policy': 'preserve initialized gameplay assets; original pack and animation mother set remain unchanged',
}
(OUT / 'gameplay_manifest.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
u.log('WOLF_GAMEPLAY_ASSETS_AUTHORED ' + bp_path)
