"""Campfire-only flame authoring. No playback, map, screenshot or acceptance test.

Run after read_campfire_flame.py. Shared torches and baked field sources are read-only.
"""
import hashlib
import json
import sys
from pathlib import Path
import unreal as u

ROOT=Path(u.Paths.convert_relative_path_to_full(u.Paths.project_dir())).resolve()
OUT=ROOT/'SourceAssets/Campfire20261012'
DEST='/Game/Building/Campfire20261012'
sys.path.insert(0,str(ROOT/'Tools/Skills'))
from build_fireball_assets import API,LIB,ref,emitters,setdata,put,assignments
from build_fireball_flames import FLOAT,VEC2,VEC3,POSITION,COLOR
from build_fireball_torch_burn import setup_emitter
from build_fireball_slow_burn import smooth

source_report=json.loads((OUT/'flame-source-read.json').read_text(encoding='utf-8'))
TORCH=source_report['system'].split('.')[0]
CREATED=[]

def sha(path):
    return hashlib.sha256((ROOT/'Content'/(path.removeprefix('/Game/')+'.uasset')).read_bytes()).hexdigest()

def own(source,name):
    target=DEST+'/'+name
    if target in {p.get_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()}:
        raise RuntimeError('Unsaved asset already present: '+target)
    result=u.load_asset(target) if u.EditorAssetLibrary.does_asset_exist(target) else u.EditorAssetLibrary.duplicate_asset(source,target)
    if not result:raise RuntimeError('Missing authoring source '+source)
    return result

def save(asset):
    if isinstance(asset,u.NiagaraSystem) and not u.RainAssetEditor.compile_rain(asset):
        raise RuntimeError('Niagara compilation failed: '+asset.get_path_name())
    if not u.EditorLoadingAndSavingUtils.save_packages([asset.get_outermost()],False):
        raise RuntimeError('Package save failed: '+asset.get_path_name())
    CREATED.append(asset.get_path_name())
    print('CAMPFIRE_FLAME_SAVED',asset.get_path_name())

before=sha(TORCH)
core=own('/Game/Skills/Fireball/TorchBurn20260921/M_FireballCohesiveCore','M_CampfireDenseFlame')
fields=next(n for n in LIB.get_material_expressions(core) if isinstance(n,u.MaterialExpressionCustom)
    and n.get_editor_property('description') in ['Fireball cohesive combustion','Campfire cohesive combustion'])
fields.set_editor_property('description','Campfire cohesive combustion')
fields.set_editor_property('code',(OUT/'CampfireBody.hlsl').read_text(encoding='utf-8'))
for node in LIB.get_material_expressions(core):
    if isinstance(node,u.MaterialExpressionScalarParameter) and str(node.get_editor_property('parameter_name'))=='EmissionGain':
        node.set_editor_property('default_value',1.8)
core.set_editor_property('refraction_method',u.RefractionMode.RM_NONE)
core.set_editor_property('allow_front_layer_translucency',False)
errors=LIB.recompile_material(core)
if errors:raise RuntimeError(str(errors))
save(core)

source_mats=[row['material'] for row in source_report['emitters'] if row['name'].startswith('NE_Flame_')]
if len(source_mats)<2:raise RuntimeError('Expected two read-back torch flame materials')
parent=own(u.load_asset(source_mats[0]).get_base_material().get_path_name(),'M_CampfireTongues')
parent.set_editor_property('refraction_method',u.RefractionMode.RM_NONE)
parent.set_editor_property('allow_front_layer_translucency',False)
parent.set_editor_property('shading_model',u.MaterialShadingModel.MSM_UNLIT)
parent.set_editor_property('two_sided',True)
parent.set_editor_property('enable_responsive_aa',True)
if not any(isinstance(n,u.MaterialExpressionEyeAdaptationInverse) for n in LIB.get_material_expressions(parent)):
    old=LIB.get_material_property_input_node(parent,u.MaterialProperty.MP_EMISSIVE_COLOR)
    inverse=LIB.create_material_expression(parent,u.MaterialExpressionEyeAdaptationInverse)
    LIB.connect_material_expressions(old,'',inverse,str(LIB.get_material_expression_input_names(inverse)[0]))
    LIB.connect_material_property(inverse,'',u.MaterialProperty.MP_EMISSIVE_COLOR)
errors=LIB.recompile_material(parent)
if errors:raise RuntimeError(str(errors))
save(parent)
materials=[]
for i,source in enumerate(source_mats[:2],1):
    mat=own(source,'MI_CampfireTongue%02d'%i)
    LIB.set_material_instance_parent(mat,parent)
    for key,value in [('Emissive_Intensity',3.2 if i==1 else 4.0),('DepthFade',3.0),('Noises_OpacityBoost',1.3)]:
        LIB.set_material_instance_scalar_parameter_value(mat,key,value)
    LIB.update_material_instance(mat);save(mat);materials.append(mat)

s=own(TORCH,'NS_CampfireFlame')
for name in emitters(s):API.call_method('RemoveEmitter',(ref(s,name),))
name='CampfireBody'
setup_emitter(s,name,core,0,True)
API.call_method('RemoveModule',(ref(s,name,'EmitterUpdateScript','SpawnRate'),))
API.call_method('RemoveModule',(ref(s,name,'ParticleUpdateScript','ParticleState'),))
API.call_method('AddModule',(ref(s,name,'EmitterUpdateScript'),u.load_asset('/Niagara/Modules/Emitter/SpawnBurst_Instantaneous')))
put(s,name,'EmitterUpdateScript','SpawnBurst_Instantaneous','Spawn Count',
    '(HlslExpression="Engine.Emitter.TotalSpawnedParticles < 2 ? 2 : 0")','/Script/NiagaraEditor.NiagaraExt_StackInputData_HlslExpression')
put(s,name,'EmitterUpdateScript','SpawnBurst_Instantaneous','Spawn Time','(Value=0)')
seed='frac(float(Particles.UniqueID)*.61803399)'
common={
    'Particles.Position':(POSITION,f'float3(lerp(-6,6,{seed}),lerp(7,-7,{seed}),32)'),
    'Particles.Velocity':(VEC3,'float3(0,0,0)'),
    'Particles.SpriteAlignment':(VEC3,'float3(0,0,1)'),
    'Particles.SpriteRotation':(FLOAT,'0'),'Particles.SpriteSize':(VEC2,'float2(58,64)'),
    'Particles.SpriteUVScale':(VEC2,'float2(1,1)'),
    'Particles.SubImageIndex':(FLOAT,'0'),'Particles.Color':(COLOR,'float4(1,1,1,.74)'),
}
assignments(s,name,'ParticleSpawnScript',{'Particles.Lifetime':(FLOAT,'1'),**common})
assignments(s,name,'ParticleUpdateScript',common)
for index,mat in enumerate(materials):
    name='CampfireTongues%02d'%(index+1)
    setup_emitter(s,name,mat,8,True)
    n='Particles.NormalizedAge';variant='frac(float(Particles.UniqueID)*.41421356)'
    phase=f'(6.2831853*{seed}+{index}*2.4)'
    envelope=smooth('0','.10',n)+'*(1-'+smooth('.68','1',n)+')'
    common={
        'Particles.Position':(POSITION,f'float3(cos({phase})*(10+8*{variant}),sin({phase})*(10+8*{variant}),16+{n}*22)'),
        'Particles.Velocity':(VEC3,'float3(0,0,0)'),
        'Particles.SpriteAlignment':(VEC3,f'normalize(float3(.08*cos({phase}),.08*sin({phase}),1))'),
        'Particles.SpriteRotation':(FLOAT,'0'),
        'Particles.SpriteSize':(VEC2,f'float2(24+7*{variant},48+14*{seed})'),
        'Particles.SpriteUVScale':(VEC2,'float2(1,1)'),
        'Particles.SubImageIndex':(FLOAT,'0'),
        'Particles.Color':(COLOR,f'float4(1,.72,.3,.72*{envelope})'),
        'Particles.DynamicMaterialParameter':('/Script/CoreUObject.Vector4f',f'float4(.05+.64*{n},1,1,1)'),
        'Particles.MaterialRandom':(FLOAT,variant),
    }
    assignments(s,name,'ParticleSpawnScript',{'Particles.Lifetime':(FLOAT,f'1.0+.3*{seed}'),**common})
    assignments(s,name,'ParticleUpdateScript',common)
# No heat-distortion or spark renderer remains. Three bounded emitters: two stable body cards
# plus <= 22 simultaneous tongues. Shared scheduler remains eight systems/one light each.
s.set_editor_property('fixed_bounds',u.Box(min=u.Vector(-80,-80,-15),max=u.Vector(80,80,115)))
save(s)
after=sha(TORCH)
if after!=before:raise RuntimeError('Shared torch source changed during authoring')
(OUT/'flame-delivery.json').write_text(json.dumps({
    'system':s.get_path_name(),'assets':CREATED,'source_torch_sha256':before,
    'shared_torch_unchanged':True,'refraction':'disabled in campfire materials; no distortion emitter',
    'sparks':0,'body_particles':2,'tongue_rate_per_second':16,'tongue_max_lifetime':1.3,
    'offline_field':'/Game/Skills/Fireball/FluidCore20260923/T_FireballCombustionFields',
    'asset_compiled_and_saved':True,'runtime_tested':False,'visual_tested':False,
},indent=2),encoding='utf-8')
print('CAMPFIRE_FLAME_AUTHORING_COMPLETE')
