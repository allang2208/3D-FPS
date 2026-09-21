"""Free Spline VFX fire flipbooks, adapted to runtime weapon/meteor contracts.

Author one stage per MCP batch. Existing pack and fireball assets are read-only.
"""
import json,sys
from pathlib import Path
import unreal as u
ROOT=Path(u.Paths.project_dir()).resolve();sys.path.insert(0,str(ROOT/'Tools/Skills'))
from build_fireball_assets import API,LIB,TOOLS,ref,emitters,setdata,put,assignments,save
from build_fireball_torch_burn import setup_emitter
from build_fireball_flames import trim,FLOAT,VEC2,VEC3,POSITION,COLOR
from build_fireball_flight import user_parameter
from build_fireball_slow_burn import smooth
from build_fireball_outer_flame import enable_sprite_usage,connect
BASE='/Game/Skills/FireMagic20260921';DEST=BASE+'/SplineV4'
OUT=ROOT/'SourceAssets/FireMagicSpline20260921'
ATLAS='/Game/_SplineVFX/_GenericSource/Texture/'
SEED='frac(float(Particles.UniqueID)*.61803398875)'
VAR='frac(float(Particles.UniqueID)*.41421356237)'
AGE='Particles.Age';N='Particles.NormalizedAge'
THETA=f'({VAR}*6.2831853)'

def own(source,name):
    path=DEST+'/'+name
    if path in {p.get_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()}:
        raise RuntimeError('Preserve unsaved edits in '+path)
    obj=u.load_asset(path) if u.EditorAssetLibrary.does_asset_exist(path) else u.EditorAssetLibrary.duplicate_asset(source,path)
    if not obj:raise RuntimeError('Missing source '+source)
    return obj

def compensate_exposure(mat):
    # AlphaComposite still masks the background when scene exposure suppresses
    # unlit RGB. Match the established torch's exposure-independent emission.
    # Keep the final depth/lifetime premultiplication and opacity path intact.
    emission=LIB.get_material_property_input_node(mat,u.MaterialProperty.MP_EMISSIVE_COLOR)
    if not emission:raise RuntimeError('Missing emission in '+mat.get_path_name())
    if isinstance(emission,u.MaterialExpressionEyeAdaptationInverse):return
    inverse=LIB.create_material_expression(mat,u.MaterialExpressionEyeAdaptationInverse)
    connect(emission,inverse,str(LIB.get_material_expression_input_names(inverse)[0]))
    if not LIB.connect_material_property(inverse,'',u.MaterialProperty.MP_EMISSIVE_COLOR):
        raise RuntimeError('Cannot connect exposure compensation in '+mat.get_path_name())


def materials():
    # The established soft-root shader reads the original RGB-on-black flipbooks.
    # A project copy avoids altering fireball or the pack's globally timed material.
    parent=own('/Game/Skills/Fireball/M_FireballOuterFireFlame','M_SplineFireSoft')
    enable_sprite_usage(parent)
    compensate_exposure(parent)
    errors=LIB.recompile_material(parent)
    if errors:raise RuntimeError(str(errors))
    save(parent)
    for name,tex,gain,opacity in [('MI_SplineFireFlame','T_Vfx_Stamp_FireFlame_88',1.75,.75),('MI_SplineFireFury','T_Vfx_Stamp_FireFury_88',1.4,.58)]:
        mi=own('/Game/Skills/Fireball/MI_FireballOuterFireFlame',name)
        LIB.set_material_instance_parent(mi,parent);enable_sprite_usage(parent,mi)
        LIB.set_material_instance_texture_parameter_value(mi,'FlameAtlas',u.load_asset(ATLAS+tex))
        for key,value in [('EmissiveGain',gain),('OpacityGain',opacity),('RootFadeStart',.68),('RootFadeEnd',.98)]:
            LIB.set_material_instance_scalar_parameter_value(mi,key,value)
        LIB.update_material_instance(mi);save(mi)
    # Smoke remains the Free Spline VFX smoke layer, with its actual 8x8 atlas.
    smoke=own('/Game/_SplineVFX/_GenericSource/Material/MI/MI_Vfx_ParticleSubUV_fog03_88_fade','MI_SplineSmoke')
    smoke_parent=own(smoke.get_editor_property('parent').get_path_name(),'M_SplineSmoke')
    LIB.set_material_instance_parent(smoke,smoke_parent)
    LIB.set_material_instance_scalar_parameter_value(smoke,'FadeDistance',8.)
    enable_sprite_usage(smoke_parent,smoke);compensate_exposure(smoke_parent)
    errors=LIB.recompile_material(smoke_parent)
    if errors:raise RuntimeError(str(errors))
    save(smoke_parent)
    LIB.update_material_instance(smoke);save(smoke)

def system(name,source,params,bounds=600):
    obj=own(source,name)
    for e in emitters(obj):API.call_method('RemoveEmitter',(ref(obj,e),))
    for key,typ in params:user_parameter(obj,key,typ)
    obj.set_editor_property('fixed_bounds',u.Box(min=u.Vector(-bounds,-bounds,-bounds),max=u.Vector(bounds,bounds,bounds)))
    return obj

def appearance(size,alpha,direction='float3(0,0,1)',smoke=False):
    envelope=smooth('0','.10',N)+'*(1-'+smooth('.52','1',N)+')'
    return {'Particles.SpriteAlignment':(VEC3,direction),'Particles.SpriteRotation':(FLOAT,'0'),
            'Particles.SpriteUVScale':(VEC2,'float2(1,1)'), 'Particles.SpriteSize':(VEC2,size),
            'Particles.SubImageIndex':(FLOAT,f'fmod({VAR}*64+{AGE}*(22+10*{SEED}),63.99)'),
            'Particles.Color':(COLOR,f'float4({".15,.13,.11" if smoke else "1,.96,.90"},{alpha}*{envelope})'),
            'Particles.DynamicMaterialParameter':('/Script/CoreUObject.Vector4f','float4(1,1,1,1)')}

def layer(obj,name,mat,rate,local,spawn,update,burst=None,delay=0):
    material=u.load_asset(DEST+'/'+mat)
    setup_emitter(obj,name,material,rate,local)
    setdata('SetRendererData',u.NiagaraExt_RendererData,ref(obj,name,renderer=0),{
        'SubImageSize':{'X':8,'Y':8},'bSubImageBlend':True,'PivotInUVSpace':{'X':.5,'Y':.80 if mat!='MI_SplineSmoke' else .5}})
    if burst is not None:
        API.call_method('RemoveModule',(ref(obj,name,'EmitterUpdateScript','SpawnRate'),))
        API.call_method('AddModule',(ref(obj,name,'EmitterUpdateScript'),u.load_asset('/Niagara/Modules/Emitter/SpawnBurst_Instantaneous')))
        put(obj,name,'EmitterUpdateScript','SpawnBurst_Instantaneous','Spawn Count',f'(Value={burst})','/Script/Niagara.NiagaraInt32')
        put(obj,name,'EmitterUpdateScript','SpawnBurst_Instantaneous','Spawn Time',f'(Value={delay})')
        source=u.load_asset('/Game/NiagaraExamples/FX_Explosions/NS_Explosion_Small')
        for key in ['Life Cycle Mode','Loop Behavior']:
            value=u.RainAssetEditor.read_input(source,'Explosion','EmitterUpdateScript','EmitterState',key)
            if key=='Life Cycle Mode':value=value.replace('NewEnumerator0','NewEnumerator1').replace('"System"','"Self"')
            else:value=value.replace('NewEnumerator0','NewEnumerator1').replace('"Infinite"','"Once"')
            put(obj,name,'EmitterUpdateScript','EmitterState',key,value,'/Script/NiagaraEditor.NiagaraExt_StackInputData_Enum')
        put(obj,name,'EmitterUpdateScript','EmitterState','Loop Duration','(Value=1.4)')
    assignments(obj,name,'ParticleSpawnScript',spawn);assignments(obj,name,'ParticleUpdateScript',update)

def curl(position,amplitude,frequency=.025):
    # Analytic curl of three sine potentials: divergence-free, no radial clumping.
    # Particle phase is independent; all derivatives are transverse to their axis.
    phase=f'({VAR}*6.283+{AGE}*2.8)'
    return f'{amplitude}*float3(cos(({position}).y*{frequency}+{phase})-sin(({position}).z*{frequency}+{phase}),cos(({position}).z*{frequency}+{phase})-sin(({position}).x*{frequency}+{phase}),cos(({position}).x*{frequency}+{phase})-sin(({position}).y*{frequency}+{phase}))'

def weapon():
    s=system('NS_ArmorSplineFire',BASE+'/PolishV2/NS_ArmorTorchJets',[(p,t) for p,t in [('Fade',FLOAT),('WeaponEnd',VEC3),('WeaponStartWorld',POSITION),('WeaponEndWorld',POSITION),('PreviousStart',POSITION),('PreviousEnd',POSITION),('WeaponVelocity',VEC3),('WeaponSize',FLOAT)]])
    a=appearance(f'float2(13+7*{SEED},29+18*{VAR})*User.WeaponSize','.86*saturate(User.Fade)',f'normalize(float3(.2*sin({AGE}*5+{THETA}),.15*cos({AGE}*4+{THETA}),1))')
    p=f'User.WeaponEnd*(.13+.84*{SEED})+float3(2*sin({THETA}),2*cos({THETA}),2+{AGE}*9)'
    a.update({'Particles.Position':(POSITION,p),'Particles.Velocity':(VEC3,'float3(0,0,0)')})
    layer(s,'BladeFireFlame','MI_SplineFireFlame',48,True,{'Particles.Lifetime':(FLOAT,f'.42+.20*{SEED}'),**a},a)
    a=appearance(f'float2(19+9*{SEED},43+24*{VAR})*User.WeaponSize','.52*saturate(User.Fade)','normalize(float3(0,0,95)-User.WeaponVelocity*.09)')
    p=f'lerp(lerp(User.PreviousStart,User.PreviousEnd,.16+.80*{SEED}),lerp(User.WeaponStartWorld,User.WeaponEndWorld,.16+.80*{SEED}),{VAR})'
    layer(s,'SwingFireFury','MI_SplineFireFury',32,False,{'Particles.Lifetime':(FLOAT,f'.26+.17*{SEED}'),'Particles.Position':(POSITION,p),'Particles.Velocity':(VEC3,'float3(0,0,55)+User.WeaponVelocity*.08'),**a},
          {'Particles.Position':(POSITION,'Particles.Position+Particles.Velocity*Engine.DeltaTime'),'Particles.Velocity':(VEC3,f'Particles.Velocity+({curl("Particles.Position",45)})*Engine.DeltaTime'),**a})
    save(s)

def field(aura=False):
    name='NS_ArmorSplineAura' if aura else 'NS_MeteorSplineAfterfire'
    src=BASE+'/NS_FlameArmorAura' if aura else BASE+'/PolishV2/NS_MeteorAfterfire'
    s=system(name,src,[('Fade',FLOAT),('Radius',FLOAT),('Spread',FLOAT)])
    for k,mat,rate,size,alpha in [('BaseFlame','MI_SplineFireFlame',30 if aura else 105,'float2(14,32)' if aura else 'float2(33,70)',.7),('RollingFury','MI_SplineFireFury',14 if aura else 44,'float2(20,43)' if aura else 'float2(48,92)',.35)]:
        r=f'User.Radius*(.88+.07*{SEED})' if aura else f'User.Radius*User.Spread*sqrt({SEED})*.91'
        p=f'float3(cos({THETA})*{r},sin({THETA})*{r},4+{AGE}*18)+float3(sin({AGE}*5+{THETA}),cos({AGE}*4+{THETA}),0)*{N}*7'
        a=appearance(f'{size}*(.7+.55*{VAR})',f'{alpha}*saturate(User.Fade)')
        a.update({'Particles.Position':(POSITION,p),'Particles.Velocity':(VEC3,'float3(0,0,0)')})
        layer(s,k,mat,rate,True,{'Particles.Lifetime':(FLOAT,f'.48+.35*{VAR}'),**a},a)
    save(s)

def mantle():
    s=system('NS_MeteorSplineMantle',BASE+'/PolishV2/NS_MeteorMantle',[('Fade',FLOAT),('FlightDirection',VEC3),('FlightSpeed',FLOAT)])
    z=f'({SEED}*1.8-.9)';rad=f'sqrt(1-{z}*{z})'
    direction=f'float3({rad}*cos({THETA}),{rad}*sin({THETA}),{z})'
    p=f'{direction}*float3(29,26,20)-User.FlightDirection*{AGE}*55'
    for name,mat,rate,size,alpha in [('SurfaceFire','MI_SplineFireFlame',45,'float2(32,65)',.80),('PeelingFire','MI_SplineFireFury',23,'float2(45,98)',.38)]:
        axis=f'normalize(-User.FlightDirection+{direction}*.24)'
        a=appearance(f'{size}*(.8+.35*{VAR})',f'{alpha}*saturate(User.Fade)',axis)
        a.update({'Particles.Position':(POSITION,p),'Particles.Velocity':(VEC3,'float3(0,0,0)')})
        layer(s,name,mat,rate,True,{'Particles.Lifetime':(FLOAT,f'.25+.22*{VAR}'),**a},a)
    save(s)

def trail():
    s=system('NS_MeteorSplineWake',BASE+'/PolishV2/NS_MeteorPlume',[('PreviousPosition',POSITION),('CurrentPosition',POSITION),('FlightDirection',VEC3),('FlightSpeed',FLOAT),('Fade',FLOAT)],1800)
    for name,mat,rate,size,alpha,life in [('TrailingFire','MI_SplineFireFlame',92,'float2(43,90)',.68,f'.23+.20*{SEED}'),('LooseFury','MI_SplineFireFury',42,'float2(63,115)',.37,f'.35+.20*{SEED}'),('CoolingSmoke','MI_SplineSmoke',24,'float2(58,64)',.22,f'.55+.28*{SEED}')]:
        smoke=mat=='MI_SplineSmoke'
        a=appearance(f'{size}*(.8+.4*{VAR})*(1+{N}*{1.1 if smoke else .35})',f'{alpha}*saturate(User.Fade)', '-User.FlightDirection',smoke)
        offset=f'float3(cos({THETA}),sin({THETA}),0)*(7+16*{SEED})'
        vel=f'-User.FlightDirection*(30+min(User.FlightSpeed*.024,100))+{offset}*1.4'
        layer(s,name,mat,rate,False,{'Particles.Lifetime':(FLOAT,life),'Particles.Position':(POSITION,f'lerp(User.PreviousPosition,User.CurrentPosition,{SEED})+{offset}'),'Particles.Velocity':(VEC3,vel),**a},
              {'Particles.Position':(POSITION,'Particles.Position+Particles.Velocity*Engine.DeltaTime'),
               'Particles.Velocity':(VEC3,f'(Particles.Velocity+({curl("Particles.Position",90 if smoke else 65)}+float3(0,0,35))*Engine.DeltaTime)*exp(-1.6*Engine.DeltaTime)'),**a})
    save(s)

def impact():
    s=system('NS_MeteorSplineImpact','/Game/Skills/Fireball/ImpactRealistic20260914/NS_FireballImpactRealistic',[('SurfaceHit',FLOAT),('LocalUp',VEC3),('ImpactGrowth',FLOAT)],700)
    for name,mat,count,delay,life,smoke in [('ImpactFire','MI_SplineFireFury',15,0,f'.40+.20*{SEED}',False),('RisingFire','MI_SplineFireFlame',10,.055,f'.50+.22*{SEED}',False),('SettlingSmoke','MI_SplineSmoke',8,.12,f'.8+.35*{SEED}',True)]:
        axis=f'normalize(float3(cos({THETA}),sin({THETA}),.8+{SEED}))'
        p=f'float3(cos({THETA}),sin({THETA}),0)*(12+{AGE}*(145+80*{SEED}))+User.LocalUp*(6+{AGE}*(55+70*{VAR}))'
        scale=f'(1+User.ImpactGrowth)*(.8+.45*{VAR})'
        a=appearance(('float2(100,110)' if smoke else 'float2(55,115)')+f'*{scale}*(.65+{N}*.9)', '.24' if smoke else '.8',axis,smoke)
        a.update({'Particles.Position':(POSITION,p),'Particles.Velocity':(VEC3,'float3(0,0,0)')})
        layer(s,name,mat,0,True,{'Particles.Lifetime':(FLOAT,life),**a},a,burst=count,delay=delay)
    save(s)

def run(stage):
    OUT.mkdir(parents=True,exist_ok=True);u.EditorAssetLibrary.make_directory(DEST)
    {'materials':materials,'weapon':weapon,'aura':lambda:field(True),'mantle':mantle,'trail':trail,'ground':field,'impact':impact}[stage]()
    (OUT/(stage+'-authored.json')).write_text(json.dumps({'stage':stage,'assets':DEST,'source':'Dr.Game Free Spline VFX Fire_B / FireBackUp / Smoke','saved':True,'tested':False},indent=2),encoding='utf8')
    print('SPLINE_FIRE_SAVED',stage)
