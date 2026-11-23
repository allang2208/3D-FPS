"""Derive a handheld-scale flame from the project's actual cooking campfire."""
import json,os,sys
from pathlib import Path
import unreal as u
root=Path(os.environ['FPS_PROJECT_ROOT'])
batch=Path(os.environ['TORCH_BATCH'])
sys.path.insert(0,str(root/'Tools/Skills'))
from build_fireball_assets import API,ref,setdata,assignments,emitters,put
lib=u.EditorAssetLibrary
src='/Game/Building/Campfire20261013/TorchFire/NS_CampfireTorchFire'
dst='/Game/Weapons/WoodenTorch20261122/HearthHeadR3/NS_HandheldHearth'
s=lib.load_asset(dst) if lib.does_asset_exist(dst) else lib.duplicate_asset(src,dst)
if not s or set(emitters(s))!={'Fire','Smoke','Sparks'}:raise RuntimeError('Missing campfire emitters')
flt='/Script/Niagara.NiagaraFloat'
vec2='/Script/CoreUObject.Vector2f'
vec3='/Script/CoreUObject.Vector3f'
pos='/Script/Niagara.NiagaraPosition'
color='/Script/CoreUObject.LinearColor'
seed='frac(float(Particles.UniqueID)*.61803399)'
mix='frac(float(Particles.UniqueID)*.41421356)'
angle='(6.2831853*'+seed+')'
# Width, height and velocities are in centimetres; the component has unit world scale.
layers={'Fire':(8.0,12.,17.,1.35,.86,1.18),'Smoke':(.70,5.,7.5,.7,1.1,1.65),'Sparks':(.42,.32,.56,1.2,.55,.90)}
for name,(rate,lo,hi,radius,short,long) in layers.items():
    put(s,name,'EmitterUpdateScript','SpawnRate','SpawnRate',f'(Value={rate})')
    size=f'lerp({lo},{hi},{mix})'
    radial=f'({radius}*sqrt({mix}))'
    height=f'(.46*{size})' if name=='Fire' else ('10.' if name=='Smoke' else '3.')
    speed={'Fire':f'float3(0,0,lerp(2.4,4.0,{seed}))','Smoke':'float3(0,0,8)','Sparks':f'float3(cos({angle})*1.5,sin({angle})*1.5,lerp(10.,17.,{seed}))'}[name]
    values={'Particles.Position':(pos,f'float3(cos({angle})*{radial},sin({angle})*{radial},{height})'),
            'Particles.Lifetime':(flt,f'lerp({short},{long},{seed})'),
            'Particles.SpriteSize':(vec2,f'float2(.77*{size},{size})' if name=='Fire' else f'float2({size},{size})'),
            'Particles.Velocity':(vec3,speed)}
    if name=='Smoke':values['Particles.Color']=(color,'float4(.22,.205,.185,.085)')
    assignments(s,name,'ParticleSpawnScript',values)
    setdata('SetEmitterData',u.NiagaraExt_EmitterData,ref(s,name),{'bLocalSpace':True,'CalculateBoundsMode':'Fixed','FixedBounds':{'min':{'x':-15,'y':-15,'z':-5},'max':{'x':15,'y':15,'z':42},'isValid':True}})
assignments(s,'Smoke','ParticleUpdateScript',{'Particles.SpriteSize':(vec2,'min(Particles.SpriteSize,float2(13,13))')})
s.set_editor_property('fixed_bounds',u.Box(min=u.Vector(-15,-15,-5),max=u.Vector(15,15,42)))
if not u.RainAssetEditor.compile_rain(s) or not lib.save_loaded_asset(s,False):raise RuntimeError('Cannot compile and save handheld fire')
(batch/'fire-saved.json').write_text(json.dumps(dict(asset=s.get_path_name(),donor=src,layers=layers,compiled=True),indent=2))
