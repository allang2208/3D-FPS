"""Add a short FireFlame mantle to the current slow-burning fireball.

Uses the user's imported Dr.Game Free Spline VFX texture. Authoring and asset
compilation only; no gameplay, preview, screenshot or acceptance run.
"""
import json
from pathlib import Path
import sys
import unreal

sys.path.insert(0, str(Path(__file__).resolve().parent))
from build_fireball_assets import API, LIB, TOOLS, ref, emitters, setdata, put, assignments, save
from build_fireball_flames import trim, FLOAT, VEC2, VEC3, POSITION, COLOR
from build_fireball_slow_burn import smooth

DEST = '/Game/Skills/Fireball'
SYSTEM = DEST + '/NS_FireballSlowBurnCore'
EMITTER = 'FireballOuterFireFlame'
ATLAS = '/Game/_SplineVFX/_GenericSource/Texture/T_Vfx_Stamp_FireFlame_88'


def enable_sprite_usage(mat, instance=None):
    # Commandlet authoring does not discover material usage through a viewport.
    # Persist the Niagara sprite permutation on both the parent and the UE 5.8
    # material instance; otherwise runtime substitutes the checkerboard material.
    usage = unreal.MaterialUsage.MATUSAGE_NIAGARA_SPRITES
    LIB.set_base_material_usage(mat, usage, True)
    if instance:
        LIB.set_material_usage_override(instance, usage, True, True)


def connect(source, target, input_name, output=''):
    if not LIB.connect_material_expressions(source, output, target, input_name):
        raise RuntimeError('Cannot connect outer-flame material: ' + target.get_name() + '/' + input_name)


def scalar(mat, name, value, x, y):
    node = LIB.create_material_expression(mat, unreal.MaterialExpressionScalarParameter, x, y)
    node.set_editor_property('parameter_name', name)
    node.set_editor_property('default_value', value)
    return node


def multiply(mat, a, b, x, y):
    node = LIB.create_material_expression(mat, unreal.MaterialExpressionMultiply, x, y)
    connect(a, node, 'A')
    connect(b, node, 'B')
    return node


def material():
    texture = unreal.load_asset(ATLAS)
    if not texture:
        raise RuntimeError('Restore the imported Free Spline VFX FireFlame texture first')
    name = 'M_FireballOuterFireFlame'
    mat = unreal.load_asset(DEST + '/' + name)
    if not mat:
        mat = TOOLS.create_asset(name, DEST, unreal.Material, unreal.MaterialFactoryNew())
    # Rebuild only our own material; the imported package stays untouched.
    LIB.delete_all_material_expressions(mat)
    mat.set_editor_property('blend_mode', unreal.BlendMode.BLEND_ALPHA_COMPOSITE)
    mat.set_editor_property('shading_model', unreal.MaterialShadingModel.MSM_UNLIT)
    mat.set_editor_property('two_sided', True)
    mat.set_editor_property('disable_depth_test', False)
    enable_sprite_usage(mat)
    tex = LIB.create_material_expression(mat, unreal.MaterialExpressionTextureSampleParameterSubUV, -800, 0)
    tex.set_editor_property('parameter_name', 'FlameAtlas')
    tex.set_editor_property('texture', texture)
    tex.set_editor_property('blend', True)
    tex.set_editor_property('sampler_type', unreal.MaterialSamplerType.SAMPLERTYPE_COLOR
                            if texture.get_editor_property('srgb') else unreal.MaterialSamplerType.SAMPLERTYPE_LINEAR_COLOR)
    color = LIB.create_material_expression(mat, unreal.MaterialExpressionParticleColor, -800, 250)
    uv = LIB.create_material_expression(mat, unreal.MaterialExpressionTextureCoordinate, -800, 450)
    opacity_gain = scalar(mat, 'OpacityGain', .60, -800, 650)
    emissive_gain = scalar(mat, 'EmissiveGain', 1.7, -200, -180)
    root_start = scalar(mat, 'RootFadeStart', .62, -800, 800)
    root_end = scalar(mat, 'RootFadeEnd', .98, -800, 950)

    soft = LIB.create_material_expression(mat, unreal.MaterialExpressionCustom, -400, 450)
    soft.set_editor_property('output_type', unreal.CustomMaterialOutputType.CMOT_FLOAT1)
    pins = []
    for name in ['Flame', 'Alpha', 'UV', 'Gain', 'RootStart', 'RootEnd']:
        pin = unreal.CustomInput()
        pin.set_editor_property('input_name', name)
        pins.append(pin)
    soft.set_editor_property('inputs', pins)
    soft.set_editor_property('code', '''
// Niagara supplies atlas-space UV0. Recover the 0..1 coordinates of this
// 8x8 frame, so the mask rotates together with the actual flame billboard.
float2 p = frac(UV * 8.0);
float sides = smoothstep(0.0, .10, p.x) * (1.0 - smoothstep(.90, 1.0, p.x));
float top = smoothstep(0.0, .035, p.y);
float root = 1.0 - smoothstep(RootStart, RootEnd, p.y);
// This source is RGB fire on black, not an Epic EOO packed atlas.
float coverage = sqrt(saturate(max(Flame.r, max(Flame.g, Flame.b))));
return saturate(coverage * sides * top * root * Alpha * Gain);
''')
    connect(tex, soft, 'Flame')
    connect(color, soft, 'Alpha', str(LIB.get_material_expression_output_names(color)[4]))
    connect(uv, soft, 'UV')
    connect(opacity_gain, soft, 'Gain')
    connect(root_start, soft, 'RootStart')
    connect(root_end, soft, 'RootEnd')
    depth = LIB.create_material_expression(mat, unreal.MaterialExpressionDepthFade, 0, 450)
    depth.set_editor_property('fade_distance_default', 6.0)
    connect(soft, depth, str(LIB.get_material_expression_input_names(depth)[0]))
    colored = multiply(mat, tex, color, -300, 0)
    bright = multiply(mat, colored, emissive_gain, 0, 0)
    # Premultiply after ALL opacity fading, preventing bright detached edges.
    emission = multiply(mat, bright, depth, 200, 0)
    LIB.connect_material_property(emission, '', unreal.MaterialProperty.MP_EMISSIVE_COLOR)
    LIB.connect_material_property(depth, '', unreal.MaterialProperty.MP_OPACITY)
    errors = LIB.recompile_material(mat)
    if errors:
        raise RuntimeError('Outer-flame material compilation failed: ' + '; '.join(errors))
    save(mat)

    name = 'MI_FireballOuterFireFlame'
    instance = unreal.load_asset(DEST + '/' + name)
    if not instance:
        instance = TOOLS.create_asset(name, DEST, unreal.MaterialInstanceConstant, unreal.MaterialInstanceConstantFactoryNew())
    LIB.set_material_instance_parent(instance, mat)
    enable_sprite_usage(mat, instance)
    for key, value in [('OpacityGain', .60), ('EmissiveGain', 1.7), ('RootFadeStart', .62), ('RootFadeEnd', .98)]:
        LIB.set_material_instance_scalar_parameter_value(instance, key, value)
    LIB.set_material_instance_texture_parameter_value(instance, 'FlameAtlas', texture)
    LIB.update_material_instance(instance)
    save(instance)
    return instance


def build():
    system = unreal.load_asset(SYSTEM)
    if not system:
        raise RuntimeError('Build the slow-burn core before adding its outer flames')
    mat = material()
    if EMITTER not in emitters(system):
        API.call_method('AddEmitter', (system,
            unreal.load_asset('/Game/NiagaraExamples/FX_Explosions/Emitters/NE_Core'), EMITTER))
    # The imported spline system's decals, lights, terrain snapping, smoke and
    # sparks are not dependencies of this texture-only outer layer.
    trim(system, EMITTER, {
        'EmitterUpdateScript': ['EmitterState', 'SpawnRate'],
        'ParticleSpawnScript': ['InitializeParticle'],
        'ParticleUpdateScript': ['ParticleState'],
    })
    for script in ['ParticleSpawnScript', 'ParticleUpdateScript']:
        unreal.EditorAssetLibrary.remove_metadata_tag(system, 'Fireball.Assignments.' + EMITTER + '.' + script)
    setdata('SetEmitterData', unreal.NiagaraExt_EmitterData, ref(system, EMITTER), {
        'bLocalSpace': True, 'SimTarget': 'CPUSim', 'bInterpolatedSpawning': False,
    })
    setdata('SetRendererData', unreal.NiagaraExt_RendererData, ref(system, EMITTER, renderer=0), {
        'Material': mat.get_path_name(), 'MaterialUserParamBinding': {'Parameter': {'Name': 'None'}},
        'SubImageSize': {'X': 8, 'Y': 8}, 'bSubImageBlend': True,
        'Alignment': 'CustomAlignment', 'FacingMode': 'FaceCamera',
        'PivotInUVSpace': {'X': .5, 'Y': .82}, 'bCastShadows': False,
    })
    for key in ['Life Cycle Mode', 'Loop Behavior']:
        value = unreal.RainAssetEditor.read_input(system, 'FireballCore', 'EmitterUpdateScript', 'EmitterState', key)
        put(system, EMITTER, 'EmitterUpdateScript', 'EmitterState', key, value,
            '/Script/NiagaraEditor.NiagaraExt_StackInputData_Enum')
    stack = API.call_method('GetScriptStackTopology', (ref(system, EMITTER, 'EmitterUpdateScript'),))
    if not any(str(m.get_editor_property('module_name')) == 'SpawnRate' for m in stack.get_editor_property('modules')):
        API.call_method('AddModule', (ref(system, EMITTER, 'EmitterUpdateScript'),
                                     unreal.load_asset('/Niagara/Modules/Emitter/SpawnRate')))
    put(system, EMITTER, 'EmitterUpdateScript', 'SpawnRate', 'SpawnRate', '(Value=8)')

    seed = 'frac(float(Particles.UniqueID)*.61803398875)'
    variant = 'frac(float(Particles.UniqueID)*.41421356237)'
    z = '(frac(float(Particles.UniqueID)*.754877666)*1.8-.9)'
    theta = '(float(Particles.UniqueID)*2.39996323)'
    direction = f'float3(sqrt(1-{z}*{z})*cos({theta}),sqrt(1-{z}*{z})*sin({theta}),{z})'
    phase = f'(6.2831853*{variant})'
    age = 'Particles.Age'
    n = 'Particles.NormalizedAge'
    blend = smooth('0', '.06', 'User.FlightAge') + '*saturate(User.Flight)'
    hover_axis = f'normalize({direction}*float3(.65,.65,.25)+float3(0,0,.70))'
    # Anchor near the roots, inside the roiling core, with modest bounded lift.
    hover_root = (f'{direction}*(8+2*{seed})+float3('
                  f'.45*(sin({age}*1.4+{phase})-sin({phase})),'
                  f'.45*(sin({age}*1.1+{phase})-sin({phase})),{age})')
    flight_root = (f'float3(-3-abs({direction}.x)*5-{n}*2,'
                   f'{direction}.y*7*(1-.35*{n}),{direction}.z*7*(1-.35*{n}))')
    fade = smooth('0', '.12', n) + '*(1-' + smooth('.55', '1', n) + ')'
    common = {
        'Particles.Position': (POSITION, f'lerp({hover_root},{flight_root},{blend})'),
        'Particles.Velocity': (VEC3, f'lerp({hover_axis}*1.5,float3(-35,0,0),{blend})'),
        # Local -X is opposite the actor's velocity. This rotates the BAKED
        # upward texture motion as well as the particle positions at launch.
        'Particles.SpriteAlignment': (VEC3, f'normalize(lerp({hover_axis},float3(-1,0,0),{blend}))'),
        'Particles.SpriteRotation': (FLOAT, '0'),
        'Particles.SpriteUVScale': (VEC2, 'float2(1,1)'),
        'Particles.SpriteSize': (VEC2, f'float2(10+3*{seed},13+3*{variant})*(1-.12*{n})'),
        'Particles.SubImageIndex': (FLOAT, f'fmod({variant}*64+{age}*(12+4*{seed}),64)'),
        'Particles.Color': (COLOR, f'float4(1,.93,.82,.58*{fade})'),
    }
    assignments(system, EMITTER, 'ParticleSpawnScript', {
        'Particles.Lifetime': (FLOAT, f'.9+.5*{seed}'), **common,
    })
    assignments(system, EMITTER, 'ParticleUpdateScript', common)
    save(system)
    out = Path(unreal.Paths.project_dir()) / 'SourceAssets/FireballOuterFlame20260914'
    out.mkdir(parents=True, exist_ok=True)
    (out / 'authoring.json').write_text(json.dumps({
        'system': system.get_path_name(), 'emitter': EMITTER, 'material': mat.get_path_name(),
        'texture': ATLAS, 'source_pack': 'Dr.Game Free Spline VFX (user imported)',
        'source_listing': 'https://www.fab.com/listings/2b923e61-b02d-4cc9-bd0b-b067c9e6056e',
        'source_reference_layer': 'NS_Spline_Fire / Fire_B',
        'spawn_rate': 8, 'lifetime_seconds': [.9,1.4], 'root_radius_cm': [8,10],
        'sprite_width_cm': [10,13], 'sprite_height_cm': [13,16], 'root_pivot_uv': [.5,.82],
        'atlas': {'columns': 8, 'rows': 8, 'fps': [12,16], 'independent_phase': True, 'frame_blend': True},
        'hover': 'Short upward/outward flames, embedded soft roots, no ring or axial orbit',
        'flight': 'Existing 60 ms blend; root positions and baked flame axis both turn toward local -X',
        'material_alpha': 'RGB coverage; smooth bottom/side masking; depth fade then premultiplied emissive',
        'dependencies': 'FireFlame texture only from Spline VFX; existing core emitter template from Epic Niagara Examples',
        'license': 'Keep acquired source-package terms and dependencies; no new redistribution grant',
        'status': 'authored and compiled; no game test or rendered acceptance',
    }, indent=2), encoding='utf-8')
    unreal.log('FIREBALL_OUTER_FIRE_FLAME_AUTHORED')


if __name__ == '__main__':
    build()
