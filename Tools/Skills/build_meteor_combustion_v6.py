"""Meteor V6: original baked combustion, layered impact, swept world-space wake.

Run in the existing DragonBreathAuthor background host. Only the V6 directory
is written. No gameplay, rock, low ground fire, sound, camera or map changes.
"""
import json
import os
import sys
from pathlib import Path
import unreal as u

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'SourceAssets/MeteorCombustionV6_20261114'
DEST = '/Game/Skills/FireMagic20260921/MeteorCombustionV6'
OLD = '/Game/Skills/FireMagic20260921/RealisticV5'
sys.path[:0] = [str(ROOT / 'Tools/Skills'), str(ROOT / 'Tools/Fluids')]
if not hasattr(u, 'DragonBreathAuthorLibrary'):
    raise RuntimeError('Use the existing DragonBreathAuthor background host')
if Path(u.Paths.project_content_dir()).resolve() != (ROOT / 'Content').resolve():
    raise RuntimeError('Author host must use current FPSGAME Content')
u.RainAssetEditor = u.DragonBreathAuthorLibrary
from build_fireball_assets import API, LIB, ref, emitters, setdata, put, assignments
from build_fireball_flames import trim, FLOAT, VEC2, VEC3, POSITION, COLOR
from build_fireball_flight import expression
from build_fireball_slow_burn import smooth
from fluid_contact_nodes import contact_nodes, clear_contact_tags

E = u.EditorAssetLibrary
TOOLS = u.AssetToolsHelpers.get_asset_tools()
VEC4 = '/Script/CoreUObject.Vector4f'
A, N = 'Particles.Age', 'Particles.NormalizedAge'
SEED = 'frac(float(Particles.UniqueID)*.61803398875+.173)'
VAR = 'frac(float(Particles.UniqueID)*.41421356237+.317)'
ANGLE = '(float(Particles.UniqueID)*2.39996323+.4)'
DIR = f'float3(cos({ANGLE}),sin({ANGLE}),0)'
R = 'User.ImpactRadius'
HEIGHT = 'clamp(sqrt(User.ImpactRadius/652.5),.85,1.25)'
SAVED = []


def save(asset):
    if isinstance(asset, u.Material):
        if not u.DragonBreathAuthorLibrary.compile_material_assets([asset]):
            raise RuntimeError('Material compilation failed ' + asset.get_name())
    if isinstance(asset, u.NiagaraSystem):
        if not u.DragonBreathAuthorLibrary.compile_rain(asset, True):
            raise RuntimeError('Niagara compilation failed ' + asset.get_name())
    if not E.save_loaded_asset(asset, False):
        raise RuntimeError('Asset save failed ' + asset.get_path_name())
    SAVED.append(asset.get_path_name())
    print('METEOR_V6_SAVED ' + asset.get_path_name(), flush=True)


def own(name, source=None):
    path = DEST + '/' + name
    if path in {str(p.get_path_name()) for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()}:
        raise RuntimeError('Preserve unsaved target ' + path)
    asset = u.load_asset(path) if E.does_asset_exist(path) else (
        E.duplicate_asset(source, path) if source else TOOLS.create_asset(name, DEST, u.Material, u.MaterialFactoryNew()))
    if not asset:
        raise RuntimeError('Cannot create ' + path)
    return asset


def node(m, cls, **values):
    obj = LIB.create_material_expression(m, cls)
    for key, value in values.items():
        obj.set_editor_property(key, value)
    return obj


def wire(source, target, pin, output=''):
    if not LIB.connect_material_expressions(source, output, target, pin):
        raise RuntimeError('Material connection failed ' + pin)


def custom(m, tag, code, inputs, width):
    obj = next((n for n in LIB.get_material_expressions(m) if isinstance(n, u.MaterialExpressionCustom)
                and n.get_editor_property('description') == tag), None)
    if obj is None:
        obj = node(m, u.MaterialExpressionCustom, description=tag)
    pins = []
    for name in inputs:
        p = u.CustomInput(); p.set_editor_property('input_name', name); pins.append(p)
    obj.set_editor_property('inputs', pins)
    obj.set_editor_property('code', code)
    obj.set_editor_property('output_type', getattr(u.CustomMaterialOutputType, 'CMOT_FLOAT' + str(width)))
    for name, source in inputs.items():
        src, output = source if isinstance(source, tuple) else (source, '')
        wire(src, obj, name, output)
    return obj


def texture(kind):
    folder = OUT / kind
    contract = json.loads((folder / 'atlas-manifest.json').read_text(encoding='utf-8'))
    path = DEST + '/' + contract['texture']
    if E.does_asset_exist(path):
        existing = u.load_asset(path)
        if E.get_metadata_tag(existing, 'Meteor.AtlasContract') == json.dumps(contract):
            SAVED.append(existing.get_path_name())
            return existing
    task = u.AssetImportTask()
    for key, value in dict(filename=str(folder / (contract['texture'] + '.png')),
                           destination_path=DEST, destination_name=contract['texture'],
                           automated=True, replace_existing=True, save=False).items():
        task.set_editor_property(key, value)
    TOOLS.import_asset_tasks([task])
    imported = task.get_editor_property('imported_object_paths')
    if not imported:
        raise RuntimeError('No imported texture for ' + kind)
    tex = u.load_asset(imported[0])
    for key, value in dict(srgb=False, compression_settings=u.TextureCompressionSettings.TC_MASKS,
                           mip_gen_settings=u.TextureMipGenSettings.TMGS_NO_MIPMAPS,
                           address_x=u.TextureAddress.TA_CLAMP, address_y=u.TextureAddress.TA_CLAMP,
                           filter=u.TextureFilter.TF_BILINEAR).items():
        tex.set_editor_property(key, value)
    E.set_metadata_tag(tex, 'Meteor.AtlasContract', json.dumps(contract))
    save(tex)
    return tex


def material(name, tex, smoke=False):
    m = own(name)
    # Reruns update marked custom nodes instead of deleting rooted expressions.
    if E.get_metadata_tag(m, 'Meteor.V6.Graph'):
        for n in LIB.get_material_expressions(m):
            if isinstance(n, u.MaterialExpressionCustom) and n.get_editor_property('description') == 'MeteorV6.Sample':
                n.set_editor_property('code', (ROOT / 'Tools/Skills/meteor_combustion_v6_sample.hlsl').read_text(encoding='utf-8'))
        save(m)
        return m
    for key, value in dict(blend_mode=u.BlendMode.BLEND_TRANSLUCENT if smoke else u.BlendMode.BLEND_ALPHA_COMPOSITE,
                           shading_model=u.MaterialShadingModel.MSM_DEFAULT_LIT if smoke else u.MaterialShadingModel.MSM_UNLIT,
                           two_sided=True, disable_depth_test=False, enable_responsive_aa=True,
                           allow_front_layer_translucency=False, output_translucent_velocity=False,
                           is_translucency_velocity_from_depth=False,
                           translucency_pass=u.MaterialTranslucencyPass.MTP_BEFORE_DOF).items():
        m.set_editor_property(key, value)
    LIB.set_base_material_usage(m, u.MaterialUsage.MATUSAGE_NIAGARA_SPRITES, True)
    uv = node(m, u.MaterialExpressionTextureCoordinate)
    dynamic = node(m, u.MaterialExpressionDynamicParameter, param_names=['SourceAge', 'Mirror', 'Energy', 'Unused'])
    color = node(m, u.MaterialExpressionParticleColor)
    atlas = node(m, u.MaterialExpressionTextureObject, texture=tex, sampler_type=u.MaterialSamplerType.SAMPLERTYPE_MASKS)
    fields = custom(m, 'MeteorV6.Sample', (ROOT / 'Tools/Skills/meteor_combustion_v6_sample.hlsl').read_text(encoding='utf-8'),
                    {'UV': uv, 'Dynamic': (dynamic, 'RGBA'), 'Atlas': atlas}, 4)
    opacity = custom(m, 'MeteorV6.Opacity',
                     'float v = max(0, Fields.' + ('b' if smoke else 'r') + '-.004); '
                     'return (1-exp(-v*' + ('2.15' if smoke else '5.0') + '))*Alpha;',
                     {'Fields': fields, 'Alpha': (color, 'A')}, 1)
    fade = node(m, u.MaterialExpressionDepthFade, fade_distance_default=12. if smoke else 7.)
    wire(opacity, fade, str(LIB.get_material_expression_input_names(fade)[0]))
    LIB.connect_material_property(fade, '', u.MaterialProperty.MP_OPACITY)
    if smoke:
        m.set_editor_property('translucency_lighting_mode', u.TranslucencyLightingMode.TLM_VOLUMETRIC_NON_DIRECTIONAL)
        tint = custom(m, 'MeteorV6.SmokeColor', 'return Tint*lerp(.6,1.25,Fields.a);',
                      {'Fields': fields, 'Tint': (color, 'RGB')}, 3)
        rough = node(m, u.MaterialExpressionConstant, r=1.)
        spec = node(m, u.MaterialExpressionConstant, r=0.)
        slab = node(m, u.MaterialExpressionSubstrateShadingModels, shading_model_override=u.MaterialShadingModel.MSM_DEFAULT_LIT)
        for pin, value in {'BaseColor': tint, 'Roughness': rough, 'Specular': spec, 'Opacity': fade}.items():
            wire(value, slab, pin)
        for key, value in {'BASE_COLOR': tint, 'ROUGHNESS': rough, 'SPECULAR': spec, 'FRONT_MATERIAL': slab}.items():
            LIB.connect_material_property(value, '', getattr(u.MaterialProperty, 'MP_' + key))
    else:
        light = custom(m, 'MeteorV6.Thermal', '''
float heat=saturate(Fields.g*.72+sqrt(saturate(Fields.r))*.28);
float3 warm=lerp(float3(.8,.035,.001),float3(1.0,.23,.012),smoothstep(.12,.60,heat));
float3 fire=lerp(warm,float3(1.0,.62,.12),smoothstep(.58,.98,heat));
return fire*(1.2+5.2*heat*heat)*max(0,Dynamic.z)*Tint;
''', {'Fields': fields, 'Tint': (color, 'RGB'), 'Dynamic': (dynamic, 'RGBA')}, 3)
        exposure = node(m, u.MaterialExpressionEyeAdaptationInverse)
        wire(light, exposure, str(LIB.get_material_expression_input_names(exposure)[0]))
        premult = node(m, u.MaterialExpressionMultiply)
        wire(exposure, premult, 'A'); wire(fade, premult, 'B')
        LIB.connect_material_property(premult, '', u.MaterialProperty.MP_EMISSIVE_COLOR)
    E.set_metadata_tag(m, 'Meteor.V6.Graph', 'Original packed fields, two frame samples, one exposure compensation')
    save(m)
    return m


def system(name, source, defaults, bounds):
    s = own(name, source)
    for en in emitters(s):
        API.call_method('RemoveEmitter', (ref(s, en),))
    values = [{'name': 'User.' + key, 'type': typ, 'value': value} for key, typ, value in defaults]
    if not u.DragonBreathAuthorLibrary.set_fluid_user_defaults(s, json.dumps(values)):
        raise RuntimeError('Missing system user defaults ' + name)
    s.set_editor_property('fixed_bounds', u.Box(min=u.Vector(*bounds[0]), max=u.Vector(*bounds[1])))
    return s


def layer(s, name, mat, local, spawn, update, count=None, delay=0, rate=0, dust=False,
          align=False, pivot=.5, native_frames=1):
    API.call_method('AddEmitter', (s, u.load_asset('/Game/NiagaraExamples/FX_Explosions/Emitters/NE_Core'), name))
    trim(s, name, {'EmitterUpdateScript': ['EmitterState'], 'ParticleSpawnScript': ['InitializeParticle'],
                   'ParticleUpdateScript': ['ParticleState']})
    for script in ['ParticleSpawnScript', 'ParticleUpdateScript']:
        E.remove_metadata_tag(s, 'Fireball.Assignments.' + name + '.' + script)
    setdata('SetEmitterData', u.NiagaraExt_EmitterData, ref(s, name),
            {'bLocalSpace': local, 'SimTarget': 'CPUSim', 'bInterpolatedSpawning': False})
    setdata('SetRendererData', u.NiagaraExt_RendererData, ref(s, name, renderer=0), {
        'Material': mat.get_path_name(), 'MaterialUserParamBinding': {'Parameter': {'Name': 'None'}},
        'Alignment': 'CustomAlignment' if align else 'Unaligned', 'FacingMode': 'FaceCamera',
        'SubImageSize': {'X': native_frames, 'Y': native_frames}, 'bSubImageBlend': native_frames > 1,
        'PivotInUVSpace': {'X': .5, 'Y': pivot}, 'bCastShadows': False, 'bUseMaterialCutoutTexture': False,
        'CutoutTexture': None, 'bEnableCameraDistanceCulling': True, 'MinCameraDistance': 0, 'MaxCameraDistance': 10000})
    template = u.load_asset('/Game/NiagaraExamples/FX_Explosions/NS_Explosion_Small')
    for key in ['Life Cycle Mode', 'Loop Behavior']:
        if count is None and key == 'Loop Behavior':
            # System-owned continuous emitters hide their independent loop
            # inputs. The unchanged source system supplies the looping clock.
            continue
        value = u.DragonBreathAuthorLibrary.read_input(template, 'Explosion', 'EmitterUpdateScript', 'EmitterState', key)
        if count is not None:
            value = value.replace('NewEnumerator0', 'NewEnumerator1').replace('"System"', '"Self"').replace('"Infinite"', '"Once"')
        else:
            value = value.replace('NewEnumerator1', 'NewEnumerator0').replace('"Self"', '"System"').replace('"Once"', '"Infinite"')
        put(s, name, 'EmitterUpdateScript', 'EmitterState', key, value, '/Script/NiagaraEditor.NiagaraExt_StackInputData_Enum')
    if count is not None:
        put(s, name, 'EmitterUpdateScript', 'EmitterState', 'Loop Duration', '(Value=3.5)')
        API.call_method('AddModule', (ref(s, name, 'EmitterUpdateScript'), u.load_asset('/Niagara/Modules/Emitter/SpawnBurst_Instantaneous')))
        expression(s, name, 'EmitterUpdateScript', 'SpawnBurst_Instantaneous', 'Spawn Count', str(count))
        put(s, name, 'EmitterUpdateScript', 'SpawnBurst_Instantaneous', 'Spawn Time', f'(Value={delay})')
    else:
        API.call_method('AddModule', (ref(s, name, 'EmitterUpdateScript'), u.load_asset('/Niagara/Modules/Emitter/SpawnRate')))
        expression(s, name, 'EmitterUpdateScript', 'SpawnRate', 'SpawnRate', str(rate))
    common = {'Particles.SpriteRotation': (FLOAT, '0'), 'Particles.SpriteUVScale': (VEC2, 'float2(1,1)'),
              'Particles.SpriteAlignment': (VEC3, 'float3(0,0,1)'), 'Particles.SubImageIndex': (FLOAT, '0')}
    assignments(s, name, 'ParticleSpawnScript', {**common, **spawn})
    assignments(s, name, 'ParticleUpdateScript', {**common, **update})
    if dust:
        clear_contact_tags(s, name)
        contact_nodes(s, name)


def impact(fire, smoke, roll):
    defaults = [('ImpactRadius', FLOAT, '(Value=652.5)'), ('LocalUp', VEC3, '(X=0,Y=0,Z=1)'),
                ('SurfaceHit', FLOAT, '(Value=1)'), ('DetailReduction', FLOAT, '(Value=0)'),
                ('Wind', VEC3, '(X=0,Y=0,Z=0)'), ('WetImpact', FLOAT, '(Value=0)')]
    s = system('NS_MeteorCollisionV6', '/Game/Skills/FireMagic20260921/MeteorImpactWeightV5/NS_MeteorImpact',
               defaults, [(-1400,-1400,-450), (1400,1400,850)])
    def burst(name, mat, count, delay, life, size, position, color, dynamic, dust=False, frames=1):
        values = {'Particles.Position': (POSITION, position), 'Particles.Velocity': (VEC3, 'float3(0,0,0)'),
                  'Particles.SpriteSize': (VEC2, size), 'Particles.Color': (COLOR, color),
                  'Particles.DynamicMaterialParameter': (VEC4, dynamic),
                  'Particles.SubImageIndex': (FLOAT, f'{frames*frames-1}*saturate({N})')}
        layer(s, name, mat, True, {'Particles.Lifetime': (FLOAT, life), **values}, values,
              count=count, delay=delay, dust=dust, native_frames=frames)
    contact = u.load_asset('/Game/Skills/FireMagic20260921/MeteorImpactWeightV5/M_MeteorBlast')
    burst('V6Contact', contact, 1, 0, '.065', f'float2(205,70)*{HEIGHT}*(.3+.7*(1-exp(-{A}*70)))',
          'User.LocalUp*18', f'float4(.42,.31,.22,1-{N})', f'float4(20*pow(1-{N},2)+.2,1,1,1)', frames=12)
    fire_alpha = f'(1-{smooth(".62","1",N)})'
    burst('V6Detonation', fire, 1, .025, '.82', f'float2(440,365)*{HEIGHT}*(.72+.28*(1-exp(-{A}*18)))',
          f'User.LocalUp*(93+{A}*35)*{HEIGHT}', f'float4(1,1,1,.95*{fire_alpha})', f'float4({N},{VAR},1.25,0)')
    burst('V6PressureLobes', fire, 4, .045, f'.64+.24*{VAR}',
          f'float2(300,270)*{HEIGHT}*(.72+.3*{VAR})*(.78+.22*(1-exp(-{A}*13)))',
          f'{DIR}*{R}*(.04+(.19+.12*{SEED})*(1-exp(-{A}*8)))+User.LocalUp*(58+{A}*55)*{HEIGHT}',
          f'float4(1,1,1,.78*{fire_alpha})', f'float4({N},{VAR},.9,0)')
    burst('V6CoolingRoll', roll, 3, .13, f'.40+.20*{VAR}',
          f'float2(125,165)*{HEIGHT}*(.7+.35*{SEED})*(.85+.2*{N})',
          f'{DIR}*{R}*(.11+.22*{SEED})+User.LocalUp*(25+{A}*28)*{HEIGHT}',
          f'float4(1,.86,.7,.55*(1-{N}))', f'float4(frac({N}*.55+{VAR}),{SEED},.65*(1-{N}),0)')
    wind = f'User.Wind*({A}-.4*(1-exp(-{A}/.4)))'
    fade = f'{smooth("0",".09",N)}*(1-{smooth(".45","1",N)})'
    budget = '(1-saturate(User.DetailReduction))'
    burst('V6GroundDust', smoke, f'(User.WetImpact<.5 && User.SurfaceHit>.5?floor(8*{budget}+.5):0)',
          .018, f'.65+.35*{VAR}', f'float2(225,82)*(.7+.35*{VAR})*(.7+.45*{N})',
          f'{DIR}*{R}*(.05+(.48+.26*{SEED})*(1-exp(-{A}*6)))+float3(0,0,22+{A}*10)+{wind}',
          f'float4(.23,.195,.15,.48*{fade})', f'float4(.22+.78*{N},{VAR},0,0)', dust=True)
    burst('V6RollingSmoke', smoke, f'floor(5*{budget}+.5)', .11, f'1.65+.65*{VAR}',
          f'float2(230,270)*(.72+.32*{VAR})*(.7+.45*{N})',
          f'{DIR}*{R}*(.05+.20*{SEED})*(1-exp(-{A}*3))+User.LocalUp*(80+{A}*(45+23*{VAR}))+{wind}',
          f'float4(lerp(float3(.16,.145,.125),float3(.44,.47,.48),saturate(User.WetImpact)),.58*{fade})',
          f'float4(.12+.88*{N},{VAR},0,0)', dust=True)
    burst('V6SettlingAsh', smoke, f'floor(3*{budget}+.5)', .35, f'.85+.4*{VAR}',
          f'float2(54,32)*(.7+.5*{VAR})*(.8+.3*{N})',
          f'{DIR}*{R}*(.14+.35*{SEED})+User.LocalUp*max(8,90+70*{VAR}-65*{A})+{wind}',
          f'float4(.22,.20,.17,.16*{fade})', f'float4(.4+.6*{N},{VAR},0,0)', dust=True)
    save(s)


def flight(fire, smoke):
    defaults = [('Fade', FLOAT, '(Value=1)'), ('FlightDirection', VEC3, '(X=0,Y=0,Z=-1)'),
                ('FlightSpeed', FLOAT, '(Value=0)')]
    mantle = system('NS_MeteorSheathV6', OLD + '/NS_MeteorNaturalMantle', defaults,
                    [(-100,-100,-100), (100,100,180)])
    z = f'({SEED}*1.6-.8)'
    ring = f'sqrt(max(.01,1-({z})*({z})))'
    radial = f'float3({ring}*cos({ANGLE}),{ring}*sin({ANGLE}),{z})'
    for name, rate, size, alpha, life, radius in [
            ('V6AttachedHeat', 20, 'float2(33,47)', '.72', '.32+.14*'+VAR, 37),
            ('V6LiftedTongues', 10, 'float2(27,62)', '.52', '.38+.18*'+VAR, 41)]:
        # These metadata names belong to the emitter just recreated above.
        for tag in ['Samples','Root']:
            E.remove_metadata_tag(mantle,'Meteor.FlightSurface.'+name+'.'+tag)
        values = {'Particles.Position': (POSITION, f'{radial}*{radius}-User.FlightDirection*{A}*(26+min(User.FlightSpeed*.009,28))'),
                  'Particles.Velocity': (VEC3, 'float3(0,0,0)'),
                  'Particles.SpriteSize': (VEC2, f'{size}*(.8+.3*{VAR})*(.8+.2*{N})'),
                  'Particles.SpriteAlignment': (VEC3, f'normalize(-User.FlightDirection+{radial}*.22+float3(0,0,.001))'),
                  'Particles.Color': (COLOR, f'float4(1,1,1,{alpha}*User.Fade*{smooth("0",".12",N)}*(1-{smooth(".6","1",N)}))'),
                  'Particles.DynamicMaterialParameter': (VEC4, f'float4(frac({VAR}+{A}*.8),{SEED},1.0-.35*{N},0)')}
        layer(mantle, name, fire, True, {'Particles.Lifetime': (FLOAT, life), **values}, values,
              rate=f'{rate}*saturate(User.Fade)', align=True, pivot=.73)
    save(mantle)
    wake_defaults = defaults + [('PreviousPosition', POSITION, '(X=0,Y=0,Z=0)'),
                               ('CurrentPosition', POSITION, '(X=0,Y=0,Z=0)'), ('VisualScale', FLOAT, '(Value=3)')]
    tail = system('NS_MeteorSlipstreamV6', OLD + '/NS_MeteorNaturalWake', wake_defaults,
                  [(-1800,-1800,-1800), (1800,1800,1800)])
    scale = 'max(User.VisualScale,1.0)'
    # Fresh births span the actual swept segment; living particles never follow
    # the rock again. Velocity drag is frame independent, with dt only on force.
    for name, mat, rate, size, life, opacity, is_smoke in [
            ('V6HotWake', fire, 34, 'float2(46,78)', '.30+.16*'+SEED, '.72', False),
            ('V6TornWake', fire, 12, 'float2(32,63)', '.26+.18*'+VAR, '.42', False),
            ('V6CoolingWake', smoke, 9, 'float2(61,76)', '.62+.28*'+SEED, '.30', True)]:
        offset = f'float3(cos({ANGLE}),sin({ANGLE}),0)*(7+8*{SEED})'
        appearance = {'Particles.SpriteSize': (VEC2, f'{size}*{scale}*(.8+.3*{VAR})*(1+{N}*'+('.50)' if is_smoke else '.18)')),
                      'Particles.SpriteAlignment': (VEC3, 'normalize(-User.FlightDirection+float3(0,0,.001))'),
                      'Particles.Color': (COLOR, f'float4('+('.18,.165,.145,' if is_smoke else '1,1,1,') +
                                                   f'{opacity}*{smooth("0",".08",N)}*(1-{smooth(".25","1",N)}))'),
                      'Particles.DynamicMaterialParameter': (VEC4, f'float4(frac({VAR}+{A}*.8),{SEED},'+
                                                                  ('0' if is_smoke else f'pow(1-{N},1.35)')+',0)')}
        spawn = {'Particles.Lifetime': (FLOAT, life),
                 'Particles.Position': (POSITION, f'lerp(User.PreviousPosition,User.CurrentPosition,{SEED})+{offset}*{scale}'),
                 'Particles.Velocity': (VEC3, f'-User.FlightDirection*(24+min(User.FlightSpeed*.012,55))+{offset}*.8'), **appearance}
        force = f'float3(sin(Particles.Position.z*.022+{VAR}*6)*23,cos(Particles.Position.z*.019+{SEED}*6)*23,18)'
        update = {'Particles.Position': (POSITION, 'Particles.Position+Particles.Velocity*Engine.DeltaTime'),
                  'Particles.Velocity': (VEC3, f'(Particles.Velocity+{force}*Engine.DeltaTime)*exp(-1.1*Engine.DeltaTime)'), **appearance}
        layer(tail, name, mat, False, spawn, update, rate=f'{rate}*saturate(User.Fade)',
              align=not is_smoke, pivot=.5 if is_smoke else .73)
    save(tail)

    # Last authoring step restores the current surface-rooted flight recipe.
    # This does not modify V7 impact assets or V4 residual ground fire.
    import meteor_flight_surface_recipe as flight_surface
    profile=flight_surface.sample_surface()
    flight_surface.apply(mantle,tail,fire,smoke,profile)
    for asset in [fire,smoke,mantle,tail]:save(asset)


def run():
    OUT.mkdir(parents=True, exist_ok=True)
    E.make_directory(DEST)
    if os.environ.get('FPSGAME_METEOR_V6_STAGE') == 'flight':
        # Resume the completed impact/material phase after a flight authoring
        # error without rebuilding or replacing those saved packages.
        for name in ['T_MeteorImpactFields', 'T_MeteorWakeFields', 'M_MeteorBurstV6',
                     'M_MeteorAfterSmokeV6', 'M_MeteorSheathV6', 'M_MeteorWakeSmokeV6', 'NS_MeteorCollisionV6']:
            asset = u.load_asset(DEST + '/' + name)
            if asset is None:
                raise RuntimeError('Missing saved prior phase ' + name)
            SAVED.append(asset.get_path_name())
        sheath = u.load_asset(DEST + '/M_MeteorSheathV6')
        wake_smoke = u.load_asset(DEST + '/M_MeteorWakeSmokeV6')
    else:
        impact_tex = texture('impact')
        wake_tex = texture('wake')
        burst = material('M_MeteorBurstV6', impact_tex)
        after_smoke = material('M_MeteorAfterSmokeV6', impact_tex, True)
        sheath = material('M_MeteorSheathV6', wake_tex)
        wake_smoke = material('M_MeteorWakeSmokeV6', wake_tex, True)
        impact(burst, after_smoke, sheath)
    flight(sheath, wake_smoke)
    receipt = dict(complete=True, saved_assets=SAVED, impact_max_particles=25,
                   impact_smoke_budget=16, mantle_rate=66, wake_rate_max=124,
                   texture_data='Two 2048-square linear RGBA atlases, 64 frames each',
                   new_lights=0, new_runtime_fluid_grids=0,
                   protected=['rock', 'ground fire V4', 'gameplay', 'sound', 'camera', 'scorch'],
                   rendered=False, runtime_tested=False, performance_measured=False)
    (OUT / 'asset-receipt.json').write_text(json.dumps(receipt, indent=2), encoding='utf-8')
    print('METEOR_V6_AUTHOR_COMPLETE ' + json.dumps(receipt), flush=True)


if __name__ == '__main__':
    run()
