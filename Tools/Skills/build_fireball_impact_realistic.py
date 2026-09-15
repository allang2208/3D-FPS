"""Author directional, non-looping combustion, heat shock and layered impact audio.

Run with -AllowCommandletRendering for actual shader compilation; no game or preview.
"""
import json, sys
from pathlib import Path
import unreal as u

ROOT=Path(u.Paths.project_dir());SOURCE=ROOT/'SourceAssets/FireballImpactRealistic20260914'
DEST='/Game/Skills/Fireball/ImpactRealistic20260914'
sys.path.insert(0,str(ROOT/'Tools/Skills'))
from build_fireball_assets import API,LIB,TOOLS,ref,emitters,setdata,put,assignments,save
from build_fireball_flames import trim,FLOAT,VEC2,VEC3,POSITION,COLOR
from build_fireball_flight import user_parameter
from build_fireball_slow_burn import smooth
from build_fireball_outer_flame import enable_sprite_usage,connect
from build_fireball_fluid_burn import moving_translucency,compensate_emission

def own(source,name):
    path=DEST+'/'+name
    asset=u.load_asset(path) if u.EditorAssetLibrary.does_asset_exist(path) else u.EditorAssetLibrary.duplicate_asset(source,path)
    if not asset:raise RuntimeError('Missing authoring source '+source)
    return asset

def new_material(name):
    path=DEST+'/'+name
    material=u.load_asset(path) if u.EditorAssetLibrary.does_asset_exist(path) else TOOLS.create_asset(name,DEST,u.Material,u.MaterialFactoryNew())
    LIB.delete_all_material_expressions(material)
    material.set_editor_property('shading_model',u.MaterialShadingModel.MSM_UNLIT)
    material.set_editor_property('disable_depth_test',False)
    material.set_editor_property('output_translucent_velocity',False)
    return material

def finish(material):
    errors=LIB.recompile_material(material)
    if errors:raise RuntimeError(material.get_name()+': '+'; '.join(errors))
    save(material)

def custom(material,code,inputs,kind=u.CustomMaterialOutputType.CMOT_FLOAT1):
    expression=LIB.create_material_expression(material,u.MaterialExpressionCustom)
    expression.set_editor_property('code',code);expression.set_editor_property('output_type',kind)
    pins=[]
    for name in inputs:
        pin=u.CustomInput();pin.set_editor_property('input_name',name);pins.append(pin)
    expression.set_editor_property('inputs',pins)
    for name,(source,output) in inputs.items():LIB.connect_material_expressions(source,output,expression,name)
    return expression

def scalar(mat,name,value):
    node=LIB.create_material_expression(mat,u.MaterialExpressionScalarParameter)
    node.set_editor_property('parameter_name',name);node.set_editor_property('default_value',value)
    return node

def materials():
    parent=own('/Game/NiagaraExamples/Materials/MasterMaterials/M_SmokeAndFire_Sprites','M_ImpactCombustion')
    moving_translucency(parent);enable_sprite_usage(parent);finish(parent)
    flame=own('/Game/NiagaraExamples/Materials/MI_Explosion_8x8','MI_ImpactCombustion')
    LIB.set_material_instance_parent(flame,parent)
    for name,value in [('Emissive Gain',1.6),('Opacity Gain',.65),('Temperature Max',4200),('Temperature Min',950),
                       ('Temperature Exponent',.7),('Near Fade Distance',8),('Depth Fade Distance',10)]:
        LIB.set_material_instance_scalar_parameter_value(flame,name,value)
    for name in ['Use Material SubUV','Use Particle Alpha As Threshold']:
        LIB.set_material_instance_static_switch_parameter_value(flame,name,False)
    LIB.set_material_usage_override(flame,u.MaterialUsage.MATUSAGE_NIAGARA_SPRITES,True,True)
    LIB.update_material_instance(flame);save(flame)
    smoke=own('/Game/Skills/Fireball/FluidBurn20260914/MI_FluidThinWisp','MI_ImpactThinSmoke')
    LIB.set_material_instance_scalar_parameter_value(smoke,'Opacity Gain',.35)
    LIB.update_material_instance(smoke);save(smoke)
    ember=new_material('M_ImpactEmber');ember.set_editor_property('blend_mode',u.BlendMode.BLEND_ADDITIVE)
    ember.set_editor_property('two_sided',True);moving_translucency(ember);enable_sprite_usage(ember)
    uv=LIB.create_material_expression(ember,u.MaterialExpressionTextureCoordinate)
    color=LIB.create_material_expression(ember,u.MaterialExpressionParticleColor)
    mask=custom(ember,'float2 p=(UV-.5)*2;return exp(-dot(p,p)*5)*saturate(1-dot(p,p))*Alpha;',{'UV':(uv,''),'Alpha':(color,'A')})
    emission=custom(ember,'return float3(2.0,.48,.035)*Color.rgb;',{'Color':(color,'RGB')},u.CustomMaterialOutputType.CMOT_FLOAT3)
    LIB.connect_material_property(compensate_emission(ember,emission),'',u.MaterialProperty.MP_EMISSIVE_COLOR)
    LIB.connect_material_property(mask,'',u.MaterialProperty.MP_OPACITY);finish(ember)
    return flame,smoke,ember

def layer(system,name,material,count,delay,kind,lifecycle):
    template=u.load_asset('/Game/NiagaraExamples/FX_Explosions/Emitters/NE_Core')
    API.call_method('AddEmitter',(system,template,name))
    trim(system,name,{'EmitterUpdateScript':['EmitterState'],'ParticleSpawnScript':['InitializeParticle'],'ParticleUpdateScript':['ParticleState']})
    for script in ['ParticleSpawnScript','ParticleUpdateScript']:
        u.EditorAssetLibrary.remove_metadata_tag(system,'Fireball.Assignments.'+name+'.'+script)
    setdata('SetEmitterData',u.NiagaraExt_EmitterData,ref(system,name),{'bLocalSpace':True,'SimTarget':'CPUSim','bInterpolatedSpawning':False})
    setdata('SetRendererData',u.NiagaraExt_RendererData,ref(system,name,renderer=0),{
        'Material':material.get_path_name(),'MaterialUserParamBinding':{'Parameter':{'Name':'None'}},
        'SubImageSize':{'X':1 if kind=='ember' else 8,'Y':1 if kind=='ember' else 8},'bSubImageBlend':kind!='ember',
        'PivotInUVSpace':{'X':.5,'Y':.5},'Alignment':'CustomAlignment','FacingMode':'FaceCamera',
        'MotionVectorSetting':'Precise','bCastShadows':False,'CutoutTexture':None,'bUseMaterialCutoutTexture':False})
    for key,value in lifecycle.items():put(system,name,'EmitterUpdateScript','EmitterState',key,value,'/Script/NiagaraEditor.NiagaraExt_StackInputData_Enum')
    put(system,name,'EmitterUpdateScript','EmitterState','Loop Duration','(Value=1.4)')
    API.call_method('AddModule',(ref(system,name,'EmitterUpdateScript'),u.load_asset('/Niagara/Modules/Emitter/SpawnBurst_Instantaneous')))
    put(system,name,'EmitterUpdateScript','SpawnBurst_Instantaneous','Spawn Count',f'(Value={count})','/Script/Niagara.NiagaraInt32')
    put(system,name,'EmitterUpdateScript','SpawnBurst_Instantaneous','Spawn Time',f'(Value={delay})')
    seed='frac(float(Particles.UniqueID)*.61803398875)';variant='frac(float(Particles.UniqueID)*.41421356237)'
    theta=f'({variant}*6.2831853)';a='Particles.Age';n='Particles.NormalizedAge'
    z=f'lerp({seed}*1.8-.9,.16+{seed}*.50,saturate(User.SurfaceHit))'
    direction=f'normalize(float3(cos({theta}),sin({theta}),{z}))'
    if kind=='contact':
        pos=f'float3(0,0,12+{a}*22)';size=f'float2(190,190)*(.40+.70*{n})';life='.32';alpha='.62'
    elif kind=='flame':
        pos=f'{direction}*(10+145*{a}/(.085+{a}))+User.LocalUp*{a}*{a}*55'
        size=f'float2(95+{seed}*36,110+{variant}*48)*(.70+.5*{n})';life=f'.48+.24*{seed}';alpha='.53'
    elif kind=='smoke':
        pos=f'{direction}*(18+60*{a})+User.LocalUp*{a}*42'
        size=f'float2(120,140)*(.75+{n}*.6)';life=f'.62+.25*{seed}';alpha='.15'
    else:
        pos=f'{direction}*(5+{a}*(130+120*{seed}))-User.LocalUp*{a}*{a}*110'
        size=f'float2(1.1+{seed},4+5*{seed})*(1-.5*{n})';life=f'.32+.30*{seed}';alpha='.65'
    # Surface fragments stay outside the struck plane; wall/ground upward drift is world up.
    position=f'float3(({pos}).xy,lerp(({pos}).z,max(4,({pos}).z),saturate(User.SurfaceHit)))'
    fade=smooth('0','.025',n)+'*(1-'+smooth('.35' if kind in ['contact','ember'] else '.50','1',n)+')'
    tint='.22,.18,.14' if kind=='smoke' else ('1,1,1' if kind=='ember' else '.18,.15,.12')
    common={'Particles.Position':(POSITION,position),'Particles.Velocity':(VEC3,'float3(0,0,0)'),
        'Particles.SpriteAlignment':(VEC3,direction if kind=='ember' else 'User.LocalUp'),
        'Particles.SpriteRotation':(FLOAT,'0' if kind=='ember' else f'({seed}-.5)*.55'),
        # Local-space component scale affects positions, not sprite world sizes.
        # Growth defaults to zero for the authored level-one appearance.
        'Particles.SpriteUVScale':(VEC2,'float2(1,1)'),
        'Particles.SpriteSize':(VEC2,f'({size})*(1+User.ImpactGrowth)'),
        'Particles.Color':(COLOR,f'float4({tint},{alpha}*{fade})'),
        'Particles.SubImageIndex':(FLOAT,'0' if kind=='ember' else f'min(62.95,{n}*70)'),
        'Particles.DynamicMaterialParameter':('/Script/CoreUObject.Vector4f','float4(1,1,1,1)')}
    assignments(system,name,'ParticleSpawnScript',{'Particles.Lifetime':(FLOAT,life),**common})
    assignments(system,name,'ParticleUpdateScript',common)

def explosion(flame,smoke,ember):
    system=own('/Game/NiagaraExamples/FX_Explosions/NS_Explosion_Small','NS_FireballImpactRealistic')
    source=u.load_asset('/Game/NiagaraExamples/FX_Explosions/NS_Explosion_Small')
    lifecycle={key:u.RainAssetEditor.read_input(source,'Explosion','EmitterUpdateScript','EmitterState',key)
               for key in ['Life Cycle Mode','Loop Behavior']}
    lifecycle['Life Cycle Mode']=lifecycle['Life Cycle Mode'].replace('NewEnumerator0','NewEnumerator1').replace('"System"','"Self"')
    lifecycle['Loop Behavior']=lifecycle['Loop Behavior'].replace('NewEnumerator0','NewEnumerator1').replace('"Infinite"','"Once"')
    for name in emitters(system):API.call_method('RemoveEmitter',(ref(system,name),))
    for name,typ in [('SurfaceHit',FLOAT),('LocalUp',VEC3),('ImpactGrowth',FLOAT)]:user_parameter(system,name,typ)
    for name,mat,count,delay,kind in [('ContactIgnition',flame,1,0,'contact'),('OutwardCombustion',flame,6,.022,'flame'),
                                    ('CoolingWisps',smoke,3,.11,'smoke'),('ShortEmbers',ember,14,.035,'ember')]:
        layer(system,name,mat,count,delay,kind,lifecycle)
    system.set_editor_property('fixed_bounds',u.Box(min=u.Vector(-350,-350,-350),max=u.Vector(350,350,350)))
    save(system);return system

def shockwave():
    mat=new_material('M_FireballHeatShockwave')
    mat.set_editor_property('blend_mode',u.BlendMode.BLEND_TRANSLUCENT)
    mat.set_editor_property('two_sided',False)
    mat.set_editor_property('translucency_pass',u.MaterialTranslucencyPass.MTP_BEFORE_DOF)
    mat.set_editor_property('refraction_method',u.RefractionMode.RM_INDEX_OF_REFRACTION)
    mat.set_editor_property('refraction_depth_bias',2.)
    uv=LIB.create_material_expression(mat,u.MaterialExpressionTextureCoordinate)
    time=LIB.create_material_expression(mat,u.MaterialExpressionTime)
    camera=LIB.create_material_expression(mat,u.MaterialExpressionCameraVectorWS)
    vertex_normal=LIB.create_material_expression(mat,u.MaterialExpressionVertexNormalWS)
    strength=scalar(mat,'HeatStrength',.038);fade=scalar(mat,'Opacity',1);surface=scalar(mat,'SurfaceHit',1)
    flow=custom(mat,'return UV*3.2+float2(Time*.18,-Time*.35);',{'UV':(uv,''),'Time':(time,'')},u.CustomMaterialOutputType.CMOT_FLOAT2)
    sample=LIB.create_material_expression(mat,u.MaterialExpressionTextureSample)
    sample.set_editor_property('texture',u.load_asset('/Game/Realistic_Starter_VFX_Pack_Vol2/Textures/T_NoiseNormal_A'))
    sample.set_editor_property('sampler_type',u.MaterialSamplerType.SAMPLERTYPE_NORMAL)
    LIB.connect_material_expressions(flow,'',sample,'UVs')
    mask=custom(mat,'float r=length((UV-.5)*2)+N.x*.045; '
        'float ring=smoothstep(.52,.70,r)*(1-smoothstep(.85,.99,r)); '
        'float shell=pow(1-saturate(abs(dot(normalize(Cam),normalize(Norm)))),2); '
        'return lerp(shell,ring,Surface)*Fade*(.75+.25*saturate(N.y*.5+.5));',
        {'UV':(uv,''),'N':(sample,'RGB'),'Cam':(camera,''),'Norm':(vertex_normal,''),'Surface':(surface,''),'Fade':(fade,'')})
    depth=LIB.create_material_expression(mat,u.MaterialExpressionDepthFade)
    depth.set_editor_property('fade_distance_default',6.)
    connect(mask,depth,str(LIB.get_material_expression_input_names(depth)[0]))
    normal=custom(mat,'return normalize(float3(N.xy*.55,max(.3,N.z)));',{'N':(sample,'RGB')},u.CustomMaterialOutputType.CMOT_FLOAT3)
    ior=custom(mat,'return 1+Mask*Strength;',{'Mask':(depth,''),'Strength':(strength,'')})
    opacity=custom(mat,'return Mask*.02;',{'Mask':(depth,'')})
    for expr,prop in [(normal,u.MaterialProperty.MP_NORMAL),(ior,u.MaterialProperty.MP_REFRACTION),(opacity,u.MaterialProperty.MP_OPACITY)]:
        LIB.connect_material_property(expr,'',prop)
    finish(mat);return mat

def audio():
    task=u.AssetImportTask()
    for name,value in {'filename':str(SOURCE/'FireballImpactLayered.wav'),'destination_path':DEST,
                       'destination_name':'S_FireballImpactLayered','automated':True,'replace_existing':True,'save':True}.items():
        task.set_editor_property(name,value)
    TOOLS.import_asset_tasks([task]);sound=u.load_asset(DEST+'/S_FireballImpactLayered')
    attenuation=TOOLS.create_asset('ATT_FireballImpact',DEST,u.SoundAttenuation,u.SoundAttenuationFactory()) if not u.EditorAssetLibrary.does_asset_exist(DEST+'/ATT_FireballImpact') else u.load_asset(DEST+'/ATT_FireballImpact')
    settings=attenuation.get_editor_property('attenuation')
    for name,value in {'attenuate':True,'spatialize':True,'attenuation_shape_extents':u.Vector(120,0,0),'falloff_distance':2400.}.items():settings.set_editor_property(name,value)
    attenuation.set_editor_property('attenuation',settings);save(attenuation)
    sound.set_editor_property('attenuation_settings',attenuation);save(sound)
    return sound

def build():
    u.EditorAssetLibrary.make_directory(DEST)
    flame,smoke,ember=materials();system=explosion(flame,smoke,ember);wave=shockwave();sound=audio()
    (SOURCE/'installation.json').write_text(json.dumps({'system':system.get_path_name(),'shockwave':wave.get_path_name(),'audio':sound.get_path_name(),
        'emission':'Once; contact 1, combustion 6, wisps 3, embers 14','flame_atlas':'Epic T_Explosion_EOO, 8x8, non-looping playback',
        'surface':'Local Z follows hit normal; LocalUp remains world up; SurfaceHit selects outward hemisphere or air burst',
        'shader':'Depth-tested; DepthFade present; OutputTranslucentVelocity disabled; actual RHI compilation required',
        'native':'Hit-based origin/orientation, 240 ms shadowed flash, 260 ms surface ring / air sphere',
        'status':'Assets compiled and saved; no game, preview, screenshot or runtime acceptance'},indent=2),encoding='utf-8')
    u.log('FIREBALL_REALISTIC_IMPACT_INSTALLED')

if __name__=='__main__':build()
