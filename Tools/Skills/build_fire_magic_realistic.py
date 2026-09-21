"""Adapt owned Realistic Vol.2 / Military Trench flames to fire-magic contracts.

Source Cascade LOD0 settings are retained in FireMagicRealistic20260922/*.t3d.
Keep original material graphs, per-source atlas dimensions and dynamic inputs.
Authoring only: no PIE or rendered acceptance. Run one stage per MCP batch.
"""
import json,sys
from pathlib import Path
import unreal as u
ROOT=Path(u.Paths.project_dir()).resolve();sys.path.insert(0,str(ROOT/'Tools/Skills'))
from build_fireball_assets import API,LIB,TOOLS,ref,emitters,setdata,put,assignments,save
from build_fireball_torch_burn import setup_emitter
from build_fireball_flames import FLOAT,VEC2,VEC3,POSITION,COLOR
from build_fireball_flight import user_parameter
from build_fireball_slow_burn import smooth
from build_fireball_outer_flame import enable_sprite_usage,connect
from build_fire_magic_spline import compensate_exposure,curl
BASE='/Game/Skills/FireMagic20260921';DEST=BASE+'/RealisticV5'
OUT=ROOT/'SourceAssets/FireMagicRealistic20260922'
PACK='/Game/Realistic_Starter_VFX_Pack_Vol2/Materials/'
SEED='frac(float(Particles.UniqueID)*.61803398875)'
VAR='frac(float(Particles.UniqueID)*.41421356237)'
THETA=f'({VAR}*6.2831853)';AGE='Particles.Age';N='Particles.NormalizedAge'
VEC4='/Script/CoreUObject.Vector4f'
MATS={
    'Blade':('M_NaturalBladeFlame',PACK+'M_Fire_B',8,4),
    'Fire':('M_NaturalRollingFlame',PACK+'M_Fire_C',6,6),
    'Meteor':('M_NaturalMeteorFlame','/Game/MilitaryTrench/Particles/Materials/M_Fire_SubUV',6,6),
    'Impact':('M_NaturalImpact',PACK+'M_Explosion_B',12,12),
    'Smoke':('M_NaturalSmoke',PACK+'M_Smoke_C',8,8),
}

def own(source,name):
    path=DEST+'/'+name
    if path in {p.get_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()}:
        raise RuntimeError('Preserve unsaved edits in '+path)
    obj=u.load_asset(path) if u.EditorAssetLibrary.does_asset_exist(path) else u.EditorAssetLibrary.duplicate_asset(source,path)
    if not obj:raise RuntimeError('Cannot author '+path+' from '+source)
    return obj

def materials():
    for key,(name,source,_,_) in MATS.items():
        m=own(source,name);enable_sprite_usage(m)
        # Native graphs decode each source's color/masks; do not substitute a
        # generic RGB-on-black shader or copy the old 8x8 Spline material.
        if LIB.get_material_property_input_node(m,u.MaterialProperty.MP_EMISSIVE_COLOR):compensate_exposure(m)
        for node in LIB.get_material_expressions(m):
            if isinstance(node,u.MaterialExpressionDepthFade):node.set_editor_property('fade_distance_default',5.)
        errors=LIB.recompile_material(m)
        if errors:raise RuntimeError(name+': '+str(errors))
        save(m)

def system(name,source,params,bounds=650):
    s=own(BASE+'/SplineV4/'+source,name)
    for e in emitters(s):API.call_method('RemoveEmitter',(ref(s,e),))
    for key,typ in params:user_parameter(s,key,typ)
    s.set_editor_property('fixed_bounds',u.Box(min=u.Vector(-bounds,-bounds,-bounds),max=u.Vector(bounds,bounds,bounds)))
    return s

def appearance(kind,size,alpha,axis='float3(0,0,1)'):
    # Original frames advance once through particle life. Staggered births give
    # variation without jumping randomly between unrelated parts of a flame.
    _,_,cols,rows=MATS[kind]
    envelope=smooth('0','.16',N)+'*(1-'+smooth('.46','1',N)+')'
    frame=f'min({N}*{cols*rows-1},{cols*rows-1}.0)'
    thermal=f'lerp(float3(2.8,.83,.12),float3(.65,.04,.003),{N})'
    if kind=='Blade':thermal=f'lerp(float3(2.5,.70,.11),float3(.60,.03,.002),{N})'
    if kind=='Meteor':thermal=f'lerp(float3(20,5,1),float3(7,.1,0),{N})*.14'
    if kind=='Smoke':thermal='float3(.09,.08,.07)'
    # Source Dynamic X = mask offset, Y = opacity exponent. Z/W are unused.
    dynamic=f'float4({VAR},.4+2.2*{SEED}+{N}*.7,0,0)'
    if kind=='Impact':
        # Normalize the source million-unit glow for exposure-compensated VFX.
        dynamic=f'float4(10*pow(1-{N},2)+.15,1,1,1)'
        thermal=f'lerp(float3(.443,.347,.307),float3(.49,.49,.49),{N})'
        envelope='1-'+smooth('.55','1',N)
        frame=f'143*(1-pow(1-{N},1.7))'
    if kind in ['Blade','Smoke']:dynamic='float4(0,0,0,0)'
    return {'Particles.SpriteAlignment':(VEC3,axis),'Particles.SpriteRotation':(FLOAT,'0'),
            'Particles.SpriteUVScale':(VEC2,'float2(1,1)'),'Particles.SpriteSize':(VEC2,size),
            'Particles.SubImageIndex':(FLOAT,frame),'Particles.Color':(COLOR,f'float4({thermal},{alpha}*{envelope})'),
            'Particles.DynamicMaterialParameter':(VEC4,dynamic)}

def layer(s,name,kind,rate,local,spawn,update,burst=None,delay=0):
    mat,_,cols,rows=MATS[kind]
    setup_emitter(s,name,u.load_asset(DEST+'/'+mat),rate,local)
    setdata('SetRendererData',u.NiagaraExt_RendererData,ref(s,name,renderer=0),{
        'SubImageSize':{'X':cols,'Y':rows},'bSubImageBlend':True,
        'PivotInUVSpace':{'X':.5,'Y':.70 if kind not in ['Smoke','Impact'] else .5},
        'Alignment':'Unaligned' if kind in ['Smoke','Impact'] else 'CustomAlignment'})
    if burst is not None:
        API.call_method('RemoveModule',(ref(s,name,'EmitterUpdateScript','SpawnRate'),))
        API.call_method('AddModule',(ref(s,name,'EmitterUpdateScript'),u.load_asset('/Niagara/Modules/Emitter/SpawnBurst_Instantaneous')))
        put(s,name,'EmitterUpdateScript','SpawnBurst_Instantaneous','Spawn Count',f'(Value={burst})','/Script/Niagara.NiagaraInt32')
        put(s,name,'EmitterUpdateScript','SpawnBurst_Instantaneous','Spawn Time',f'(Value={delay})')
        source=u.load_asset('/Game/NiagaraExamples/FX_Explosions/NS_Explosion_Small')
        for key in ['Life Cycle Mode','Loop Behavior']:
            value=u.RainAssetEditor.read_input(source,'Explosion','EmitterUpdateScript','EmitterState',key)
            if key=='Life Cycle Mode':value=value.replace('NewEnumerator0','NewEnumerator1').replace('"System"','"Self"')
            else:value=value.replace('NewEnumerator0','NewEnumerator1').replace('"Infinite"','"Once"')
            put(s,name,'EmitterUpdateScript','EmitterState',key,value,'/Script/NiagaraEditor.NiagaraExt_StackInputData_Enum')
        put(s,name,'EmitterUpdateScript','EmitterState','Loop Duration','(Value=2.2)')
    assignments(s,name,'ParticleSpawnScript',spawn);assignments(s,name,'ParticleUpdateScript',update)

def weapon():
    s=system('NS_ArmorNaturalFire','NS_ArmorSplineFire',[(p,t) for p,t in [('Fade',FLOAT),('WeaponEnd',VEC3),('WeaponStartWorld',POSITION),('WeaponEndWorld',POSITION),('PreviousStart',POSITION),('PreviousEnd',POSITION),('WeaponVelocity',VEC3),('WeaponSize',FLOAT)]])
    axis='normalize(float3(0,0,110)-User.WeaponVelocity*.045)'
    for name,kind,rate,size,alpha in [('SmallFlame','Blade',24,'float2(11,23)',1.1),('BladeRoll','Fire',10,'float2(14,27)',.65)]:
        a=appearance(kind,f'{size}*(.8+.35*{VAR})*User.WeaponSize',f'{alpha}*User.Fade',axis)
        p=f'User.WeaponEnd*(.12+.86*{SEED})+float3(cos({THETA}),sin({THETA}),0)*1.8+float3(0,0,2+{AGE}*6)'
        a.update({'Particles.Position':(POSITION,p),'Particles.Velocity':(VEC3,'float3(0,0,0)')})
        layer(s,name,kind,rate,True,{'Particles.Lifetime':(FLOAT,f'.65+.3*{VAR}'),**a},a)
    a=appearance('Fire',f'float2(17,31)*User.WeaponSize','User.Fade*.45',axis)
    p=f'lerp(lerp(User.PreviousStart,User.PreviousEnd,{SEED}),lerp(User.WeaponStartWorld,User.WeaponEndWorld,{SEED}),{VAR})'
    layer(s,'SwingEmbers','Fire',13,False,{'Particles.Lifetime':(FLOAT,f'.30+.18*{SEED}'),'Particles.Position':(POSITION,p),'Particles.Velocity':(VEC3,'float3(0,0,22)+User.WeaponVelocity*.045'),**a},
          {'Particles.Position':(POSITION,'Particles.Position+Particles.Velocity*Engine.DeltaTime'),**a})
    save(s)

def ground(aura=False):
    s=system('NS_ArmorNaturalAura' if aura else 'NS_MeteorNaturalAfterfire','NS_ArmorSplineAura' if aura else 'NS_MeteorSplineAfterfire',[('Fade',FLOAT),('Radius',FLOAT),('Spread',FLOAT)])
    r=f'User.Radius*(.86+.10*{SEED})' if aura else f'User.Radius*User.Spread*sqrt({SEED})*.9'
    for name,kind,rate,size,alpha in [('LowFlame','Blade',16 if aura else 38,'float2(13,25)' if aura else 'float2(29,48)',.8),('GroundRoll','Fire',9 if aura else 26,'float2(18,31)' if aura else 'float2(38,62)',.9)]:
        p=f'float3(cos({THETA})*{r},sin({THETA})*{r},3+{AGE}*9)'
        a=appearance(kind,f'{size}*(.8+.35*{VAR})',f'{alpha}*User.Fade')
        a.update({'Particles.Position':(POSITION,p),'Particles.Velocity':(VEC3,'float3(0,0,0)')})
        layer(s,name,kind,rate,True,{'Particles.Lifetime':(FLOAT,f'.85+.35*{VAR}'),**a},a)
    save(s)

def mantle():
    s=system('NS_MeteorNaturalMantle','NS_MeteorSplineMantle',[('Fade',FLOAT),('FlightDirection',VEC3),('FlightSpeed',FLOAT)])
    z=f'({SEED}*1.8-.9)';r=f'sqrt(1-{z}*{z})';direction=f'float3({r}*cos({THETA}),{r}*sin({THETA}),{z})'
    a=appearance('Meteor',f'float2(33,53)*(.8+.35*{VAR})','1.1*User.Fade',f'normalize(-User.FlightDirection+{direction}*.28)')
    a.update({'Particles.Position':(POSITION,f'{direction}*float3(25,24,21)-User.FlightDirection*{AGE}*24'),'Particles.Velocity':(VEC3,'float3(0,0,0)')})
    layer(s,'TrenchSurfaceFlame','Meteor',24,True,{'Particles.Lifetime':(FLOAT,f'.55+.25*{VAR}'),**a},a)
    save(s)

def trail():
    s=system('NS_MeteorNaturalWake','NS_MeteorSplineWake',[('PreviousPosition',POSITION),('CurrentPosition',POSITION),('FlightDirection',VEC3),('FlightSpeed',FLOAT),('Fade',FLOAT)],1800)
    for name,kind,rate,size,alpha,life in [('RealisticJet','Fire',38,'float2(41,68)',.9,f'.43+.22*{SEED}'),('TrenchBreakup','Meteor',12,'float2(50,74)',.65,f'.48+.22*{SEED}'),('LightSmoke','Smoke',8,'float2(62,66)',.22,f'.70+.30*{SEED}')]:
        a=appearance(kind,f'{size}*(.8+.3*{VAR})*(1+{N}*.4)',f'{alpha}*User.Fade','-User.FlightDirection')
        offset=f'float3(cos({THETA}),sin({THETA}),0)*(6+10*{SEED})'
        vel=f'-User.FlightDirection*(20+min(User.FlightSpeed*.012,55))+{offset}*.6'
        layer(s,name,kind,rate,False,{'Particles.Lifetime':(FLOAT,life),'Particles.Position':(POSITION,f'lerp(User.PreviousPosition,User.CurrentPosition,{SEED})+{offset}'),'Particles.Velocity':(VEC3,vel),**a},
              {'Particles.Position':(POSITION,'Particles.Position+Particles.Velocity*Engine.DeltaTime'),
               'Particles.Velocity':(VEC3,f'(Particles.Velocity+({curl("Particles.Position",28)}+float3(0,0,18))*Engine.DeltaTime)*exp(-1.2*Engine.DeltaTime)'),**a})
    save(s)

def impact():
    s=system('NS_MeteorNaturalImpact','NS_MeteorSplineImpact',[('SurfaceHit',FLOAT),('LocalUp',VEC3),('ImpactGrowth',FLOAT)],850)
    # Three compact native explosion sprites, followed by Molotov-style fire.
    for name,kind,count,delay,size,alpha,life in [('NativeExplosion','Impact',3,0,'float2(160,170)',.9,f'.9+.2*{VAR}'),('MolotovRoll','Fire',9,.065,'float2(49,74)',1.2,f'.65+.35*{VAR}'),('ImpactSmoke','Smoke',5,.16,'float2(110,115)',.28,f'.95+.35*{VAR}')]:
        if kind=='Impact':p=f'float3(cos({THETA}),sin({THETA}),0)*(8+{AGE}*28)+User.LocalUp*(32+{AGE}*25)'
        else:p=f'float3(cos({THETA}),sin({THETA}),0)*(10+{AGE}*(105+70*{SEED}))+User.LocalUp*(5+{AGE}*(30+35*{VAR}))'
        a=appearance(kind,f'{size}*(.8+.25*{VAR})*(.9+{N}*.35)',str(alpha),f'normalize(float3(cos({THETA}),sin({THETA}),1))')
        a.update({'Particles.Position':(POSITION,p),'Particles.Velocity':(VEC3,'float3(0,0,0)')})
        layer(s,name,kind,0,True,{'Particles.Lifetime':(FLOAT,life),**a},a,burst=count,delay=delay)
    save(s)

def run(stage):
    OUT.mkdir(parents=True,exist_ok=True);u.EditorAssetLibrary.make_directory(DEST)
    {'materials':materials,'weapon':weapon,'aura':lambda:ground(True),'mantle':mantle,'trail':trail,'ground':ground,'impact':impact}[stage]()
    (OUT/(stage+'-authored.json')).write_text(json.dumps({'stage':stage,'destination':DEST,'saved':True,'game_tested':False},indent=2),encoding='utf8')
    print('NATURAL_FIRE_AUTHORED',stage)
