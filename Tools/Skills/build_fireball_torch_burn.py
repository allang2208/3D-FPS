"""Replace fireball combustion with the bronze torch's flowing erosion flame.

Asset authoring only. Keep the runtime paths and all spell C++ contracts stable.
Build stages: materials, candidate_core, candidate_trail, install_core, install_trail.
The owning torch and Vefects originals are read-only sources.
"""
import json
import hashlib
import shutil
import sys
from pathlib import Path
import unreal

ROOT=Path(unreal.Paths.project_dir()).resolve()
if ROOT.as_posix().lower()!='d:/fps3d/fpsgame':raise RuntimeError('Expected FPSGAME')
sys.path.insert(0,str(ROOT/'Tools/Skills'))
from build_fireball_assets import API,LIB,TOOLS,ref,emitters,setdata,put,assignments
from build_fireball_flames import trim,FLOAT,VEC2,VEC3,POSITION,COLOR
from build_fireball_flight import user_parameter
from build_fireball_slow_burn import smooth
from build_fireball_outer_flame import enable_sprite_usage,connect

OUT=ROOT/'SourceAssets/FireballTorchBurn20260921'
DEST='/Game/Skills/Fireball/TorchBurn20260921'
TORCH='/Game/Props/RomanColumn20260915/NS_TorchFlame'
CORE='/Game/Skills/Fireball/NS_FireballSlowBurnCore'
TRAIL='/Game/Skills/Fireball/NS_FireballVelocityTrail'
TEMPLATE='/Game/Vefects/Free_Fire/Shared/Particles/NE_FireFlame'
VECTOR4='/Script/CoreUObject.Vector4f'
OUT.mkdir(parents=True,exist_ok=True)

def save(asset):
    if isinstance(asset,unreal.NiagaraSystem):
        if not unreal.RainAssetEditor.compile_rain(asset):
            # Editing emitter structure can leave the editor's cached compile graph stale.
            unreal.SystemLibrary.collect_garbage()
            if not unreal.RainAssetEditor.compile_rain(asset):raise RuntimeError('Niagara compile failed '+asset.get_path_name())
    if not unreal.EditorLoadingAndSavingUtils.save_packages([asset.get_outermost()],False):
        raise RuntimeError('Save failed '+asset.get_path_name())
    print('TORCH_FIREBALL_SAVED',asset.get_path_name())

def copy(source,name):
    path=DEST+'/'+name
    asset=unreal.load_asset(path) if unreal.EditorAssetLibrary.does_asset_exist(path) else unreal.EditorAssetLibrary.duplicate_asset(source,path)
    if not asset:raise RuntimeError('Missing source '+source)
    return asset

def backup(path,folder='Before'):
    source=ROOT/'Content'/(path.removeprefix('/Game/')+'.uasset')
    target=OUT/folder/source.name
    target.parent.mkdir(parents=True,exist_ok=True)
    if not target.exists():shutil.copy2(source,target)
    return {'source':path,'backup':str(target),'sha256':hashlib.sha256(target.read_bytes()).hexdigest()}

def body_material():
    """Continuous optical core; torch erosion is reserved for the outer tongues.

    A dense center and a broad, noisy soft edge remain independent of dissolve.
    Two advected samples of the torch's noise provide rolling heat variation.
    """
    path=DEST+'/M_FireballCohesiveCore'
    mat=unreal.load_asset(path) if unreal.EditorAssetLibrary.does_asset_exist(path) else TOOLS.create_asset(
        'M_FireballCohesiveCore',DEST,unreal.Material,unreal.MaterialFactoryNew())
    LIB.delete_all_material_expressions(mat)
    for key,value in {
        'blend_mode':unreal.BlendMode.BLEND_ALPHA_COMPOSITE,
        'shading_model':unreal.MaterialShadingModel.MSM_UNLIT,
        'translucency_pass':unreal.MaterialTranslucencyPass.MTP_AFTER_DOF,
        'two_sided':True,'disable_depth_test':False,'enable_responsive_aa':True,
        'output_translucent_velocity':False,'is_translucency_velocity_from_depth':False,
    }.items():mat.set_editor_property(key,value)
    enable_sprite_usage(mat)

    def node(cls,**values):
        result=LIB.create_material_expression(mat,cls)
        for key,value in values.items():result.set_editor_property(key,value)
        return result

    def custom(code,inputs,kind):
        pins=[]
        for key in inputs:
            pin=unreal.CustomInput();pin.set_editor_property('input_name',key);pins.append(pin)
        result=node(unreal.MaterialExpressionCustom,code=code,inputs=pins,output_type=kind)
        for key,(source,output) in inputs.items():connect(source,result,key,output)
        return result

    uv=node(unreal.MaterialExpressionTextureCoordinate)
    time=node(unreal.MaterialExpressionTime)
    color=node(unreal.MaterialExpressionParticleColor)
    gain=node(unreal.MaterialExpressionScalarParameter,parameter_name='EmissionGain',default_value=2.3)
    noise=unreal.load_asset('/Game/Vefects/Free_Fire/Shared/Textures/T_VFX_Noise_01')
    if not noise:raise RuntimeError('Missing torch noise for the cohesive core')
    samples=[]
    for code in [
        'float2 p=(UV-.5)*2; float z=sqrt(saturate(1-dot(p,p))); '
        'return p*(.85+.32*z)+float2(Time*.10,-Time*.23);',
        'float2 p=(UV-.5)*2; return float2(p.x*.82-p.y*.57,p.x*.57+p.y*.82)*2.15'
        '+float2(-Time*.17,-Time*.09);',
    ]:
        moving=custom(code,{'UV':(uv,''),'Time':(time,'')},unreal.CustomMaterialOutputType.CMOT_FLOAT2)
        # The torch noise is stored as linear grayscale, not an RGB color map.
        sample=node(unreal.MaterialExpressionTextureSample,texture=noise,
            sampler_type=unreal.MaterialSamplerType.SAMPLERTYPE_LINEAR_GRAYSCALE)
        connect(moving,sample,'UVs');samples.append(sample)
    fields=custom('''
float2 p=(UV-.5)*2;
float r=length(p);
float turbulence=saturate(N1*.62+N2*.38);
float edgeRadius=r+.085*(N1-.5)+.035*(N2-.5);
float edge=1-smoothstep(.64,.97,edgeRadius);
float thickness=sqrt(saturate(1-r*r));
float heat=saturate(.22+.52*thickness+.33*turbulence);
float3 ember=float3(1,.075,.004);
float3 orange=float3(1,.30,.018);
float3 hot=float3(1,.66,.13);
float3 rgb=lerp(ember,orange,smoothstep(.20,.60,heat));
rgb=lerp(rgb,hot,smoothstep(.60,.98,heat));
// Noise modulates density without eating through the central fireball.
return float4(rgb*(.78+.22*thickness),edge*(.82+.12*turbulence));
''',{'UV':(uv,''),'N1':(samples[0],'R'),'N2':(samples[1],'R')},unreal.CustomMaterialOutputType.CMOT_FLOAT4)
    rgb=node(unreal.MaterialExpressionComponentMask,r=True,g=True,b=True,a=False)
    alpha=node(unreal.MaterialExpressionComponentMask,r=False,g=False,b=False,a=True)
    connect(fields,rgb,str(LIB.get_material_expression_input_names(rgb)[0]))
    connect(fields,alpha,str(LIB.get_material_expression_input_names(alpha)[0]))
    coverage=node(unreal.MaterialExpressionMultiply)
    connect(alpha,coverage,'A');connect(color,coverage,'B','A')
    fade=node(unreal.MaterialExpressionDepthFade,fade_distance_default=4.0)
    connect(coverage,fade,str(LIB.get_material_expression_input_names(fade)[0]))
    tinted=node(unreal.MaterialExpressionMultiply)
    connect(rgb,tinted,'A');connect(color,tinted,'B','RGB')
    bright=node(unreal.MaterialExpressionMultiply)
    connect(tinted,bright,'A');connect(gain,bright,'B')
    exposed=node(unreal.MaterialExpressionEyeAdaptationInverse)
    connect(bright,exposed,str(LIB.get_material_expression_input_names(exposed)[0]))
    emission=node(unreal.MaterialExpressionMultiply)
    connect(exposed,emission,'A');connect(fade,emission,'B')
    LIB.connect_material_property(emission,'',unreal.MaterialProperty.MP_EMISSIVE_COLOR)
    LIB.connect_material_property(fade,'',unreal.MaterialProperty.MP_OPACITY)
    errors=LIB.recompile_material(mat)
    if errors:raise RuntimeError('Cohesive core material: '+str(errors))
    save(mat)

def materials():
    parent=copy('/Game/Vefects/Free_Fire/Shared/Materials/M_VFX_Erosion','M_FireballTorchErosion')
    parent.set_editor_property('shading_model',unreal.MaterialShadingModel.MSM_UNLIT)
    parent.set_editor_property('translucency_pass',unreal.MaterialTranslucencyPass.MTP_AFTER_DOF)
    parent.set_editor_property('output_translucent_velocity',False)
    parent.set_editor_property('is_translucency_velocity_from_depth',False)
    parent.set_editor_property('enable_responsive_aa',True)
    parent.set_editor_property('disable_depth_test',False)
    parent.set_editor_property('two_sided',True)
    enable_sprite_usage(parent)
    # Retain the torch's actual erosion graph. Only the fireball copy gets exposure
    # compensation so its flame does not turn black under the daytime player camera.
    if not any(isinstance(n,unreal.MaterialExpressionEyeAdaptationInverse) for n in LIB.get_material_expressions(parent)):
        old=LIB.get_material_property_input_node(parent,unreal.MaterialProperty.MP_EMISSIVE_COLOR)
        inv=LIB.create_material_expression(parent,unreal.MaterialExpressionEyeAdaptationInverse)
        connect(old,inv,str(LIB.get_material_expression_input_names(inv)[0]))
        LIB.connect_material_property(inv,'',unreal.MaterialProperty.MP_EMISSIVE_COLOR)
    errors=LIB.recompile_material(parent)
    if errors:raise RuntimeError(str(errors))
    save(parent)
    for number,energy in [(1,5.5),(2,7.0)]:
        mat=copy('/Game/Props/RomanColumn20260915/MI_TorchSoft_Flame%02d'%number,'MI_FireballTorch%02d'%number)
        LIB.set_material_instance_parent(mat,parent)
        for key,value in [('Emissive_Intensity',energy),('DepthFade',5.0),('Noise_01_Speed_X',.23),
                          ('Noise_01_Speed_Y',.37),('Noises_OpacityBoost',1.1)]:
            LIB.set_material_instance_scalar_parameter_value(mat,key,value)
        enable_sprite_usage(parent,mat)
        LIB.update_material_instance(mat)
        save(mat)
    body_material()

def setup_emitter(system,name,material,rate,local):
    if name not in emitters(system):API.call_method('AddEmitter',(system,unreal.load_asset(TEMPLATE),name))
    trim(system,name,{'EmitterUpdateScript':['EmitterState','SpawnRate'],
        'ParticleSpawnScript':['InitializeParticle'],'ParticleUpdateScript':['ParticleState']})
    for script in ['ParticleSpawnScript','ParticleUpdateScript']:
        unreal.EditorAssetLibrary.remove_metadata_tag(system,'Fireball.Assignments.'+name+'.'+script)
    setdata('SetEmitterData',unreal.NiagaraExt_EmitterData,ref(system,name),
        {'bLocalSpace':local,'SimTarget':'CPUSim','bInterpolatedSpawning':False})
    # The torch's renderer binds the actual SpriteAlignment attribute. The old
    # fireball template still pointed at the removed ShapeLocation.ShapeVector.
    torch=unreal.load_asset(TORCH)
    source_data=json.loads(API.call_method('GetRendererData',(ref(torch,'NE_Flame_01',renderer=0),)).get_editor_property('property_values'))
    setdata('SetRendererData',unreal.NiagaraExt_RendererData,ref(system,name,renderer=0),{
        'Material':material.get_path_name(),'MaterialUserParamBinding':{'Parameter':{'Name':'None'}},
        'Alignment':'CustomAlignment','FacingMode':'FaceCamera','SpriteAlignmentBinding':source_data['SpriteAlignmentBinding'],
        'SubImageSize':{'X':1,'Y':1},'bSubImageBlend':False,'PivotInUVSpace':{'X':.5,'Y':.5},
        'bCastShadows':False,'bUseMaterialCutoutTexture':False,'CutoutTexture':None,
        'MotionVectorSetting':'Precise','SortOrderHint':1 if local else 0})
    mode=unreal.RainAssetEditor.read_input(torch,'NE_Flame_01','EmitterUpdateScript','EmitterState','Life Cycle Mode')
    # Vefects lifecycle stays System; do not substitute the old Self loop contract.
    put(system,name,'EmitterUpdateScript','EmitterState','Life Cycle Mode',mode,'/Script/NiagaraEditor.NiagaraExt_StackInputData_Enum')
    put(system,name,'EmitterUpdateScript','SpawnRate','SpawnRate','(Value='+str(rate)+')')

def cohesive_body(system):
    name='TorchBurnCohesiveCore'
    mat=unreal.load_asset(DEST+'/M_FireballCohesiveCore')
    if not mat:raise RuntimeError('Build body_material before the core')
    setup_emitter(system,name,mat,0,True)
    # The body is one persistent particle, owned by the projectile component.
    # It must not fade/expire in step with short-lived flame particles. There is
    # no ParticleState age-kill; impact uses the existing DeactivateImmediate.
    API.call_method('RemoveModule',(ref(system,name,'EmitterUpdateScript','SpawnRate'),))
    API.call_method('RemoveModule',(ref(system,name,'ParticleUpdateScript','ParticleState'),))
    API.call_method('AddModule',(ref(system,name,'EmitterUpdateScript'),
        unreal.load_asset('/Niagara/Modules/Emitter/SpawnBurst_Instantaneous')))
    put(system,name,'EmitterUpdateScript','SpawnBurst_Instantaneous','Spawn Count',
        '(HlslExpression="Engine.Emitter.TotalSpawnedParticles < 1 ? 1 : 0")',
        '/Script/NiagaraEditor.NiagaraExt_StackInputData_HlslExpression')
    put(system,name,'EmitterUpdateScript','SpawnBurst_Instantaneous','Spawn Time','(Value=0)')
    setdata('SetRendererData',unreal.NiagaraExt_RendererData,ref(system,name,renderer=0),{
        'Alignment':'Unaligned','FacingMode':'FaceCamera','SortOrderHint':0})
    common={
        'Particles.Position':(POSITION,'float3(0,0,0)'),
        'Particles.Velocity':(VEC3,'float3(0,0,0)'),
        'Particles.SpriteRotation':(FLOAT,'0'),
        'Particles.SpriteUVScale':(VEC2,'float2(1,1)'),
        'Particles.SpriteSize':(VEC2,'float2(30,30)*max(.01,Engine.Owner.Scale.x)'),
        'Particles.SubImageIndex':(FLOAT,'0'),
        'Particles.Color':(COLOR,'float4(1,1,1,1)'),
    }
    assignments(system,name,'ParticleSpawnScript',{'Particles.Lifetime':(FLOAT,'1'),**common})
    assignments(system,name,'ParticleUpdateScript',common)

def core(system):
    for n in emitters(system):API.call_method('RemoveEmitter',(ref(system,n),))
    user_parameter(system,'Flight',FLOAT);user_parameter(system,'FlightAge',FLOAT)
    # The dust-mask "volume" dissolved into disconnected wisps. Replace that
    # layer with a stable optical body while retaining the torch flame mantle.
    cohesive_body(system)
    for name,number,rate in [('TorchBurnTongues',1,15)]:
        mat=unreal.load_asset(DEST+'/MI_FireballTorch%02d'%number)
        setup_emitter(system,name,mat,rate,True)
        seed='frac(float(Particles.UniqueID)*.61803398875)'
        variant='frac(float(Particles.UniqueID)*.41421356237)'
        phase=f'(6.2831853*{variant})'
        age='Particles.Age';n='Particles.NormalizedAge'
        blend=smooth('0','.08','User.FlightAge')+'*saturate(User.Flight)'
        radius='(5.0+3.0*'+seed+')'
        height=f'(-3+{n}*9)'
        hover=f'float3(cos({phase})*{radius},sin({phase})*{radius},{height})'
        rear=f'float3(-2-{n}*24,cos({phase})*{radius}*.70,sin({phase})*{radius}*.70)'
        direction=f'normalize(lerp(float3(.18*cos({phase}),.18*sin({phase}),1),float3(-1,0,0),{blend}))'
        dimensions=f'float2(13+6*{seed},27+8*{variant})'
        # SpriteSize is world-space in Niagara: component scale alone only grows positions.
        size=dimensions+f'*float2(1-.18*{blend},1+.28*{blend})*(.88+.12*sin(3.14159*{n}))*max(.01,Engine.Owner.Scale.x)'
        envelope=smooth('0','.12',n)+'*(1-'+smooth('.55','1',n)+')'
        alpha='.58'
        tint=f'float3(1,lerp(.37,.08,{n}),lerp(.035,.006,{n}))'
        common={
            'Particles.Position':(POSITION,f'lerp({hover},{rear},{blend})'),
            'Particles.Velocity':(VEC3,'float3(0,0,0)'),
            'Particles.SpriteAlignment':(VEC3,direction),'Particles.SpriteRotation':(FLOAT,'0'),
            'Particles.SpriteSize':(VEC2,size),'Particles.SpriteUVScale':(VEC2,'float2(1,1)'),
            'Particles.SubImageIndex':(FLOAT,'0'),
            'Particles.Color':(COLOR,f'float4({tint},{alpha}*{envelope})'),
            'Particles.DynamicMaterialParameter':(VECTOR4,f'float4(.06+.80*{n},1,1,1)'),
            'Particles.MaterialRandom':(FLOAT,variant),
        }
        assignments(system,name,'ParticleSpawnScript',{'Particles.Lifetime':(FLOAT,'.48+.25*'+seed),**common})
        assignments(system,name,'ParticleUpdateScript',common)
    system.set_editor_property('fixed_bounds',unreal.Box(min=unreal.Vector(-90,-50,-50),max=unreal.Vector(50,50,75)))
    save(system)

def trail(system):
    for n in emitters(system):API.call_method('RemoveEmitter',(ref(system,n),))
    for name,typ in [('FlightDirection',VEC3),('FlightSpeed',FLOAT),('PreviousPosition',POSITION),('CurrentPosition',POSITION)]:
        user_parameter(system,name,typ)
    name='TorchBurnTrail'
    setup_emitter(system,name,unreal.load_asset(DEST+'/MI_FireballTorch01'),1,False)
    put(system,name,'EmitterUpdateScript','SpawnRate','SpawnRate',
        '(HlslExpression="clamp(User.FlightSpeed/18,0,160)")','/Script/NiagaraEditor.NiagaraExt_StackInputData_HlslExpression')
    seed='frac(float(Particles.UniqueID)*.61803398875)';n='Particles.NormalizedAge'
    assignments(system,name,'ParticleSpawnScript',{
        'Particles.Lifetime':(FLOAT,f'.06+.035*{seed}'),
        'Particles.Position':(POSITION,f'lerp(User.PreviousPosition,User.CurrentPosition,{seed})'),
        'Particles.Velocity':(VEC3,'-User.FlightDirection*35'),
        'Particles.SpriteAlignment':(VEC3,'-User.FlightDirection'),
        'Particles.SpriteRotation':(FLOAT,'0'),'Particles.SpriteUVScale':(VEC2,'float2(1,1)'),
        'Particles.SubImageIndex':(FLOAT,'0'),
        'Particles.SpriteSize':(VEC2,f'float2(13+4*{seed},24+6*{seed})'),
        'Particles.Color':(COLOR,'float4(1,.3,.03,.30)'),
        'Particles.DynamicMaterialParameter':(VECTOR4,'float4(.12,1,1,1)'),
        'Particles.MaterialRandom':(FLOAT,seed)})
    assignments(system,name,'ParticleUpdateScript',{
        'Particles.Position':(POSITION,'Particles.Position+Particles.Velocity*Engine.DeltaTime'),
        'Particles.SpriteSize':(VEC2,f'float2(13+4*{seed},24+6*{seed})*(1-.7*{n})'),
        'Particles.Color':(COLOR,f'float4(1,lerp(.3,.08,{n}),.012,.30*(1-{n})*(1-{n}))'),
        'Particles.DynamicMaterialParameter':(VECTOR4,f'float4(.12+.78*{n},1,1,1)')})
    # Flight covers world space; the system uses dynamic bounds just like the prior trail.
    save(system)

def run(stage):
    if stage=='materials':materials()
    elif stage=='body_material':body_material()
    elif stage=='candidate_core':core(copy(CORE,'NS_FireballTorchCore'))
    elif stage=='candidate_trail':trail(copy(TRAIL,'NS_FireballTorchTrail'))
    elif stage in ('install_core','install_trail'):
        target=CORE if stage=='install_core' else TRAIL
        # Do not replace a shared runtime package with another unsaved edit in it.
        dirty={p.get_name() for p in unreal.EditorLoadingAndSavingUtils.get_dirty_content_packages()}
        if target in dirty:raise RuntimeError('Runtime asset has unsaved edits: '+target)
        receipt=backup(target)
        if stage=='install_core':receipt['before_body_repair']=backup(target,'BeforeBodyRepair')
        (core if stage=='install_core' else trail)(unreal.load_asset(target))
        receipt.update({'stage':stage,'materials':DEST,'status':'compiled and saved; no game test'})
        (OUT/(stage+'.json')).write_text(json.dumps(receipt,indent=2),encoding='utf-8')
    else:raise ValueError(stage)
    print('FIREBALL_TORCH_STAGE_COMPLETE',stage)

if __name__=='__main__':
    for stage in ('materials','candidate_core','candidate_trail','install_core','install_trail'):run(stage)
