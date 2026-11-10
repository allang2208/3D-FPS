"""Author isolated campfire weapon/arrow flames; no game simulation or rendering.
The current game's TorchV2 assets and the StarMarrow blue material stay intact.
"""
import json
import sys
from pathlib import Path
import unreal as u

ROOT = Path('D:/FPS3D/FPSGAME')
OUT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT/'Tools/Fluids'))
import author_flame_armor_v2 as base
from author_flame_armor_v2 import API, LIB, ref, put, setdata, assignments, setup_emitter, user_parameter
from author_flame_armor_v2 import FLOAT, VEC2, VEC3, VEC4, POSITION, COLOR, smooth
from build_fireball_assets import emitters
from build_fireball_outer_flame import enable_sprite_usage

OLD = '/Game/Skills/FlameArmor20261016/TorchV2'
DEST = '/Game/Skills/FlameArmor20261107/CampfireV6'
DONOR = '/Game/Building/Campfire20261013/TorchFire/NS_CampfireTorchFire'
MATERIAL = DEST+'/M_FlameArmorCampfire'
SAVED = []
EXPR = '/Script/NiagaraEditor.NiagaraExt_StackInputData_HlslExpression'


def save(asset):
    if not u.EditorAssetLibrary.save_loaded_asset(asset, False):
        raise RuntimeError('Cannot save '+asset.get_path_name())
    SAVED.append(asset.get_path_name())


def owned(source, dest):
    if dest in {p.get_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()}:
        raise RuntimeError('Preserve dirty target '+dest)
    result = u.load_asset(dest) if u.EditorAssetLibrary.does_asset_exist(dest) else u.EditorAssetLibrary.duplicate_asset(source, dest)
    if result is None:
        raise RuntimeError('Missing source '+source)
    return result


def material():
    donor = u.load_asset(DONOR)
    renderer = json.loads(API.call_method('GetRendererData', (ref(donor, 'Fire', renderer=0),)).get_editor_property('property_values'))
    path = renderer['Material']
    if isinstance(path, dict):
        path = path['refPath']
    mat = owned(path, MATERIAL)
    nodes = list(LIB.get_material_expressions(mat))
    tag = 'FlameArmor campfire blended atlas V6'
    atlas = next((n for n in nodes if n.get_editor_property('desc') == tag), None)
    if atlas is None:
        sample = next(n for n in nodes if isinstance(n, u.MaterialExpressionTextureSample) and n.get_editor_property('texture'))
        atlas = LIB.create_material_expression(mat, u.MaterialExpressionTextureSampleParameterSubUV)
        atlas.set_editor_property('desc', tag)
        atlas.set_editor_property('parameter_name', 'CampfireFlameAtlas')
        atlas.set_editor_property('texture', sample.get_editor_property('texture'))
        atlas.set_editor_property('sampler_type', sample.get_editor_property('sampler_type'))
        atlas.set_editor_property('blend', True)
        for target in nodes:
            names = LIB.get_material_expression_input_names(target)
            for i, connection in enumerate(LIB.get_inputs_for_material_expression(mat, target)):
                if connection == sample:
                    output = LIB.get_input_node_output_name_for_material_expression(target, sample)
                    if not LIB.connect_material_expressions(atlas, output, target, str(names[i])):
                        raise RuntimeError('Cannot preserve campfire texture channel')
    fade_tag = 'FlameArmor surface contact fade V6'
    fade = next((n for n in nodes if n.get_editor_property('desc') == fade_tag), None)
    if fade is None:
        fade = LIB.create_material_expression(mat, u.MaterialExpressionConstant)
        fade.set_editor_property('desc', fade_tag)
    fade.set_editor_property('r', .45)
    for node in nodes:
        if isinstance(node, u.MaterialExpressionDepthFade):
            if not LIB.connect_material_expressions(fade, '', node, 'FadeDistance'):
                raise RuntimeError('Cannot fit contact fade')
    mat.set_editor_property('two_sided', True)
    mat.set_editor_property('translucency_pass', u.MaterialTranslucencyPass.MTP_AFTER_DOF)
    mat.set_editor_property('disable_depth_test', False)
    enable_sprite_usage(mat)
    errors = LIB.recompile_material(mat)
    if errors:
        raise RuntimeError(str(errors))
    save(mat)
    return mat, path


def seed(channel):
    return f'frac(sin(float(Particles.UniqueID)*{1.13+channel*.377:.6f}+User.VariationSeed*.713+{17.5+channel*31.47:.5f})*43758.5453)'


def cache(system, name):
    keys = ('Particles.FlameSeed', 'Particles.FlameShape')
    entries = []
    for key in keys:
        e = u.NiagaraExt_SetParameterEntry()
        e.import_text('(Variable=(Name="'+key+'",Type=(ClassStructOrEnum="'+VEC4+'",UnderlyingType=2)))')
        entries.append(e)
    module = str(API.call_method('AddSetParametersModule', (ref(system, name, 'ParticleSpawnScript'), entries)).get_editor_property('module_name'))
    h = [seed(i) for i in range(6)]
    for key, value in zip(keys, (f'float4({h[0]},6.2831853*{h[1]},(1.15+1.75*{h[2]})*({h[3]}<.5?-1.:1.),{h[4]})',
                                 f'float4(9.+7.*{h[2]},16.+13.*{h[3]},48.+12.*{h[1]},.64+.25*{h[5]})')):
        put(system, name, 'ParticleSpawnScript', module, key, '(HlslExpression="'+value+'")', EXPR)


def cross_section(t):
    # Continuous interpolation of eight actual blade sections, including their
    # lateral centre offsets: kukri curves and axe heads do not share a cylinder.
    value = 'User.Surface0'
    for i in range(1, 8):
        value = f'lerp({value},User.Surface{i},saturate(({t})*7.-{i-1}.))'
    return '('+value+')'


def render(system, name, mat, rate, local, scale='User.Detail'):
    setup_emitter(system, name, mat, rate, local)
    put(system, name, 'EmitterUpdateScript', 'SpawnRate', 'SpawnRate',
        f'(HlslExpression="{rate}*max(0,{scale})")', EXPR)
    setdata('SetRendererData', u.NiagaraExt_RendererData, ref(system, name, renderer=0), {
        'SubImageSize': {'X': 8, 'Y': 8}, 'bSubImageBlend': True,
        'PivotInUVSpace': {'X': .5, 'Y': .84}, 'SortMode': 'None', 'SortOrderHint': 1})


def flame_look(tint='float3(1,.88,.65)'):
    n, age, shape, seed_ = 'Particles.NormalizedAge', 'Particles.Age', 'Particles.FlameShape', 'Particles.FlameSeed'
    envelope = f'{smooth("0", ".08", n)}*(1.-{smooth(".68", "1", n)})'
    return {
        'Particles.SpriteRotation': (FLOAT, '0'), 'Particles.UVScale': (VEC2, 'float2(1,1)'),
        'Particles.SubImageIndex': (FLOAT, f'min(62.999,{seed_}.w*10.+{age}*{shape}.z)'),
        'Particles.MaterialRandom': (FLOAT, f'{seed_}.w'),
        'Particles.Color': (COLOR, f'float4({tint},User.Fade*{shape}.w*{envelope})'),
        # Same channel semantics as the live campfire: RGB and alpha exponents.
        'Particles.DynamicMaterialParameter': (VEC4, f'float4(1.15+.25*{seed_}.w,.9+.4*{smooth(".65", "1", n)},1,1)'),
    }


def weapon(mat, system=None, follow=False):
    if system is None:
        system = owned(OLD+'/NS_FlameArmorWeaponV2', DEST+'/NS_FlameArmorWeapon')
    for key in ('VariationSeed', 'FlameClock'):
        user_parameter(system, key, FLOAT)
    for key in ('WeaponSide', 'WeaponNormal'):
        user_parameter(system, key, VEC3)
    for i in range(8):
        user_parameter(system, 'Surface'+str(i), VEC4)
    keep = {'WeaponFireballCore', 'WeaponFireballTongues', 'MotionFireballFlame', 'WeaponEmbers'}
    if follow:
        keep -= {'MotionFireballFlame', 'WeaponEmbers'}
    for name in emitters(system):
        if name not in keep:
            API.call_method('RemoveEmitter', (ref(system, name),))
    side, normal = 'User.WeaponSide', 'User.WeaponNormal'
    axis = 'normalize(User.WeaponEnd+float3(.0001,0,0))'
    scale = 'User.Detail*(.65+.35*saturate(User.Coverage))'
    name = 'WeaponFireballCore'
    setup_emitter(system, name, u.load_asset(OLD+'/FireballV3/M_FA_FireballCoreV3'), 0, True)
    API.call_method('RemoveModule', (ref(system, name, 'EmitterUpdateScript', 'SpawnRate'),))
    API.call_method('RemoveModule', (ref(system, name, 'ParticleUpdateScript', 'ParticleState'),))
    API.call_method('AddModule', (ref(system, name, 'EmitterUpdateScript'), u.load_asset('/Niagara/Modules/Emitter/SpawnBurst_Instantaneous')))
    put(system, name, 'EmitterUpdateScript', 'SpawnBurst_Instantaneous', 'Spawn Count',
        '(HlslExpression="Engine.Emitter.TotalSpawnedParticles < 20 ? 20 : 0")', EXPR)
    put(system, name, 'EmitterUpdateScript', 'SpawnBurst_Instantaneous', 'Spawn Time', '(Value=0)')
    setdata('SetRendererData', u.NiagaraExt_RendererData, ref(system, name, renderer=0), {
        'SubImageSize': {'X': 1, 'Y': 1}, 'bSubImageBlend': False,
        'PivotInUVSpace': {'X': .5, 'Y': .5}, 'SortOrderHint': 0, 'SortMode': 'None'})
    t = '(floor(fmod(float(Particles.UniqueID),20.)*.5)+.5)/10.'
    section = cross_section(t)
    face = '(fmod(float(Particles.UniqueID),2.)<1.?-1.:1.)'
    root = f'User.WeaponEnd*({t})+{side}*{section}.x+{normal}*({section}.y+{face}*{section}.w)'
    bed = {
        'Particles.Position': (POSITION, root), 'Particles.SpriteAlignment': (VEC3, axis),
        'Particles.SpriteRotation': (FLOAT, '0'), 'Particles.UVScale': (VEC2, 'float2(1,1)'),
        'Particles.SpriteSize': (VEC2, f'float2(max(3.,2.*{section}.z+1.5),max(3.,length(User.WeaponEnd)*.16))'),
        'Particles.SubImageIndex': (FLOAT, '0'), 'Particles.MaterialRandom': (FLOAT, seed(0)),
        'Particles.DynamicMaterialParameter': (VEC4, 'float4(1,1,1,1)'),
        'Particles.Color': (COLOR, f'float4(1,1,1,User.Fade*(.30+.07*sin(User.FlameClock*3.7+{seed(0)}*19.))*User.Detail)'),
    }
    assignments(system, name, 'ParticleSpawnScript', {'Particles.Lifetime': (FLOAT, '3600'),
        'Particles.Velocity': (VEC3, 'float3(0,0,0)'), **bed})
    assignments(system, name, 'ParticleUpdateScript', bed)
    name = 'WeaponFireballTongues'
    render(system, name, mat, 28, True, scale)
    cache(system, name)
    seed_, age = 'Particles.FlameSeed', 'Particles.Age'
    t = f'clamp(.025+.95*{seed_}.x+{age}*.015,.025,.975)'
    section = cross_section(t)
    angle = f'({seed_}.y+{age}*{seed_}.z+.17*sin({age}*5.3+{seed_}.y))'
    # A rounded surface path follows each section's width/thickness; every
    # particle keeps its own phase and direction for its lifetime.
    c, s = f'cos({angle})', f'sin({angle})'
    shell = f'({side}*({section}.x+sign({c})*pow(abs({c}),.35)*{section}.z)+{normal}*({section}.y+sign({s})*pow(abs({s}),.35)*{section}.w))'
    position = f'User.WeaponEnd*({t})+{shell}'
    up = 'User.FlameUp*.72' if follow else 'float3(0,0,.72)'
    direction = f'normalize({axis}*.28+({side}*{c}+{normal}*{s})*.45+{up}-User.WeaponVelocity*.0002)'
    look = {**flame_look(), 'Particles.Position': (POSITION, position),
        'Particles.SpriteSize': (VEC2, 'Particles.FlameShape.xy*User.WeaponSize*User.FlameProfile.xy*(.9+.1*sin(Particles.NormalizedAge*3.141593))'),
        'Particles.SpriteAlignment': (VEC3, direction)}
    assignments(system, name, 'ParticleSpawnScript', {'Particles.Lifetime': (FLOAT, '.55+.3*Particles.FlameSeed.w'),
        'Particles.Velocity': (VEC3, 'float3(0,0,0)'), **look})
    assignments(system, name, 'ParticleUpdateScript', look)
    if follow:
        return system  # FollowV10 authors local accents and saves the new copy.
    name = 'MotionFireballFlame'
    render(system, name, mat, 12, False, scale+'*User.MotionEnergy*User.FlameProfile.z')
    cache(system, name)
    look = {**flame_look(),
        'Particles.SpriteSize': (VEC2, 'Particles.FlameShape.xy*User.WeaponSize*.65*(1.-Particles.NormalizedAge*.55)'),
        'Particles.SpriteAlignment': (VEC3, 'normalize(float3(0,0,1)-User.WeaponVelocity*.001)')}
    assignments(system, name, 'ParticleSpawnScript', {
        'Particles.Lifetime': (FLOAT, '.12+.1*Particles.FlameSeed.w'),
        'Particles.Position': (POSITION, 'lerp(lerp(User.PreviousStart,User.PreviousEnd,Particles.FlameSeed.x),lerp(User.WeaponStartWorld,User.WeaponEndWorld,Particles.FlameSeed.x),Particles.FlameSeed.w)'),
        'Particles.Velocity': (VEC3, 'User.WeaponVelocity*.06+float3(0,0,15)'), **look})
    assignments(system, name, 'ParticleUpdateScript', {
        'Particles.Position': (POSITION, 'Particles.Position+Particles.Velocity*Engine.DeltaTime'), **look})
    # Keep the old compatible ember material/update and lower decorative rate.
    put(system, 'WeaponEmbers', 'EmitterUpdateScript', 'SpawnRate', 'SpawnRate',
        f'(HlslExpression="4*{scale}")', EXPR)
    finish(system)


def arrow(mat):
    system = owned(OLD+'/NS_FlameArmorArrowV2', DEST+'/NS_FlameArmorArrow')
    user_parameter(system, 'VariationSeed', FLOAT)
    for name, rate, local in (('ArrowFireballFlame', 14, True), ('ArrowFireballWake', 20, False)):
        render(system, name, mat, rate, local)
        cache(system, name)
        look = {**flame_look(), 'Particles.SpriteSize': (VEC2, 'float2(5.5,14.)*(.8+.3*Particles.FlameSeed.w)*(1.-Particles.NormalizedAge*.4)'),
            'Particles.SpriteAlignment': (VEC3, 'float3(-1,0,.2)' if local else 'normalize(-User.Velocity+float3(0,0,.01))')}
        assignments(system, name, 'ParticleSpawnScript', {
            'Particles.Lifetime': (FLOAT, '.18+.1*Particles.FlameSeed.w'),
            'Particles.Position': (POSITION, 'float3(-3,0,0)' if local else 'lerp(User.PreviousPosition,User.CurrentPosition,Particles.FlameSeed.x)'),
            'Particles.Velocity': (VEC3, 'float3(0,0,0)' if local else 'User.Velocity*.025+float3(0,0,8)'), **look})
        assignments(system, name, 'ParticleUpdateScript', {
            'Particles.Position': (POSITION, 'float3(-3,0,0)' if local else 'Particles.Position+Particles.Velocity*Engine.DeltaTime'), **look})
    finish(system)


def finish(system):
    if not u.RainAssetEditor.compile_rain(system, True):
        raise RuntimeError('Niagara compile failed: '+system.get_path_name())
    u.EditorAssetLibrary.set_metadata_tag(system, 'FlameArmor.Revision', 'CampfireSurfaceV6-20261107')
    save(system)


def run():
    mat, source = material()
    weapon(mat)
    arrow(mat)
    receipt = dict(revision='CampfireSurfaceV6', saved_assets=SAVED, donor=DONOR, donor_material=source,
        persistent_surface_particles_per_span=20, maximum_spans=4, random_tongues_per_second=28,
        motion_flames_per_second=12, embers_per_second=4, animation_fps=[48,60], subuv_blending=True,
        colors='native warm orange/red', source_assets_modified=False, lights_added=0, runtime_tested=False, rendered=False)
    (OUT/'install-receipt.json').write_text(json.dumps(receipt, indent=2), encoding='utf-8')
    print('FLAME_ARMOR_CAMPFIRE_SAVED', receipt)


if __name__ == '__main__':
    run()
