"""Build contiguous sea-of-fire Niagara asset (NE_Flame_01 + NE_Flame_02 + NE_Sparkles) over wet oil cells."""
from pathlib import Path
import json
import sys
import unreal as u

project = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(project / 'Tools/Skills'))
from build_fireball_assets import API, ref, emitters, put, setdata, save
from build_fireball_flight import user_parameter

assets = u.EditorAssetLibrary
donor = '/Game/WorldGeneration/TemperateHills/HotOil/TorchField/NS_OilTorchField'
sparkles_emitter = '/Game/Vefects/Free_Fire/Shared/Particles/NE_Sparkles'
path = '/Game/WorldGeneration/TemperateHills/HotOil/SeaOfFireV3/NS_OilSeaOfFire'
assets.make_directory(path.rsplit('/', 1)[0])

previous = u.load_asset(donor)
if not previous:
    raise RuntimeError('Could not load donor Niagara system: ' + donor)
system = u.load_asset(path) if assets.does_asset_exist(path) else assets.duplicate_asset(donor, path)
if not system:
    raise RuntimeError('Could not create sea-of-fire system from ' + donor)

primary, secondary, detail = 'NE_Flame_01', 'NE_Flame_02', 'NE_Sparkles'
if detail not in emitters(system):
    em_asset = u.load_asset(sparkles_emitter)
    if not em_asset:
        raise RuntimeError('Could not load Vefects emitter: ' + sparkles_emitter)
    API.call_method('AddEmitter', (system, em_asset, detail))

for name in list(emitters(system)):
    if name not in (primary, secondary, detail):
        API.call_method('RemoveEmitter', (ref(system, name),))

array_type = '/Script/Niagara.NiagaraDataInterfaceArrayFloat4'
hl = '/Script/NiagaraEditor.NiagaraExt_StackInputData_HlslExpression'
enum_kind = '/Script/NiagaraEditor.NiagaraExt_StackInputData_Enum'
dyn_kind = '/Script/NiagaraEditor.NiagaraExt_StackInputData_DynamicInput'
link_kind = '/Script/NiagaraEditor.NiagaraExt_StackInputData_Linked'
scalar = '/Script/Niagara.NiagaraFloat'
vec2 = '/Script/CoreUObject.Vector2f'
vec3 = '/Script/CoreUObject.Vector3f'
vec4 = '/Script/CoreUObject.Vector4f'
position = '/Script/Niagara.NiagaraPosition'

variables = API.call_method('GetUserVariables', (system,)).export_text()
for name in ('WetRootCount', 'BandStride', 'HotRootCount', 'PrimaryRate', 'SecondaryRate', 'DetailRate'):
    if 'User.' + name not in variables:
        user_parameter(system, name, scalar)
if 'User.OilView' not in variables:
    user_parameter(system, 'OilView', vec4)
if 'User.Wind' not in variables:
    user_parameter(system, 'Wind', vec3)


def append_assignment(emitter, stage, name, fields, reuse_prefix=None):
    tag = f'OilSeaOfFire.{emitter}.{stage}.{name}'
    module = assets.get_metadata_tag(system, tag)
    field_prop = 'particle_spawn_script' if stage == 'ParticleSpawnScript' else 'particle_update_script'
    topology = API.call_method('GetEmitterTopology', (ref(system, emitter),))
    names = [str(m.get_editor_property('module_name')) for m in topology.get_editor_property(field_prop).get_editor_property('modules')]

    if reuse_prefix:
        orig_tag = f'{reuse_prefix}.{emitter}.{stage}.{name}'
        original = assets.get_metadata_tag(previous, orig_tag)
        if original and original in names:
            if module and module != original and module in names:
                API.call_method('RemoveModule', (ref(system, emitter, stage, module),))
            assets.set_metadata_tag(system, tag, original)
            return original

    if not module or module not in names:
        entries = []
        for fld, kind in fields:
            entry = u.NiagaraExt_SetParameterEntry()
            entry.import_text(f'(Variable=(Name="{fld}",Type=(ClassStructOrEnum="{kind}",UnderlyingType=2)))')
            entries.append(entry)
        result = API.call_method('AddSetParametersModule', (ref(system, emitter, stage), entries))
        module = str(result.get_editor_property('module_name'))
        assets.set_metadata_tag(system, tag, module)
    return module


def configure_oil_lookup(emitter, stage, hlsl_index, reuse_prefix=None):
    lookup = append_assignment(emitter, stage, 'Lookup', [('Particles.OilRoot', vec4)], reuse_prefix=reuse_prefix)
    put(system, emitter, stage, lookup, 'Particles.OilRoot',
        '(DynamicInputAsset="/Niagara/DynamicInputs/Arrays/SelectVector4_FromArray.SelectVector4_FromArray")', dyn_kind)
    put(system, emitter, stage, lookup, 'Particles.OilRoot|Array Sampling Mode',
        '(Enum="/Niagara/Enums/ENiagaraArraySamplingMode.ENiagaraArraySamplingMode",EnumName="ENiagaraArraySamplingMode::NewEnumerator1",DisplayName="Direct Set")', enum_kind)
    put(system, emitter, stage, lookup, 'Particles.OilRoot|Vector4 Selection Array',
        f'(LinkedVariable=(Name="User.OilRoots",Type=(ClassStructOrEnum="{array_type}",UnderlyingType=1)))', link_kind)
    put(system, emitter, stage, lookup, 'Particles.OilRoot|Direct Array Index',
        f'(HlslExpression="{hlsl_index}")', hl)
    return lookup


spawn, update = 'ParticleSpawnScript', 'ParticleUpdateScript'
bounds = {'min': {'x': -700, 'y': -700, 'z': -570}, 'max': {'x': 700, 'y': 700, 'z': 380}, 'isValid': True}
serial = 'float(Particles.UniqueID)'
hash_x = f'(frac(sin({serial}*12.9898)*43758.5453)*2.-1.)'
hash_y = f'(frac(sin({serial}*78.233)*43758.5453)*2.-1.)'
hash_z = f'frac({serial}*0.381966)'
wind_expr = '(HlslExpression="Particles.Position+User.Wind*Engine.DeltaTime*(0.25+0.75*Particles.NormalizedAge)")'

flame_configs = (
    (primary, 'PrimaryRate', 0.88, 0.78, 1.18, 1.95, 1.25, 18.0),
    (secondary, 'SecondaryRate', 1.05, 0.85, 1.30, 1.25, 2.05, 12.0),
)

for emitter, rate_var, curve_scale, life_min, life_max, width, height, scatter_xy in flame_configs:
    low = emitter == primary
    put(system, emitter, 'EmitterUpdateScript', 'SpawnRate', 'SpawnRate', f'(HlslExpression="User.{rate_var}")', hl)
    put(system, emitter, spawn, 'InitializeParticle', 'Lifetime Min', f'(Value={life_min:.4f})')
    put(system, emitter, spawn, 'InitializeParticle', 'Lifetime Max', f'(Value={life_max:.4f})')
    put(system, emitter, update, 'ScaleSpriteSize', 'Uniform Curve Scale', f'(Value={curve_scale:.4f})')

    count = 'max(1.,User.WetRootCount)'
    band = f'fmod(fmod({serial},{count})*User.BandStride,{count})'
    index = (
        f'int({band}*3.+fmod(floor({serial}/{count})+{band},3.))'
        if low else
        f'int(User.WetRootCount*3.+fmod({serial},max(1.,User.HotRootCount)))'
    )
    configure_oil_lookup(emitter, spawn, index, reuse_prefix='OilTorch')

    size = 'Particles.OilSize'
    cap = 'max(24.,length(Particles.OilRoot.xyz-User.OilView.xyz)*User.OilView.w)'
    size_expr = f'(HlslExpression="float2(min(Particles.SpriteSize.x*{width}*Particles.OilRoot.w,{cap}),Particles.SpriteSize.y*{height}*Particles.OilRoot.w)")'
    pos_expr = f'(HlslExpression="Particles.OilRoot.xyz+float3({hash_x}*{scatter_xy:.1f},{hash_y}*{scatter_xy:.1f},2.)")'

    place = append_assignment(emitter, spawn, 'Place', [('Particles.Position', position), (size, vec2)], reuse_prefix='OilTorch')
    put(system, emitter, spawn, place, 'Particles.Position', pos_expr, hl)
    put(system, emitter, spawn, place, size, size_expr, hl)

    resize = append_assignment(emitter, update, 'Size', [(size, vec2)], reuse_prefix='OilTorch')
    put(system, emitter, update, resize, size, size_expr, hl)

    drift = append_assignment(emitter, update, 'Drift', [('Particles.Position', position)], reuse_prefix=None)
    put(system, emitter, update, drift, 'Particles.Position', wind_expr, hl)

    renderer = ref(system, emitter, renderer=0)
    props = json.loads(API.call_method('GetRendererData', (renderer,)).get_editor_property('property_values'))
    binding = props['SpriteSizeBinding']
    binding['rootName'] = binding['dataSetName'] = 'OilSize'
    binding['paramMapVariable']['name'] = binding['cachedDisplayName'] = size
    setdata('SetRendererData', u.NiagaraExt_RendererData, renderer, {'SpriteSizeBinding': binding, 'bCastShadows': False})
    setdata('SetEmitterData', u.NiagaraExt_EmitterData, ref(system, emitter), {'bLocalSpace': True, 'CalculateBoundsMode': 'Fixed', 'FixedBounds': bounds})

# Configure NE_Sparkles detail layer
sparkle_topo = API.call_method('GetEmitterTopology', (ref(system, detail),))
sparkle_eu_mods = [str(m.get_editor_property('module_name')) for m in sparkle_topo.get_editor_property('emitter_update_script').get_editor_property('modules')]
if 'SpawnBurst_Instantaneous' in sparkle_eu_mods:
    API.call_method('RemoveModule', (ref(system, detail, 'EmitterUpdateScript', 'SpawnBurst_Instantaneous'),))

put(system, detail, 'EmitterUpdateScript', 'SpawnRate', 'SpawnRate', '(HlslExpression="User.DetailRate")', hl)
put(system, detail, spawn, 'InitializeParticle', 'Lifetime Min', '(Value=0.6500)')
put(system, detail, spawn, 'InitializeParticle', 'Lifetime Max', '(Value=1.1500)')

sparkle_idx = f'int(fmod({serial}*7.,max(1.,User.WetRootCount*3.)))'
configure_oil_lookup(detail, spawn, sparkle_idx, reuse_prefix=None)
sparkle_pos = f'(HlslExpression="Particles.OilRoot.xyz+float3({hash_x}*22.,{hash_y}*22.,6.+{hash_z}*12.)")'
sparkle_place = append_assignment(detail, spawn, 'Place', [('Particles.Position', position)], reuse_prefix=None)
put(system, detail, spawn, sparkle_place, 'Particles.Position', sparkle_pos, hl)

sparkle_drift = append_assignment(detail, update, 'Drift', [('Particles.Position', position)], reuse_prefix=None)
put(system, detail, update, sparkle_drift, 'Particles.Position', wind_expr, hl)

setdata('SetRendererData', u.NiagaraExt_RendererData, ref(system, detail, renderer=0), {'bCastShadows': False})
setdata('SetEmitterData', u.NiagaraExt_EmitterData, ref(system, detail), {'bLocalSpace': True, 'CalculateBoundsMode': 'Fixed', 'FixedBounds': bounds})

system.set_editor_property('bFixedBounds', True)
system.set_editor_property('FixedBounds', u.Box(min=u.Vector(-700, -700, -570), max=u.Vector(700, 700, 380)))
save(system)

final_vars = API.call_method('GetUserVariables', (system,)).export_text()
required_vars = ('User.OilRoots', 'User.WetRootCount', 'User.BandStride', 'User.HotRootCount',
                 'User.PrimaryRate', 'User.SecondaryRate', 'User.DetailRate', 'User.OilView', 'User.Wind')
missing = [v for v in required_vars if v not in final_vars]
if missing:
    raise RuntimeError('Compiled NS_OilSeaOfFire missing user variables: ' + ', '.join(missing))

rae = u.RainAssetEditor
delivery = {
    'asset': system.get_path_name(),
    'emitters': list(emitters(system)),
    'scale_flame_01': rae.read_input(system, primary, update, 'ScaleSpriteSize', 'Uniform Curve Scale'),
    'scale_flame_02': rae.read_input(system, secondary, update, 'ScaleSpriteSize', 'Uniform Curve Scale'),
    'life_flame_01': [rae.read_input(system, primary, spawn, 'InitializeParticle', 'Lifetime Min'),
                      rae.read_input(system, primary, spawn, 'InitializeParticle', 'Lifetime Max')],
    'life_flame_02': [rae.read_input(system, secondary, spawn, 'InitializeParticle', 'Lifetime Min'),
                      rae.read_input(system, secondary, spawn, 'InitializeParticle', 'Lifetime Max')],
    'life_sparkles': [rae.read_input(system, detail, spawn, 'InitializeParticle', 'Lifetime Min'),
                      rae.read_input(system, detail, spawn, 'InitializeParticle', 'Lifetime Max')],
}
out_dir = Path('F:/FPSGAMEData/ArtProduction/HighVillageDefense/HotOilUpgrade-20261126')
out_dir.mkdir(parents=True, exist_ok=True)
(out_dir / 'delivery.json').write_text(json.dumps(delivery, indent=2), encoding='utf-8')
u.log('OIL_SEA_OF_FIRE_SAVED')
