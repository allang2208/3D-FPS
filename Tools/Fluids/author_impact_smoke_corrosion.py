"""Incremental fire impact smoke / venom mist / corrosive residue authoring.

Preserves accepted combustion emitters, damage footprints, water and RT settings.
Run via the existing editor mutex bridge, or a rendering-enabled Python commandlet.
No world/PIE, preview, screenshot, gameplay test or acceptance is performed.
"""
import json
import shutil
import sys
from pathlib import Path
import unreal as u

ROOT=Path(u.Paths.project_dir())
OUT=ROOT/'SourceAssets/ImpactSmokeCorrosion20260924'
DEST='/Game/Fluids/ImpactSmokeCorrosion20260924'
VENOM='/Game/Monsters/PoisonMaggot/VenomLiquid20260915'
ATLAS='/Game/Weapons/GunplayFX/T_MuzzleSmokeMantaflowV14'
SYSTEMS=[('/Game/Skills/Fireball/ImpactRealistic20260914/NS_FireballImpactRealistic',False),
         ('/Game/Skills/FireMagic20260921/RealisticV5/NS_MeteorNaturalImpact',True)]
POOLS=['/Game/Monsters/FatZombieMeshy/Pus/M_FatZombie_Pus',
       '/Game/Dungeons/SlimeSheet20260922/Materials/M_PusSingleImpact',
       '/Game/Dungeons/CombatExpansion20260922/Materials/M_PusFluidV2',
       '/Game/Dungeons/Routes20260922/Materials/M_RoutePusImpact',
       '/Game/Dungeons/Routes20260922/Materials/M_RoutePusChannel']
sys.path[:0]=[str(ROOT/'Tools/Skills'),str(ROOT/'Tools/Fluids')]
from build_fireball_assets import API,ref,emitters,setdata,put,assignments
from build_fireball_flames import trim,FLOAT,VEC2,VEC3,POSITION,COLOR
from build_fireball_slow_burn import smooth
from build_fireball_flight import user_parameter
from fluid_contact_nodes import contact_nodes,clear_contact_tags
from author_river_pilot import node,wire,prop,scalar,custom

L=u.MaterialEditingLibrary;E=u.EditorAssetLibrary
TAG='ImpactSmokeCorrosion20260924'
SAVED=[]

def save(asset):
    if isinstance(asset,u.Material):
        errors=L.recompile_material(asset)
        if errors:raise RuntimeError(asset.get_path_name()+': '+str(errors))
    if isinstance(asset,u.NiagaraSystem) and not u.RainAssetEditor.compile_rain(asset):
        raise RuntimeError('Niagara compilation failed '+asset.get_path_name())
    if not E.save_loaded_asset(asset,False):raise RuntimeError('Cannot save '+asset.get_path_name())
    SAVED.append(asset.get_path_name())
    u.log('IMPACT_CORROSION_SAVED '+asset.get_path_name())

def source(name):return (OUT/(name+'.hlsl')).read_text(encoding='utf8')
def constant(m,value):
    n=node(m,u.MaterialExpressionConstant);n.set_editor_property('r',value);return n
def material(path,decal=False,instanced=False):
    m=u.load_asset(path) if E.does_asset_exist(path) else u.AssetToolsHelpers.get_asset_tools().create_asset(
        path.rsplit('/',1)[1],path.rsplit('/',1)[0],u.Material,u.MaterialFactoryNew())
    if not m:raise RuntimeError('Cannot create '+path)
    # ConstructorHelpers-rooted venom assets also root their old expressions.
    # DeleteAllMaterialExpressions asserts while marking those nodes as garbage.
    # Replace the output graph and retain disconnected rooted nodes instead.
    m.set_editor_property('blend_mode',u.BlendMode.BLEND_TRANSLUCENT)
    m.set_editor_property('shading_model',u.MaterialShadingModel.MSM_DEFAULT_LIT)
    m.set_editor_property('material_domain',u.MaterialDomain.MD_DEFERRED_DECAL if decal else u.MaterialDomain.MD_SURFACE)
    m.set_editor_property('two_sided',True)
    m.set_editor_property('disable_depth_test',False)
    m.set_editor_property('output_translucent_velocity',False)
    m.set_editor_property('is_translucency_velocity_from_depth',False)
    # Refraction stays unconnected, including the explicit Substrate surface.
    if not decal:
        m.set_editor_property('allow_front_layer_translucency',False)
        m.set_editor_property('translucency_lighting_mode',u.TranslucencyLightingMode.TLM_VOLUMETRIC_NON_DIRECTIONAL)
        m.set_editor_property('translucency_pass',u.MaterialTranslucencyPass.MTP_BEFORE_DOF)
        L.set_base_material_usage(m,u.MaterialUsage.MATUSAGE_INSTANCED_STATIC_MESHES if instanced else u.MaterialUsage.MATUSAGE_NIAGARA_SPRITES,True)
    return m

def surface(m,inputs,decal=False):
    slab=node(m,u.MaterialExpressionSubstrateShadingModels)
    slab.set_editor_property('shading_model_override',u.MaterialShadingModel.MSM_DEFAULT_LIT)
    names={'BASE_COLOR':'BaseColor','ROUGHNESS':'Roughness','SPECULAR':'Specular','OPACITY':'Opacity','NORMAL':'Normal'}
    for name,value in inputs.items():prop(m,value,name);wire(value,slab,names[name])
    if decal:
        convert=node(m,u.MaterialExpressionSubstrateConvertToDecal)
        wire(slab,convert,str(L.get_material_expression_input_names(convert)[0]));slab=convert
    prop(m,slab,'FRONT_MATERIAL')

def instance_data(m,index,default=0):
    n=node(m,u.MaterialExpressionPerInstanceCustomData)
    n.set_editor_property('data_index',index);n.set_editor_property('const_default_value',default)
    p=node(m,u.MaterialExpressionVertexInterpolator)
    wire(n,p,str(L.get_material_expression_input_names(p)[0]));return p

def smoke_material(venom=False):
    m=material(VENOM+'/M_VenomMist' if venom else DEST+'/M_RollingImpactSmoke',instanced=venom)
    density=next((n for n in L.get_material_expressions(m) if isinstance(n,u.MaterialExpressionCustom)
                  and n.get_editor_property('description')==TAG+' Density'),None)
    if density:
        density.set_editor_property('code',source('RollingSmoke'));save(m);return m
    uv=node(m,u.MaterialExpressionTextureCoordinate)
    tex=node(m,u.MaterialExpressionTextureObjectParameter)
    tex.set_editor_property('parameter_name','DensityAtlas')
    tex.set_editor_property('texture',u.load_asset(ATLAS))
    tex.set_editor_property('sampler_type',u.MaterialSamplerType.SAMPLERTYPE_MASKS)
    if venom:
        alpha=instance_data(m,0);seed=instance_data(m,1);age=instance_data(m,2)
        tint=custom(m,'return lerp(float3(.095,.12,.027),float3(.18,.205,.055),Seed);',{'Seed':seed},3)
    else:
        color=node(m,u.MaterialExpressionParticleColor)
        dynamic=node(m,u.MaterialExpressionDynamicParameter)
        dynamic.set_editor_property('param_names',['SmokeSeed','UnusedY','UnusedZ','UnusedW'])
        age=node(m,u.MaterialExpressionParticleRelativeTime);seed=dynamic;alpha=(color,'A')
        tint=custom(m,'return Tint;',{'Tint':(color,'RGB')},3)
    density=custom(m,source('RollingSmoke'),{'UV':uv,'Atlas':tex,'Age':age,'Seed':seed,'Alpha':alpha},1,TAG+' Density')
    fade=node(m,u.MaterialExpressionDepthFade);fade.set_editor_property('fade_distance_default',5. if venom else 18.)
    wire(density,fade,str(L.get_material_expression_input_names(fade)[0]))
    surface(m,{'BASE_COLOR':tint,'OPACITY':fade,'ROUGHNESS':constant(m,1),'SPECULAR':constant(m,0)})
    save(m);return m

def impact_smoke(system,meteor=False,mat=None):
    mat=mat or u.load_asset(DEST+'/M_RollingImpactSmoke') or smoke_material()
    for name,typ in [('Wind',VEC3),('DetailReduction',FLOAT),('WetImpact',FLOAT)]:user_parameter(system,name,typ)
    names=['ImpactRollingSmoke','ImpactGroundSmoke','ImpactLingeringSmoke']
    for name in emitters(system):
        if name in names+['ImpactSmoke','CoolingWisps']:
            API.call_method('RemoveEmitter',(ref(system,name),))
    lifecycle_source=u.load_asset('/Game/NiagaraExamples/FX_Explosions/NS_Explosion_Small')
    lifecycle={k:u.RainAssetEditor.read_input(lifecycle_source,'Explosion','EmitterUpdateScript','EmitterState',k)
               for k in ['Life Cycle Mode','Loop Behavior']}
    lifecycle['Life Cycle Mode']=lifecycle['Life Cycle Mode'].replace('NewEnumerator0','NewEnumerator1').replace('"System"','"Self"')
    lifecycle['Loop Behavior']=lifecycle['Loop Behavior'].replace('NewEnumerator0','NewEnumerator1').replace('"Infinite"','"Once"')
    phase='frac(sin(float(Engine.System.RandomSeed)*.0001)*43758.5453)'
    seed=f'frac(float(Particles.UniqueID)*.61803398875+{phase})'
    var=f'frac(float(Particles.UniqueID)*.41421356237+{phase}*.731)'
    a='Particles.Age';n='Particles.NormalizedAge';theta=f'({var}*6.2831853)'
    direction=f'float3(cos({theta}),sin({theta}),0)'
    distance='Engine.Owner.LODDistance'
    distance_fade=f'saturate((8500-{distance})/2500)'
    for index,(name,count,delay) in enumerate(zip(names,[5,4,3] if meteor else [4,3,2],[.10,.075,.40])):
        clear_contact_tags(system,name)
        API.call_method('AddEmitter',(system,u.load_asset('/Game/NiagaraExamples/FX_Explosions/Emitters/NE_Core'),name))
        trim(system,name,{'EmitterUpdateScript':['EmitterState'],'ParticleSpawnScript':['InitializeParticle'],'ParticleUpdateScript':['ParticleState']})
        for script in ['ParticleSpawnScript','ParticleUpdateScript']:
            E.remove_metadata_tag(system,'Fireball.Assignments.'+name+'.'+script)
        setdata('SetEmitterData',u.NiagaraExt_EmitterData,ref(system,name),{
            'bLocalSpace':True,'SimTarget':'CPUSim','bInterpolatedSpawning':False})
        setdata('SetRendererData',u.NiagaraExt_RendererData,ref(system,name,renderer=0),{
            'Material':mat.get_path_name(),'MaterialUserParamBinding':{'Parameter':{'Name':'None'}},
            'SubImageSize':{'X':1,'Y':1},'bSubImageBlend':False,
            'PivotInUVSpace':{'X':.5,'Y':.5},'Alignment':'Unaligned','FacingMode':'FaceCamera',
            'bCastShadows':False,'CutoutTexture':None,'bUseMaterialCutoutTexture':False,
            'bEnableCameraDistanceCulling':True,'MinCameraDistance':0,'MaxCameraDistance':8500})
        for key,value in lifecycle.items():put(system,name,'EmitterUpdateScript','EmitterState',key,value,'/Script/NiagaraEditor.NiagaraExt_StackInputData_Enum')
        put(system,name,'EmitterUpdateScript','EmitterState','Loop Duration','(Value=3.5)')
        API.call_method('AddModule',(ref(system,name,'EmitterUpdateScript'),u.load_asset('/Niagara/Modules/Emitter/SpawnBurst_Instantaneous')))
        count_expr=f'({distance}<3500?{count}:({distance}<8500?{max(1,count//2)}:0))'
        count_expr=f'floor(({count_expr})*(1-saturate(User.DetailReduction))+.5)'
        if index==1:count_expr=f'(User.SurfaceHit>.5 && User.LocalUp.z>.5 && User.WetImpact<.5?{count_expr}:0)'
        put(system,name,'EmitterUpdateScript','SpawnBurst_Instantaneous','Spawn Count','(HlslExpression="'+count_expr+'")','/Script/NiagaraEditor.NiagaraExt_StackInputData_HlslExpression')
        put(system,name,'EmitterUpdateScript','SpawnBurst_Instantaneous','Spawn Time',f'(Value={delay})')
        if index==0:
            pos=f'{direction}*(18+(60+25*{seed})*(1-exp(-{a}*2.6)))+User.LocalUp*(15+{a}*(32+18*{var}))+float3(0,0,8)'
            life=f'1.45+.40*{seed}'
            size=f'float2(125,140)*(.68+.65*{n})*(.85+.25*{var})'
            opacity='.44';tint='float3(.095,.088,.078)'
        elif index==1:
            pos=f'{direction}*(20+(100+30*{seed})*(1-exp(-{a}*3.1)))+float3(0,0,9+{a}*9)'
            life=f'.80+.35*{seed}'
            size=f'float2(122,44)*(.65+.8*{n})'
            opacity='.28';tint='float3(.12,.105,.087)'
        else:
            pos=f'{direction}*(22+{seed}*45+{a}*10)+User.LocalUp*(38+{a}*(34+18*{var}))+float3(0,0,8)'
            life=f'2.05+.60*{seed}'
            size=f'float2(130,160)*(.62+.9*{n})'
            opacity='.22';tint='float3(.13,.125,.115)'
        position=f'float3(({pos}).xy,lerp(({pos}).z,max(6,({pos}).z),saturate(User.SurfaceHit)))+User.Wind*({a}-.55*(1-exp(-{a}/.55)))'
        envelope=smooth('0','.12',n)+'*(1-'+smooth('.42','1',n)+')'
        common={'Particles.Position':(POSITION,position),'Particles.Velocity':(VEC3,'float3(0,0,0)'),
            'Particles.SpriteSize':(VEC2,f'({size})*(1+max(0,User.ImpactGrowth))*'+('1.25' if meteor else '1')),
            'Particles.SpriteRotation':(FLOAT,'0' if index==1 else f'({seed}-.5)*.6+{a}*({var}-.5)*.12'),
            'Particles.SpriteUVScale':(VEC2,'float2(1,1)'),
            'Particles.Color':(COLOR,f'float4(lerp({tint},float3(.44,.47,.48),saturate(User.WetImpact)),{opacity}*{envelope}*{distance_fade})'),
            'Particles.DynamicMaterialParameter':('/Script/CoreUObject.Vector4f',f'float4({seed},0,0,0)')}
        assignments(system,name,'ParticleSpawnScript',{'Particles.Lifetime':(FLOAT,life),**common})
        assignments(system,name,'ParticleUpdateScript',common)
        contact_nodes(system,name)
    E.set_metadata_tag(system,TAG,'Three bounded smoke layers; combustion unchanged')
    save(system)

def wet_film():
    m=material(VENOM+'/M_VenomWetFilm',decal=True)
    owned=next((n for n in L.get_material_expressions(m) if isinstance(n,u.MaterialExpressionCustom)
                and n.get_editor_property('description')==TAG+' Wet film'),None)
    if owned:
        owned.set_editor_property('code',source('WetFilm'));save(m);return m
    uv=node(m,u.MaterialExpressionTextureCoordinate);clock=node(m,u.MaterialExpressionTime)
    life=node(m,u.MaterialExpressionDecalLifetimeOpacity)
    field=custom(m,source('WetFilm'),{'UV':uv,'Clock':clock,'Life':life,
        'Seed':scalar(m,'ImpactSeed',.5),'ImpactTime':scalar(m,'ImpactTime',0)},4,TAG+' Wet film')
    alpha=custom(m,'return F.x;',{'F':field})
    tint=custom(m,'float3 c=lerp(float3(.017,.028,.003),float3(.065,.087,.010),F.y); return lerp(c,float3(.13,.14,.035),F.z*.25);',{'F':field},3)
    rough=custom(m,'return lerp(.12+.08*F.y+.12*F.z,.65,F.w);',{'F':field})
    surface(m,{'BASE_COLOR':tint,'OPACITY':alpha,'ROUGHNESS':rough,'SPECULAR':constant(m,.58)},decal=True)
    save(m);return m

def pool_surface(m):
    # Refresh owned field code on rerun; never stack multiple augmentation graphs.
    owned=[n for n in L.get_material_expressions(m) if isinstance(n,u.MaterialExpressionCustom)
           and n.get_editor_property('description')==TAG+' Pool field']
    if owned:
        owned[0].set_editor_property('code',source('CorrosionSurface'));save(m);return
    originals={name:(L.get_material_property_input_node(m,getattr(u.MaterialProperty,'MP_'+name)),
                     L.get_material_property_input_node_output_name(m,getattr(u.MaterialProperty,'MP_'+name)))
               for name in ['BASE_COLOR','NORMAL','ROUGHNESS']}
    if any(value[0] is None for value in originals.values()):raise RuntimeError('Incomplete pool graph '+m.get_path_name())
    def parameter(name,default):
        return next((n for n in L.get_material_expressions(m) if isinstance(n,u.MaterialExpressionScalarParameter)
                     and str(n.get_editor_property('parameter_name'))==name),None) or scalar(m,name,default)
    field=custom(m,source('CorrosionSurface'),{'UV':node(m,u.MaterialExpressionTextureCoordinate),
        'Clock':node(m,u.MaterialExpressionTime),'Dryness':parameter('Dryness',0),
        'Variation':parameter('Variation',.5)},4,TAG+' Pool field')
    color=custom(m,'return max(0,Base*(1+F.w*.065)+float3(.08,.073,.013)*F.z*.32);',{'Base':originals['BASE_COLOR'],'F':field},3,TAG+' Pool color')
    normal=custom(m,'return normalize(N+float3(F.xy,0));',{'N':originals['NORMAL'],'F':field},3,TAG+' Pool normal')
    rough=custom(m,'return clamp(R+F.z*.07-F.w*.012,.055,1);',{'R':originals['ROUGHNESS'],'F':field},1,TAG+' Pool roughness')
    for name,value in [('BASE_COLOR',color),('NORMAL',normal),('ROUGHNESS',rough)]:prop(m,value,name)
    # Also update explicit Substrate slabs if this installed parent uses one.
    for n in L.get_material_expressions(m):
        if isinstance(n,u.MaterialExpressionSubstrateShadingModels):
            wire(color,n,'BaseColor');wire(normal,n,'Normal');wire(rough,n,'Roughness')
    E.set_metadata_tag(m,TAG,'Internal motion only; opacity, vertex arrival, WPO and damage footprint preserved')
    save(m)

def main():
    OUT.mkdir(parents=True,exist_ok=True)
    if '-run=pythonscript' not in u.SystemLibrary.get_command_line().lower():
        if u.get_editor_subsystem(u.UnrealEditorSubsystem).get_game_world():raise RuntimeError('Play is running; preserve it')
    targets=[p for p,_ in SYSTEMS]+POOLS+[VENOM+'/M_VenomMist',VENOM+'/M_VenomWetFilm',DEST+'/M_RollingImpactSmoke']
    dirty={str(p.get_path_name()) for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()}
    conflict=dirty.intersection(targets)
    if conflict:raise RuntimeError('Preserve unsaved target packages: '+str(sorted(conflict)))
    for path in targets:
        disk=ROOT/'Content'/(path.removeprefix('/Game/')+'.uasset')
        backup=OUT/'Backup'/disk.relative_to(ROOT/'Content')
        if disk.exists() and not backup.exists():backup.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(disk,backup)
    E.make_directory(DEST)
    mat=smoke_material()
    for path,meteor in SYSTEMS:impact_smoke(u.load_asset(path),meteor,mat)
    smoke_material(True);wet_film()
    for path in POOLS:pool_surface(u.load_asset(path))
    # Finish material shader compilation as part of asset authoring, not a test.
    materials=[u.load_asset(p) for p in SAVED if isinstance(u.load_asset(p),u.Material)]
    if not u.PoisonMaggotMonster.compile_material_assets(materials):raise RuntimeError('Shader compilation failed')
    for mat in materials:E.save_loaded_asset(mat,False)
    (OUT/'assets-saved.json').write_text(json.dumps({'saved':SAVED,'source_density':ATLAS,
        'near_fireball_smoke':9,'near_meteor_smoke':12,'reduced_counts_distance_cm':3500,
        'smoke_fade_cm':[6000,8500],'venom_pool_capacity':{'drops':192,'mist':48,'marks':40},
        'status':'Assets authored, compiled and saved. Native build recorded separately. Not game/visually tested.'},indent=2),encoding='utf8')
    print('IMPACT_SMOKE_CORROSION_ASSETS_SAVED',len(SAVED))

if __name__=='__main__':main()
