"""Create wildlife animation sets and character blueprints for the animal pack.

Runs inside UnrealEditor-Cmd (see Tools/Wildlife/install_wildlife.ps1).
Idempotent: existing animations, datasets and blueprints are preserved.
No maps, gameplay runs, previews or tests are started here.
"""
import json
import runpy
from pathlib import Path

import unreal as u

PROJECT = Path(__file__).resolve().parents[2]
OUT = Path(globals().get('WILDLIFE_OUTPUT', PROJECT / 'SourceAssets/Wildlife20261022'))
PACK = '/Game/AnimalVarietyPack'
DEST_ROOT = '/Game/Monsters/Wildlife'
lib = u.EditorAssetLibrary
tools = u.AssetToolsHelpers.get_asset_tools()

# role, source suffix, loop, hold last pose, terminal, follow-up action
SLOTS = {
    'Idle': (None, True, False, False, ''),
    'IdleAlert': (None, True, False, False, ''),
    'LookAround': ('IdleLookAround', False, False, False, ''),
    'Walk': ('Walk', True, False, False, ''),
    'WalkTurnLeft': ('WalkTurnL', True, False, False, ''),
    'WalkTurnRight': ('WalkTurnR', True, False, False, ''),
    'Run': ('Run', True, False, False, ''),
    'RunTurnLeft': ('RunTurnL', True, False, False, ''),
    'RunTurnRight': ('RunTurnR', True, False, False, ''),
    'AttackBite': (None, False, False, False, ''),
    'AttackRunBite': (None, False, False, False, ''),
    'AttackPounce': (None, False, False, False, ''),
    'HitFront': (None, False, False, False, ''),
    'HitLeft': (None, False, False, False, ''),
    'HitRight': (None, False, False, False, ''),
    'RestEnter': (None, False, False, False, 'RestLoop'),
    'RestLoop': (None, True, False, False, ''),
    'RestExit': (None, False, False, False, ''),
    'SleepLoop': (None, True, False, False, ''),
    'Death': (None, False, True, True, ''),
    'Forage': (None, True, False, False, ''),
    'TakeOff': (None, False, True, False, ''),
    'Fly': (None, True, False, False, ''),
    'Glide': (None, True, False, False, ''),
    'Land': (None, False, True, False, ''),
    'AirFall': (None, True, False, False, ''),
}

SPECIES = [
    {
        'id': 'deer_doe', 'folder': 'DeerDoe', 'asset': 'DeerDoe',
        'source': PACK + '/DeerStagAndDoe', 'mesh': 'SK_DeerDoe',
        'walk': 105.0, 'run': 520.0,
        'map': {
            'Forage': 'IdleGraze',
            'Idle': 'IdleBreathe', 'IdleAlert': 'IdleLookAround', 'LookAround': 'IdleLookAround',
            'Walk': 'Walk', 'WalkTurnLeft': 'WalkTurnL', 'WalkTurnRight': 'WalkTurnR',
            'Run': 'Run', 'RunTurnLeft': 'RunTurnL', 'RunTurnRight': 'RunTurnR',
            'HitFront': 'GetHit', 'HitLeft': 'GetHit', 'HitRight': 'GetHit',
            'RestEnter': 'GoToRest', 'RestLoop': 'IdleRest', 'RestExit': 'RestToGoBackUp',
            'SleepLoop': 'IdleSleep', 'Death': 'Death',
        },
    },
    {
        'id': 'deer_stag', 'folder': 'DeerStag', 'asset': 'DeerStag',
        'source': PACK + '/DeerStagAndDoe', 'mesh': 'SK_DeerStag',
        'walk': 110.0, 'run': 560.0,
        'map': {
            'Forage': 'IdleGraze',
            'Idle': 'IdleBreathe', 'IdleAlert': 'IdleLookAround', 'LookAround': 'IdleLookAround',
            'Walk': 'Walk', 'WalkTurnLeft': 'WalkTurnL', 'WalkTurnRight': 'WalkTurnR',
            'Run': 'Run', 'RunTurnLeft': 'RunTurnL', 'RunTurnRight': 'RunTurnR',
            'AttackBite': 'AntlersAttack', 'AttackRunBite': 'AntlersComboAttack',
            'HitFront': 'GetHit', 'HitLeft': 'GetHit', 'HitRight': 'GetHit',
            'RestEnter': 'GoToRest', 'RestLoop': 'Rest', 'RestExit': 'RestToGoBackUp',
            'SleepLoop': 'Sleep', 'Death': 'Death',
        },
    },
    {
        'id': 'boar', 'folder': 'Pig', 'asset': 'Pig',
        'source': PACK + '/Pig', 'mesh': 'SK_Pig',
        'walk': 100.0, 'run': 430.0,
        'map': {
            'Forage': 'SniffleforFood',
            'Idle': 'IdleBreathe', 'IdleAlert': 'IdleLookAround', 'LookAround': 'IdleLookAround',
            'Walk': 'Walk', 'WalkTurnLeft': 'WalkTurnL', 'WalkTurnRight': 'WalkTurnR',
            'Run': 'Run', 'RunTurnLeft': 'RunTurnL', 'RunTurnRight': 'RunTurnR',
            'AttackBite': 'ComboAttackForward', 'AttackPounce': 'JumpAttack',
            'HitFront': 'GetHit', 'HitLeft': 'GetHit', 'HitRight': 'GetHit',
            'RestEnter': 'GoToRest', 'RestLoop': 'Rest', 'RestExit': 'GoBackUp',
            'Death': 'Death',
        },
    },
    {
        'id': 'fox', 'folder': 'Fox', 'asset': 'Fox',
        'source': PACK + '/Fox', 'mesh': 'SK_Fox',
        'walk': 130.0, 'run': 480.0,
        'map': {
            'Idle': 'IdleBreathe', 'IdleAlert': 'IdleAggressive', 'LookAround': 'IdleLookAround',
            'Walk': 'Walk', 'WalkTurnLeft': 'WalkTurnL', 'WalkTurnRight': 'WalkTurnR',
            'Run': 'Run', 'RunTurnLeft': 'RunTurnL', 'RunTurnRight': 'RunTurnR',
            'AttackBite': 'Bite', 'AttackRunBite': 'RunBite', 'AttackPounce': 'JumpBite',
            'HitFront': 'GetHitFront', 'HitLeft': 'GetHitLeft', 'HitRight': 'GetHitRight',
            'RestEnter': 'GoToRest', 'RestLoop': 'Resting', 'RestExit': 'RestToGoBackUp',
            'SleepLoop': 'Sleeping', 'Death': 'Death',
        },
    },
    {
        'id': 'crow', 'folder': 'Crow', 'asset': 'Crow',
        'source': PACK + '/Crow', 'mesh': 'SK_Crow',
        'walk': 90.0, 'run': 200.0,
        'map': {
            'Idle': 'IdleLookAround', 'IdleAlert': 'IdleStretchWings', 'LookAround': 'IdleScratchWing',
            'Walk': 'Walk', 'Run': 'Hop',
            'RestEnter': 'IdleScratchWing', 'RestLoop': 'IdleScratchWing',
            'Death': 'DeathGrounded',
            'TakeOff': 'TakeOff', 'Fly': 'Fly', 'Glide': 'Glide',
            'Land': 'Landing', 'AirFall': 'Falling',
        },
    },
]

CAPSULES = {
    'deer_doe': (38.0, 62.0), 'deer_stag': (42.0, 68.0), 'boar': (46.0, 58.0),
    'fox': (28.0, 42.0), 'crow': (16.0, 20.0),
}


def save(asset):
    if not lib.save_loaded_asset(asset, False):
        raise RuntimeError('Could not save ' + asset.get_path_name())


def create_missing(name, folder, cls, factory):
    path = folder + '/' + name
    if lib.does_asset_exist(path):
        return u.load_asset(path), False
    asset = tools.create_asset(name, folder, cls, factory)
    if asset is None:
        raise RuntimeError('Could not create ' + path)
    return asset, True


report = {
    'version': 1,
    'stage': 'wildlife animation sets and character blueprints; no gameplay run',
    'runtime_tested': False,
    'visually_accepted': False,
    'contact_windows': 'not authored; design values live in Content/ColdSteelData/wildlife.json',
    'policy': 'create missing assets only; preserve existing edits',
    'species': [],
}

for spec in SPECIES:
    if 'WILDLIFE_SPECIES' in globals() and spec['id'] not in WILDLIFE_SPECIES:
        continue
    folder = DEST_ROOT + '/' + spec['folder']
    anim_folder = folder + '/Animations'
    mesh_path = spec['source'] + '/Meshes/' + spec['mesh']
    if spec['id'] == 'boar' and lib.does_asset_exist(folder + '/Appearance/SK_WL_Boar'):
        mesh_path = folder + '/Appearance/SK_WL_Boar'
    mesh = u.load_asset(mesh_path)
    if mesh is None:
        raise RuntimeError('Missing source mesh ' + mesh_path)
    definitions = {}
    rows = []
    for role, (_, loop, hold, terminal, followup) in SLOTS.items():
        if 'WILDLIFE_ROLES' in globals() and role not in WILDLIFE_ROLES:
            continue
        suffix = spec['map'].get(role)
        if not suffix:
            continue
        source = spec['source'] + '/Animations/ANIM_' + spec['asset'] + '_' + suffix
        if not lib.does_asset_exist(source):
            if 'WILDLIFE_ROLES' in globals():
                raise RuntimeError('Missing mapped wildlife animation ' + source)
            continue
        dst = anim_folder + '/A_WL_' + spec['asset'] + '_' + role
        created = not lib.does_asset_exist(dst)
        clip = lib.duplicate_asset(source, dst) if created else u.load_asset(dst)
        if clip is None:
            raise RuntimeError('Could not create animation ' + dst)
        if created:
            clip.set_editor_property('enable_root_motion', False)
            clip.set_editor_property('force_root_lock', True)
            clip.set_editor_property('root_motion_root_lock', u.RootMotionRootLock.ANIM_FIRST_FRAME)
            clip.set_editor_property('rate_scale', 1.0)
            lib.set_metadata_tag(clip, 'Wildlife.Source', source)
            lib.set_metadata_tag(clip, 'Wildlife.Action', role)
            save(clip)
        entry = u.QuadrupedTemplateAction()
        for prop, value in {
            'sequence': clip, 'loop': loop, 'hold_last_pose': hold, 'terminal': terminal,
            'next_action': followup, 'blend_seconds': 0.15, 'play_rate': 1.0,
            'contact_start_seconds': -1.0, 'contact_end_seconds': -1.0,
        }.items():
            entry.set_editor_property(prop, value)
        definitions[role] = entry
        rows.append({'slot': role, 'source': source, 'clip': dst,
                     'seconds': round(clip.get_play_length(), 4), 'created': created})

    factory = u.DataAssetFactory()
    factory.set_editor_property('data_asset_class', u.QuadrupedAnimationSet)
    dataset, ds_created = create_missing('DA_WL_' + spec['asset'] + '_AnimationSet',
                                         folder, u.QuadrupedAnimationSet, factory)
    if ds_created:
        dataset.set_editor_property('reference_mesh', mesh)
        dataset.set_editor_property('actions', definitions)
        dataset.set_editor_property('walk_speed', spec['walk'])
        dataset.set_editor_property('run_speed', spec['run'])
        save(dataset)
    else:
        # Merge only the slots that are missing; keep any tuned values already saved.
        actions = dataset.get_editor_property('actions')
        present = {str(key) for key in actions.keys()}
        missing = [role for role in definitions if role not in present]
        if missing:
            for role in missing:
                actions[role] = definitions[role]
            dataset.set_editor_property('actions', actions)
            save(dataset)
            u.log('WILDLIFE_SET_SYNCED ' + spec['id'] + ' added=' + ','.join(missing))
    filled = dataset.get_editor_property('actions')
    if len(filled) < len(definitions):
        raise RuntimeError('Animation set %s has %d slots, expected %d'
                           % (dataset.get_path_name(), len(filled), len(definitions)))

    bp_factory = u.BlueprintFactory()
    bp_factory.set_editor_property('parent_class', u.ColdSteelAnimal)
    blueprint, bp_created = create_missing('BP_WL_' + spec['asset'], folder, u.Blueprint, bp_factory)
    if bp_created:
        u.BlueprintEditorLibrary.compile_blueprint(blueprint)
        defaults = u.get_default_object(blueprint.generated_class())
        defaults.set_editor_property('species_id', spec['id'])
        defaults.set_editor_property('animation_set', dataset)
        defaults.get_editor_property('mesh').set_skeletal_mesh_asset(mesh)
        radius, half_height = CAPSULES[spec['id']]
        try:
            capsule = defaults.get_editor_property('capsule_component')
            capsule.set_editor_property('capsule_radius', radius)
            capsule.set_editor_property('capsule_half_height', half_height)
        except Exception as error:  # noqa: BLE001 - reported, not hidden
            rows.append({'capsule_cdo_error': str(error)})
        save(blueprint)
        if spec['id'] == 'boar':
            runpy.run_path(str(PROJECT / 'Tools/Wildlife/boar_materials.py'))['apply'](blueprint)

    report['species'].append({
        'id': spec['id'],
        'animation_set': dataset.get_path_name(),
        'animation_set_created': ds_created,
        'blueprint': blueprint.get_path_name(),
        'blueprint_created': bp_created,
        'mesh': mesh.get_path_name(),
        'slots': rows,
        'note': spec.get('note', ''),
    })
    u.log('WILDLIFE_SPECIES_READY ' + spec['id'] + ' slots=' + str(len(rows)))

OUT.mkdir(parents=True, exist_ok=True)
(OUT / 'authoring_manifest.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
u.log('WILDLIFE_AUTHORING_DONE species=' + str(len(report['species'])))
