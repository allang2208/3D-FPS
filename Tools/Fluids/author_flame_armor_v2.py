"""Legacy TorchV2 helpers. The public run entry now installs FireballV3."""
import json
import math
import sys
from pathlib import Path
import unreal as u

ROOT = Path('D:/FPS3D/FPSGAME')
OUT = ROOT / 'SourceAssets/FlameArmor20261016/TorchV2'
DEST = '/Game/Skills/FlameArmor20261016/TorchV2'
sys.path.insert(0, str(ROOT / 'Tools/Skills'))
sys.path.insert(0, str(ROOT / 'Tools/Fluids'))
from build_fireball_assets import API, LIB, TOOLS, ref, emitters, setdata, put, assignments
from build_fireball_torch_burn import setup_emitter
from build_fireball_flight import user_parameter
from build_fireball_slow_burn import smooth
from build_fireball_outer_flame import enable_sprite_usage
import apply_fire_magic_fluid_fields as thermal

FLOAT = '/Script/Niagara.NiagaraFloat'
VEC2, VEC3, VEC4 = ['/Script/CoreUObject.Vector%df' % i for i in (2, 3, 4)]
POSITION = '/Script/Niagara.NiagaraPosition'
COLOR = '/Script/CoreUObject.LinearColor'
S = 'frac(float(Particles.UniqueID)*.61803398875)'
V = 'frac(float(Particles.UniqueID)*.41421356237)'
Q = 'frac(float(Particles.UniqueID)*.754877666)'
AGE, N = 'Particles.Age', 'Particles.NormalizedAge'
ANGLE = f'({V}*6.2831853)'
MATERIALS = {
    'torch': ('M_FA_Torch', '/Game/Building/Campfire20261013/TorchFire/M_CampfireTorchFire', 8, 8),
    'roll': ('M_FA_Roll', '/Game/Skills/FireMagic20260921/RealisticV5/M_NaturalRollingFlame', 6, 6),
    'heat': ('M_FA_Heat', '/Game/Skills/FireMagic20260921/RealisticV5/M_NaturalBladeFlame', 8, 4),
    'smoke': ('M_FA_Smoke', '/Game/Building/Campfire20261013/TorchFire/M_CampfireTorchSmoke', 8, 8),
    'ember': ('M_FA_Ember', None, 1, 1),
}
RECORDS = []


def connect(a, b, pin, output=''):
    if not LIB.connect_material_expressions(a, output, b, pin):
        raise RuntimeError('Material connection failed: ' + pin)


def owned(source, name):
    path = DEST + '/' + name
    if path in {p.get_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()}:
        raise RuntimeError('Preserve dirty target: ' + path)
    asset = u.load_asset(path) if u.EditorAssetLibrary.does_asset_exist(path) else u.EditorAssetLibrary.duplicate_asset(source, path)
    if not asset:
        raise RuntimeError('Cannot create ' + path)
    return asset


def save(asset):
    if isinstance(asset, u.NiagaraSystem) and not u.RainAssetEditor.compile_rain(asset, True):
        raise RuntimeError('Niagara compilation failed: ' + asset.get_path_name())
    if not u.EditorLoadingAndSavingUtils.save_packages([asset.get_outermost()], False):
        raise RuntimeError('Save failed: ' + asset.get_path_name())
    RECORDS.append(asset.get_path_name())


def materials():
    for kind, (name, source, _, _) in MATERIALS.items():
        if not source:
            continue
        mat = owned(source, name)
        enable_sprite_usage(mat)
        mat.set_editor_property('disable_depth_test', False)
        mat.set_editor_property('two_sided', True)
        if kind == 'torch':
            # Native TorchFire color/erosion, plus the existing RGB combustion
            # field before its single exposure-compensation node. Opacity stays native.
            thermal.PROFILES['ArmorTorch'] = {'grid': [8, 8], 'values': [17., .31, .48, 0.]}
            thermal.install_on_material(mat, 'ArmorTorch')
            for node in LIB.get_material_expressions(mat):
                if isinstance(node, u.MaterialExpressionDepthFade):
                    node.set_editor_property('fade_distance_default', 1.8)
                    c = next((x for x in LIB.get_material_expressions(mat)
                              if x.get_editor_property('desc') == 'FlameArmor contact fade'), None)
                    if c is None:
                        c = LIB.create_material_expression(mat, u.MaterialExpressionConstant)
                        c.set_editor_property('desc', 'FlameArmor contact fade')
                    c.set_editor_property('r', 1.8)
                    connect(c, node, 'FadeDistance')
        # The campfire smoke is lit through BaseColor, with no emissive input.
        # Preserve that lighting instead of adding fire exposure compensation.
        errors = LIB.recompile_material(mat)
        if errors:
            raise RuntimeError(str(errors))
        save(mat)
    name = MATERIALS['ember'][0]
    path = DEST + '/' + name
    mat = u.load_asset(path)
    if mat is None:
        mat = TOOLS.create_asset(name, DEST, u.Material, u.MaterialFactoryNew())
        mat.set_editor_property('blend_mode', u.BlendMode.BLEND_ADDITIVE)
        mat.set_editor_property('shading_model', u.MaterialShadingModel.MSM_UNLIT)
        mat.set_editor_property('two_sided', True)
        enable_sprite_usage(mat)
        uv = LIB.create_material_expression(mat, u.MaterialExpressionTextureCoordinate)
        color = LIB.create_material_expression(mat, u.MaterialExpressionParticleColor)
        shape = LIB.create_material_expression(mat, u.MaterialExpressionCustom)
        shape.set_editor_property('description', 'FlameArmor ember seed, no rectangular background')
        shape.set_editor_property('output_type', u.CustomMaterialOutputType.CMOT_FLOAT1)
        shape.set_editor_property('code', 'float2 p=(UV-.5)*2; return exp(-dot(p*float2(2.8,1.65),p*float2(2.8,1.65)))*saturate(1-dot(p,p));')
        inp = u.CustomInput(); inp.set_editor_property('input_name', 'UV'); shape.set_editor_property('inputs', [inp])
        connect(uv, shape, 'UV')
        alpha = LIB.create_material_expression(mat, u.MaterialExpressionMultiply)
        connect(shape, alpha, 'A'); connect(color, alpha, 'B', 'A')
        eye = LIB.create_material_expression(mat, u.MaterialExpressionEyeAdaptationInverse)
        connect(color, eye, str(LIB.get_material_expression_input_names(eye)[0]), 'RGB')
        LIB.connect_material_property(eye, '', u.MaterialProperty.MP_EMISSIVE_COLOR)
        LIB.connect_material_property(alpha, '', u.MaterialProperty.MP_OPACITY)
    errors = LIB.recompile_material(mat)
    if errors:
        raise RuntimeError(str(errors))
    save(mat)


def system(name, params, bounds):
    s = owned('/Game/Skills/FireMagic20260921/RealisticV5/NS_ArmorNaturalFire', name)
    for e in emitters(s):
        API.call_method('RemoveEmitter', (ref(s, e),))
    for key, typ in params.items():
        user_parameter(s, key, typ)
    s.set_editor_property('fixed_bounds', u.Box(min=u.Vector(*[-n for n in bounds]), max=u.Vector(*bounds)))
    setdata('SetSystemData', u.NiagaraExt_SystemData, s, {'bFixedBounds': True})
    return s


def appearance(kind, size, opacity, axis='float3(0,0,1)'):
    _, _, cols, rows = MATERIALS[kind]
    envelope = smooth('0', '.12', N) + '*(1-' + smooth('.5', '1', N) + ')'
    frame = f'min({N}*{cols*rows-1},{cols*rows-1}.0)'
    tint = f'lerp(float3(1.02,.89,.72),float3(.64,.27,.08),{N})'
    # TorchFire's "Index 0 Param 1/2" labels are one-based: X is the
    # RGB power (Emissive), Y is the alpha power (Dissolve). X=0 was
    # incorrectly borrowed from the unrelated Fire_C offset contract.
    dynamic = f'float4(1.15+.25*{V},.9+.4*{smooth(".65", "1", N)},1,1)'
    if kind == 'roll':
        tint = f'lerp(float3(2.1,.68,.10),float3(.6,.055,.006),{N})'
        dynamic = f'float4({V},.65+1.25*{S}+{N}*.65,0,0)'
    elif kind == 'heat':
        tint = f'lerp(float3(1.8,.25,.025),float3(.55,.025,.002),{N})'
        dynamic = 'float4(0,0,0,0)'
    elif kind == 'smoke':
        tint = 'float3(.18,.155,.13)'
        dynamic = 'float4(0,0,0,0)'
    elif kind == 'ember':
        tint = f'lerp(float3(3.8,1.4,.16),float3(.8,.045,.002),{N})'
        dynamic = 'float4(0,0,0,0)'
    return {'Particles.SpriteSize': (VEC2, size), 'Particles.Color': (COLOR, f'float4({tint},({opacity})*{envelope})'),
            'Particles.SpriteAlignment': (VEC3, axis), 'Particles.SpriteRotation': (FLOAT, '0'),
            'Particles.UVScale': (VEC2, 'float2(1,1)'), 'Particles.SubImageIndex': (FLOAT, frame),
            'Particles.DynamicMaterialParameter': (VEC4, dynamic)}


def layer(s, name, kind, rate, local, lifetime, spawn_position, update_position, size, opacity,
          velocity='float3(0,0,0)', axis='float3(0,0,1)', spawn_scale='User.Detail', update_velocity=None):
    material, _, cols, rows = MATERIALS[kind]
    setup_emitter(s, name, u.load_asset(DEST + '/' + material), rate, local)
    put(s, name, 'EmitterUpdateScript', 'SpawnRate', 'SpawnRate',
        f'(HlslExpression="{rate}*max(0,{spawn_scale})")', '/Script/NiagaraEditor.NiagaraExt_StackInputData_HlslExpression')
    setdata('SetRendererData', u.NiagaraExt_RendererData, ref(s, name, renderer=0), {
        'SubImageSize': {'X': cols, 'Y': rows}, 'bSubImageBlend': True,
        'PivotInUVSpace': {'X': .5, 'Y': .72 if kind in ('torch', 'roll') else .5},
        'Alignment': 'Unaligned' if kind == 'smoke' else 'CustomAlignment'})
    look = appearance(kind, size, opacity, axis)
    assignments(s, name, 'ParticleSpawnScript', {'Particles.Lifetime': (FLOAT, lifetime),
                'Particles.Position': (POSITION, spawn_position), 'Particles.Velocity': (VEC3, velocity), **look})
    update = {'Particles.Position': (POSITION, update_position), **look}
    if update_velocity:
        update['Particles.Velocity'] = (VEC3, update_velocity)
    assignments(s, name, 'ParticleUpdateScript', update)


def body():
    params = {x: FLOAT for x in ('Fade', 'Detail', 'UpperVisibility', 'Radius', 'BodyHeight', 'Clock')}
    params.update({x: VEC3 for x in ('BodyVelocity', 'Wind', 'WaistL', 'WaistR', 'ShoulderL', 'ShoulderR', 'ForearmL', 'ForearmR')})
    params['BodyOrigin'] = POSITION
    s = system('NS_FlameArmorBodyV2', params, (260, 260, 280))
    patch = f'(floor({S}*5)*1.25663706+.14*sin(User.Clock*.9+{S}*8))'
    foot = f'float3(cos({patch}),sin({patch}),0)*(User.Radius*(.76+.18*{V}))+float3(0,0,4+{AGE}*5)'
    up = 'normalize(float3(0,0,100)+User.Wind*.04-User.BodyVelocity*.035)'
    layer(s, 'FootTongues', 'torch', 19, True, f'.55+.35*{Q}', foot, foot,
          f'float2(14,24)*(.8+.3*{V})', 'User.Fade*.9', axis=up)
    anchor = f'({S}<.2?User.WaistL:({S}<.4?User.WaistR:({S}<.55?User.ShoulderL:({S}<.7?User.ShoulderR:({S}<.85?User.ForearmL:User.ForearmR)))))'
    attached = f'{anchor}+float3(cos({ANGLE})*3,sin({ANGLE})*3,3+{AGE}*10)'
    layer(s, 'BoundTongues', 'torch', 25, True, f'.55+.5*{Q}', attached, attached,
          f'float2(13,28)*(.75+.4*{V})', 'User.Fade*User.UpperVisibility*.8', axis=up,
          spawn_scale='User.Detail*User.UpperVisibility')
    orbit = f'({ANGLE}+User.Clock*.45+{AGE}*.8)'
    rolling = f'float3(cos({orbit}),sin({orbit}),0)*User.Radius*(.76+.15*{Q})+float3(0,0,User.BodyHeight*(.20+.32*{S})+{AGE}*19)'
    layer(s, 'RisingRoll', 'roll', 9, True, f'.7+.4*{Q}', rolling, rolling,
          f'float2(21,37)*(.8+.25*{V})', 'User.Fade*User.UpperVisibility*.45', axis=up,
          spawn_scale='User.Detail*User.UpperVisibility')
    origin = f'User.BodyOrigin+float3(cos({ANGLE}),sin({ANGLE}),0)*User.Radius*.8+float3(0,0,15+{S}*75*User.UpperVisibility)'
    motion = 'Particles.Position+Particles.Velocity*Engine.DeltaTime'
    layer(s, 'DetachedWarmSmoke', 'smoke', 3, False, f'.6+.35*{Q}', origin, motion,
          f'float2(18,22)*(1+{N}*.65)', 'User.Fade*.065',
          velocity='User.BodyVelocity*.1+User.Wind*.04+float3(0,0,25)',
          spawn_scale='User.Detail*User.UpperVisibility')
    layer(s, 'BodyEmbers', 'ember', 9, False, f'.35+.45*{Q}', origin, motion,
          f'float2(.65,1.8)*(.8+.5*{V})', 'User.Fade*.9',
          velocity=f'float3(cos({ANGLE})*9,sin({ANGLE})*9,35+{V}*30)+User.BodyVelocity*.12+User.Wind*.06',
          axis='normalize(Particles.Velocity+float3(0,0,.1))')
    save(s)


def weapon():
    params = {x: FLOAT for x in ('Fade', 'WeaponSize', 'Detail', 'MotionEnergy', 'Coverage')}
    params.update({x: VEC3 for x in ('WeaponEnd', 'WeaponVelocity', 'FlameProfile')})
    params.update({x: POSITION for x in ('WeaponStartWorld', 'WeaponEndWorld', 'PreviousStart', 'PreviousEnd')})
    s = system('NS_FlameArmorWeaponV2', params, (350, 350, 350))
    along = 'normalize(User.WeaponEnd+float3(.0001,0,0))'
    side = f'normalize(cross({along},abs({along}.z)<.9?float3(0,0,1):float3(0,1,0)))'
    across = f'({side}*cos({ANGLE})+cross({along},{side})*sin({ANGLE}))'
    point = f'User.WeaponEnd*(.06+.90*{S})+{across}*(.7+1.2*{V})*User.FlameProfile.x'
    up = 'normalize(float3(0,0,110)-User.WeaponVelocity*.045)'
    scale = 'User.Detail*User.Coverage'
    layer(s, 'SurfaceHeat', 'heat', 17, True, f'.25+.15*{V}', point, point,
          'float2(6,21)*User.WeaponSize*float2(User.FlameProfile.x,1)', 'User.Fade*.64',
          axis=along, spawn_scale=scale)
    tongue = f'{point}+{up}*(1+{AGE}*6)*User.WeaponSize'
    layer(s, 'TorchLicks', 'torch', 19, True, f'.42+.35*{Q}', tongue, tongue,
          f'float2(17,31)*User.WeaponSize*User.FlameProfile.xy*(.8+.4*{V})', 'User.Fade*.95',
          axis=up, spawn_scale=scale)
    layer(s, 'FlameRoll', 'roll', 6, True, f'.4+.3*{Q}', point, tongue,
          f'float2(18,27)*User.WeaponSize*User.FlameProfile.xy*(.8+.3*{V})', 'User.Fade*.40',
          axis=up, spawn_scale=scale)
    history = f'lerp(lerp(User.PreviousStart,User.PreviousEnd,{S}),lerp(User.WeaponStartWorld,User.WeaponEndWorld,{S}),{V})'
    motion = 'Particles.Position+Particles.Velocity*Engine.DeltaTime'
    layer(s, 'MotionFlame', 'torch', 13, False, f'.14+.12*{Q}', history, motion,
          f'float2(15,23)*User.WeaponSize*(1-{N}*.55)', 'User.Fade*.48',
          velocity='User.WeaponVelocity*.08+float3(0,0,18)', axis=up,
          spawn_scale=scale+'*User.MotionEnergy*User.FlameProfile.z')
    layer(s, 'WeaponEmbers', 'ember', 5, False, f'.18+.28*{Q}', history, motion,
          f'float2(.55,1.5)*(.7+.5*{V})', 'User.Fade*.85',
          velocity=f'User.WeaponVelocity*.055+float3(cos({ANGLE})*8,sin({ANGLE})*8,25)',
          axis='normalize(Particles.Velocity+float3(0,0,.1))', spawn_scale=scale)
    save(s)


def arrow():
    params = {'Fade': FLOAT, 'Detail': FLOAT, 'Velocity': VEC3, 'PreviousPosition': POSITION, 'CurrentPosition': POSITION}
    s = system('NS_FlameArmorArrowV2', params, (420, 420, 420))
    layer(s, 'ArrowTipFlame', 'torch', 12, True, '.20', 'float3(-3,0,0)', 'float3(-3,0,0)',
          'float2(4.5,11)', 'User.Fade*.8', axis='float3(-1,0,.25)')
    origin = f'lerp(User.PreviousPosition,User.CurrentPosition,{S})'
    motion = 'Particles.Position+Particles.Velocity*Engine.DeltaTime'
    layer(s, 'ArrowWake', 'torch', 24, False, f'.10+.09*{V}', origin, motion,
          f'float2(4,12)*(1-{N}*.6)', 'User.Fade*.50', velocity='User.Velocity*.025+float3(0,0,8)',
          axis='normalize(-User.Velocity+float3(0,0,.01))')
    layer(s, 'ArrowSparks', 'ember', 6, False, '.24', origin, motion,
          'float2(.45,1.3)', 'User.Fade*.8', velocity='User.Velocity*.035+float3(0,0,12)',
          axis='normalize(Particles.Velocity+float3(0,0,.01))')
    save(s)


def run(stage):
    # Keep existing production callers on the installed revision. The V2
    # functions above remain the shared low-level authoring/recovery helpers.
    from author_flame_armor_fireball_v3 import run as run_current
    run_current(stage)
