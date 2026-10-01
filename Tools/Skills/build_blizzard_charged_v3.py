"""Save Blizzard ChargedV3 clouds, mixed rain/snow, soft frost and aim decal.

Owns only /Game/Skills/Blizzard/ChargedV3. Existing storm and IceSpike assets
are read-only sources. No PIE, rendering, playback or gameplay tests.
"""
import json
import re
import sys
from pathlib import Path
import unreal as u

ROOT = Path(u.Paths.project_dir())
sys.path.insert(0, str(ROOT / 'Tools/Skills'))
from build_fireball_assets import API, LIB, TOOLS, ref, emitters, setdata, put, assignments, save, CREATED
from build_fireball_flames import trim, FLOAT, VEC2, VEC3, POSITION, COLOR
from build_fireball_flight import user_parameter, expression
from build_blizzard_assets import custom
from build_ice_spike_frost_v2 import strip_source_renderers
import build_blizzard_storm_cloud as storm

DEST = '/Game/Skills/Blizzard/ChargedV3'
EAL = u.EditorAssetLibrary
CLOUD_LAYERS = [('CloudCrown', 0., (.19, .22, .26)), ('CloudBody', .50, (.12, .14, .17)),
                ('CloudShadowBase', 1.04, (.055, .066, .085)), ('CloudLowerRoll', 1.26, (.08, .095, .12))]
GATHER_CLOUD_COUNTS = [12, 10, 7, 0]


def preview_color():
    # The ground indicator and projectile paths use the same authored color.
    source = (ROOT / 'Source/FPSGAME/Skills/FPSMagicPreview.cpp').read_text(encoding='utf-8-sig')
    match = re.search(r'FPSMagicPreview::LineColor\(\)\s*\{\s*return FLinearColor\(([^)]+)\)', source)
    if not match:
        raise RuntimeError('Cannot read the shared magic preview color')
    return u.LinearColor(*(float(value.strip().rstrip('f')) for value in match.group(1).split(',')))


def own(source, name):
    path = DEST + '/' + name
    obj = u.load_asset(path) if EAL.does_asset_exist(path) else EAL.duplicate_asset(source, path)
    if not obj:
        raise RuntimeError('Missing Blizzard source: ' + source)
    return obj


def material(name, decal=False):
    path = DEST + '/' + name
    m = u.load_asset(path) if EAL.does_asset_exist(path) else TOOLS.create_asset(name, DEST, u.Material, u.MaterialFactoryNew())
    LIB.delete_all_material_expressions(m)
    m.set_editor_property('blend_mode', u.BlendMode.BLEND_TRANSLUCENT)
    if decal:
        m.set_editor_property('material_domain', u.MaterialDomain.MD_DEFERRED_DECAL)
    else:
        m.set_editor_property('shading_model', u.MaterialShadingModel.MSM_DEFAULT_LIT)
        m.set_editor_property('translucency_lighting_mode', u.TranslucencyLightingMode.TLM_VOLUMETRIC_NON_DIRECTIONAL)
        m.set_editor_property('output_translucent_velocity', False)
        m.set_editor_property('disable_depth_test', False)
        LIB.set_material_usage(m, u.MaterialUsage.MATUSAGE_NIAGARA_SPRITES)
    return m


def out(expr, prop, channel=''):
    if not LIB.connect_material_property(expr, channel, prop):
        raise RuntimeError('Cannot connect Blizzard material output')


def finish(m):
    errors = LIB.recompile_material(m)
    if errors:
        raise RuntimeError(m.get_path_name() + ': ' + str(errors))
    save(m)
    return m


def surfaces():
    for name in ['Heart', 'Shell']:
        ice = own('/Game/Skills/IceSpike/FrostV2/M_Ice' + name, 'M_BlizzardIce' + name)
        LIB.set_material_usage(ice, u.MaterialUsage.MATUSAGE_INSTANCED_STATIC_MESHES)
        finish(ice)
    frost = material('M_BlizzardGroundFrost', True)
    uv = LIB.create_material_expression(frost, u.MaterialExpressionTextureCoordinate)
    tiled = custom(frost, 'return UV*5;', {'UV': (uv, '')}, u.CustomMaterialOutputType.CMOT_FLOAT2)
    tex = LIB.create_material_expression(frost, u.MaterialExpressionTextureSample)
    tex.set_editor_property('texture', u.load_asset('/Game/Skills/IceWall/FabIceV3/T_IceSurfaceColor'))
    tex.set_editor_property('sampler_type', u.MaterialSamplerType.SAMPLERTYPE_COLOR)
    LIB.connect_material_expressions(tiled, '', tex, 'Coordinates')
    fade = LIB.create_material_expression(frost, u.MaterialExpressionScalarParameter)
    fade.set_editor_property('parameter_name', 'Fade')
    fade.set_editor_property('default_value', 0.)
    mask = custom(frost, 'float2 p=(UV-.5)*2;float a=atan2(p.y,p.x);float d=length(p)+.075*sin(a*7)+.045*sin(a*13+1.2);float e=saturate((1.06-d)*3.0);float n=saturate((C.r*.65+C.g*.35-.22)*2);return e*e*(3-2*e)*(.09+.46*n*n)*Fade;',
                  {'UV': (uv, ''), 'C': (tex, 'RGB'), 'Fade': (fade, '')})
    color = custom(frost, 'return lerp(float3(.46,.57,.62),float3(.78,.85,.87),saturate(C.r*.65+C.g*.35));',
                   {'C': (tex, 'RGB')}, u.CustomMaterialOutputType.CMOT_FLOAT3)
    out(mask, u.MaterialProperty.MP_OPACITY)
    out(color, u.MaterialProperty.MP_BASE_COLOR)
    out(custom(frost, 'return .62;', {}), u.MaterialProperty.MP_ROUGHNESS)
    finish(frost)

    preview = material('M_BlizzardAimPreview', True)
    uv = LIB.create_material_expression(preview, u.MaterialExpressionTextureCoordinate)
    tint = LIB.create_material_expression(preview, u.MaterialExpressionVectorParameter)
    tint.set_editor_property('parameter_name', 'Tint')
    tint.set_editor_property('default_value', preview_color())
    fade = LIB.create_material_expression(preview, u.MaterialExpressionScalarParameter)
    fade.set_editor_property('parameter_name', 'Fade')
    fade.set_editor_property('default_value', 1.)
    mask = custom(preview, 'float2 p=(UV-.5)*2;float d=length(p);float a=atan2(p.y,p.x);float ring=saturate((.034-abs(d-.91))/.018);float marks=.68+.32*saturate(sin(a*24));return (ring*marks*.82+saturate((.88-d)*4)*.025)*Fade;',
                  {'UV': (uv, ''), 'Fade': (fade, '')})
    out(mask, u.MaterialProperty.MP_OPACITY)
    out(tint, u.MaterialProperty.MP_BASE_COLOR, 'RGB')
    out(custom(preview, 'return .72;', {}), u.MaterialProperty.MP_ROUGHNESS)
    finish(preview)

    rain = material('M_BlizzardRain')
    uv = LIB.create_material_expression(rain, u.MaterialExpressionTextureCoordinate)
    pc = LIB.create_material_expression(rain, u.MaterialExpressionParticleColor)
    mask = custom(rain, 'float2 p=(UV-.5)*2;return pow(saturate(1-abs(p.x)),2.5)*saturate(1-p.y*p.y)*A;', {'UV': (uv, ''), 'A': (pc, 'A')})
    depth = LIB.create_material_expression(rain, u.MaterialExpressionDepthFade)
    depth.set_editor_property('fade_distance_default', 7.)
    LIB.connect_material_expressions(mask, '', depth, 'InOpacity')
    out(depth, u.MaterialProperty.MP_OPACITY)
    out(pc, u.MaterialProperty.MP_BASE_COLOR, 'RGB')
    out(custom(rain, 'return .15;', {}), u.MaterialProperty.MP_ROUGHNESS)
    finish(rain)
    return rain


def gather_cloud_material(source):
    # Normandy's DepthFade reads scene depth. UE forbids that when translucent
    # velocity output also writes depth; responsive AA and local simulation
    # retain the held-cloud motion without replacing its soft intersection mask.
    parent = own(source.get_editor_property('parent').get_path_name(), 'M_BlizzardGatherCloud')
    parent.set_editor_property('output_translucent_velocity', False)
    parent.set_editor_property('enable_responsive_aa', True)
    LIB.set_material_usage(parent, u.MaterialUsage.MATUSAGE_NIAGARA_SPRITES)
    finish(parent)
    instance = own(source.get_path_name(), 'MI_BlizzardGatherCloud')
    LIB.set_material_instance_parent(instance, parent)
    for key, value in {'Opacity': 1.45, 'Cloud_Speed': .13,
                       'AdditionalNoise_SpeedX': .075, 'AdditionalNoise_SpeedY': -.095}.items():
        LIB.set_material_instance_scalar_parameter_value(instance, key, value)
    LIB.update_material_instance(instance)
    save(instance)
    return instance


def cloud_particle_fields(level, color, gather):
    a = 'frac(float(Particles.UniqueID)*.618033989)'
    b = 'frac(float(Particles.UniqueID)*.754877666)'
    c = 'frac(float(Particles.UniqueID)*.569840296)'
    width = f'User.RadiusX*(.88+{c}*.48)'
    height = f'min(({width})*.80,User.CloudHeight*.62)'
    radial = f'sqrt({b})*' + ('.66' if level < .2 else '.85')
    theta = f'({a}*6.2831853+{level}+.065*sin(Particles.Age*.5+{c}*6.2831853))'
    pos = (f'User.CurrentPosition+(User.Side*cos({theta})*User.RadiusX+User.Up*sin({theta})*User.RadiusY)*({radial})'
           f'+User.SurfaceNormal*(User.CloudHeight-({height})*.5-min(User.RadiusY*.90,User.CloudHeight*.26)*{level})')
    size = f'float2({width},{height})*(1+.028*sin(Particles.Age*.6+{c}*6.2831853))'
    rgba = f'float4({color[0]},{color[1]},{color[2]},saturate(User.Strength))'
    rotation = f'({c}-.5)*32'
    if gather:
        # The component already follows CloudOrigin late in the frame. Simulate
        # offsets locally so old world positions cannot remain behind the player.
        seed = f'(float(Particles.UniqueID)+{level}*17.23)'
        a, b, c = [f'frac({seed}*{value})' for value in ['.618033989', '.754877666', '.569840296']]
        phase = f'({c}*6.2831853)'
        direction = '-1' if level > .75 else '1'
        width = f'User.RadiusX*(.82+{c}*.46)'
        height = f'min(({width})*.80,User.CloudHeight*.62)'
        spread = '.62' if level < .2 else '.80'
        radial = f'sqrt({b})*{spread}*(1+.06*sin(Particles.Age*(.71+{b}*.31)+{phase}))'
        theta = f'({a}*6.2831853+{level}+Particles.Age*(.16+{b}*.10)*({direction})+.07*sin(Particles.Age*.57+{phase}))'
        pos = (f'-User.SurfaceNormal*(User.CloudHeight*.5)+(User.Side*cos({theta})*User.RadiusX+User.Up*sin({theta})*User.RadiusY)*({radial})'
               f'+User.SurfaceNormal*(User.CloudHeight-({height})*.5-min(User.RadiusY*.90,User.CloudHeight*.26)*{level}'
               f'+User.CloudHeight*.045*sin(Particles.Age*(.91+{b}*.35)+{phase}))')
        size = (f'float2(({width})*(1+.065*sin(Particles.Age*(.80+{b}*.27)+{phase})),'
                f'({height})*(1+.07*sin(Particles.Age*.93+{phase}+1.3)))')
        shade = f'(1+.07*sin(Particles.Age*.65+{phase}))'
        alpha = f'saturate(User.Strength)*(.82+{b}*.14)*(.92+.08*sin(Particles.Age*(.68+{a}*.22)+{phase}))'
        rgba = f'float4({color[0]}*{shade},{color[1]}*{shade},{color[2]}*{shade},{alpha})'
        rotation = f'({c}-.5)*48+Particles.Age*(2+{b}*2)*({direction})'
    spawn = {'Particles.Lifetime': (FLOAT, 'max(.6,User.StormDuration+.6)'),
             'Particles.Position': (POSITION, pos), 'Particles.SpriteSize': (VEC2, size),
             'Particles.SpriteRotation': (FLOAT, rotation), 'Particles.Color': (COLOR, rgba),
             'Particles.SubImageIndex': (FLOAT, '0')}
    update = {key: value for key, value in spawn.items() if key not in ['Particles.Lifetime', 'Particles.SpriteRotation']}
    if gather:
        update['Particles.SpriteRotation'] = (FLOAT, rotation)
    return spawn, update


def cloud_layer(system, mat, name, count, level, color, lifecycle, gather):
    # These emitter stacks are rebuilt; their cached assignment node IDs are stale.
    for script in ['ParticleSpawnScript', 'ParticleUpdateScript']:
        EAL.remove_metadata_tag(system, 'Fireball.Assignments.' + name + '.' + script)
    API.call_method('AddEmitter', (system, u.load_asset('/Game/NiagaraExamples/FX_Explosions/Emitters/NE_Core'), name))
    trim(system, name, {'EmitterUpdateScript': ['EmitterState'], 'ParticleSpawnScript': ['InitializeParticle'], 'ParticleUpdateScript': ['ParticleState']})
    setdata('SetEmitterData', u.NiagaraExt_EmitterData, ref(system, name), {
        'bLocalSpace': gather, 'SimTarget': 'CPUSim',
        'InterpolatedSpawnMode': 'NoInterpolation' if gather else 'Interpolation'})
    setdata('SetRendererData', u.NiagaraExt_RendererData, ref(system, name, renderer=0), {
        'Material': mat.get_path_name(), 'MaterialUserParamBinding': {'Parameter': {'Name': 'None'}},
        'SubImageSize': {'X': 1, 'Y': 1}, 'bSubImageBlend': False, 'Alignment': 'Unaligned', 'FacingMode': 'FaceCamera',
        'SortMode': 'ViewDepth', 'bCastShadows': False, 'CutoutTexture': None, 'bUseMaterialCutoutTexture': False,
        'MotionVectorSetting': 'Precise' if gather else 'Disable'})
    for key, val in lifecycle.items():
        put(system, name, 'EmitterUpdateScript', 'EmitterState', key, val, '/Script/NiagaraEditor.NiagaraExt_StackInputData_Enum')
    expression(system, name, 'EmitterUpdateScript', 'EmitterState', 'Loop Duration', 'max(.6,User.StormDuration+.6)')
    API.call_method('AddModule', (ref(system, name, 'EmitterUpdateScript'), u.load_asset('/Niagara/Modules/Emitter/SpawnBurst_Instantaneous')))
    expression(system, name, 'EmitterUpdateScript', 'SpawnBurst_Instantaneous', 'Spawn Count', f'floor({count}*(1-saturate(User.DetailReduction)*.25)+.5)')
    put(system, name, 'EmitterUpdateScript', 'SpawnBurst_Instantaneous', 'Spawn Time', '(Value=0)')
    spawn, update = cloud_particle_fields(level, color, gather)
    assignments(system, name, 'ParticleSpawnScript', spawn)
    assignments(system, name, 'ParticleUpdateScript', update)


def cloud_lifecycle():
    source = u.load_asset(storm.TEMPLATE)
    lifecycle = {key: u.RainAssetEditor.read_input(source, 'Explosion', 'EmitterUpdateScript', 'EmitterState', key)
                 for key in ['Life Cycle Mode', 'Loop Behavior']}
    lifecycle['Life Cycle Mode'] = lifecycle['Life Cycle Mode'].replace('NewEnumerator0', 'NewEnumerator1').replace('"System"', '"Self"')
    lifecycle['Loop Behavior'] = lifecycle['Loop Behavior'].replace('NewEnumerator0', 'NewEnumerator1').replace('"Infinite"', '"Once"')
    return lifecycle


def clouds():
    storm.DEST = DEST
    mat = storm.cloud_material()
    for name, value in {'Opacity': 1.6, 'Fade': 12., 'DistanceFade_Distance': 8., 'DistanceFade_FallOff': 18.}.items():
        LIB.set_material_instance_scalar_parameter_value(mat, name, value)
    LIB.update_material_instance(mat)
    save(mat)
    gather_mat = gather_cloud_material(mat)
    lifecycle = cloud_lifecycle()
    for gather, name, counts in [(False, 'NS_BlizzardStormCloud', [18, 14, 9, 8]), (True, 'NS_BlizzardGatherCloud', GATHER_CLOUD_COUNTS)]:
        system = own(storm.TEMPLATE, name)
        for en in emitters(system):
            API.call_method('RemoveEmitter', (ref(system, en),))
        for key, typ in [('CurrentPosition', POSITION), ('Side', VEC3), ('Up', VEC3), ('SurfaceNormal', VEC3), ('Wind', VEC3),
                         ('RadiusX', FLOAT), ('RadiusY', FLOAT), ('CloudHeight', FLOAT), ('StormDuration', FLOAT),
                         ('CloudEmission', FLOAT), ('Strength', FLOAT), ('DetailReduction', FLOAT)]:
            user_parameter(system, key, typ)
        # The explosion template's system ends after five seconds. Match the
        # owning spell's duration, including the cloud's short release fade.
        expression(system, '', 'SystemUpdateScript', 'SystemState', 'Loop Duration',
                   'max(.6,User.StormDuration+.6)')
        for count, (en, level, color) in zip(counts, CLOUD_LAYERS):
            if count:
                cloud_layer(system, gather_mat if gather else mat, en, count, level, color, lifecycle, gather)
        system.set_editor_property('fixed_bounds',
            u.Box(min=u.Vector(-90, -90, -90), max=u.Vector(90, 90, 90)) if gather else
            u.Box(min=u.Vector(-1200, -1200, -80), max=u.Vector(1200, 1200, 1400)))
        save(system)


def particle_layer(system, name, mat, kind):
    trim(system, name, {'EmitterUpdateScript': ['EmitterState', 'SpawnRate'], 'ParticleSpawnScript': ['InitializeParticle'], 'ParticleUpdateScript': ['ParticleState']})
    for script in ['ParticleSpawnScript', 'ParticleUpdateScript']:
        EAL.remove_metadata_tag(system, 'Fireball.Assignments.' + name + '.' + script)
    setdata('SetEmitterData', u.NiagaraExt_EmitterData, ref(system, name), {'bLocalSpace': False, 'SimTarget': 'CPUSim', 'bInterpolatedSpawning': False})
    mist = kind == 'mist'
    setdata('SetRendererData', u.NiagaraExt_RendererData, ref(system, name, renderer=0), {
        'Material': mat.get_path_name(), 'MaterialUserParamBinding': {'Parameter': {'Name': 'None'}},
        'SubImageSize': {'X': 8 if mist else 1, 'Y': 8 if mist else 1}, 'bSubImageBlend': mist,
        'Alignment': 'VelocityAligned' if kind == 'rain' else 'Unaligned', 'FacingMode': 'FaceCamera',
        'bCastShadows': False, 'MotionVectorSetting': 'Disable', 'CutoutTexture': None, 'bUseMaterialCutoutTexture': False})
    strip_source_renderers(system, name)
    if kind == 'rain':
        source = u.load_asset('/Game/Skills/IceSpike/FrostV2/NS_ColdMist')
        for key in ['Life Cycle Mode', 'Loop Behavior']:
            val = u.RainAssetEditor.read_input(source, 'RocketTrail', 'EmitterUpdateScript', 'EmitterState', key)
            put(system, name, 'EmitterUpdateScript', 'EmitterState', key, val, '/Script/NiagaraEditor.NiagaraExt_StackInputData_Enum')
    for key, typ in [('CurrentPosition', POSITION), ('Side', VEC3), ('Up', VEC3), ('SurfaceNormal', VEC3), ('Wind', VEC3),
                     ('RadiusX', FLOAT), ('RadiusY', FLOAT), ('CloudHeight', FLOAT), ('Strength', FLOAT), ('DetailReduction', FLOAT)]:
        user_parameter(system, key, typ)
    a = 'frac(float(Particles.UniqueID)*.618033989)'
    b = 'frac(float(Particles.UniqueID)*.754877666)'
    c = 'frac(float(Particles.UniqueID)*.569840296)'
    t = f'({a}*6.2831853)'
    radial = f'(.65+sqrt({b})*.35)' if mist else f'sqrt({b})'
    pos = f'User.CurrentPosition+(User.Side*cos({t})*User.RadiusX+User.Up*sin({t})*User.RadiusY)*{radial}'
    if kind == 'snow':
        rate, life = '95', 'max(.15,(User.CloudHeight+35)/220)'
        pos += f'+User.SurfaceNormal*(User.CloudHeight*(.72+{c}*.18))'
        vel = f'-User.SurfaceNormal*(170+{b}*100)+User.Wind*.65+User.Side*sin({t})*32'
        size, rgb, alpha = f'float2(1.5,2.6)*(1+{b}*1.5)', '.86,.92,.95', '.82'
    elif kind == 'rain':
        rate, life = '100', 'max(.10,(User.CloudHeight+25)/1150)'
        pos += f'+User.SurfaceNormal*(User.CloudHeight*(.76+{c}*.20))'
        vel = f'-User.SurfaceNormal*(1000+{b}*380)+User.Wind*.18'
        size, rgb, alpha = f'float2(.55,12)*(1+{b}*.45)', '.49,.63,.70', '.38'
    else:
        rate, life = '24', f'1.2+{c}*.7'
        pos += f'+User.SurfaceNormal*(12+{c}*24)'
        vel = f'User.Wind*.4+(User.Side*(-sin({t}))+User.Up*cos({t}))*24+User.SurfaceNormal*5'
        size, rgb, alpha = f'float2(76,38)*(1+{b}*.6)', '.58,.71,.77', '.32'
    expression(system, name, 'EmitterUpdateScript', 'SpawnRate', 'SpawnRate', f'{rate}*saturate(User.Strength)*(1-saturate(User.DetailReduction))')
    fade = 'saturate(Particles.NormalizedAge*6)*saturate((1-Particles.NormalizedAge)*4)'
    if not mist:
        fade += '*saturate(dot(Particles.Position-User.CurrentPosition,User.SurfaceNormal)/18)'
    assignments(system, name, 'ParticleSpawnScript', {'Particles.Lifetime': (FLOAT, life), 'Particles.Position': (POSITION, pos),
        'Particles.Velocity': (VEC3, vel), 'Particles.SpriteSize': (VEC2, size), 'Particles.SpriteRotation': (FLOAT, '0' if kind == 'rain' else f'{c}*360'),
        'Particles.Color': (COLOR, f'float4({rgb},{alpha})'), 'Particles.SubImageIndex': (FLOAT, '0')})
    update_pos = 'Particles.Position+Particles.Velocity*Engine.DeltaTime'
    if kind == 'snow':
        update_pos += f'+User.Side*cos(Particles.Age*5+{a}*6.2831853)*22*Engine.DeltaTime'
    assignments(system, name, 'ParticleUpdateScript', {'Particles.Position': (POSITION, update_pos),
        'Particles.SpriteSize': (VEC2, size + ('*(1+Particles.NormalizedAge*.25)' if mist else '')),
        'Particles.Color': (COLOR, f'float4({rgb},{alpha}*({fade}))'),
        'Particles.SubImageIndex': (FLOAT, 'clamp(Particles.NormalizedAge*56,0,63)' if mist else '0')})


def precipitation(rain):
    source = '/Game/Skills/IceSpike/FrostV2/NS_ColdMist'
    system = own(source, 'NS_BlizzardPrecipitation')
    for en in emitters(system):
        if en != 'RocketTrail':
            API.call_method('RemoveEmitter', (ref(system, en),))
    particle_layer(system, 'RocketTrail', u.load_asset('/Game/Skills/IceSpike/FrostV2/M_FrostCrystalSoft'), 'snow')
    # Use the installed Core template, replacing its renderer and one-shot spawning.
    en_source = u.load_asset('/Game/NiagaraExamples/FX_Explosions/Emitters/NE_Core')
    if not en_source:
        raise RuntimeError('Restore NiagaraExamples Core emitter')
    API.call_method('AddEmitter', (system, en_source, 'BlizzardRain'))
    API.call_method('AddModule', (ref(system, 'BlizzardRain', 'EmitterUpdateScript'), u.load_asset('/Niagara/Modules/Emitter/SpawnRate')))
    particle_layer(system, 'BlizzardRain', rain, 'rain')
    system.set_editor_property('fixed_bounds', u.Box(min=u.Vector(-1100, -1100, -100), max=u.Vector(1100, 1100, 1400)))
    save(system)
    mist = own(source, 'NS_BlizzardBoundaryMist')
    particle_layer(mist, 'RocketTrail', u.load_asset('/Game/Skills/IceSpike/FrostV2/MI_ColdMist'), 'mist')
    mist.set_editor_property('fixed_bounds', u.Box(min=u.Vector(-1100, -1100, -100), max=u.Vector(1100, 1100, 250)))
    save(mist)


def main():
    dirty = {str(p.get_path_name()) for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()}
    if any(p.startswith(DEST) for p in dirty):
        raise RuntimeError('Preserve unsaved Blizzard ChargedV3 packages')
    EAL.make_directory(DEST)
    rain = surfaces()
    clouds()
    precipitation(rain)
    receipt = {'saved_assets': list(CREATED), 'cloud_core_particles': 49, 'gather_core_particles': 29,
               'gather_local_space': True, 'gather_motion_vectors': 'Precise',
               'gather_material': DEST + '/MI_BlizzardGatherCloud',
               'preview_color_source': 'FPSMagicPreview::LineColor',
               'rain_rate': 100, 'snow_rate': 95, 'boundary_mist_rate': 24, 'systems_per_zone': 3,
               'ice_mesh_source': '/Game/Skills/IceSpike/FrostV2/SM_IceSpike_01..03',
               'ice_materials': ['M_IceHeart', 'M_IceShell'], 'gameplay_tested': False, 'rendered': False}
    folder = ROOT / 'Saved/BlizzardCharged20261001'
    folder.mkdir(parents=True, exist_ok=True)
    (folder / 'asset-authoring.json').write_text(json.dumps(receipt, indent=2), encoding='utf-8')
    print('BLIZZARD_CHARGED_V3_SAVED ' + json.dumps(receipt))


if __name__ == '__main__':
    main()
