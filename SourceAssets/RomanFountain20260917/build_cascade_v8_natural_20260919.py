"""Author coherent random overflow and clustered droplets, without running the game.

Reuses the accepted V7 sheet geometry and particle material. V7 assets stay intact.
The small periodic RGBA field is original numerical data generated below, not an
image download. Water flow uses retarded time so variation travels with the water.
"""
import importlib.util
import json
import math
import random
import struct
from pathlib import Path
import unreal as u

SOURCE = Path(__file__).parent
spec = importlib.util.spec_from_file_location('fountain_v7_library', SOURCE/'build_cascade_v7_20260919.py')
v7 = importlib.util.module_from_spec(spec)
spec.loader.exec_module(v7)
ROOT = '/Game/Props/RomanFountain20260917/OverflowV8'
v7.ROOT = ROOT
M, E, TOOLS, API = v7.M, v7.E, v7.TOOLS, v7.API
node, wire, prop, scalar, custom = v7.node, v7.wire, v7.prop, v7.scalar, v7.custom
ref, expr, assignments = v7.ref, v7.expr, v7.assignments
RECEIPT = []


def save(asset):
    if isinstance(asset, u.Material):
        errors = M.recompile_material(asset)
        if errors:
            raise RuntimeError(str(errors))
    if isinstance(asset, u.NiagaraSystem) and not u.RainAssetEditor.compile_rain(asset):
        raise RuntimeError('Niagara compilation failed: '+asset.get_path_name())
    if not E.save_loaded_asset(asset, False):
        raise RuntimeError('Asset save failed: '+asset.get_path_name())
    RECEIPT.append(asset.get_path_name())
    u.log('FOUNTAIN_V8_AUTHORED '+asset.get_path_name())


def noise_texture():
    path = ROOT+'/T_FountainFlowNoiseV8'
    if E.does_asset_exist(path):
        return u.load_asset(path)
    size = 256
    rng = random.Random(2026091908)
    grids = [[(n, [rng.random() for _ in range(n*n)]) for n in (16, 32, 64)] for _ in range(4)]

    def value(grid, x, y):
        n, data = grid
        px, py = x*n/size, y*n/size
        ix, iy = int(px), int(py)
        fx, fy = px-ix, py-iy
        fx, fy = fx*fx*(3-2*fx), fy*fy*(3-2*fy)
        a, b = data[(iy % n)*n+ix % n], data[(iy % n)*n+(ix+1) % n]
        c, d = data[((iy+1) % n)*n+ix % n], data[((iy+1) % n)*n+(ix+1) % n]
        return (a+(b-a)*fx)*(1-fy)+(c+(d-c)*fx)*fy

    pixels = bytearray()
    for y in range(size):
        for x in range(size):
            rgba = []
            for channel in grids:
                n = sum(w*value(g, x, y) for w, g in zip((.68, .24, .08), channel))
                rgba.append(round(max(0., min(1., .5+(n-.5)*1.35))*255))
            pixels.extend((rgba[2], rgba[1], rgba[0], rgba[3]))
    source = SOURCE/'fountain_flow_noise_v8.tga'
    source.write_bytes(struct.pack('<BBBHHBHHHHBB', 0, 0, 2, 0, 0, 0, 0, 0, size, size, 32, 0x28)+pixels)
    E.make_directory(ROOT)
    task = u.AssetImportTask()
    for key, val in dict(filename=str(source), destination_path=ROOT,
                         destination_name='T_FountainFlowNoiseV8', automated=True, save=False).items():
        task.set_editor_property(key, val)
    TOOLS.import_asset_tasks([task])
    texture = u.load_asset(path)
    if not texture:
        raise RuntimeError('Noise texture import failed')
    texture.set_editor_property('srgb', False)
    texture.set_editor_property('compression_settings', u.TextureCompressionSettings.TC_MASKS)
    texture.set_editor_property('address_x', u.TextureAddress.TA_WRAP)
    texture.set_editor_property('address_y', u.TextureAddress.TA_WRAP)
    save(texture)
    return texture


def sheet_material(name, noise, detailed):
    mat, fresh = v7.new_material(name)
    if not fresh:
        return mat
    uv = node(mat, u.MaterialExpressionTextureCoordinate)
    meta = node(mat, u.MaterialExpressionTextureCoordinate)
    meta.set_editor_property('coordinate_index', 1)
    phase = scalar(mat, 'InstancePhase', 0)
    time = node(mat, u.MaterialExpressionTime)
    tex = node(mat, u.MaterialExpressionTextureObjectParameter)
    tex.set_editor_property('parameter_name', 'FlowNoise')
    tex.set_editor_property('texture', noise)
    tex.set_editor_property('sampler_type', u.MaterialSamplerType.SAMPLERTYPE_MASKS)
    # Both tiers share exactly the same low-frequency domain. Detail fades before
    # 40 m, leaving the same holes/outline as the one-sample far material.
    detail = scalar(mat, 'FlowDetail', 1 if detailed else 0)
    code = '''
float f=saturate(UV.y);
float q=T+Phase-f*Meta.y;
float shift=frac(Phase*.1031+Meta.x*.217);
float2 domain=float2(UV.x+shift,q*.023+Meta.x*.319);
float4 broad=Texture2DSampleLevel(NoiseTex,NoiseTexSampler,domain,1);
float4 fine=broad;
'''
    if detailed:
        code += '''
float2 small=float2(UV.x*3+shift+(broad.g-.5)*.11,q*.16+Meta.x*.413);
fine=lerp(broad,Texture2DSampleLevel(NoiseTex,NoiseTexSampler,small,0),Detail);
'''
    code += '''
float feed=saturate((broad.r-.28)*2.15);
float breakup=smoothstep(.06,.90,f);
float threshold=.25+.15*breakup;
float ribbon=smoothstep(threshold,threshold+.18,feed+(fine.r-.5)*.35);
float coverage=lerp(.72+.28*feed,ribbon,breakup);
float foam=(.06+.22*f)*smoothstep(.58,.88,fine.g)*smoothstep(.12,.60,feed);
float sway=(broad.g-.5)*2.6+(fine.b-.5)*.45;
return float4(coverage,foam,sway,(fine.a-.5)*2);
'''
    field = custom(mat, code, dict(UV=uv, Meta=meta, T=time, Phase=phase, NoiseTex=tex, Detail=detail), 4)
    displacement = custom(mat, '''
float a=UV.x*6.2831853;
float f=saturate(UV.y);
float envelope=smoothstep(0,.26,f)*(.35+.65*f);
float radial=envelope*F.z*Amplitude;
float tangent=envelope*F.w*Amplitude*.16;
return float3(cos(a)*radial-sin(a)*tangent,
              sin(a)*radial+cos(a)*tangent,F.w*Amplitude*.18*(4*f*(1-f)));
''', dict(UV=uv, F=field, Amplitude=scalar(mat, 'WaveAmplitude', 3.6)), 3)
    transform = node(mat, u.MaterialExpressionTransform)
    transform.set_editor_property('transform_source_type', u.MaterialVectorCoordTransformSource.TRANSFORMSOURCE_LOCAL)
    transform.set_editor_property('transform_type', u.MaterialVectorCoordTransform.TRANSFORM_WORLD)
    wire(displacement, transform, '')
    prop(transform, 'WORLD_POSITION_OFFSET')
    prop(custom(mat, 'return lerp(float3(.16,.26,.29),float3(.72,.80,.81),F.y);', dict(F=field), 3), 'BASE_COLOR')
    prop(scalar(mat, 'Roughness', .13), 'ROUGHNESS')
    prop(scalar(mat, 'Specular', .5), 'SPECULAR')
    prop(custom(mat, 'return normalize(float3(F.z*.19,F.w*.13,1));', dict(F=field), 3), 'NORMAL')
    fresnel = node(mat, u.MaterialExpressionFresnel)
    fresnel.set_editor_property('exponent', 4.)
    alpha = custom(mat, '''
float edge=saturate((1-UV.y)*24);
return F.x*edge*min(.68,Base+Fresnel*.26+F.y*.34);
''', dict(UV=uv, F=field, Fresnel=fresnel, Base=scalar(mat, 'OpacityBase', .22)))
    fade = node(mat, u.MaterialExpressionDepthFade)
    fade.set_editor_property('fade_distance_default', 3.)
    wire(alpha, fade, 'Opacity')
    prop(fade, 'OPACITY')
    save(mat)
    return mat


def random_value(source, salt):
    # Spawn-only scalar hash. Different salts decorrelate tier, speed and size.
    return f'frac(sin(({source})*12.9898+User.FountainSeed*17.173+{salt:.3f})*43758.5453)'


def smooth_random(time, salt):
    cell = f'floor({time})'
    # Emitter scripts execute in Niagara's CPU VM, which lacks smoothstep.
    t = f'frac({time})'
    blend = f'({t}*{t}*(3.0-2.0*{t}))'
    return f'lerp({random_value(cell,salt)},{random_value(f"({cell}+1.0)",salt)},{blend})'


def splash_system():
    path = ROOT+'/NS_FountainLandingSprayV8'
    if E.does_asset_exist(path):
        system = u.load_asset(path)
        if E.get_metadata_tag(system, 'FountainV8Complete') == '1':
            return system
    else:
        system = E.duplicate_asset('/Game/Props/RomanFountain20260917/OverflowV7/NS_FountainLandingSprayV7', path)
    if not system:
        raise RuntimeError('Missing V7 spray scaffold')
    en = 'RainSplashes'
    for sc, keep in [('ParticleSpawnScript', {'InitializeParticle'}), ('ParticleUpdateScript', {'ParticleState'})]:
        stack = API.call_method('GetScriptStackTopology', (ref(system, en, sc),))
        for module in stack.get_editor_property('modules'):
            name = str(module.get_editor_property('module_name'))
            if name not in keep:
                API.call_method('RemoveModule', (ref(system, en, sc, name),))
    if 'FountainSeed' not in API.call_method('GetUserVariables', (system,)).export_text():
        var = u.NiagaraExt_UserVariable()
        var.import_text('(Name="User.FountainSeed",Type=(ClassStructOrEnum="/Script/Niagara.NiagaraFloat",UnderlyingType=2))')
        API.call_method('AddUserVariables', (system, [var]))
    # Smooth emitter-level variation only lowers the actor's rate limit.
    rate = f'clamp(User.SpawnRate,0.0,480.0)*(.62+.38*{smooth_random("Emitter.Age*.7",19.7)})'
    expr(system, en, 'EmitterUpdateScript', 'SpawnRate', 'SpawnRate', rate)
    FLOAT = '/Script/Niagara.NiagaraFloat'
    VEC2, VEC3 = '/Script/CoreUObject.Vector2f', '/Script/CoreUObject.Vector3f'
    POS, COLOR = '/Script/Niagara.NiagaraPosition', '/Script/CoreUObject.LinearColor'
    rnd = lambda salt: random_value('float(Particles.UniqueID)', salt)
    layer = rnd(11.3)
    tier = f'({layer}<.15?0.0:({layer}<.45?1.0:({layer}<.87?2.0:3.0)))'
    def choose(values):
        return f'({tier}==0.0?{values[0]}:({tier}==1.0?{values[1]}:({tier}==2.0?{values[2]}:{values[3]})))'
    radius = choose([f"{f['landing']:.5f}" for f in v7.FALLS])
    height = choose([f"{f['bottom']:.5f}" for f in v7.FALLS])
    group = f'(floor({rnd(31.7)}*7.0)+{tier}*13.0)'
    centre = random_value(group, 17.1)
    drift = smooth_random(f'(Emitter.Age*.17+{tier}*.37)', 27.3)
    clustered = f'({centre}+({rnd(71.5)}-.5)*(.035+.07*{rnd(73.1)})+({drift}-.5)*.05)'
    angle = f'(6.2831853*({rnd(53.7)}<.22?{rnd(59.3)}:{clustered}))'
    r = f'({radius}+({rnd(89.3)}-.5)*6.0)'
    speed, upward, tangent = f'(30+45*{rnd(101.7)})', f'(90+85*{rnd(107.3)})', f'(({rnd(113.9)}-.5)*36)'
    origin = f'float3(cos({angle})*{r},sin({angle})*{r},{height}+1)'
    velocity = f'float3(cos({angle})*{speed}-sin({angle})*{tangent},sin({angle})*{speed}+cos({angle})*{tangent},{upward})'
    # Store random initial conditions once. Update only advances the trajectory;
    # no changing hash or emitter clock may move an already living droplet sideways.
    assignments(system, en, 'ParticleSpawnScript', {
        'Particles.FountainOrigin': (VEC3, origin),
        'Particles.FountainVelocity': (VEC3, velocity),
        'Particles.FountainAlpha': (FLOAT, f'(.5+.5*{rnd(127.1)})'),
        'Particles.Lifetime': (FLOAT, f'({upward}*2/980.0)'),
        'Particles.SpriteSize': (VEC2, f'float2(1.0+{rnd(137.3)}*1.8,2.5+{rnd(149.9)}*4.0)'),
        'Particles.SubImageIndex': (FLOAT, '0'),
        'Particles.SpriteRotation': (FLOAT, '0'),
    })
    age = 'Particles.Age'
    fade = 'saturate(Particles.NormalizedAge*10)*saturate((1-Particles.NormalizedAge)*5)*Particles.FountainAlpha'
    common = {
        'Particles.Position': (POS, f'Particles.FountainOrigin+Particles.FountainVelocity*{age}-float3(0,0,490*{age}*{age})'),
        'Particles.Velocity': (VEC3, f'Particles.FountainVelocity-float3(0,0,980*{age})'),
        'Particles.Color': (COLOR, f'float4(.66,.77,.80,{fade})'),
    }
    assignments(system, en, 'ParticleSpawnScript', common)
    assignments(system, en, 'ParticleUpdateScript', common)
    E.set_metadata_tag(system, 'FountainV8Budget', 'rate<=480/s; life<=.3572s; max4 systems/world; random initial conditions only at spawn')
    save(system)
    E.set_metadata_tag(system, 'FountainV8Complete', '1')
    E.save_loaded_asset(system, False)
    return system


def main():
    noise = noise_texture()
    near = sheet_material('M_FountainOverflowNearV8', noise, True)
    far = sheet_material('M_FountainOverflowFarV8', noise, False)
    spray = splash_system()
    out = Path(u.Paths.project_saved_dir())/'FountainOverflowV8'
    out.mkdir(parents=True, exist_ok=True)
    (out/'authoring.json').write_text(json.dumps({
        'assets': [a.get_path_name() for a in (noise, near, far, spray)],
        'saved_this_run': RECEIPT, 'noise': {'size': 256, 'channels': 4, 'seed': 2026091908},
        'geometry': 'unchanged V7 mesh', 'near_noise_fetches': 2, 'far_noise_fetches': 1,
        'particle_rate_cap': 480, 'runtime_tested': False,
    }, indent=2), encoding='utf-8')
    u.log('FOUNTAIN_V8_AUTHORING_COMPLETE (assets only; no runtime test)')


if __name__ == '__main__':
    main()
