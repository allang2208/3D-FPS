"""Create a campfire-only derivative; never save vendor/old packages or run a world."""
import json,sys,hashlib,math
from pathlib import Path
import unreal as u
ROOT=Path('D:/FPS3D/FPSGAME')
OUT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'Tools/Skills'))
from build_fireball_assets import API,ref,emitters,setdata,assignments
HELP=getattr(u,'CampfireAssetTools',getattr(u,'RainAssetEditor',None))
assert HELP
u.RainAssetEditor=HELP
DEST='/Game/Building/Campfire20261013/TorchFire'
SOURCE='/Game/TorchFire/FX/NS_TorchFire_Standard'
TARGET=DEST+'/NS_CampfireTorchFire'
assert not u.EditorAssetLibrary.does_asset_exist(TARGET),'New destination must be absent'
s=u.EditorAssetLibrary.duplicate_asset(SOURCE,TARGET)
assert s
for name in ('Light001','Sparks001'):
    assert name in emitters(s)
    API.call_method('RemoveEmitter',(ref(s,name),))
FLOAT='/Script/Niagara.NiagaraFloat'
VEC2='/Script/CoreUObject.Vector2f'
VEC3='/Script/CoreUObject.Vector3f'
POSITION='/Script/Niagara.NiagaraPosition'
COLOR='/Script/CoreUObject.LinearColor'
records=[]
def put(e,stage,module,key,value,typ=FLOAT):
    assert HELP.set_input(s,e,stage,module,key,typ,value),(e,module,key,value)
    records.append({'emitter':e,'stage':stage,'module':module,'input':key,'value':HELP.read_input(s,e,stage,module,key)})
def drop(e,stage,module):API.call_method('RemoveModule',(ref(s,e,stage,module),))
def module_names(e,prop):
    return [str(m.get_editor_property('module_name')) for m in API.call_method('GetEmitterTopology',(ref(s,e),)).get_editor_property(prop).get_editor_property('modules')]
seed='frac(float(Particles.UniqueID)*.61803398875)'
variant='frac(float(Particles.UniqueID)*.41421356237)'
angle=f'(6.2831853*{seed})'
layers={'Fire':{'rate':12.,'life':[1.1,1.55],'size':[62.,76.],'radius':14.},
        'Smoke':{'rate':1.4,'life':[2.3,3.0],'size':[35.,45.],'radius':12.},
        'Sparks':{'rate':2.5,'life':[1.1,1.7],'size':[1.1,1.8],'radius':18.}}
for name,params in layers.items():
    setdata('SetEmitterData',u.NiagaraExt_EmitterData,ref(s,name),{'bLocalSpace':True,'CalculateBoundsMode':'Fixed','FixedBounds':{'min':{'x':-115,'y':-115,'z':-15},'max':{'x':115,'y':115,'z':225},'isValid':True}})
    put(name,'EmitterUpdateScript','SpawnRate','SpawnRate',f'(Value={params["rate"]})')
    # Keep native animation, material erosion and age/color curves. Override physical
    # birth attributes after initialization, with independent natural-aspect sprites.
    spawn_modules=module_names(name,'particle_spawn_script')
    for mod in ('CameraOffset','ShapeLocation','AddVelocity','AddVelocity001'):
        if mod in spawn_modules:drop(name,'ParticleSpawnScript',mod)
    size=f'lerp({params["size"][0]},{params["size"][1]},{variant})'
    radius=f'({params["radius"]}*sqrt({variant}))'
    z=f'({size})*.5' if name=='Fire' else ('45' if name=='Smoke' else '10')
    vel=('float3(0,0,lerp(10,16,'+seed+'))') if name=='Fire' else ('float3(0,0,22)' if name=='Smoke' else f'float3(cos({angle})*5,sin({angle})*5,lerp(35,52,{seed}))')
    values={'Particles.Position':(POSITION,f'float3(cos({angle})*{radius},sin({angle})*{radius},{z})'),
        'Particles.Lifetime':(FLOAT,f'lerp({params["life"][0]},{params["life"][1]},{seed})'),
        'Particles.SpriteSize':(VEC2,f'float2({size},{size})'),
        'Particles.Velocity':(VEC3,vel)}
    if name=='Smoke':values['Particles.Color']=(COLOR,'float4(.22,.205,.185,.15)')
    assignments(s,name,'ParticleSpawnScript',values)
    setdata('SetRendererData',u.NiagaraExt_RendererData,ref(s,name,renderer=0),{'bCastShadows':False})
    if name=='Fire':
        setdata('SetRendererData',u.NiagaraExt_RendererData,ref(s,name,renderer=0),{'PivotInUVSpace':{'X':.5,'Y':.5}})
    elif name=='Smoke':
        put(name,'ParticleUpdateScript','AccelerationForce','Acceleration','(X=0,Y=0,Z=3)',VEC3)
        put(name,'ParticleUpdateScript','Drag','Drag','(Value=.15)')
    elif name=='Sparks':
        put(name,'ParticleUpdateScript','CurlNoiseForce','Noise Strength','(Value=3.5)')
        put(name,'ParticleUpdateScript','Drag','Drag','(Value=.35)')
s.set_editor_property('fixed_bounds',u.Box(min=u.Vector(-115,-115,-15),max=u.Vector(115,115,225)))
sd=u.NiagaraExt_SystemData()
sd.set_editor_property('property_values',json.dumps({'bFixedBounds':True}))
API.call_method('SetSystemData',(s,sd))
assignments(s,'Smoke','ParticleUpdateScript',{'Particles.SpriteSize':(VEC2,'min(Particles.SpriteSize,float2(72,72))')})
assert HELP.compile_rain(s),'Niagara compile failed'
assert u.EditorLoadingAndSavingUtils.save_packages([s.get_outermost()],False),'Save failed'
readback={'asset':s.get_path_name(),'source':SOURCE,'layers':layers,'changes':records,'emitters':{},'fixed_bounds':str(s.get_editor_property('fixed_bounds')),'niagara_compiled':True,'saved':True,'game_or_pie_started':False}
for name in emitters(s):
    readback['emitters'][name]={'settings':json.loads(API.call_method('GetEmitterData',(ref(s,name),)).get_editor_property('property_values')),'renderer':json.loads(API.call_method('GetRendererData',(ref(s,name,renderer=0),)).get_editor_property('property_values'))}
assert set(readback['emitters'])==set(layers)
readback['upper_particle_estimate']=sum(math.ceil(p['rate']*p['life'][1])+1 for p in layers.values())
(OUT/'authored-readback.json').write_text(json.dumps(readback,indent=2),encoding='utf-8')
print('CAMPFIRE_TORCH_AUTHORED',s.get_path_name())
