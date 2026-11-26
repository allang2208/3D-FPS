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
donor = '/Game/Props/RomanColumn20260915/NS_TorchFlame'
path = '/Game/WorldGeneration/TemperateHills/HotOil/TorchField/NS_OilTorchField'
assets.make_directory(path.rsplit('/', 1)[0])
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
if 'User.OilRoots' not in variables:
    default_array = u.new_object(u.NiagaraDataInterfaceArrayFloat4, outer=system)
    roots = u.NiagaraExt_UserVariable()
    default = (f'/Script/NiagaraEditor.NiagaraExt_VariableValue_DataInterface'
               f'(DataInterfaceClass="{array_type}",DataInterface="{default_array.get_path_name()}")')
    roots.import_text(f'(Name="User.OilRoots",Type=(ClassStructOrEnum="{array_type}",UnderlyingType=1),DefaultValue={default})')
    API.call_method('AddUserVariables', (system,[roots]))
    if 'User.OilRoots' not in API.call_method('GetUserVariables', (system,)).export_text():
        raise RuntimeError('Niagara did not expose the oil root array')
for name in ('WetRootCount', 'PrimaryRate', 'SecondaryRate'):
    if 'User.' + name not in variables:
        user_parameter(system, name, scalar)


def append_assignment(emitter, stage, name, fields):
    tag = f'OilTorch.{emitter}.{stage}.{name}'
    module = assets.get_metadata_tag(system,tag)
    if not module:
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
for emitter, rate, offset in ((primary,'PrimaryRate',0.0),(secondary,'SecondaryRate',0.37)):
    put(system,emitter,'EmitterUpdateScript','SpawnRate','SpawnRate',f'(HlslExpression="User.{rate}")',hl)
    lookup = append_assignment(emitter,spawn,'Lookup',[('Particles.OilRoot',vec4)])
    def select(key, value, kind):
        put(system,emitter,spawn,lookup,'Particles.OilRoot'+key,value,'/Script/NiagaraEditor.NiagaraExt_StackInputData_'+kind)
    select('', '(DynamicInputAsset="/Niagara/DynamicInputs/Arrays/SelectVector4_FromArray.SelectVector4_FromArray")','DynamicInput')
    select('|Array Sampling Mode','(Enum="/Niagara/Enums/ENiagaraArraySamplingMode.ENiagaraArraySamplingMode",EnumName="ENiagaraArraySamplingMode::NewEnumerator1",DisplayName="Direct Set")','Enum')
    select('|Vector4 Selection Array',f'(LinkedVariable=(Name="User.OilRoots",Type=(ClassStructOrEnum="{array_type}",UnderlyingType=1)))','Linked')
    select('|Direct Array Index',f'(HlslExpression="int(frac(float(Particles.UniqueID)*.618034+{offset})*max(User.WetRootCount,1.))")','HlslExpression')
    # Keep the donor's initial motion, age, colour, noise and sprite-size animation.
    # Choose the root once at birth; later arrivals never move an existing particle.
    size = 'Particles.OilSize'
    size_expr = '(HlslExpression="Particles.SpriteSize*float2(3.6,2.4)*Particles.OilRoot.w")'
    place = append_assignment(emitter,spawn,'Place',[('Particles.Position',position),(size,vec2)])
    put(system,emitter,spawn,place,'Particles.Position','(HlslExpression="Particles.Position+Particles.OilRoot.xyz")',hl)
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
