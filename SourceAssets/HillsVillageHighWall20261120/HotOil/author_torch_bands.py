"""Batch the two installed bronze-torch flame emitters over wetted ground."""
from pathlib import Path
import json
import sys
import unreal as u

project = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(project/'Tools/Skills'))
from build_fireball_assets import API, ref, emitters, put, setdata, save
from build_fireball_flight import user_parameter

assets = u.EditorAssetLibrary
# The shipped first oil variant contains the untouched bronze-torch renderers and a saved array interface.
donor = '/Game/WorldGeneration/TemperateHills/HotOil/TorchField/NS_OilTorchField'
path = '/Game/WorldGeneration/TemperateHills/HotOil/TorchFieldR2/NS_OilTorchBands'
assets.make_directory(path.rsplit('/', 1)[0])
previous = u.load_asset(donor)
system = u.load_asset(path) if assets.does_asset_exist(path) else assets.duplicate_asset(donor, path)
if not system:
    raise RuntimeError('Could not create oil field from ' + donor)

primary, secondary = 'NE_Flame_01', 'NE_Flame_02'
for name in emitters(system):
    if name not in (primary, secondary):
        API.call_method('RemoveEmitter', (ref(system, name),))

array_type = '/Script/Niagara.NiagaraDataInterfaceArrayFloat4'
hl = '/Script/NiagaraEditor.NiagaraExt_StackInputData_HlslExpression'
scalar = '/Script/Niagara.NiagaraFloat'
vec2 = '/Script/CoreUObject.Vector2f'
vec4 = '/Script/CoreUObject.Vector4f'
position = '/Script/Niagara.NiagaraPosition'
variables = API.call_method('GetUserVariables', (system,)).export_text()
for name in ('WetRootCount','BandStride','HotRootCount','PrimaryRate','SecondaryRate'):
    if 'User.' + name not in variables:
        user_parameter(system, name, scalar)
if 'User.OilView' not in variables:
    user_parameter(system,'OilView',vec4)


def append_assignment(emitter, stage, name, fields):
    tag = f'OilTorch.{emitter}.{stage}.{name}'
    module = assets.get_metadata_tag(system,tag)
    # A duplicated system can inherit the assignment graphs even on hosts that do
    # not copy their editor metadata. Reuse those original modules in stack order.
    original = assets.get_metadata_tag(previous,tag)
    field = 'particle_spawn_script' if stage == 'ParticleSpawnScript' else 'particle_update_script'
    topology = API.call_method('GetEmitterTopology',(ref(system,emitter),))
    names = [str(m.get_editor_property('module_name')) for m in topology.get_editor_property(field).get_editor_property('modules')]
    if original and original in names:
        if module and module != original and module in names:
            API.call_method('RemoveModule',(ref(system,emitter,stage,module),))
        assets.set_metadata_tag(system,tag,original)
        return original
    if not module or module not in names:
        entries = []
        for field, kind in fields:
            entry = u.NiagaraExt_SetParameterEntry()
            entry.import_text(f'(Variable=(Name="{field}",Type=(ClassStructOrEnum="{kind}",UnderlyingType=2)))')
            entries.append(entry)
        result = API.call_method('AddSetParametersModule',(ref(system,emitter,stage),entries))
        module = str(result.get_editor_property('module_name'))
        assets.set_metadata_tag(system,tag,module)
    return module


spawn, update = 'ParticleSpawnScript', 'ParticleUpdateScript'
for emitter, rate in ((primary,'PrimaryRate'),(secondary,'SecondaryRate')):
    low = emitter == primary
    put(system,emitter,'EmitterUpdateScript','SpawnRate','SpawnRate',f'(HlslExpression="User.{rate}")',hl)
    lookup = append_assignment(emitter,spawn,'Lookup',[('Particles.OilRoot',vec4)])
    def select(key, value, kind):
        put(system,emitter,spawn,lookup,'Particles.OilRoot'+key,value,'/Script/NiagaraEditor.NiagaraExt_StackInputData_'+kind)
    select('', '(DynamicInputAsset="/Niagara/DynamicInputs/Arrays/SelectVector4_FromArray.SelectVector4_FromArray")','DynamicInput')
    select('|Array Sampling Mode','(Enum="/Niagara/Enums/ENiagaraArraySamplingMode.ENiagaraArraySamplingMode",EnumName="ENiagaraArraySamplingMode::NewEnumerator1",DisplayName="Direct Set")','Enum')
    param = 'OilRoots'
    select('|Vector4 Selection Array',f'(LinkedVariable=(Name="User.{param}",Type=(ClassStructOrEnum="{array_type}",UnderlyingType=1)))','Linked')
    count = 'max(1.,User.WetRootCount)'
    serial = 'float(Particles.UniqueID)'
    band = f'fmod(fmod({serial},{count})*User.BandStride,{count})'
    # One visit per band per cycle. Advance along the band on the next visit.
    index = (f'int({band}*5.+fmod(floor({serial}/{count})+{band},5.))' if low else
             f'int(User.WetRootCount*5.+fmod({serial},max(1.,User.HotRootCount)))')
    select('|Direct Array Index',f'(HlslExpression="{index}")','HlslExpression')
    # Keep the donor's initial motion, age, colour, noise and sprite-size animation.
    # Choose the root once at birth; later arrivals never move an existing particle.
    size = 'Particles.OilSize'
    width,height = (2.95,1.65) if low else (1.80,2.85)
    # OilView is the camera position in field coordinates and a horizontal FOV factor.
    cap = 'max(8.,length(Particles.OilRoot.xyz-User.OilView.xyz)*User.OilView.w)'
    size_expr = f'(HlslExpression="float2(min(Particles.SpriteSize.x*{width}*Particles.OilRoot.w,{cap}),Particles.SpriteSize.y*{height}*Particles.OilRoot.w)")'
    place = append_assignment(emitter,spawn,'Place',[('Particles.Position',position),(size,vec2)])
    # The sampled ground position is authoritative for XY, including shoreline roots.
    put(system,emitter,spawn,place,'Particles.Position','(HlslExpression="Particles.OilRoot.xyz")',hl)
    put(system,emitter,spawn,place,size,size_expr,hl)
    resize = append_assignment(emitter,update,'Size',[(size,vec2)])
    put(system,emitter,update,resize,size,size_expr,hl)
    renderer = ref(system,emitter,renderer=0)
    props = json.loads(API.call_method('GetRendererData',(renderer,)).get_editor_property('property_values'))
    binding = props['SpriteSizeBinding']
    binding['rootName'] = binding['dataSetName'] = 'OilSize'
    binding['paramMapVariable']['name'] = binding['cachedDisplayName'] = size
    setdata('SetRendererData',u.NiagaraExt_RendererData,renderer,{'SpriteSizeBinding':binding,'bCastShadows':False})
    bounds = {'min':{'x':-700,'y':-700,'z':-570},'max':{'x':700,'y':700,'z':380},'isValid':True}
    setdata('SetEmitterData',u.NiagaraExt_EmitterData,ref(system,emitter),{'bLocalSpace':True,'CalculateBoundsMode':'Fixed','FixedBounds':bounds})
system.set_editor_property('bFixedBounds',True)
system.set_editor_property('FixedBounds',u.Box(min=u.Vector(-700,-700,-570),max=u.Vector(700,700,380)))
save(system)
if 'User.OilRoots' not in API.call_method('GetUserVariables', (system,)).export_text():
    raise RuntimeError('The compiled field must expose its source array')
