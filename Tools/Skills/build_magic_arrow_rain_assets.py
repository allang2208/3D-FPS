"""Author only /Game/Skills/MagicArrowRain20261026. No gameplay or render run."""
from pathlib import Path
import json,sys
import unreal as u
ROOT=Path(__file__).resolve().parents[2];SRC=ROOT/'SourceAssets/MagicArrowRain20261026'
sys.path.insert(0,str(ROOT/'Tools/Skills'))
from build_fireball_assets import API,ref,emitters,setdata,put,assignments,save
from build_fireball_flames import trim,FLOAT,VEC2,VEC3,POSITION,COLOR
from build_fireball_flight import user_parameter
DEST='/Game/Skills/MagicArrowRain20261026';EAL=u.EditorAssetLibrary;LIB=u.MaterialEditingLibrary;TOOLS=u.AssetToolsHelpers.get_asset_tools();saved=[]
def finish(asset):
    save(asset);saved.append(asset.get_path_name())
def node(m,cls):return LIB.create_material_expression(m,cls)
def custom(m,code,inputs,vector=False):
    n=node(m,u.MaterialExpressionCustom);n.set_editor_property('code',code);n.set_editor_property('output_type',u.CustomMaterialOutputType.CMOT_FLOAT3 if vector else u.CustomMaterialOutputType.CMOT_FLOAT1)
    pins=[]
    for key in inputs:p=u.CustomInput();p.set_editor_property('input_name',key);pins.append(p)
    n.set_editor_property('inputs',pins)
    for key,(value,channel) in inputs.items():
        if not LIB.connect_material_expressions(value,channel,n,key):raise RuntimeError('Material pin '+key)
    return n
def output(n,prop,channel=''):
    if not LIB.connect_material_property(n,channel,prop):raise RuntimeError('Material output '+str(prop))
def scalar(m,name,value):
    n=node(m,u.MaterialExpressionScalarParameter);n.set_editor_property('parameter_name',name);n.set_editor_property('default_value',value);return n
def material(name):
    m=u.load_asset(DEST+'/'+name) if EAL.does_asset_exist(DEST+'/'+name) else TOOLS.create_asset(name,DEST,u.Material,u.MaterialFactoryNew())
    LIB.delete_all_material_expressions(m);return m
def compile_material(m):
    LIB.recompile_material(m)
    if hasattr(u,'DragonBreathAuthorLibrary') and not u.DragonBreathAuthorLibrary.compile_material_assets([m]):raise RuntimeError('Material compile '+m.get_name())
    finish(m)
def materials():
    metal=material('M_ArrowRainMetal');metal.set_editor_property('blend_mode',u.BlendMode.BLEND_OPAQUE)
    LIB.set_material_usage(metal,u.MaterialUsage.MATUSAGE_INSTANCED_STATIC_MESHES)
    for prop,code,vector in [(u.MaterialProperty.MP_BASE_COLOR,'return float3(.38,.45,.41);',True),(u.MaterialProperty.MP_METALLIC,'return .85;',False),(u.MaterialProperty.MP_ROUGHNESS,'return .3;',False),(u.MaterialProperty.MP_EMISSIVE_COLOR,'return float3(.005,.045,.012);',True)]:output(custom(metal,code,{},vector),prop)
    compile_material(metal)
    flow=material('M_ArrowRainFlow');flow.set_editor_property('blend_mode',u.BlendMode.BLEND_TRANSLUCENT);flow.set_editor_property('shading_model',u.MaterialShadingModel.MSM_UNLIT)
    flow.set_editor_property('two_sided',True);flow.set_editor_property('disable_depth_test',False);flow.set_editor_property('output_translucent_velocity',False)
    LIB.set_material_usage(flow,u.MaterialUsage.MATUSAGE_INSTANCED_STATIC_MESHES)
    uv=node(flow,u.MaterialExpressionTextureCoordinate);time=node(flow,u.MaterialExpressionTime)
    code='float end=smoothstep(0,.045,UV.y)*(1-smoothstep(.95,1,UV.y)); float strand=pow(saturate(cos((UV.x*3+UV.y*2-T*1.25)*6.28318)),12); float pulse=pow(saturate(cos((UV.y-T*1.25)*6.28318)),6); return end*(.06+strand*.55+pulse*.20);'
    opacity=custom(flow,code,{'UV':(uv,''),'T':(time,'')});output(opacity,u.MaterialProperty.MP_OPACITY)
    rgb=custom(flow,'return float3(.06,1,.24)*2.2;',{},True);output(rgb,u.MaterialProperty.MP_EMISSIVE_COLOR)
    compile_material(flow)
    preview=material('M_ArrowRainPreview');preview.set_editor_property('material_domain',u.MaterialDomain.MD_DEFERRED_DECAL);preview.set_editor_property('blend_mode',u.BlendMode.BLEND_TRANSLUCENT)
    world=node(preview,u.MaterialExpressionWorldPosition);center=node(preview,u.MaterialExpressionVectorParameter);center.set_editor_property('parameter_name','GroundCenter')
    radius=scalar(preview,'Radius',400);valid=scalar(preview,'Valid',1);ready=scalar(preview,'Ready',0)
    opacity=custom(preview,'''float2 p=(World.xy-Center.xy)/max(Radius,1);float r=length(p);float w=max(.008,fwidth(r)*1.3);
float outer=1-smoothstep(w,w*2,abs(r-1.0));float angle=atan2(p.y,p.x);
float dash=step(.28,frac((angle+3.14159)/6.28318*32));outer*=lerp(dash,1,Valid);
float inner=(1-smoothstep(w*.6,w*1.5,abs(r-.89)))*.17;
float fill=(1-smoothstep(.93,.96,r))*.025;float center=(1-smoothstep(.025,.04,r))*.7;
return saturate(outer*(.72+Ready*.15)+inner+fill+center);''',{'World':(world,''),'Center':(center,''),'Radius':(radius,''),'Valid':(valid,''),'Ready':(ready,'')})
    color=custom(preview,'return lerp(float3(.65,.12,.07),float3(.07,.75,.24),Valid);',{'Valid':(valid,'')},True)
    output(opacity,u.MaterialProperty.MP_OPACITY);output(color,u.MaterialProperty.MP_BASE_COLOR);output(color,u.MaterialProperty.MP_EMISSIVE_COLOR)
    compile_material(preview)
    glow=material('M_ArrowRainGlow');glow.set_editor_property('blend_mode',u.BlendMode.BLEND_ADDITIVE);glow.set_editor_property('shading_model',u.MaterialShadingModel.MSM_UNLIT)
    glow.set_editor_property('two_sided',True);glow.set_editor_property('disable_depth_test',False)
    LIB.set_material_usage(glow,u.MaterialUsage.MATUSAGE_NIAGARA_SPRITES)
    uv=node(glow,u.MaterialExpressionTextureCoordinate);color=node(glow,u.MaterialExpressionParticleColor)
    opacity=custom(glow,'float r=length((UV-.5)*2);return saturate(1-r)*saturate(1-r)*Alpha;',{'UV':(uv,''),'Alpha':(color,'A')})
    rgb=custom(glow,'return RGB*2.0;',{'RGB':(color,'RGB')},True)
    output(opacity,u.MaterialProperty.MP_OPACITY);output(rgb,u.MaterialProperty.MP_EMISSIVE_COLOR);compile_material(glow)
    return metal
def import_sources(metal):
    task=u.AssetImportTask();task.filename=str(SRC/'SM_ArrowRain.obj');task.destination_path=DEST;task.destination_name='SM_ArrowRain';task.automated=True;task.replace_existing=True;task.save=False
    options=u.FbxImportUI();options.import_mesh=True;options.import_materials=False;options.import_textures=False;options.automated_import_should_detect_type=False;options.import_as_skeletal=False;options.mesh_type_to_import=u.FBXImportType.FBXIT_STATIC_MESH
    data=options.static_mesh_import_data;data.combine_meshes=True;data.auto_generate_collision=False;data.convert_scene=False;data.convert_scene_unit=False;data.generate_lightmap_u_vs=False
    task.options=options;TOOLS.import_asset_tasks([task]);mesh=u.load_asset(DEST+'/SM_ArrowRain')
    if not mesh:raise RuntimeError('Arrow mesh import failed')
    mesh.set_material(0,metal);finish(mesh)
    for name in ['S_ArrowRainRelease','S_ArrowRainBurst','S_ArrowRainImpact']:
        task=u.AssetImportTask();task.filename=str(SRC/(name+'.wav'));task.destination_path=DEST;task.destination_name=name;task.automated=True;task.replace_existing=True;task.save=False
        TOOLS.import_asset_tasks([task]);sound=u.load_asset(DEST+'/'+name)
        if not isinstance(sound,u.SoundWave):raise RuntimeError('Audio import '+name)
        sound.set_editor_property('volume',1.);sound.set_editor_property('pitch',1.);sound.set_editor_property('looping',False)
        sound.set_editor_property('loading_behavior',u.SoundWaveLoadingBehavior.FORCE_INLINE);sound.set_sound_asset_compression_type(u.SoundAssetCompressionType.PCM);finish(sound)
    att=u.load_asset(DEST+'/ATT_ArrowRain') if EAL.does_asset_exist(DEST+'/ATT_ArrowRain') else TOOLS.create_asset('ATT_ArrowRain',DEST,u.SoundAttenuation,u.SoundAttenuationFactory())
    settings=att.get_editor_property('attenuation');settings.set_editor_property('attenuation_shape_extents',u.Vector(450,0,0));settings.set_editor_property('falloff_distance',4000.);settings.set_editor_property('attenuate',True);settings.set_editor_property('spatialize',True);att.set_editor_property('attenuation',settings);finish(att)
def smoke(name,impact):
    source=u.load_asset('/Game/NiagaraExamples/FX_Explosions/NS_Explosion_Small')
    dust=u.load_asset('/Game/Fluids/ImpactSmokeCorrosion20260924/M_RollingImpactSmoke')
    if not source or not dust:raise RuntimeError('Restore Niagara example and rolling impact smoke')
    target=DEST+'/'+name;system=u.load_asset(target) if EAL.does_asset_exist(target) else EAL.duplicate_asset(source.get_path_name(),target)
    for en in emitters(system):API.call_method('RemoveEmitter',(ref(system,en),))
    en='GroundImpact' if impact else 'AirPressure'
    for stage in ['ParticleSpawnScript','ParticleUpdateScript']:EAL.remove_metadata_tag(system,'Fireball.Assignments.'+en+'.'+stage)
    API.call_method('AddEmitter',(system,u.load_asset('/Game/NiagaraExamples/FX_Explosions/Emitters/NE_Core'),en))
    trim(system,en,{'EmitterUpdateScript':['EmitterState'],'ParticleSpawnScript':['InitializeParticle'],'ParticleUpdateScript':['ParticleState']})
    setdata('SetEmitterData',u.NiagaraExt_EmitterData,ref(system,en),{'bLocalSpace':True,'SimTarget':'CPUSim','bInterpolatedSpawning':False})
    setdata('SetRendererData',u.NiagaraExt_RendererData,ref(system,en,renderer=0),{'Material':dust.get_path_name(),'MaterialUserParamBinding':{'Parameter':{'Name':'None'}},'SubImageSize':{'X':1,'Y':1},'bSubImageBlend':False,'Alignment':'Unaligned','FacingMode':'FaceCamera','bCastShadows':False,'CutoutTexture':None,'bUseMaterialCutoutTexture':False,'MotionVectorSetting':'Disable'})
    for key in ['Life Cycle Mode','Loop Behavior']:
        value=u.RainAssetEditor.read_input(source,'Explosion','EmitterUpdateScript','EmitterState',key).replace('NewEnumerator0','NewEnumerator1').replace('"System"','"Self"').replace('"Infinite"','"Once"')
        put(system,en,'EmitterUpdateScript','EmitterState',key,value,'/Script/NiagaraEditor.NiagaraExt_StackInputData_Enum')
    put(system,en,'EmitterUpdateScript','EmitterState','Loop Duration','(Value=1.4)')
    for param,typ in [('Radius',FLOAT),('Count',FLOAT),('Seed',FLOAT)]+[(f'Impact{i}',VEC3) for i in range(32)]:user_parameter(system,param,typ)
    API.call_method('AddModule',(ref(system,en,'EmitterUpdateScript'),u.load_asset('/Niagara/Modules/Emitter/SpawnBurst_Instantaneous')))
    put(system,en,'EmitterUpdateScript','SpawnBurst_Instantaneous','Spawn Count','(HlslExpression="floor(User.Count+.5)")' if impact else '(HlslExpression="14")','/Script/NiagaraEditor.NiagaraExt_StackInputData_HlslExpression')
    put(system,en,'EmitterUpdateScript','SpawnBurst_Instantaneous','Spawn Time','(Value=0)')
    a='frac((float(Particles.UniqueID)+User.Seed)*.618033989)';b='frac((float(Particles.UniqueID)+User.Seed)*.414213562)';age='Particles.Age';norm='Particles.NormalizedAge';direction=f'float3(cos({a}*6.28318),sin({a}*6.28318),0)'
    if impact:
        origin='User.Impact31'
        for i in reversed(range(31)):origin=f'(float(Particles.UniqueID)=={i}.0?User.Impact{i}:{origin})'
        position=f'{origin}+{direction}*(38*(1-exp(-{age}*10)))+float3(0,0,8+{age}*16)'
        size=f'float2(55,42)*(1+{b}*.35)*(1+{age}*1.2)';tint='.26,.25,.22';life=f'.8+{a}*.35';alpha='.45'
    else:
        position=f'{direction}*(User.Radius*.55*(1-exp(-{age}*14)))*(0.6+{b}*.4)+float3(0,0,({b}-.5)*45+{age}*12)'
        size=f'float2(110,85)*(1+{a}*.35)*(.45+1.3*(1-exp(-{age}*12)))';tint='.20,.29,.23';life=f'.55+{a}*.35';alpha='.52'
    common={'Particles.Position':(POSITION,position),'Particles.Velocity':(VEC3,'float3(0,0,0)'),
        'Particles.SpriteSize':(VEC2,size),'Particles.SpriteRotation':(FLOAT,f'{b}*360'),'Particles.SpriteUVScale':(VEC2,'float2(1,1)'),
        'Particles.Color':(COLOR,f'float4({tint},{alpha}*saturate({age}/.025)*pow(1-{norm},1.4))'),
        'Particles.SubImageIndex':(FLOAT,'0'),'Particles.DynamicMaterialParameter':('/Script/CoreUObject.Vector4f',f'float4({a},0,0,0)')}
    assignments(system,en,'ParticleSpawnScript',{'Particles.Lifetime':(FLOAT,life),**common});assignments(system,en,'ParticleUpdateScript',common)
    accents(system,source,impact)
    system.set_editor_property('fixed_bounds',u.Box(min=u.Vector(-650,-650,-200),max=u.Vector(650,650,650)));finish(system)

def accents(system,source,impact):
    en='EmeraldFragments' if impact else 'PressureFlash'
    for stage in ['ParticleSpawnScript','ParticleUpdateScript']:EAL.remove_metadata_tag(system,'Fireball.Assignments.'+en+'.'+stage)
    API.call_method('AddEmitter',(system,u.load_asset('/Game/NiagaraExamples/FX_Explosions/Emitters/NE_Core'),en))
    trim(system,en,{'EmitterUpdateScript':['EmitterState'],'ParticleSpawnScript':['InitializeParticle'],'ParticleUpdateScript':['ParticleState']})
    setdata('SetEmitterData',u.NiagaraExt_EmitterData,ref(system,en),{'bLocalSpace':True,'SimTarget':'CPUSim','bInterpolatedSpawning':False})
    setdata('SetRendererData',u.NiagaraExt_RendererData,ref(system,en,renderer=0),{'Material':DEST+'/M_ArrowRainGlow.M_ArrowRainGlow','MaterialUserParamBinding':{'Parameter':{'Name':'None'}},'SubImageSize':{'X':1,'Y':1},'bSubImageBlend':False,'Alignment':'Unaligned','FacingMode':'FaceCamera','bCastShadows':False,'CutoutTexture':None,'bUseMaterialCutoutTexture':False,'MotionVectorSetting':'Disable'})
    for key in ['Life Cycle Mode','Loop Behavior']:
        value=u.RainAssetEditor.read_input(source,'Explosion','EmitterUpdateScript','EmitterState',key).replace('NewEnumerator0','NewEnumerator1').replace('"System"','"Self"').replace('"Infinite"','"Once"')
        put(system,en,'EmitterUpdateScript','EmitterState',key,value,'/Script/NiagaraEditor.NiagaraExt_StackInputData_Enum')
    put(system,en,'EmitterUpdateScript','EmitterState','Loop Duration','(Value=.5)')
    API.call_method('AddModule',(ref(system,en,'EmitterUpdateScript'),u.load_asset('/Niagara/Modules/Emitter/SpawnBurst_Instantaneous')))
    put(system,en,'EmitterUpdateScript','SpawnBurst_Instantaneous','Spawn Count','(HlslExpression="floor(User.Count+.5)*3")' if impact else '(HlslExpression="1")','/Script/NiagaraEditor.NiagaraExt_StackInputData_HlslExpression')
    put(system,en,'EmitterUpdateScript','SpawnBurst_Instantaneous','Spawn Time','(Value=0)')
    a='frac((float(Particles.UniqueID)+User.Seed)*.618033989)';b='frac((float(Particles.UniqueID)+User.Seed)*.414213562)';age='Particles.Age';norm='Particles.NormalizedAge'
    if impact:
        origin='User.Impact31'
        for i in reversed(range(31)):origin=f'(floor(float(Particles.UniqueID)/3.0)=={i}.0?User.Impact{i}:{origin})'
        position=f'{origin}+float3(cos({a}*6.28318),sin({a}*6.28318),0)*{age}*(70+{b}*100)+float3(0,0,4+{age}*(150+{b}*90)-{age}*{age}*350)'
        size=f'float2(3.5,14)*(1-{norm}*.7)';life=f'.18+{a}*.18';alpha=f'.8*pow(1-{norm},1.8)'
    else:
        position='float3(0,0,0)';size=f'float2(125,125)*(1+{norm}*1.5)';life='.11';alpha=f'.8*pow(1-{norm},2)'
    common={'Particles.Position':(POSITION,position),'Particles.Velocity':(VEC3,'float3(0,0,0)'),
        'Particles.SpriteSize':(VEC2,size),'Particles.SpriteRotation':(FLOAT,f'{b}*360'),'Particles.SpriteUVScale':(VEC2,'float2(1,1)'),
        'Particles.Color':(COLOR,f'float4(.1,1,.3,{alpha})'),'Particles.SubImageIndex':(FLOAT,'0')}
    assignments(system,en,'ParticleSpawnScript',{'Particles.Lifetime':(FLOAT,life),**common});assignments(system,en,'ParticleUpdateScript',common)
def main():
    if Path(u.Paths.project_content_dir()).resolve()!=(ROOT/'Content').resolve():raise RuntimeError('Author host must share FPSGAME Content')
    dirty={str(p.get_path_name()) for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()}
    if any(p.startswith(DEST) for p in dirty):raise RuntimeError('Preserve unsaved Arrow Rain assets')
    EAL.make_directory(DEST);metal=materials();import_sources(metal);smoke('NS_ArrowRainBurst',False);smoke('NS_ArrowRainDust',True)
    from build_magic_arrow_rain_airburst_v2 import upgrade
    saved.extend(upgrade())
    from build_magic_arrow_rain_cone_impacts_v3 import upgrade as upgrade_cone_impacts
    saved.extend(upgrade_cone_impacts())
    from build_magic_arrow_rain_visibility_v4 import upgrade as upgrade_visibility
    saved.extend(upgrade_visibility())
    saved[:]=list(dict.fromkeys(saved))
    out=ROOT/'Saved/MagicArrowRain20261026';out.mkdir(parents=True,exist_ok=True)
    receipt={'saved_assets':saved,'gameplay_tested':False,'rendered':False,'source_directory':str(SRC),'only_owned_destination':DEST}
    (out/'asset-receipt.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2),encoding='utf-8');print('MAGIC_ARROW_RAIN_SAVED '+json.dumps(receipt))
if __name__=='__main__':main()
