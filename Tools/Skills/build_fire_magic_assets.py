"""Author independent meteor / flame-armor assets. Run bounded stages via MCP.

Existing bronze-torch, Vefects, Epic and fireball assets are read-only sources.
Stages: materials, audio, meteor, lava, armor_aura, armor_weapon, sparks.
"""
import json
import sys
from pathlib import Path
import unreal as u

ROOT=Path(u.Paths.project_dir()).resolve()
sys.path.insert(0,str(ROOT/'Tools/Skills'))
from build_fireball_torch_burn import setup_emitter,save,VECTOR4
from build_fireball_assets import API,LIB,TOOLS,ref,emitters,setdata,put,assignments
from build_fireball_flames import FLOAT,VEC2,VEC3,POSITION,COLOR
from build_fireball_flight import user_parameter
from build_fireball_slow_burn import smooth
from build_fireball_impact_realistic import custom,scalar,layer

DEST='/Game/Skills/FireMagic20260921'
OUT=ROOT/'SourceAssets/FireMagic20260921'

def own(source,name):
    path=DEST+'/'+name
    result=u.load_asset(path) if u.EditorAssetLibrary.does_asset_exist(path) else u.EditorAssetLibrary.duplicate_asset(source,path)
    if not result:raise RuntimeError('Missing source '+source)
    return result

def materials():
    rock=own('/Game/EasyBuildingSystem/Meshes/Environment/Stylized/Organic/SM_SmallRock_001','SM_MeteorRock')
    mat=u.load_asset(DEST+'/M_MeteorRock') or TOOLS.create_asset('M_MeteorRock',DEST,u.Material,u.MaterialFactoryNew())
    LIB.delete_all_material_expressions(mat)
    uv=LIB.create_material_expression(mat,u.MaterialExpressionTextureCoordinate)
    time=LIB.create_material_expression(mat,u.MaterialExpressionTime)
    # Irregular cellular veins reveal a molten interior between rough black crust.
    field=custom(mat,'''
float2 p=UV*7.0;
float2 cell=floor(p), f=frac(p);
float nearest=10.0, second=10.0;
for(int y=-1;y<=1;y++)for(int x=-1;x<=1;x++){
    float2 q=float2(x,y);
    float2 h=frac(sin(float2(dot(cell+q,float2(127.1,311.7)),dot(cell+q,float2(269.5,183.3))))*43758.5453);
    float d=length(q+h-f);
    if(d<nearest){second=nearest;nearest=d;}else second=min(second,d);
}
float crack=1.0-smoothstep(.018,.068,second-nearest);
float crust=.018+.028*saturate(nearest);
return float4(crust.xxx,crack);
''',{'UV':(uv,'')},u.CustomMaterialOutputType.CMOT_FLOAT4)
    base=custom(mat,'return Field.rgb;',{'Field':(field,'')},u.CustomMaterialOutputType.CMOT_FLOAT3)
    emission=custom(mat,'return float3(6.5,1.05,.055)*Field.a*(.88+.12*sin(Time*3.7));',{'Field':(field,''),'Time':(time,'')},u.CustomMaterialOutputType.CMOT_FLOAT3)
    LIB.connect_material_property(base,'',u.MaterialProperty.MP_BASE_COLOR)
    LIB.connect_material_property(emission,'',u.MaterialProperty.MP_EMISSIVE_COLOR)
    LIB.connect_material_property(scalar(mat,'Roughness',.88),'',u.MaterialProperty.MP_ROUGHNESS)
    normal=u.load_asset('/Game/EasyBuildingSystem/Textures/Environment/Stylized/Tiles/T_Tile_Rock_Cracked_001_N')
    if normal:
        node=LIB.create_material_expression(mat,u.MaterialExpressionTextureSample)
        node.set_editor_property('texture',normal);node.set_editor_property('sampler_type',u.MaterialSamplerType.SAMPLERTYPE_NORMAL)
        LIB.connect_material_property(node,'RGB',u.MaterialProperty.MP_NORMAL)
    errors=LIB.recompile_material(mat)
    if errors:raise RuntimeError(str(errors))
    save(mat)
    for index in range(len(rock.get_editor_property('static_materials'))):rock.set_material(index,mat)
    save(rock)
    flame=own('/Game/Skills/Fireball/TorchBurn20260921/MI_FireballTorch01','MI_FireMagicTongue')
    LIB.set_material_instance_scalar_parameter_value(flame,'Emissive_Intensity',4.4)
    LIB.set_material_instance_scalar_parameter_value(flame,'DepthFade',8.)
    LIB.update_material_instance(flame);save(flame)

def audio():
    attenuation=own('/Game/Skills/Fireball/ImpactRealistic20260914/ATT_FireballImpact','ATT_FireMagic')
    settings=attenuation.get_editor_property('attenuation')
    settings.set_editor_property('attenuation_shape_extents',u.Vector(110,0,0));settings.set_editor_property('falloff_distance',1900.)
    attenuation.set_editor_property('attenuation',settings);save(attenuation)
    for name in ['S_FireMagicCast','S_MeteorLand','S_MeteorBurn']:
        task=u.AssetImportTask();task.filename=str(OUT/(name+'.wav'));task.destination_path=DEST;task.destination_name=name
        task.automated=True;task.replace_existing=True;task.save=False
        TOOLS.import_asset_tasks([task]);wave=u.load_asset(DEST+'/'+name)
        if not isinstance(wave,u.SoundWave):raise RuntimeError('Import failed '+name)
        wave.set_editor_property('looping',name=='S_MeteorBurn')
        wave.set_editor_property('loading_behavior',u.SoundWaveLoadingBehavior.FORCE_INLINE)
        wave.set_editor_property('attenuation_settings',attenuation)
        wave.set_editor_property('volume',.42 if name=='S_MeteorBurn' else .8)
        save(wave)

def flames(kind):
    names={'meteor':'NS_MeteorFire','lava':'NS_MeteorLava','armor_aura':'NS_FlameArmorAura','armor_weapon':'NS_FlameArmorWeapon'}
    system=own('/Game/Props/RomanColumn20260915/NS_TorchFlame',names[kind])
    for name in emitters(system):API.call_method('RemoveEmitter',(ref(system,name),))
    for name,typ in [('Radius',FLOAT),('Fade',FLOAT),('WeaponEnd',VEC3)]:user_parameter(system,name,typ)
    emitter='FireMagicTongues'
    rates={'meteor':42,'lava':165,'armor_aura':38,'armor_weapon':40}
    setup_emitter(system,emitter,u.load_asset(DEST+'/MI_FireMagicTongue'),rates[kind],True)
    seed='frac(float(Particles.UniqueID)*.61803398875)';v='frac(float(Particles.UniqueID)*.41421356237)'
    theta=f'({v}*6.2831853)';n='Particles.NormalizedAge'
    fade=smooth('0','.10',n)+'*(1-'+smooth('.52','1',n)+')'
    if kind=='meteor':
        # Local positions are scaled with the component; sprite sizes require explicit scale.
        r=f'(12+5*{seed})';z=f'(-3+{n}*26)';size=f'float2(20+7*{seed},38+14*{v})*Engine.Owner.Scale.x'
        pos=f'float3(cos({theta})*{r},sin({theta})*{r},{z})';life='.45+.20*'+seed;alpha='.65';external='1'
    elif kind=='lava':
        r=f'(sqrt({seed})*User.Radius*.92)';z=f'(7+{n}*32)'
        pos=f'float3(cos({theta})*{r},sin({theta})*{r},{z})';size=f'float2(30+18*{seed},54+32*{v})'
        life='.6+.3*'+v;alpha='.67';external='saturate(User.Fade)'
    elif kind=='armor_aura':
        r=f'(User.Radius*(.88+.12*{seed}))';z=f'(3+{n}*9)'
        pos=f'float3(cos({theta})*{r},sin({theta})*{r},{z})';size=f'float2(10+5*{seed},20+9*{v})'
        life='.38+.18*'+seed;alpha='.46';external='saturate(User.Fade)'
    else:
        pos=f'User.WeaponEnd*(.08+.90*{seed})+float3(cos({theta})*2,sin({theta})*2,2+{n}*8)'
        size=f'float2(5+3*{seed},10+7*{v})';life='.24+.16*'+v;alpha='.48';external='saturate(User.Fade)'
    common={
        'Particles.Position':(POSITION,pos),'Particles.Velocity':(VEC3,'float3(0,0,0)'),
        'Particles.SpriteAlignment':(VEC3,'float3(0,0,1)'),'Particles.SpriteRotation':(FLOAT,'0'),
        'Particles.SpriteSize':(VEC2,size),'Particles.SpriteUVScale':(VEC2,'float2(1,1)'),
        'Particles.SubImageIndex':(FLOAT,'0'),
        'Particles.Color':(COLOR,f'float4(1,lerp(.40,.09,{n}),.022,{alpha}*{fade}*{external})'),
        'Particles.DynamicMaterialParameter':(VECTOR4,f'float4(.04+.80*{n},1,1,1)'),
        'Particles.MaterialRandom':(FLOAT,v)}
    assignments(system,emitter,'ParticleSpawnScript',{'Particles.Lifetime':(FLOAT,life),**common})
    assignments(system,emitter,'ParticleUpdateScript',common)
    system.set_editor_property('fixed_bounds',u.Box(min=u.Vector(-650,-650,-120),max=u.Vector(650,650,650)))
    u.EditorAssetLibrary.set_metadata_tag(system,'FireMagic.Authoring',kind+'; local torch erosion; actor owns lifetime; User.Fade and User.Radius / WeaponEnd')
    save(system)

def sparks():
    system=own('/Game/Skills/Fireball/ImpactRealistic20260914/NS_FireballImpactRealistic','NS_FireMagicSparks')
    # Keep the established one-shot ember emitter and its lifecycle / renderer binding.
    for name in emitters(system):
        if name!='ShortEmbers':API.call_method('RemoveEmitter',(ref(system,name),))
    name='ShortEmbers'
    put(system,name,'EmitterUpdateScript','SpawnBurst_Instantaneous','Spawn Count','(Value=7)','/Script/Niagara.NiagaraInt32')
    put(system,name,'EmitterUpdateScript','SpawnBurst_Instantaneous','Spawn Time','(Value=0)')
    seed='frac(float(Particles.UniqueID)*.61803398875)';v='frac(float(Particles.UniqueID)*.41421356237)'
    a='Particles.Age';n='Particles.NormalizedAge'
    direction=f'normalize(float3(cos({v}*6.2831853),sin({v}*6.2831853),.25+{seed}))'
    common={'Particles.Position':(POSITION,f'{direction}*{a}*65-float3(0,0,{a}*{a}*70)'),
        'Particles.SpriteAlignment':(VEC3,direction),'Particles.SpriteSize':(VEC2,f'float2(1,3.5)*(1-.65*{n})'),
        'Particles.Color':(COLOR,f'float4(1,.6,.25,1-{n})')}
    assignments(system,name,'ParticleSpawnScript',{'Particles.Lifetime':(FLOAT,'.22+.15*'+seed),**common})
    assignments(system,name,'ParticleUpdateScript',common)
    save(system)

def run(stage):
    u.EditorAssetLibrary.make_directory(DEST)
    if stage=='materials':materials()
    elif stage=='audio':audio()
    elif stage=='sparks':sparks()
    else:flames(stage)
    (OUT/(stage+'-authored.json')).write_text(json.dumps({'stage':stage,'destination':DEST,'status':'authored, compiled where required and saved','tested':False},indent=2),encoding='utf-8')
    print('FIRE_MAGIC_STAGE_COMPLETE',stage)
