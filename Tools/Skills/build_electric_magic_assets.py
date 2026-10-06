"""Author and save the two electric spells in /Game/Skills/ElectricMagic.

Background Python commandlet or the serialized existing editor bridge only.
Owned cloud/spline sources remain read-only. No play, preview or render.
"""
import json
import sys
from pathlib import Path
import unreal as u
ROOT=Path(u.Paths.project_dir())
sys.path.insert(0,str(ROOT/'Tools/Skills'))
from build_fireball_assets import API,LIB,TOOLS,ref,emitters,setdata,put,assignments,save,CREATED
from build_fireball_flames import trim,FLOAT,VEC2,VEC3,POSITION,COLOR
from build_fireball_flight import user_parameter,expression
from build_blizzard_assets import custom
from build_blizzard_storm_cloud import layer

DEST='/Game/Skills/ElectricMagic'
EAL=u.EditorAssetLibrary
TEMPLATE='/Game/NiagaraExamples/FX_Explosions/NS_Explosion_Small'
ENUM='/Script/NiagaraEditor.NiagaraExt_StackInputData_Enum'
SEED='frac(float(Particles.UniqueID)*.618033989)'
SEED2='frac(float(Particles.UniqueID)*.754877666)'
SEED3='frac(float(Particles.UniqueID)*.569840296)'

def own(source,name):
    path=DEST+'/'+name
    obj=u.load_asset(path) if EAL.does_asset_exist(path) else EAL.duplicate_asset(source,path)
    if not obj:raise RuntimeError('Missing installed electric authoring source: '+source)
    return obj

def shape_material(name,filament=False,ring=False):
    path=DEST+'/'+name
    m=u.load_asset(path) if EAL.does_asset_exist(path) else TOOLS.create_asset(name,DEST,u.Material,u.MaterialFactoryNew())
    LIB.delete_all_material_expressions(m)
    m.set_editor_property('blend_mode',u.BlendMode.BLEND_ADDITIVE)
    m.set_editor_property('shading_model',u.MaterialShadingModel.MSM_UNLIT)
    m.set_editor_property('two_sided',True)
    m.set_editor_property('disable_depth_test',False)
    LIB.set_material_usage(m,u.MaterialUsage.MATUSAGE_NIAGARA_SPRITES)
    uv=LIB.create_material_expression(m,u.MaterialExpressionTextureCoordinate)
    particle=LIB.create_material_expression(m,u.MaterialExpressionParticleColor)
    code=('float y=.5+.042*sin(UV.x*17)+.025*sin(UV.x*43);return exp(-abs(UV.y-y)*110)*saturate(UV.x*12)*saturate((1-UV.x)*12);' if filament else
          'float r=length((UV-.5)*2);return exp(-abs(r-.72)*75)*saturate((1-r)*6);' if ring else
          'float r=length((UV-.5)*2);return exp(-r*r*13)*saturate((1-r)*5);')
    shape=custom(m,code,{'UV':(uv,'')})
    alpha=LIB.create_material_expression(m,u.MaterialExpressionMultiply)
    LIB.connect_material_expressions(shape,'',alpha,'A');LIB.connect_material_expressions(particle,'A',alpha,'B')
    gain=LIB.create_material_expression(m,u.MaterialExpressionConstant);gain.set_editor_property('r',14 if filament else 9)
    light=LIB.create_material_expression(m,u.MaterialExpressionMultiply)
    LIB.connect_material_expressions(particle,'RGB',light,'A');LIB.connect_material_expressions(gain,'',light,'B')
    LIB.connect_material_property(light,'',u.MaterialProperty.MP_EMISSIVE_COLOR)
    LIB.connect_material_property(alpha,'',u.MaterialProperty.MP_OPACITY)
    errors=LIB.recompile_material(m)
    if errors:raise RuntimeError('Electric material compilation: '+str(errors))
    save(m);return m

def lifecycle(continuous=False):
    source=u.load_asset(TEMPLATE)
    result={key:u.RainAssetEditor.read_input(source,'Explosion','EmitterUpdateScript','EmitterState',key) for key in ('Life Cycle Mode','Loop Behavior')}
    result['Life Cycle Mode']=result['Life Cycle Mode'].replace('NewEnumerator0','NewEnumerator1').replace('"System"','"Self"')
    if not continuous:
        result['Loop Behavior']=result['Loop Behavior'].replace('NewEnumerator0','NewEnumerator1').replace('"Infinite"','"Once"')
    return result

def empty(name):
    system=own(TEMPLATE,name)
    for emitter in emitters(system):
        API.call_method('RemoveEmitter',(ref(system,emitter),))
        for stage in ('ParticleSpawnScript','ParticleUpdateScript'):
            EAL.remove_metadata_tag(system,'Fireball.Assignments.'+emitter+'.'+stage)
    return system

def sprite(system,name,material,rate=None,burst=None,life=.7,position='float3(0,0,0)',size='float2(8,8)',color='float4(.35,.6,1,1)',velocity=None,rotation='0',loop_seconds='1',continuous=False):
    API.call_method('AddEmitter',(system,u.load_asset('/Game/NiagaraExamples/FX_Explosions/Emitters/NE_Core'),name))
    trim(system,name,{'EmitterUpdateScript':['EmitterState'],'ParticleSpawnScript':['InitializeParticle'],'ParticleUpdateScript':['ParticleState']})
    setdata('SetEmitterData',u.NiagaraExt_EmitterData,ref(system,name),{'bLocalSpace':True,'SimTarget':'CPUSim','bInterpolatedSpawning':False})
    setdata('SetRendererData',u.NiagaraExt_RendererData,ref(system,name,renderer=0),{
        'Material':material.get_path_name(),'MaterialUserParamBinding':{'Parameter':{'Name':'None'}},'SubImageSize':{'X':1,'Y':1},'bSubImageBlend':False,
        'Alignment':'Unaligned','FacingMode':'FaceCamera','SortMode':'ViewDepth','bCastShadows':False,'CutoutTexture':None,'bUseMaterialCutoutTexture':False,'MotionVectorSetting':'Disable'})
    for key,value in lifecycle(continuous).items():put(system,name,'EmitterUpdateScript','EmitterState',key,value,ENUM)
    expression(system,name,'EmitterUpdateScript','EmitterState','Loop Duration',loop_seconds)
    spawn='SpawnRate' if rate is not None else 'SpawnBurst_Instantaneous'
    API.call_method('AddModule',(ref(system,name,'EmitterUpdateScript'),u.load_asset('/Niagara/Modules/Emitter/'+spawn)))
    expression(system,name,'EmitterUpdateScript',spawn,'SpawnRate' if rate is not None else 'Spawn Count',str(rate if rate is not None else burst))
    if burst is not None:put(system,name,'EmitterUpdateScript',spawn,'Spawn Time','(Value=0)')
    assignments(system,name,'ParticleSpawnScript',{'Particles.Lifetime':(FLOAT,str(life)),'Particles.Position':(POSITION,position),'Particles.SpriteSize':(VEC2,size),'Particles.Color':(COLOR,color),'Particles.SpriteRotation':(FLOAT,rotation),'Particles.SubImageIndex':(FLOAT,'0')})
    moving=position if velocity is None else f'Particles.Initial.Position+({velocity})*Particles.Age'
    # Keep all positions and sizes analytic; no force solver or particle collision.
    assignments(system,name,'ParticleUpdateScript',{'Particles.Position':(POSITION,moving),'Particles.SpriteSize':(VEC2,size),'Particles.Color':(COLOR,f'({color})*float4(1,1,1,saturate(Particles.NormalizedAge*12)*saturate((1-Particles.NormalizedAge)*3))'),'Particles.SubImageIndex':(FLOAT,'0')})

def cloud(filament,spark):
    system=empty('NS_StormDomainCloud')
    for name,typ in [('CurrentPosition',POSITION),('Side',VEC3),('Up',VEC3),('SurfaceNormal',VEC3),('Wind',VEC3),('RadiusX',FLOAT),('RadiusY',FLOAT),('CloudHeight',FLOAT),('StormDuration',FLOAT),('CloudEmission',FLOAT),('Strength',FLOAT),('DetailReduction',FLOAT)]:user_parameter(system,name,typ)
    material=u.load_asset('/Game/Skills/Blizzard/StormV2/MI_BlizzardStormCloud')
    if not material:raise RuntimeError('Restore build_blizzard_storm_cloud.py first')
    state=lifecycle()
    layer(system,material,'DarkElectricBase',18,1,.62,1,.36,(.07,.095,.18),.92,state)
    layer(system,material,'IndigoCloudBody',14,.84,.5,.82,.20,(.12,.20,.40),.88,state)
    layer(system,material,'BlueCloudCrown',10,.62,.4,.64,.06,(.22,.35,.63),.82,state)
    layer(system,material,'ElectricHighlights',6,.42,.28,.46,0,(.38,.55,.84),.66,state)
    layer(system,material,'DriftingElectricFringe',0,1,.45,.60,.25,(.08,.14,.29),.24,state)
    emission='saturate(User.CloudEmission)*saturate(User.Strength)*(1-saturate(User.DetailReduction))'
    theta=f'{SEED}*6.2831853'
    position=f'User.CurrentPosition+User.Side*cos({theta})*User.RadiusX*.45+User.Up*sin({theta})*User.RadiusY*.5+User.SurfaceNormal*(User.CloudHeight-50-{SEED2}*55)'
    for name,mat,rate,life,size,color in [
        ('CloudDischarges',filament,f'12*{emission}',.15,f'float2(45+{SEED3}*65,16)',f'float4(.55,.73,1,User.Strength)'),
        ('FallingElectricSparks',spark,f'14*{emission}',.5,'float2(3,12)',f'float4(.35,.57,1,User.Strength)')]:
        sprite(system,name,mat,rate=rate,life=life,position=position,size=size,color=color,rotation=f'{SEED3}*95',loop_seconds='max(.6,User.StormDuration+.6)')
        setdata('SetEmitterData',u.NiagaraExt_EmitterData,ref(system,name),{'bLocalSpace':False})
        if name=='FallingElectricSparks':assignments(system,name,'ParticleUpdateScript',{'Particles.Position':(POSITION,position+'-User.SurfaceNormal*Particles.Age*95')})
    system.set_editor_property('fixed_bounds',u.Box(min=u.Vector(-1150,-1150,-120),max=u.Vector(1150,1150,750)))
    EAL.set_metadata_tag(system,'Electric.Source','storm-cloud-fx.js; Normandy layered material; 48 core cloud sprites + bounded fringe/discharges')
    save(system)

def beam():
    # Lance beam moved to author_thunder_lance_ray.py (M09-ray recipe);
    # ThunderFluxV3 retired to trash/thunder-lance-flux-retired-20261006.
    pass

def charge(spark,filament,ring):
    system=empty('NS_ThunderCharge');user_parameter(system,'Charge',FLOAT)
    # Full charge remains held until release; the source explosion system is Once.
    loop=u.RainAssetEditor.read_input(system,'','SystemUpdateScript','SystemState','Loop Behavior')
    put(system,'','SystemUpdateScript','SystemState','Loop Behavior',loop.replace('NewEnumerator1','NewEnumerator0').replace('"Once"','"Infinite"'),ENUM)
    theta=f'{SEED}*6.2831853+Particles.Age*(12+User.Charge*9)'
    radius='(14+User.Charge*16)*(1-Particles.NormalizedAge*.6)'
    position=f'float3(cos({theta})*{radius},sin({theta})*{radius},({SEED2}-.5)*18)'
    sprite(system,'GatheringSparks',spark,rate=90,life=.3,position=position,size='float2(2+User.Charge*3,7+User.Charge*6)',color='float4(.45,.65,1,.8)',rotation=f'{SEED3}*360',continuous=True)
    sprite(system,'ChargingFilaments',filament,rate=32,life=.14,position=position,size='float2(22+User.Charge*24,11)',color='float4(.7,.85,1,1)',rotation=f'{SEED2}*360',continuous=True)
    sprite(system,'EnergyCore',spark,rate=10,life=.2,size='float2(15+User.Charge*18,15+User.Charge*18)',color='float4(.75,.90,1,.9)',continuous=True)
    sprite(system,'GatheringRings',ring,rate=4,life=.35,size='float2(58,58)*(1-Particles.NormalizedAge*.55)',color='float4(.32,.38,1,.45)',continuous=True)
    system.set_editor_property('fixed_bounds',u.Box(min=u.Vector(-75,-75,-75),max=u.Vector(75,75,75)));save(system)

def impact(spark,filament,ring):
    system=empty('NS_ElectricImpact')
    z=f'({SEED2}*2-1)';theta=f'{SEED}*6.2831853'
    direction=f'float3(sqrt(1-{z}*{z})*cos({theta}),sqrt(1-{z}*{z})*sin({theta}),{z})'
    # Origin-based trajectories avoid borrowing imported forces or environment meshes.
    sprite(system,'RadialSparks',spark,burst=32,life=.65,position=f'({direction})*Particles.Age*(110+{SEED3}*95)',size='float2(3,14)*(1-Particles.NormalizedAge*.6)',color='float4(.46,.72,1,1)',rotation=f'{SEED3}*360')
    sprite(system,'ElectricSplinters',filament,burst=9,life=.25,position=f'({direction})*Particles.Age*100',size='float2(35,12)*(1-Particles.NormalizedAge*.6)',color='float4(.7,.84,1,1)',rotation=f'{SEED2}*360')
    sprite(system,'ImpactCore',spark,burst=1,life=.2,size='float2(78,78)*(1-Particles.NormalizedAge*.5)',color='float4(.8,.92,1,1)')
    sprite(system,'ImpactRing',ring,burst=1,life=.42,size='float2(35+Particles.NormalizedAge*185,35+Particles.NormalizedAge*185)',color='float4(.27,.40,1,.6)')
    system.set_editor_property('fixed_bounds',u.Box(min=u.Vector(-240,-240,-240),max=u.Vector(240,240,240)));save(system)

def audio():
    def create(name,kind,factory):return u.load_asset(DEST+'/'+name) if EAL.does_asset_exist(DEST+'/'+name) else TOOLS.create_asset(name,DEST,kind,factory)
    att=create('ATT_ElectricMagic',u.SoundAttenuation,u.SoundAttenuationFactory());settings=att.get_editor_property('attenuation')
    for key,value in {'attenuate':True,'spatialize':True,'attenuation_shape_extents':u.Vector(100,0,0),'falloff_distance':2300.}.items():settings.set_editor_property(key,value)
    att.set_editor_property('attenuation',settings);save(att)
    con=create('CON_ElectricMagic',u.SoundConcurrency,u.SoundConcurrencyFactory());settings=con.get_editor_property('concurrency')
    settings.set_editor_property('max_count',6);settings.set_editor_property('limit_to_owner',False);settings.set_editor_property('resolution_rule',u.MaxConcurrentResolutionRule.PREVENT_NEW)
    con.set_editor_property('concurrency',settings);save(con)
    for index in (1,2):
        sound=own(f'/Game/Skills/Lightning/S_LightningCast{index}',f'S_ElectricCast{index}')
        sound.set_editor_property('looping',False);sound.set_editor_property('loading_behavior',u.SoundWaveLoadingBehavior.FORCE_INLINE)
        sound.set_editor_property('attenuation_settings',att);sound.set_editor_property('override_concurrency',False);sound.set_editor_property('concurrency_set',{con});save(sound)

def main():
    dirty={str(p.get_path_name()) for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()}
    if any(p.startswith(DEST) for p in dirty):raise RuntimeError('Preserve unsaved ElectricMagic packages')
    EAL.make_directory(DEST)
    spark=shape_material('M_ElectricSpark');filament=shape_material('M_ElectricFilament',filament=True);ring=shape_material('M_ElectricRing',ring=True)
    cloud(filament,spark);beam();charge(spark,filament,ring);impact(spark,filament,ring);audio()
    from build_thunder_lance_circle import build_circle
    CREATED.append(build_circle().get_path_name())
    receipt={'saved_assets':list(CREATED),'cloud_source':'/Game/UnrealNormandy/Materials/M_Master_StormCloud','cloud_owned_parent':'/Game/Skills/Blizzard/StormV2/MI_BlizzardStormCloud','beam_source':'SourceAssets/ThunderLanceFlux20261001','beam_runtime':'/Game/Skills/ElectricMagic/ThunderFluxV3',
             'sounds_original':['game-dev/public/assets/sounds/skills/lightning-1.mp3','game-dev/public/assets/sounds/skills/lightning-2.mp3'],
             'cloud_core_particles':48,'charge_particles_approx_max':40,'impact_particles':43,'max_local_arc_actors':48,'max_local_impact_systems':24,'max_audio_voices':6,
             'gameplay_tested':False,'rendered':False,'audio_played':False}
    folder=ROOT/'Saved/ElectricMagic20261001';folder.mkdir(parents=True,exist_ok=True)
    (folder/'asset-authoring.json').write_text(json.dumps(receipt,indent=2),encoding='utf-8')
    print('ELECTRIC_MAGIC_SAVED '+json.dumps(receipt))
if __name__=='__main__':main()
