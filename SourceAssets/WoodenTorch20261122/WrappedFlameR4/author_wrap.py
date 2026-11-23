"""Build the wrapped handheld fire from the saved R3 flame and the measured head."""
import json,os,sys
from pathlib import Path
import unreal as u

root=Path(os.environ['FPS_PROJECT_ROOT'])
batch=Path(os.environ['TORCH_BATCH'])
sections=json.loads((root/'SourceAssets/WoodenTorch20261122/WrappedFlameR4/head-sections.json').read_text())
sys.path.insert(0,str(root/'Tools/Skills'))
from build_fireball_assets import ref,setdata,assignments,emitters,put
lib=u.EditorAssetLibrary
edit=u.MaterialEditingLibrary
base='/Game/Weapons/WoodenTorch20261122'
folder=base+'/WrappedFlameR4'
donor=base+'/HearthHeadR3/NS_HandheldHearth'
def derive(source,name):
    path=folder+'/'+name
    obj=lib.load_asset(path) if lib.does_asset_exist(path) else lib.duplicate_asset(source,path)
    if not obj: raise RuntimeError('Cannot create '+path)
    return obj
def save(obj):
    if not lib.save_loaded_asset(obj,False):raise RuntimeError('Cannot save '+obj.get_path_name())
mat=derive('/Game/Building/Campfire20261013/TorchFire/M_CampfireTorchFire','M_ClothContactFire')
nodes=edit.get_material_expressions(mat)
fade,=[n for n in nodes if isinstance(n,u.MaterialExpressionDepthFade)]
contact,=[n for n in nodes if isinstance(n,u.MaterialExpressionConstant) and 'Campfire contact fade' in str(n.get_editor_property('desc'))]
fade.set_editor_property('fade_distance_default',0.65)
contact.set_editor_property('r',0.65)
edit.recompile_material(mat)
save(mat)
system=derive(donor,'NS_WrappedHandheldHearth')
if set(emitters(system))!={'Fire','Smoke','Sparks'}:raise RuntimeError('Unexpected R3 emitter layout')
flt='/Script/Niagara.NiagaraFloat'
v2='/Script/CoreUObject.Vector2f'
v3='/Script/CoreUObject.Vector3f'
pos='/Script/Niagara.NiagaraPosition'
stage='ParticleSpawnScript'
# Every fourth tongue forms the plume. The others rotate around three courses on the cloth.
crown='((Particles.UniqueID % 4) == 0)'
band='(Particles.UniqueID % 3)'
seed='frac(float(Particles.UniqueID)*.61803399)'
mix='frac(float(Particles.UniqueID)*.41421356)'
angle=f'(6.2831853*{seed})'
def by_course(key):
    a,b,c=[d[key] for d in sections[:3]]
    return f'(({band} == 0) ? {a:.4f} : (({band} == 1) ? {b:.4f} : {c:.4f}))'
cx,cy,rx,ry,z=map(by_course,('cx','cy','rx','ry','z'))
surface=f'float3({cx}+({rx}+.30)*cos({angle}),{cy}+({ry}+.30)*sin({angle}),{z})'
cap=f'float3(1.25*cos({angle}),1.25*sin({angle}),.10)'
h=f'({crown} ? lerp(12.,16.,{mix}) : lerp(10.,14.,{mix}))'
w=f'({crown} ? lerp(8.8,11.5,{mix}) : lerp(5.0,7.1,{mix}))'
# In the attached simulation frame, these dot products express world-up in torch space.
up='float3(dot(Engine.Owner.SystemXAxis,float3(0,0,1)),dot(Engine.Owner.SystemYAxis,float3(0,0,1)),dot(Engine.Owner.SystemZAxis,float3(0,0,1)))'
put(system,'Fire','EmitterUpdateScript','SpawnRate','SpawnRate','(Value=17.0)')
assignments(system,'Fire',stage,{
    'Particles.Position':(pos,f'(({crown} ? {cap} : {surface}) + {up}*(.47*{h}))'),
    'Particles.SpriteSize':(v2,f'float2({w},{h})'),
    'Particles.Lifetime':(flt,f'lerp(.88,1.20,{mix})'),
    'Particles.Velocity':(v3,f'{up}*lerp(2.8,5.4,{seed})')
})
setdata('SetRendererData',u.NiagaraExt_RendererData,ref(system,'Fire',renderer=0),{'Material':mat.get_path_name()})
assignments(system,'Smoke',stage,{'Particles.Velocity':(v3,f'{up}*8.0')})
assignments(system,'Sparks',stage,{'Particles.Velocity':(v3,f'{up}*lerp(10.,17.,{seed})+float3(1.3*cos({angle}),1.3*sin({angle}),0)')})
# Bounds allow for the shaft tilting while the sheet centres and small plume rise vertically.
lo,hi=-36,42
box={'min':dict(x=lo,y=lo,z=lo),'max':dict(x=hi,y=hi,z=hi),'isValid':True}
for emitter in ('Fire','Smoke','Sparks'):
    setdata('SetEmitterData',u.NiagaraExt_EmitterData,ref(system,emitter),{'bLocalSpace':True,'CalculateBoundsMode':'Fixed','FixedBounds':box})
system.set_editor_property('fixed_bounds',u.Box(min=u.Vector(lo,lo,lo),max=u.Vector(hi,hi,hi)))
if not u.RainAssetEditor.compile_rain(system,True):raise RuntimeError('Wrapped flame failed to compile')
save(system)
(batch/'fire-saved.json').write_text(json.dumps(dict(asset=system.get_path_name(),material=mat.get_path_name(),source=donor,spawn_rate=17,wrap_fraction=.75,contact_fade_cm=.65,surface_clearance_cm=.30,rings_cm=sections[:3]),indent=2))
