"""Lower opacity & add smooth radial edge fade to Thunder Lance charge circle and electric FX.

Headless UE5 commandlet script. Backs up before-versions to
F:/FPSGAMEData/ArtProduction/ElectricMagic/ThunderLanceChargeClarity-20261127/Before
and writes a SHA-256 published.json receipt. No gameplay/rendering.
"""
import hashlib
import json
import shutil
import sys
from pathlib import Path
import unreal as u

ROOT = Path(u.Paths.convert_relative_path_to_full(u.Paths.project_dir()))
RAY_ROOT = ROOT / 'SourceAssets/ThunderLanceRay20261005'
PROD = Path('F:/FPSGAMEData/ArtProduction/ElectricMagic/ThunderLanceChargeClarity-20261127')
BEFORE = PROD / 'Before'
BEFORE.mkdir(parents=True, exist_ok=True)

sys.path.insert(0, str(ROOT / 'Tools/Skills'))
from build_fireball_assets import API, ref, emitters, setdata, put, assignments
from build_fireball_flames import trim, FLOAT, VEC2, VEC3, POSITION, COLOR
from build_fireball_flight import user_parameter, expression

EAL = u.EditorAssetLibrary
LIB = u.MaterialEditingLibrary
SEED = 'frac(float(Particles.UniqueID)*.618033989)'
SEED2 = 'frac(float(Particles.UniqueID)*.754877666)'
SEED3 = 'frac(float(Particles.UniqueID)*.569840296)'
ENUM = '/Script/NiagaraEditor.NiagaraExt_StackInputData_Enum'
TEMPLATE = '/Game/NiagaraExamples/FX_Explosions/NS_Explosion_Small'

TARGETS = [
    '/Game/Skills/ElectricMagic/ThunderLanceV2/M_ThunderLanceCircle',
    '/Game/Skills/ElectricMagic/LanceRay/Materials/M_ThunderLanceIris',
    '/Game/Skills/ElectricMagic/LanceRay/Materials/M_ThunderLanceGatherSpeck',
    '/Game/Skills/ElectricMagic/LanceRay/Materials/M_ThunderLanceGatherStreak',
    '/Game/Skills/ElectricMagic/LanceRay/NS_ThunderLanceGather',
    '/Game/Skills/ElectricMagic/NS_ThunderCharge',
]


def disk_path(asset_path):
    return ROOT / 'Content' / (asset_path.split('.')[0].removeprefix('/Game/') + '.uasset')


def backup_targets():
    for ap in TARGETS:
        src = disk_path(ap)
        dst = BEFORE / (ap.split('/')[-1] + '.uasset')
        if src.is_file() and not dst.exists():
            shutil.copy2(src, dst)


def sha256(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for chunk in iter(lambda: f.read(1 << 20), b''):
            h.update(chunk)
    return h.hexdigest()


def clear_expressions(mat):
    # Snapshot deletion avoids UE 5.8 iteration bug leaving stranded Custom nodes.
    for old in list(LIB.get_material_expressions(mat)):
        LIB.delete_material_expression(mat, old)


def save_asset(asset):
    if isinstance(asset, u.Material):
        errors = [str(e) for e in LIB.recompile_material(asset)]
        if errors:
            raise RuntimeError(f'Material compile failed {asset.get_path_name()}: {errors}')
    elif isinstance(asset, u.NiagaraSystem):
        if not u.RainAssetEditor.compile_rain(asset):
            raise RuntimeError(f'Niagara compile failed {asset.get_path_name()}')
    if not EAL.save_loaded_asset(asset, False):
        raise RuntimeError(f'Save failed {asset.get_path_name()}')
    print('THUNDER_CLARITY_SAVED', asset.get_path_name(), flush=True)


def rebuild_circle():
    path = '/Game/Skills/ElectricMagic/ThunderLanceV2/M_ThunderLanceCircle'
    mat = u.load_asset(path)
    if not mat:
        raise RuntimeError('Missing ' + path)
    clear_expressions(mat)
    mat.set_editor_property('blend_mode', u.BlendMode.BLEND_ADDITIVE)
    mat.set_editor_property('shading_model', u.MaterialShadingModel.MSM_UNLIT)
    mat.set_editor_property('two_sided', True)
    mat.set_editor_property('disable_depth_test', False)
    mat.set_editor_property('enable_responsive_aa', True)
    mat.set_editor_property('output_translucent_velocity', True)

    def node(cls):
        return LIB.create_material_expression(mat, cls)

    uv = node(u.MaterialExpressionTextureCoordinate)
    time = node(u.MaterialExpressionTime)
    charge = node(u.MaterialExpressionScalarParameter)
    charge.set_editor_property('parameter_name', 'Charge')
    charge.set_editor_property('default_value', 0.)

    shape = node(u.MaterialExpressionCustom)
    shape.set_editor_property('output_type', u.CustomMaterialOutputType.CMOT_FLOAT1)
    # Soft outer radial dissolve (0.68 -> 1.0) + clear central aiming window (0.24 -> 0.56)
    # + lowered overall opacity so the rune circle frames the target without obstructing aim.
    shape.set_editor_property('code', '''
float2 p=(UV-.5)*2;
float r=length(p),a=atan2(p.y,p.x),c=saturate(Charge);
float aa=max(fwidth(r)*1.35,.003);
float outer=1-smoothstep(.014,.014+aa*1.6,abs(r-.86));
float inner=1-smoothstep(.010,.010+aa*1.5,abs(r-.66));
float turn=a-Time*.28,back=a+Time*.19;
float notches=pow(saturate(.5+.5*cos(turn*24)),16);
float ticks=notches*(1-smoothstep(.022,.022+aa*1.4,abs(r-.80)));
float q=abs(frac((back+3.14159265)*12/6.2831853)-.5);
float stave=(1-smoothstep(.020,.038,q))*(1-smoothstep(.042,.042+aa*1.4,abs(r-.745)));
float diamond=1-smoothstep(.013,.013+aa*1.4,abs(abs(r-.745)+q*.30-.044));
diamond*=1-smoothstep(.14,.18,q);
float core=1-smoothstep(.007,.007+aa*1.6,abs(r-(.47-.05*c)));
core*=.22+.32*pow(saturate(.5+.5*cos(turn*6)),10);
float outerFade=pow(saturate(1-smoothstep(.66,1.0,r)),1.45);
float centerClear=smoothstep(.24,.56,r);
float edgeSoft=outerFade*centerClear;
float halo=exp(-pow((r-.74)/.13,2))*0.10*outerFade*centerClear;
float pulse=.93+.07*sin(Time*3.0);
float pattern=saturate(outer*.52+inner*.62+ticks*.52+stave*.60+diamond*.66+core*.58);
return (pattern*edgeSoft+halo)*lerp(.30,.46,c)*pulse;
''')
    pins = []
    for name in ('UV', 'Time', 'Charge'):
        pin = u.CustomInput()
        pin.set_editor_property('input_name', name)
        pins.append(pin)
    shape.set_editor_property('inputs', pins)
    for name, expr in (('UV', uv), ('Time', time), ('Charge', charge)):
        if not LIB.connect_material_expressions(expr, '', shape, name):
            raise RuntimeError('Circle input ' + name)

    tint = node(u.MaterialExpressionConstant3Vector)
    tint.set_editor_property('constant', u.LinearColor(.52, .78, 1., 1.))
    glow = node(u.MaterialExpressionMultiply)
    glow.set_editor_property('const_b', 4.2)
    LIB.connect_material_expressions(tint, '', glow, 'A')
    LIB.connect_material_property(glow, '', u.MaterialProperty.MP_EMISSIVE_COLOR)
    LIB.connect_material_property(shape, '', u.MaterialProperty.MP_OPACITY)
    save_asset(mat)
    return mat


def rebuild_iris():
    path = '/Game/Skills/ElectricMagic/LanceRay/Materials/M_ThunderLanceIris'
    mat = u.load_asset(path)
    if not mat:
        raise RuntimeError('Missing ' + path)
    clear_expressions(mat)
    mat.set_editor_property('blend_mode', u.BlendMode.BLEND_TRANSLUCENT)
    mat.set_editor_property('shading_model', u.MaterialShadingModel.MSM_UNLIT)
    mat.set_editor_property('two_sided', True)
    mat.set_editor_property('disable_depth_test', False)
    LIB.set_base_material_usage(mat, u.MaterialUsage.MATUSAGE_INSTANCED_STATIC_MESHES, True)

    def node(cls, **props):
        n = LIB.create_material_expression(mat, cls)
        for k, v in props.items():
            n.set_editor_property(k, v)
        return n

    def wire(a, b, pin):
        if isinstance(pin, int):
            pin = str(LIB.get_material_expression_input_names(b)[pin])
        if not LIB.connect_material_expressions(a, '', b, pin):
            raise RuntimeError('Iris wire failed ' + str(pin))

    data = node(u.MaterialExpressionPerInstanceCustomData, data_index=0, const_default_value=1.)
    interp = node(u.MaterialExpressionVertexInterpolator)
    wire(data, interp, 0)
    inputs = {
        'UV': node(u.MaterialExpressionTextureCoordinate),
        'Strength': node(u.MaterialExpressionScalarParameter, parameter_name='Strength', default_value=0.),
        'Clock': node(u.MaterialExpressionScalarParameter, parameter_name='Clock', default_value=0.),
        'FirePower': node(u.MaterialExpressionScalarParameter, parameter_name='FirePower', default_value=0.),
        'Exposure': node(u.MaterialExpressionEyeAdaptation),
        'InstanceAlpha': interp,
    }
    custom = node(u.MaterialExpressionCustom, description='ThunderLanceRay M_ThunderLanceIris',
                  output_type=u.CustomMaterialOutputType.CMOT_FLOAT4,
                  code=(RAY_ROOT / 'Authoring/LanceIris.hlsl').read_text(encoding='utf-8'))
    pins = []
    for k in inputs:
        p = u.CustomInput(); p.set_editor_property('input_name', k); pins.append(p)
    custom.set_editor_property('inputs', pins)
    for k, src in inputs.items():
        wire(src, custom, k)
    rgb = node(u.MaterialExpressionComponentMask, r=True, g=True, b=True, a=False)
    alpha = node(u.MaterialExpressionComponentMask, r=False, g=False, b=False, a=True)
    wire(custom, rgb, 0); wire(custom, alpha, 0)
    fade = node(u.MaterialExpressionDepthFade, fade_distance_default=.35)
    wire(alpha, fade, 0)
    LIB.connect_material_property(rgb, '', u.MaterialProperty.MP_EMISSIVE_COLOR)
    LIB.connect_material_property(fade, '', u.MaterialProperty.MP_OPACITY)
    save_asset(mat)
    return mat


def rebuild_gather_material(name, streak):
    path = '/Game/Skills/ElectricMagic/LanceRay/Materials/' + name
    m = u.load_asset(path)
    if not m:
        raise RuntimeError('Missing ' + path)
    clear_expressions(m)
    m.set_editor_property('blend_mode', u.BlendMode.BLEND_ADDITIVE)
    m.set_editor_property('shading_model', u.MaterialShadingModel.MSM_UNLIT)
    m.set_editor_property('two_sided', True)
    m.set_editor_property('disable_depth_test', False)
    LIB.set_base_material_usage(m, u.MaterialUsage.MATUSAGE_NIAGARA_SPRITES, True)

    def node(cls, **props):
        n = LIB.create_material_expression(m, cls)
        for k, v in props.items():
            n.set_editor_property(k, v)
        return n

    def wire(a, b, pin, out=''):
        if isinstance(pin, int):
            pin = str(LIB.get_material_expression_input_names(b)[pin])
        if not LIB.connect_material_expressions(a, out, b, pin):
            raise RuntimeError('Gather mat wire failed ' + str(pin))

    uv = node(u.MaterialExpressionTextureCoordinate)
    # Stronger edge feathering on both radial specks and streaks.
    code = ('float2 p=UV*2-1;return exp(-p.x*p.x*11)*pow(saturate(1-abs(p.y)),2.2)*smoothstep(1.,.42,abs(p.x));'
            if streak else
            'float r=length(UV*2-1);return exp(-r*r*6.5)*pow(saturate(1-smoothstep(.25,1.,r)),1.6);')
    mask = node(u.MaterialExpressionCustom, code=code, output_type=u.CustomMaterialOutputType.CMOT_FLOAT1)
    pin = u.CustomInput(); pin.set_editor_property('input_name', 'UV')
    mask.set_editor_property('inputs', [pin])
    wire(uv, mask, 'UV')
    color = node(u.MaterialExpressionParticleColor)
    gain = node(u.MaterialExpressionConstant, r=4.2 if streak else 5.0)
    light = node(u.MaterialExpressionMultiply); wire(color, light, 'A', 'RGB'); wire(gain, light, 'B')
    exposure = node(u.MaterialExpressionEyeAdaptationInverse); wire(light, exposure, 0)
    LIB.connect_material_property(exposure, '', u.MaterialProperty.MP_EMISSIVE_COLOR)
    alpha = node(u.MaterialExpressionMultiply); wire(mask, alpha, 'A'); wire(color, alpha, 'B', 'A')
    fade = node(u.MaterialExpressionDepthFade, fade_distance_default=2.5); wire(alpha, fade, 'Opacity')
    LIB.connect_material_property(fade, '', u.MaterialProperty.MP_OPACITY)
    save_asset(m)
    return m


def rebuild_gather_niagara(speck, streak):
    path = '/Game/Skills/ElectricMagic/LanceRay/NS_ThunderLanceGather'
    system = u.load_asset(path)
    if not system:
        raise RuntimeError('Missing ' + path)
    recipes = [
        ('GatheringSparks', 54, .42, 54, 3.4, 3.0, speck),
        ('ChargingFilaments', 16, .28, 42, 13.5, 1.9, streak),
        ('GatheringRings', 24, .34, 34, 2.0, 2.0, speck),
    ]
    for name, rate, life, start_radius, length, width, mat in recipes:
        trim(system, name, {'EmitterUpdateScript': ['EmitterState', 'SpawnRate'],
                            'ParticleSpawnScript': ['InitializeParticle'], 'ParticleUpdateScript': ['ParticleState']})
        for stage in ('ParticleSpawnScript', 'ParticleUpdateScript'):
            EAL.remove_metadata_tag(system, 'Fireball.Assignments.' + name + '.' + stage)
        setdata('SetEmitterData', u.NiagaraExt_EmitterData, ref(system, name),
                {'bLocalSpace': True, 'SimTarget': 'CPUSim', 'bInterpolatedSpawning': False})
        setdata('SetRendererData', u.NiagaraExt_RendererData, ref(system, name, renderer=0), {
            'Material': mat.get_path_name(), 'MaterialUserParamBinding': {'Parameter': {'Name': 'None'}},
            'Alignment': 'VelocityAligned' if name == 'ChargingFilaments' else 'Unaligned',
            'FacingMode': 'FaceCamera', 'SortMode': 'ViewDepth', 'bCastShadows': False, 'MotionVectorSetting': 'Disable',
            'CutoutTexture': None, 'bUseMaterialCutoutTexture': False, 'SubImageSize': {'X': 1, 'Y': 1}})
        expression(system, name, 'EmitterUpdateScript', 'SpawnRate', 'SpawnRate',
                   f'{rate}*(.28+.72*saturate(User.Charge))')
        seed = SEED
        age = 'saturate(Particles.NormalizedAge)'
        charge = 'saturate(User.Charge)'
        theta = f'({seed}*6.2831853+Particles.Age*(5+{charge}*5))'
        collapse = f'(1-.96*pow(saturate(({charge}-.82)/.18),2))'
        radius = f'(.4+({start_radius}-.4)*(1-pow({age},1.65))*{collapse})'
        position = f'float3(1+9*(1-{age})*{collapse},cos({theta})*{radius},sin({theta})*{radius})'
        velocity = f'float3(-.2,-cos({theta})-.55*sin({theta}),-sin({theta})+.55*cos({theta}))*100'
        size = f'float2({width},{length})*(.68+.30*{charge})*(1-.35*{age})'
        # Smooth edge fade-in at outer spawn boundary and soft fade-out near center collapse.
        edge_fade = f'saturate({age}*4.5)*pow(saturate((1-{age})*2.8),1.4)'
        alpha = f'(.16+.24*{charge})*{edge_fade}'
        color = f'float4(.32+.15*{seed},.60+.18*{seed},1.,{alpha})'
        values = {'Particles.Lifetime': (FLOAT, str(life)), 'Particles.Position': (POSITION, position),
                  'Particles.Velocity': (VEC3, velocity), 'Particles.SpriteSize': (VEC2, size),
                  'Particles.Color': (COLOR, color), 'Particles.SpriteRotation': (FLOAT, '0'),
                  'Particles.SubImageIndex': (FLOAT, '0')}
        assignments(system, name, 'ParticleSpawnScript', values)
        assignments(system, name, 'ParticleUpdateScript', {k: v for k, v in values.items() if k != 'Particles.Lifetime'})
    save_asset(system)
    return system


def rebuild_thunder_charge():
    path = '/Game/Skills/ElectricMagic/NS_ThunderCharge'
    system = u.load_asset(path)
    if not system:
        raise RuntimeError('Missing ' + path)
    spark = u.load_asset('/Game/Skills/ElectricMagic/M_ElectricSpark')
    filament = u.load_asset('/Game/Skills/ElectricMagic/M_ElectricFilament')
    ring = u.load_asset('/Game/Skills/ElectricMagic/M_ElectricRing')
    for em in emitters(system):
        API.call_method('RemoveEmitter', (ref(system, em),))
        for stage in ('ParticleSpawnScript', 'ParticleUpdateScript'):
            EAL.remove_metadata_tag(system, 'Fireball.Assignments.' + em + '.' + stage)

    source = u.load_asset(TEMPLATE)
    lc = {k: u.RainAssetEditor.read_input(source, 'Explosion', 'EmitterUpdateScript', 'EmitterState', k)
          for k in ('Life Cycle Mode', 'Loop Behavior')}
    lc['Life Cycle Mode'] = lc['Life Cycle Mode'].replace('NewEnumerator0', 'NewEnumerator1').replace('"System"', '"Self"')

    def add_sprite(name, mat, rate, life, pos, size, color, rot='0'):
        API.call_method('AddEmitter', (system, u.load_asset('/Game/NiagaraExamples/FX_Explosions/Emitters/NE_Core'), name))
        trim(system, name, {'EmitterUpdateScript': ['EmitterState'], 'ParticleSpawnScript': ['InitializeParticle'], 'ParticleUpdateScript': ['ParticleState']})
        setdata('SetEmitterData', u.NiagaraExt_EmitterData, ref(system, name), {'bLocalSpace': True, 'SimTarget': 'CPUSim', 'bInterpolatedSpawning': False})
        setdata('SetRendererData', u.NiagaraExt_RendererData, ref(system, name, renderer=0), {
            'Material': mat.get_path_name(), 'MaterialUserParamBinding': {'Parameter': {'Name': 'None'}},
            'SubImageSize': {'X': 1, 'Y': 1}, 'bSubImageBlend': False,
            'Alignment': 'Unaligned', 'FacingMode': 'FaceCamera', 'SortMode': 'ViewDepth',
            'bCastShadows': False, 'CutoutTexture': None, 'bUseMaterialCutoutTexture': False, 'MotionVectorSetting': 'Disable'})
        for k, v in lc.items():
            put(system, name, 'EmitterUpdateScript', 'EmitterState', k, v, ENUM)
        expression(system, name, 'EmitterUpdateScript', 'EmitterState', 'Loop Duration', '1')
        API.call_method('AddModule', (ref(system, name, 'EmitterUpdateScript'), u.load_asset('/Niagara/Modules/Emitter/SpawnRate')))
        expression(system, name, 'EmitterUpdateScript', 'SpawnRate', 'SpawnRate', str(rate))
        # Smooth bell-curve alpha fade-in and fade-out at outer/inner boundaries.
        fade = 'saturate(Particles.NormalizedAge*5)*pow(saturate((1-Particles.NormalizedAge)*2.4),1.6)'
        assignments(system, name, 'ParticleSpawnScript', {
            'Particles.Lifetime': (FLOAT, str(life)), 'Particles.Position': (POSITION, pos),
            'Particles.SpriteSize': (VEC2, size), 'Particles.Color': (COLOR, f'({color})*float4(1,1,1,0)'),
            'Particles.SpriteRotation': (FLOAT, rot), 'Particles.SubImageIndex': (FLOAT, '0')})
        assignments(system, name, 'ParticleUpdateScript', {
            'Particles.Position': (POSITION, pos), 'Particles.SpriteSize': (VEC2, size),
            'Particles.Color': (COLOR, f'({color})*float4(1,1,1,{fade})'), 'Particles.SubImageIndex': (FLOAT, '0')})

    theta = f'{SEED}*6.2831853+Particles.Age*(11+User.Charge*8)'
    radius = '(12+User.Charge*14)*(1-Particles.NormalizedAge*.62)'
    pos = f'float3(cos({theta})*{radius},sin({theta})*{radius},({SEED2}-.5)*14)'
    add_sprite('GatheringSparks', spark, 54, .32, pos, 'float2(1.8+User.Charge*2.2,5.5+User.Charge*4.5)', 'float4(.45,.68,1,.36)', f'{SEED3}*360')
    add_sprite('ChargingFilaments', filament, 18, .16, pos, 'float2(15+User.Charge*15,8.5)', 'float4(.68,.84,1,.38)', f'{SEED2}*360')
    add_sprite('EnergyCore', spark, 8, .24, 'float3(0,0,0)', 'float2(8+User.Charge*8,8+User.Charge*8)', 'float4(.68,.88,1,.30)')
    add_sprite('GatheringRings', ring, 3.5, .38, 'float3(0,0,0)', 'float2(46,46)*(1-Particles.NormalizedAge*.52)', 'float4(.34,.48,1,.18)')
    system.set_editor_property('fixed_bounds', u.Box(min=u.Vector(-65, -65, -65), max=u.Vector(65, 65, 65)))
    save_asset(system)
    return system


def main():
    backup_targets()
    rebuild_circle()
    rebuild_iris()
    speck = rebuild_gather_material('M_ThunderLanceGatherSpeck', False)
    streak = rebuild_gather_material('M_ThunderLanceGatherStreak', True)
    rebuild_gather_niagara(speck, streak)
    rebuild_thunder_charge()

    hashes = {}
    for ap in TARGETS:
        p = disk_path(ap)
        hashes[p.name] = sha256(p)
    receipt = {
        'revision': 'ThunderLanceChargeClarity_20261127',
        'saved_assets': TARGETS,
        'sha256': hashes,
        'changes': {
            'M_ThunderLanceCircle': 'emissive 14->4.2, opacity lerp 0.30..0.46, outer radial fade (0.66..1.0) + clear center aim window (0.24..0.56)',
            'M_ThunderLanceIris': 'soft pow(1.65) outer feather, wider clear center pupil (0.06..0.36), opacity 0.66->0.44',
            'M_ThunderLanceGatherSpeck/Streak': 'gain 10.5/8.4->5.0/4.2, stronger edge falloff',
            'NS_ThunderLanceGather': 'alpha ~40% with smooth outer/inner age fade, reduced spawn rate',
            'NS_ThunderCharge': 'EnergyCore size 15..33->8..16, alpha 0.30..0.38 with smooth bell-curve edge fade',
        },
        'backup_dir': str(BEFORE),
        'gameplay_tested': False,
        'rendered': False,
    }
    (PROD / 'published.json').write_text(json.dumps(receipt, indent=2), encoding='utf-8')
    print('THUNDER_CLARITY_ALL_PASS ' + json.dumps(receipt), flush=True)


if __name__ == '__main__':
    main()
