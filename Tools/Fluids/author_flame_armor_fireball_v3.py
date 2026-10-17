"""Flame armor using the actual fireball core and erosion-flame materials.

Keep the installed system paths and runtime attachment parameters. Author,
compile and save only; no PIE, screenshots or particle simulation probes.
"""
import hashlib
import json
import shutil
import sys
from pathlib import Path
import unreal as u

ROOT = Path('D:/FPS3D/FPSGAME')
OUT = ROOT / 'SourceAssets/FlameArmor20261016/FireballV3'
RUNTIME = '/Game/Skills/FlameArmor20261016/TorchV2'
DEST = RUNTIME + '/FireballV3'
FIREBALL = '/Game/Skills/Fireball/TorchBurn20260921'
sys.path.insert(0, str(ROOT / 'Tools/Fluids'))
import author_flame_armor_v2 as base
from author_flame_armor_v2 import API, LIB, ref, put, setdata, assignments, setup_emitter
from author_flame_armor_v2 import FLOAT, VEC2, VEC3, VEC4, POSITION, COLOR, S, V, Q, AGE, N, ANGLE, smooth
from build_fireball_outer_flame import enable_sprite_usage

MATERIALS = {'core': DEST + '/M_FA_FireballCoreV3',
             'flame': DEST + '/MI_FA_FireballFlameV3',
             'curl': DEST + '/MI_FA_FireballFlameV3',
             'ember': RUNTIME + '/M_FA_Ember'}


def owned(source, name):
    path = DEST + '/' + name
    if path in {p.get_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()}:
        raise RuntimeError('Preserve dirty target: ' + path)
    asset = u.load_asset(path) if u.EditorAssetLibrary.does_asset_exist(path) else u.EditorAssetLibrary.duplicate_asset(source, path)
    if not asset:
        raise RuntimeError('Missing fireball source: ' + source)
    return asset


def backup_system(leaf):
    source = ROOT / 'Content/Skills/FlameArmor20261016/TorchV2' / (leaf + '.uasset')
    target = OUT / 'Before' / source.name
    target.parent.mkdir(parents=True, exist_ok=True)
    if not target.exists():
        shutil.copy2(source, target)
    return {'source': str(source), 'backup': str(target),
            'sha256': hashlib.sha256(target.read_bytes()).hexdigest()}


def materials():
    # These are isolated derivatives of the two materials bound by the actual
    # NS_FireballSlowBurnCore. The fireball's own assets stay read-only.
    parent = owned(FIREBALL + '/M_FireballTorchErosion', 'M_FA_FireballErosionV3')
    core = owned(FIREBALL + '/M_FireballCohesiveCore', 'M_FA_FireballCoreV3')
    for mat in (parent, core):
        enable_sprite_usage(mat)
        mat.set_editor_property('disable_depth_test', False)
        mat.set_editor_property('two_sided', True)
        mat.set_editor_property('translucency_pass', u.MaterialTranslucencyPass.MTP_AFTER_DOF)
    # Preserve the existing premultiplied density and single exposure correction.
    # The projectile's 4 cm contact fade removes too much of a small weapon flame.
    for node in LIB.get_material_expressions(core):
        if isinstance(node, u.MaterialExpressionScalarParameter) and str(node.get_editor_property('parameter_name')) == 'EmissionGain':
            node.set_editor_property('default_value', 2.7)
        elif isinstance(node, u.MaterialExpressionDepthFade):
            node.set_editor_property('fade_distance_default', .8)
    for mat in (parent, core):
        errors = LIB.recompile_material(mat)
        if errors:
            raise RuntimeError(str(errors))
        base.save(mat)
    flame = owned(FIREBALL + '/MI_FireballTorch01', 'MI_FA_FireballFlameV3')
    LIB.set_material_instance_parent(flame, parent)
    for key, value in (('Emissive_Intensity', 6.5), ('DepthFade', 1.0),
                       ('Noises_OpacityBoost', 1.2), ('Noise_01_Speed_X', .23), ('Noise_01_Speed_Y', .37)):
        LIB.set_material_instance_scalar_parameter_value(flame, key, value)
    enable_sprite_usage(parent, flame)
    LIB.update_material_instance(flame)
    base.save(flame)


def layer(system, name, kind, rate, local, life, spawn, update, size, opacity,
          axis='float3(0,0,1)', velocity='float3(0,0,0)', scale='User.Detail'):
    mat = u.load_asset(MATERIALS[kind])
    if not mat:
        raise RuntimeError('Build materials first: ' + MATERIALS[kind])
    setup_emitter(system, name, mat, rate, local)
    put(system, name, 'EmitterUpdateScript', 'SpawnRate', 'SpawnRate',
        f'(HlslExpression="{rate}*max(0,{scale})")', '/Script/NiagaraEditor.NiagaraExt_StackInputData_HlslExpression')
    setdata('SetRendererData', u.NiagaraExt_RendererData, ref(system, name, renderer=0), {
        'SubImageSize': {'X': 1, 'Y': 1}, 'bSubImageBlend': False,
        'PivotInUVSpace': {'X': .5, 'Y': .5 if kind in ('core', 'ember') else .7},
        'Alignment': 'CustomAlignment', 'SortOrderHint': 0 if kind == 'core' else 1})
    # The fireball's erosion material uses X as erosion, NOT the campfire
    # flipbook's RGB exponent. Hold a substantial flame through most of its life.
    envelope = smooth('0', '.06', N) + '*(1-' + smooth('.70', '1', N) + ')'
    tint = f'float3(1,lerp(.45,.12,{N}),lerp(.07,.01,{N}))'
    dynamic = f'float4(.03+.64*{smooth(".35", "1", N)},1,1,1)'
    if kind == 'core':
        tint, dynamic = 'float3(1,1,1)', 'float4(1,1,1,1)'
        envelope = smooth('0', '.10', N) + '*(1-' + smooth('.78', '1', N) + ')'
    elif kind == 'curl':
        dynamic = f'float4(.10+.65*{smooth(".25", "1", N)},1,1,1)'
    elif kind == 'ember':
        tint, dynamic = f'lerp(float3(4.1,1.5,.18),float3(.8,.045,.002),{N})', 'float4(0,0,0,0)'
    look = {'Particles.SpriteSize': (VEC2, size),
            'Particles.Color': (COLOR, f'float4({tint},({opacity})*{envelope})'),
            'Particles.SpriteAlignment': (VEC3, axis), 'Particles.SpriteRotation': (FLOAT, '0'),
            'Particles.UVScale': (VEC2, 'float2(1,1)'), 'Particles.SubImageIndex': (FLOAT, '0'),
            'Particles.MaterialRandom': (FLOAT, V), 'Particles.DynamicMaterialParameter': (VEC4, dynamic)}
    assignments(system, name, 'ParticleSpawnScript', {
        'Particles.Lifetime': (FLOAT, life), 'Particles.Position': (POSITION, spawn),
        'Particles.Velocity': (VEC3, velocity), **look})
    assignments(system, name, 'ParticleUpdateScript', {'Particles.Position': (POSITION, update), **look})


def save_system(system):
    u.EditorAssetLibrary.set_metadata_tag(system, 'FlameArmor.Author', 'author_flame_armor_fireball_v3.py')
    u.EditorAssetLibrary.set_metadata_tag(system, 'FlameArmor.Revision', 'FireballV3')
    base.save(system)


def remove_body_layers(system):
    # User direction, 2026-10-17: weapons and the foot ring only in third person.
    removed = []
    for name in ('BoundFireballCores', 'BoundFireballTongues', 'RisingFireballCurls', 'BodyEmbers'):
        if name in base.emitters(system):
            API.call_method('RemoveEmitter', (ref(system, name),))
            removed.append(name)
    u.EditorAssetLibrary.set_metadata_tag(system, 'FlameArmor.BodyPresentation', 'RingOnly20261017')
    return removed


def body():
    params = {x: FLOAT for x in ('Fade', 'Detail', 'UpperVisibility', 'Radius', 'BodyHeight', 'Clock')}
    params.update({x: VEC3 for x in ('BodyVelocity', 'Wind', 'WaistL', 'WaistR', 'ShoulderL', 'ShoulderR', 'ForearmL', 'ForearmR')})
    params['BodyOrigin'] = POSITION
    s = base.system('NS_FlameArmorBodyV2', params, (260, 260, 280))
    # Preserve the runtime parameter contract, but only author the foot ring.
    # Upper-body flames must not return when this system is rebuilt.
    from author_flame_armor_ring_v4 import add_ring_layers
    add_ring_layers(s)
    save_system(s)


def weapon():
    params = {x: FLOAT for x in ('Fade', 'WeaponSize', 'Detail', 'MotionEnergy', 'Coverage')}
    params.update({x: VEC3 for x in ('WeaponEnd', 'WeaponVelocity', 'FlameProfile')})
    params.update({x: POSITION for x in ('WeaponStartWorld', 'WeaponEndWorld', 'PreviousStart', 'PreviousEnd')})
    s = base.system('NS_FlameArmorWeaponV2', params, (350, 350, 350))
    along = 'normalize(User.WeaponEnd+float3(.0001,0,0))'
    side = f'normalize(cross({along},abs({along}.z)<.9?float3(0,0,1):float3(0,1,0)))'
    across = f'({side}*cos({ANGLE})+cross({along},{side})*sin({ANGLE}))'
    point = f'User.WeaponEnd*(.06+.90*{S})+{across}*(.7+1.2*{V})*User.FlameProfile.x'
    up = 'normalize(float3(0,0,110)-User.WeaponVelocity*.045)'
    # Short hammer faces previously multiplied spawn rate by .3, leaving only
    # sparse fading wisps. Keep a visible core on short spans as well as blades.
    scale = 'User.Detail*(.65+.35*saturate(User.Coverage))'
    layer(s, 'WeaponFireballCore', 'core', 8, True, f'.75+.25*{Q}', point, point,
          'float2(11,25)*User.WeaponSize*float2(User.FlameProfile.x,1)', 'User.Fade*.72', axis=along, scale=scale)
    tongue = f'{point}+{up}*(1+{AGE}*8)*User.WeaponSize'
    layer(s, 'WeaponFireballTongues', 'flame', 24, True, f'.60+.30*{Q}', tongue, tongue,
          f'float2(20,42)*User.WeaponSize*User.FlameProfile.xy*(.85+.3*{V})', 'User.Fade*.95', axis=up, scale=scale)
    layer(s, 'WeaponFireballCurls', 'curl', 6, True, f'.5+.25*{Q}', point, tongue,
          f'float2(20,32)*User.WeaponSize*User.FlameProfile.xy*(.85+.25*{V})', 'User.Fade*.55', axis=up, scale=scale)
    history = f'lerp(lerp(User.PreviousStart,User.PreviousEnd,{S}),lerp(User.WeaponStartWorld,User.WeaponEndWorld,{S}),{V})'
    motion = 'Particles.Position+Particles.Velocity*Engine.DeltaTime'
    layer(s, 'MotionFireballFlame', 'flame', 18, False, f'.16+.12*{Q}', history, motion,
          f'float2(20,32)*User.WeaponSize*(1-{N}*.5)', 'User.Fade*.68',
          velocity='User.WeaponVelocity*.08+float3(0,0,18)', axis=up, scale=scale+'*User.MotionEnergy*User.FlameProfile.z')
    layer(s, 'WeaponEmbers', 'ember', 6, False, f'.18+.28*{Q}', history, motion,
          f'float2(.7,1.8)*(.7+.5*{V})', 'User.Fade*.9',
          velocity=f'User.WeaponVelocity*.055+float3(cos({ANGLE})*8,sin({ANGLE})*8,25)',
          axis='normalize(Particles.Velocity+float3(0,0,.1))', scale=scale)
    save_system(s)


def arrow():
    params = {'Fade': FLOAT, 'Detail': FLOAT, 'Velocity': VEC3, 'PreviousPosition': POSITION, 'CurrentPosition': POSITION}
    s = base.system('NS_FlameArmorArrowV2', params, (420, 420, 420))
    layer(s, 'ArrowFireballFlame', 'flame', 14, True, '.24', 'float3(-3,0,0)', 'float3(-3,0,0)',
          'float2(6,15)', 'User.Fade*.9', axis='float3(-1,0,.25)')
    origin = f'lerp(User.PreviousPosition,User.CurrentPosition,{S})'
    motion = 'Particles.Position+Particles.Velocity*Engine.DeltaTime'
    layer(s, 'ArrowFireballWake', 'flame', 26, False, f'.12+.10*{V}', origin, motion,
          f'float2(5.5,16)*(1-{N}*.55)', 'User.Fade*.65', velocity='User.Velocity*.025+float3(0,0,8)',
          axis='normalize(-User.Velocity+float3(0,0,.01))')
    layer(s, 'ArrowSparks', 'ember', 6, False, '.24', origin, motion,
          'float2(.5,1.5)', 'User.Fade*.85', velocity='User.Velocity*.035+float3(0,0,12)',
          axis='normalize(Particles.Velocity+float3(0,0,.01))')
    save_system(s)


def run(stage):
    (OUT / 'Receipts').mkdir(parents=True, exist_ok=True)
    u.EditorAssetLibrary.make_directory(DEST)
    before = backup_system({'body': 'NS_FlameArmorBodyV2', 'weapon': 'NS_FlameArmorWeaponV2', 'arrow': 'NS_FlameArmorArrowV2'}[stage]) if stage != 'materials' else None
    base.RECORDS.clear()
    {'materials': materials, 'body': body, 'weapon': weapon, 'arrow': arrow}[stage]()
    receipt = {'stage': stage, 'revision': 'FireballV3', 'saved_assets': list(base.RECORDS),
               'before': before, 'source_materials': FIREBALL, 'runtime_paths_changed': False,
               'new_lights': 0, 'runtime_test_or_render': False}
    (OUT / 'Receipts' / (stage + '-saved.json')).write_text(json.dumps(receipt, indent=2), encoding='utf-8')
    print('FLAME_ARMOR_FIREBALL_V3_SAVED', stage, receipt['saved_assets'])


if __name__ == '__main__':
    for stage in ('materials', 'body', 'weapon', 'arrow'):
        run(stage)
