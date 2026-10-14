"""Author only the new, user-approved Realistic Vol.2 campfire packages.

Native 8x4/6x6 flames and 8x8 light smoke; no dense/noise body, heat or light renderer.
No world, gameplay, preview, screenshot or render. Run via the existing bridge batch
or a background FPSGAME Python commandlet after the normal Editor DLL build.
"""
import hashlib
import json
import math
import sys
from pathlib import Path
import unreal as u

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'SourceAssets/Campfire20261012/Realistic'
DEST = '/Game/Building/Campfire20261012/Realistic'
SYSTEM_NAME = 'NS_CampfireRealisticFlame'
PACK = '/Game/Realistic_Starter_VFX_Pack_Vol2'
sys.path.insert(0, str(ROOT / 'Tools/Skills'))
from build_fireball_assets import API, LIB, ref, emitters, setdata, assignments
from build_fireball_torch_burn import setup_emitter
from build_fireball_slow_burn import smooth
from build_fireball_outer_flame import enable_sprite_usage

FLOAT = '/Script/Niagara.NiagaraFloat'
VEC2 = '/Script/CoreUObject.Vector2f'
VEC3 = '/Script/CoreUObject.Vector3f'
VEC4 = '/Script/CoreUObject.Vector4f'
POSITION = '/Script/Niagara.NiagaraPosition'
COLOR = '/Script/CoreUObject.LinearColor'
SAVED = []
OUT.mkdir(parents=True, exist_ok=True)

LAYERS = [
    dict(name='ShortNativeFlames', material='M_CampfireNative8x4', source=PACK+'/Materials/M_Fire_B',
         cols=8, rows=4, rate=7.0, life_min=.85, life_max=1.15, width_min=23.0, width_max=31.0,
         height_min=44.0, height_max=60.0, alpha=.82, smoke=False),
    dict(name='RollingNativeFlames', material='M_CampfireNative6x6', source=PACK+'/Materials/M_Fire_C',
         cols=6, rows=6, rate=6.0, life_min=1.0, life_max=1.35, width_min=24.0, width_max=34.0,
         height_min=49.0, height_max=68.0, alpha=.62, smoke=False),
    dict(name='SparseNativeSmoke', material='M_CampfireNativeSmoke', source=PACK+'/Materials/M_Smoke_C',
         cols=8, rows=8, rate=1.2, life_min=1.9, life_max=2.6, width_min=32.0, width_max=42.0,
         height_min=37.0, height_max=46.0, alpha=.075, smoke=True),
]

def disk_sha(package):
    file = ROOT / 'Content' / (package.removeprefix('/Game/').split('.')[0] + '.uasset')
    return hashlib.sha256(file.read_bytes()).hexdigest()

protected = [PACK+'/Particles/Fire/P_Fire_Small',
    PACK+'/Materials/M_Fire_B', PACK+'/Materials/M_Fire_C', PACK+'/Materials/M_Smoke_C',
    '/Game/Building/Campfire20261012/NS_CampfireFlame',
    '/Game/Building/Campfire20261012/M_CampfireDenseFlame',
    '/Game/Building/Campfire20261012/M_CampfireTongues']
before = {p: disk_sha(p) for p in protected}

def owned_copy(source, name):
    target = DEST + '/' + name
    if target in {p.get_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()}:
        raise RuntimeError('Preserve unsaved edits: ' + target)
    asset = u.load_asset(target) if u.EditorAssetLibrary.does_asset_exist(target) else u.EditorAssetLibrary.duplicate_asset(source, target)
    if not asset:
        raise RuntimeError('Cannot create ' + target)
    return asset

def save(asset):
    if not asset.get_path_name().startswith(DEST + '/'):
        raise RuntimeError('Save outside owned destination refused')
    if isinstance(asset, u.NiagaraSystem):
        if not u.RainAssetEditor.compile_rain(asset):
            raise RuntimeError('Niagara compile failed: ' + asset.get_path_name())
    if not u.EditorLoadingAndSavingUtils.save_packages([asset.get_outermost()], False):
        raise RuntimeError('Package save failed: ' + asset.get_path_name())
    SAVED.append(asset.get_path_name())
    print('CAMPFIRE_REALISTIC_SAVED', asset.get_path_name())

def create_material(layer):
    mat = owned_copy(layer['source'], layer['material'])
    opacity = LIB.get_material_property_input_node(mat, u.MaterialProperty.MP_OPACITY)
    if not opacity:
        raise RuntimeError('Native opacity chain missing: ' + layer['source'])
    original_opacity_name = opacity.get_name()
    enable_sprite_usage(mat)
    mat.set_editor_property('refraction_method', u.RefractionMode.RM_NONE)
    mat.set_editor_property('allow_front_layer_translucency', False)
    mat.set_editor_property('two_sided', True)
    mat.set_editor_property('enable_responsive_aa', True)
    # Retain all native frame/mask/color/alpha connections. Only shorten contact
    # fading to this approximately 0.9m firepit; no procedural flame field is added.
    for node in LIB.get_material_expressions(mat):
        if isinstance(node, u.MaterialExpressionDepthFade):
            node.set_editor_property('fade_distance_default', 7.0 if layer['smoke'] else 4.0)
        if isinstance(node, u.MaterialExpressionParticleSubUV) and not node.get_editor_property('texture'):
            raise RuntimeError('Native ParticleSubUV texture missing: ' + mat.get_name())
    if not layer['smoke'] and not any(isinstance(n, u.MaterialExpressionEyeAdaptationInverse) for n in LIB.get_material_expressions(mat)):
        previous = LIB.get_material_property_input_node(mat, u.MaterialProperty.MP_EMISSIVE_COLOR)
        inverse = LIB.create_material_expression(mat, u.MaterialExpressionEyeAdaptationInverse)
        inverse.set_editor_property('desc', 'Campfire exposure compensation; native color/opacity retained')
        LIB.connect_material_expressions(previous, '', inverse, str(LIB.get_material_expression_input_names(inverse)[0]))
        LIB.connect_material_property(inverse, '', u.MaterialProperty.MP_EMISSIVE_COLOR)
    if LIB.get_material_property_input_node(mat, u.MaterialProperty.MP_OPACITY).get_name() != original_opacity_name:
        raise RuntimeError('Native opacity output was replaced')
    compile_result = LIB.recompile_material(mat)
    # UE commandlet returns false with no RHI; it is not a list of errors.
    if isinstance(compile_result, (list, tuple)) and compile_result:
        raise RuntimeError(str(compile_result))
    save(mat)
    return mat

materials = {layer['name']: create_material(layer) for layer in LAYERS}
# This source supplies a looping system container only. Every source emitter is
# removed; the final three renderers all use the new native Realistic materials.
system = owned_copy('/Game/NiagaraExamples/FX_Misc/NS_Fire', SYSTEM_NAME)
for name in emitters(system):
    API.call_method('RemoveEmitter', (ref(system, name),))

age = 'Particles.Age'
norm = 'Particles.NormalizedAge'
seed = 'frac(float(Particles.UniqueID)*.61803398875)'
variant = 'frac(float(Particles.UniqueID)*.41421356237)'
for index, layer in enumerate(LAYERS):
    name = layer['name']
    # Existing helper provides a CPU sprite lifecycle and canonical attribute
    # bindings; it trims the source to EmitterState/SpawnRate/Initialize/ParticleState.
    # No source fire shader, light, heat, force or noise module is retained.
    setup_emitter(system, name, materials[name], layer['rate'], True)
    setdata('SetRendererData', u.NiagaraExt_RendererData, ref(system, name, renderer=0), {
        'Material': materials[name].get_path_name(),
        'SubImageSize': {'X': layer['cols'], 'Y': layer['rows']}, 'bSubImageBlend': True,
        'PivotInUVSpace': {'X': .5, 'Y': .5},
        'Alignment': 'Unaligned' if layer['smoke'] else 'CustomAlignment',
        'FacingMode': 'FaceCamera', 'SortOrderHint': 0 if layer['smoke'] else 1,
        'bCastShadows': False,
    })
    phase = f'(6.2831853*{seed}+{index}*2.1)'
    width = f'lerp({layer["width_min"]},{layer["width_max"]},{variant})'
    height = f'lerp({layer["height_min"]},{layer["height_max"]},{seed})'
    envelope = smooth('0', '.14', norm) + '*(1-' + smooth('.52', '1', norm) + ')'
    if layer['smoke']:
        position = f'float3(cos({phase})*(4+{age}*3),sin({phase})*(4+{age}*3),40+{age}*24)'
        size = f'float2({width},{height})*(.7+{norm}*.95)'
        tint = 'float3(.13,.115,.095)'
        dynamic = 'float4(0,0,0,0)'
    else:
        position = f'float3(cos({phase})*(5+9*{variant})+sin({age}*2.1+{phase})*2,sin({phase})*(5+9*{variant}),6+({height})*.5+{age}*7)'
        size = f'float2({width},{height})*(.92+.12*{norm})'
        # Keep the source RGB detail: a restrained, near-neutral warm gain replaces
        # the original demonstration's hundreds/thousands-unit colored light curves.
        tint = f'lerp(float3(2.3,1.95,1.48),float3(1.5,.85,.39),{norm})'
        # Native M_Fire_C uses X for mask offset and Y for opacity exponent.
        dynamic = f'float4({variant},.55+.6*{seed}+{norm}*.3,0,0)' if layer['cols'] == 6 else 'float4(0,0,0,0)'
    appearance = {
        'Particles.Position': (POSITION, position), 'Particles.Velocity': (VEC3, 'float3(0,0,0)'),
        'Particles.SpriteSize': (VEC2, size), 'Particles.SpriteUVScale': (VEC2, 'float2(1,1)'),
        'Particles.SpriteAlignment': (VEC3, f'normalize(float3(.04*cos({phase}),.04*sin({phase}),1))'),
        'Particles.SpriteRotation': (FLOAT, f'{seed}*360' if layer['smoke'] else '0'),
        'Particles.Color': (COLOR, f'float4({tint},{layer["alpha"]}*{envelope})'),
        'Particles.SubImageIndex': (FLOAT, f'min({norm}*{layer["cols"]*layer["rows"]-1},{layer["cols"]*layer["rows"]-1}.0)'),
        'Particles.DynamicMaterialParameter': (VEC4, dynamic),
        'Particles.MaterialRandom': (FLOAT, variant),
    }
    assignments(system, name, 'ParticleSpawnScript', {
        'Particles.Lifetime': (FLOAT, f'lerp({layer["life_min"]},{layer["life_max"]},{variant})'), **appearance})
    assignments(system, name, 'ParticleUpdateScript', appearance)
system.set_editor_property('fixed_bounds', u.Box(min=u.Vector(-85,-85,-12), max=u.Vector(85,85,165)))
save(system)

after = {p: disk_sha(p) for p in protected}
if before != after:
    raise RuntimeError('A protected source or rejected previous package changed')

readback = {'system': system.get_path_name(), 'emitters': [], 'materials': []}
for name in emitters(system):
    data = json.loads(API.call_method('GetRendererData', (ref(system, name, renderer=0),)).get_editor_property('property_values'))
    readback['emitters'].append({'name': name, 'material': data.get('Material'),
        'subimage_size': data.get('SubImageSize'), 'frame_blending': data.get('bSubImageBlend')})
for mat in materials.values():
    nodes = LIB.get_material_expressions(mat)
    readback['materials'].append({'path': mat.get_path_name(), 'blend': str(mat.get_editor_property('blend_mode')),
        'refraction': str(mat.get_editor_property('refraction_method')),
        'opacity_node': LIB.get_material_property_input_node(mat, u.MaterialProperty.MP_OPACITY).get_name(),
        'textures': [node.get_editor_property('texture').get_path_name() for node in nodes
            if isinstance(node, (u.MaterialExpressionParticleSubUV, u.MaterialExpressionTextureSample)) and node.get_editor_property('texture')]})
(OUT/'asset-readback.json').write_text(json.dumps(readback, indent=2), encoding='utf-8')
(OUT/'delivery.json').write_text(json.dumps({
    'system': system.get_path_name(), 'assets': SAVED, 'source_cascade': PACK+'/Particles/Fire/P_Fire_Small',
    'source_parameters': '../local-fire-cascade-profiles.json', 'layers': LAYERS,
    'upper_live_particles_estimate': sum(math.ceil(v['rate']*v['life_max'])+1 for v in LAYERS),
    'shared_source_and_rejected_assets_unchanged': before == after, 'protected_sha256': before,
    'particle_lights': 0, 'heat_distortion_emitters': 0, 'sparks': 0,
    'runtime_budget_preserved': '8 visible systems; 30m enter/35m leave; existing parent 350lm no-shadow light',
    'component_anchor_contract_cm': {'existing_parent_z':20,'new_sprite_bottom_at_birth_relative_z':6},
    'niagara_compiled': True, 'assets_saved': True, 'runtime_tested': False, 'visual_tested': False,
}, indent=2), encoding='utf-8')
print('CAMPFIRE_REALISTIC_AUTHORING_COMPLETE', system.get_path_name())
