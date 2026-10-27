"""Incrementally author the approved Arrow Rain airburst, without gameplay/rendering.

Only the five owned assets below are saved. Existing ground impact/audio assets
and the shared smoke atlas remain untouched. The full recipe calls upgrade().
"""
from pathlib import Path
from datetime import datetime
import json
import shutil
import sys
import unreal as u

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / 'SourceAssets/MagicArrowRain20261026/AirburstV2'
OUT = ROOT / 'Saved/MagicArrowRain20261026/AirburstV2'
sys.path.insert(0, str(ROOT / 'Tools/Skills'))
import build_magic_arrow_rain_assets as base
from build_fireball_assets import API, ref, emitters, setdata, put, assignments
from build_fireball_flames import trim, FLOAT, VEC2, VEC3, POSITION, COLOR
from build_fireball_flight import user_parameter
from build_fireball_slow_burn import smooth

DEST = base.DEST
EAL, LIB = u.EditorAssetLibrary, u.MaterialEditingLibrary
OWNED = ['M_ArrowRainBurstCoreV2', 'M_ArrowRainPressureWaveV2',
         'M_ArrowRainBurstSmokeV2', 'M_ArrowRainMetal', 'NS_ArrowRainBurst']
VEC4 = '/Script/CoreUObject.Vector4f'


def sprite_material(name, mask, gain, source_directory=SRC):
    mat = base.material(name)
    mat.set_editor_property('blend_mode', u.BlendMode.BLEND_ADDITIVE)
    mat.set_editor_property('shading_model', u.MaterialShadingModel.MSM_UNLIT)
    mat.set_editor_property('two_sided', True)
    mat.set_editor_property('disable_depth_test', False)
    mat.set_editor_property('output_translucent_velocity', False)
    LIB.set_base_material_usage(mat, u.MaterialUsage.MATUSAGE_NIAGARA_SPRITES, True)
    uv = base.node(mat, u.MaterialExpressionTextureCoordinate)
    color = base.node(mat, u.MaterialExpressionParticleColor)
    age = base.node(mat, u.MaterialExpressionParticleRelativeTime)
    seed = base.node(mat, u.MaterialExpressionDynamicParameter)
    seed.set_editor_property('param_names', ['BurstSeed', 'UnusedY', 'UnusedZ', 'UnusedW'])
    opacity = base.custom(mat, (source_directory / mask).read_text(encoding='utf8'), {
        'UV': (uv, ''), 'Alpha': (color, 'A'), 'Age': (age, ''), 'Seed': (seed, '')})
    rgb = base.custom(mat, f'return RGB*{gain};', {'RGB': (color, 'RGB')}, True)
    base.output(opacity, u.MaterialProperty.MP_OPACITY)
    base.output(rgb, u.MaterialProperty.MP_EMISSIVE_COLOR)
    base.compile_material(mat)
    return mat


def smoke_material():
    mat = base.material('M_ArrowRainBurstSmokeV2')
    mat.set_editor_property('blend_mode', u.BlendMode.BLEND_TRANSLUCENT)
    mat.set_editor_property('shading_model', u.MaterialShadingModel.MSM_UNLIT)
    mat.set_editor_property('two_sided', True)
    mat.set_editor_property('disable_depth_test', False)
    mat.set_editor_property('output_translucent_velocity', False)
    mat.set_editor_property('allow_front_layer_translucency', False)
    LIB.set_base_material_usage(mat, u.MaterialUsage.MATUSAGE_NIAGARA_SPRITES, True)
    uv = base.node(mat, u.MaterialExpressionTextureCoordinate)
    color = base.node(mat, u.MaterialExpressionParticleColor)
    age = base.node(mat, u.MaterialExpressionParticleRelativeTime)
    seed = base.node(mat, u.MaterialExpressionDynamicParameter)
    seed.set_editor_property('param_names', ['SmokeSeed', 'UnusedY', 'UnusedZ', 'UnusedW'])
    atlas = base.node(mat, u.MaterialExpressionTextureObjectParameter)
    atlas.set_editor_property('parameter_name', 'DensityAtlas')
    texture = u.load_asset('/Game/Weapons/GunplayFX/T_MuzzleSmokeMantaflowV14')
    if not texture:
        raise RuntimeError('Missing approved Mantaflow smoke atlas')
    atlas.set_editor_property('texture', texture)
    atlas.set_editor_property('sampler_type', u.MaterialSamplerType.SAMPLERTYPE_MASKS)
    density = base.custom(mat, (ROOT / 'SourceAssets/ImpactSmokeCorrosion20260924/RollingSmoke.hlsl').read_text(encoding='utf8'), {
        'UV': (uv, ''), 'Atlas': (atlas, ''), 'Age': (age, ''),
        'Seed': (seed, ''), 'Alpha': (color, 'A')})
    fade = base.node(mat, u.MaterialExpressionDepthFade)
    fade.set_editor_property('fade_distance_default', 12.)
    if not LIB.connect_material_expressions(density, '', fade, str(LIB.get_material_expression_input_names(fade)[0])):
        raise RuntimeError('Smoke depth fade connection')
    rgb = base.custom(mat, '''float r=length((UV-.5)*2);
float rim=smoothstep(.25,.70,r)*(1-smoothstep(.8,1,r));
float shade=lerp(.58,1.10,saturate(1-UV.y));
float glow=1-smoothstep(.10,.36,Age);
return RGB*shade+float3(.025,.40,.095)*rim*glow;''',
        {'UV': (uv, ''), 'RGB': (color, 'RGB'), 'Age': (age, '')}, True)
    base.output(fade, u.MaterialProperty.MP_OPACITY)
    base.output(rgb, u.MaterialProperty.MP_EMISSIVE_COLOR)
    base.compile_material(mat)
    return mat


def arrow_tip_material(tip_gain=4.0):
    mat = base.material('M_ArrowRainMetal')
    mat.set_editor_property('blend_mode', u.BlendMode.BLEND_OPAQUE)
    LIB.set_base_material_usage(mat, u.MaterialUsage.MATUSAGE_INSTANCED_STATIC_MESHES, True)
    for prop, code, vector in [
        (u.MaterialProperty.MP_BASE_COLOR, 'return float3(.38,.45,.41);', True),
        (u.MaterialProperty.MP_METALLIC, 'return .85;', False),
        (u.MaterialProperty.MP_ROUGHNESS, 'return .3;', False)]:
        base.output(base.custom(mat, code, {}, vector), prop)
    uv = base.node(mat, u.MaterialExpressionTextureCoordinate)
    pulse = base.node(mat, u.MaterialExpressionPerInstanceCustomData)
    pulse.set_editor_property('data_index', 0)
    pulse.set_editor_property('const_default_value', 0.)
    interpolator = base.node(mat, u.MaterialExpressionVertexInterpolator)
    pin = str(LIB.get_material_expression_input_names(interpolator)[0])
    if not LIB.connect_material_expressions(pulse, '', interpolator, pin):
        raise RuntimeError('Arrow head instance pulse connection')
    # The authored OBJ has U=(X+76)/76: the +X arrow tip is at U=1.
    rgb = base.custom(mat, '''float head=smoothstep(.78,.94,UV.x);
return float3(.005,.045,.012)+float3(.10,1,.28)*head*saturate(Pulse)*TIP_GAIN;'''.replace('TIP_GAIN', str(tip_gain)),
        {'UV': (uv, ''), 'Pulse': (interpolator, '')}, True)
    base.output(rgb, u.MaterialProperty.MP_EMISSIVE_COLOR)
    base.compile_material(mat)


def layer(system, source, name, material, count, lifetime, values, alignment='Unaligned', spawn_values=None):
    # These named layers own their assignment nodes; replacing them is repeatable.
    if name in emitters(system):
        API.call_method('RemoveEmitter', (ref(system, name),))
    for stage in ['ParticleSpawnScript', 'ParticleUpdateScript']:
        EAL.remove_metadata_tag(system, 'Fireball.Assignments.' + name + '.' + stage)
    API.call_method('AddEmitter', (system, u.load_asset('/Game/NiagaraExamples/FX_Explosions/Emitters/NE_Core'), name))
    trim(system, name, {'EmitterUpdateScript': ['EmitterState'],
                        'ParticleSpawnScript': ['InitializeParticle'], 'ParticleUpdateScript': ['ParticleState']})
    setdata('SetEmitterData', u.NiagaraExt_EmitterData, ref(system, name), {
        'bLocalSpace': True, 'SimTarget': 'CPUSim', 'bInterpolatedSpawning': False})
    setdata('SetRendererData', u.NiagaraExt_RendererData, ref(system, name, renderer=0), {
        'Material': material.get_path_name(), 'MaterialUserParamBinding': {'Parameter': {'Name': 'None'}},
        'SubImageSize': {'X': 1, 'Y': 1}, 'bSubImageBlend': False,
        'Alignment': alignment, 'FacingMode': 'FaceCamera', 'bCastShadows': False,
        'CutoutTexture': None, 'bUseMaterialCutoutTexture': False, 'MotionVectorSetting': 'Disable'})
    for key in ['Life Cycle Mode', 'Loop Behavior']:
        value = u.RainAssetEditor.read_input(source, 'Explosion', 'EmitterUpdateScript', 'EmitterState', key)
        value = value.replace('NewEnumerator0', 'NewEnumerator1').replace('"System"', '"Self"').replace('"Infinite"', '"Once"')
        put(system, name, 'EmitterUpdateScript', 'EmitterState', key, value, '/Script/NiagaraEditor.NiagaraExt_StackInputData_Enum')
    put(system, name, 'EmitterUpdateScript', 'EmitterState', 'Loop Duration', '(Value=1.0)')
    API.call_method('AddModule', (ref(system, name, 'EmitterUpdateScript'), u.load_asset('/Niagara/Modules/Emitter/SpawnBurst_Instantaneous')))
    put(system, name, 'EmitterUpdateScript', 'SpawnBurst_Instantaneous', 'Spawn Count',
        f'(HlslExpression="{count}")', '/Script/NiagaraEditor.NiagaraExt_StackInputData_HlslExpression')
    put(system, name, 'EmitterUpdateScript', 'SpawnBurst_Instantaneous', 'Spawn Time', '(Value=0)')
    common = {'Particles.Velocity': (VEC3, 'float3(0,0,0)'),
              'Particles.SpriteUVScale': (VEC2, 'float2(1,1)'), 'Particles.SubImageIndex': (FLOAT, '0'),
              'Particles.SpriteRotation': (FLOAT, '0'), **values}
    if spawn_values:
        # Cache per-contact slot data before the normal spawn assignment reads it.
        # Give this module its own tag so the update module never repeats the lookup.
        assignments(system, name, 'ParticleSpawnScript', spawn_values)
        tag = 'Fireball.Assignments.' + name + '.ParticleSpawnScript'
        EAL.set_metadata_tag(system, 'ArrowRain.SpawnCache.' + name, EAL.get_metadata_tag(system, tag))
        EAL.remove_metadata_tag(system, tag)
    assignments(system, name, 'ParticleSpawnScript', {'Particles.Lifetime': (FLOAT, lifetime), **common})
    assignments(system, name, 'ParticleUpdateScript', common)


def upgrade(*, resume_owned_burst=False):
    if Path(u.Paths.project_content_dir()).resolve() != (ROOT / 'Content').resolve():
        raise RuntimeError('Author host must share FPSGAME Content')
    dirty = {str(p.get_path_name()) for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()}
    protected = [name for name in OWNED if not (resume_owned_burst and name == 'NS_ArrowRainBurst')]
    if any(DEST + '/' + name in dirty for name in protected):
        raise RuntimeError('Preserve unsaved Arrow Rain airburst assets')
    SRC.mkdir(parents=True, exist_ok=True)
    OUT.mkdir(parents=True, exist_ok=True)
    # Keep the pre-upgrade versions as bounded, task-owned recovery sources.
    before = SRC / 'Before'
    before.mkdir(exist_ok=True)
    for name in OWNED:
        package = ROOT / 'Content/Skills/MagicArrowRain20261026' / (name + '.uasset')
        if package.exists() and not (before / package.name).exists():
            shutil.copy2(package, before / package.name)
    first = len(base.saved)
    core = sprite_material('M_ArrowRainBurstCoreV2', 'CoreMask.hlsl', '2.8')
    wave = sprite_material('M_ArrowRainPressureWaveV2', 'WaveMask.hlsl', '2.0')
    smoke = smoke_material()
    arrow_tip_material()
    system = u.load_asset(DEST + '/NS_ArrowRainBurst')
    source = u.load_asset('/Game/NiagaraExamples/FX_Explosions/NS_Explosion_Small')
    glow = u.load_asset(DEST + '/M_ArrowRainGlow')
    if not system or not source or not glow:
        raise RuntimeError('Restore base Arrow Rain assets first')
    # Only replace the original owned burst layers and our V2 layers.
    for name in ['AirPressure', 'PressureFlash']:
        if name in emitters(system):
            API.call_method('RemoveEmitter', (ref(system, name),))
    for name, typ in [('Radius', FLOAT), ('Seed', FLOAT)]:
        user_parameter(system, name, typ)
    a = 'frac((float(Particles.UniqueID)+User.Seed)*.618033989)'
    b = 'frac((float(Particles.UniqueID)+User.Seed)*.414213562)'
    age, norm = 'Particles.Age', 'Particles.NormalizedAge'
    direction = f'float3(cos({a}*6.28318),sin({a}*6.28318),0)'
    seed = {'Particles.DynamicMaterialParameter': (VEC4, f'float4({a},0,0,0)')}
    layer(system, source, 'BurstCoreV2', core, 1, '.20', {
        **seed, 'Particles.Position': (POSITION, 'float3(0,0,0)'),
        'Particles.SpriteSize': (VEC2, f'float2(1,1)*(140+180*(1-exp(-{age}*24)))'),
        'Particles.Color': (COLOR, f'float4(lerp(float3(.55,1,.72),float3(.07,.9,.23),saturate({age}/.065)),.96*(1-{smooth(.055,.20,age)}))')})
    layer(system, source, 'PressureWaveV2', wave, 1, '.28', {
        **seed, 'Particles.Position': (POSITION, 'float3(0,0,8)'),
        'Particles.SpriteSize': (VEC2, f'float2(1,.48)*(80+(User.Radius*1.8-80)*(1-pow(1-saturate({age}/.25),2)))'),
        'Particles.Color': (COLOR, f'float4(.10,.88,.26,{smooth(.015,.04,age)}*.78*(1-{smooth(.09,.28,age)}))')})
    inner = '(float(Particles.UniqueID)<4.0)'
    radius = f'({inner}?User.Radius*.10:User.Radius*(.34+{b}*.10))'
    alpha = f'({inner}?.82*(1-{smooth(.12,.30,age)}):.72*(1-{smooth(.22,.80,age)}))'
    layer(system, source, 'RollingSmokeV2', smoke, 16, f'.60+{a}*.20', {
        **seed, 'Particles.Position': (POSITION, f'{direction}*{radius}*(1-exp(-{age}*17))+float3(0,0,({b}-.5)*45+{age}*22)'),
        'Particles.SpriteSize': (VEC2, f'float2(125,95)*(.55+.95*(1-exp(-{age}*15)))*(.85+{b}*.25)'),
        'Particles.SpriteRotation': (FLOAT, f'({b}-.5)*45'),
        'Particles.Color': (COLOR, f'float4(.22,.32,.25,{alpha}*saturate({age}/.025))')})
    ray = f'normalize({direction}+float3(0,0,({b}-.5)*.50))'
    layer(system, source, 'RadialStreaksV2', glow, 10, f'.18+{b}*.08', {
        **seed, 'Particles.Position': (POSITION, f'{ray}*(20+240*(1-exp(-{age}*12)))'),
        'Particles.SpriteAlignment': (VEC3, ray),
        'Particles.SpriteSize': (VEC2, f'float2(5.5,85)*(.55+.45*(1-{norm}))'),
        'Particles.Color': (COLOR, f'float4(.18,1,.36,.80*(1-{smooth(.04,.25,age)}))')}, 'CustomAlignment')
    system.set_editor_property('fixed_bounds', u.Box(min=u.Vector(-450,-450,-250), max=u.Vector(450,450,250)))
    EAL.set_metadata_tag(system, 'ArrowRain.AirburstVersion', 'V2: core / pressure wave / 16 smoke / 10 rays')
    base.finish(system)
    saved = base.saved[first:]
    receipt = {'version': 'AirburstV2', 'saved_at': datetime.now().isoformat(), 'saved_assets': saved,
               'particle_budget': {'core': 1, 'wave': 1, 'smoke': 16, 'streaks': 10, 'total': 28},
               'max_particle_lifetime_seconds': .8, 'new_runtime_components': 0,
               'gameplay_tested': False, 'rendered': False, 'audio_changed': False}
    (OUT / 'asset-receipt.json').write_text(json.dumps(receipt, ensure_ascii=False, indent=2), encoding='utf8')
    u.log('MAGIC_ARROW_RAIN_AIRBURST_V2_SAVED ' + json.dumps(receipt))
    return saved


if __name__ == '__main__':
    upgrade()
