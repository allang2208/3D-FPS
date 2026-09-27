"""Build scoped charge materials/audio, bind BP references, and save. No PIE or rendering."""
from pathlib import Path
import json, shutil
import unreal as u
ROOT=Path(__file__).resolve().parent;PROJECT=ROOT.parents[1];OUT=ROOT/'ChargeVisual';OUT.mkdir(exist_ok=True)
DEST='/Game/Monsters/FleshHand/ChargeVisual20260927';TAG='FleshHandChargeVisualV2'
E=u.EditorAssetLibrary;L=u.MaterialEditingLibrary;TOOLS=u.AssetToolsHelpers.get_asset_tools()
if Path(u.Paths.project_dir()).resolve()!=PROJECT.resolve():raise RuntimeError('Wrong project')
if '-run=' not in u.SystemLibrary.get_command_line().lower():
    if u.get_editor_subsystem(u.LevelEditorSubsystem).is_in_play_in_editor():raise RuntimeError('End PIE before importing')
bp_path='/Game/Monsters/FleshHand/BP_FleshHand'
dirty={p.get_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()}
if any(p==bp_path or p.startswith(DEST) for p in dirty):raise RuntimeError('Preserving unsaved target assets')
bp=u.load_asset(bp_path);cdo=u.get_default_object(bp.generated_class());cdo.get_editor_property('charge_dust_material')
report={'state':'authoring','saved':[],'runtime_tested':False,'rendered':False,'slots':8,
        'dust_cards':64,'air_cards':24,'decorative_chips':32,
        'dust_source':'/Game/Weapons/GunplayFX/T_MuzzleSmokeMantaflowV14',
        'renderer':'three shared ISM renderers, existing fluid detail budget'}
def record():(OUT/'installation.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
def backup(path):
    file=PROJECT/'Content'/(path.removeprefix('/Game/')+'.uasset');target=(ROOT.parents[1]/'trash/monster-hands-20260927/SourceAssets/FleshHand20260926/ChargeVisual/Before')/file.relative_to(PROJECT/'Content')
    if file.exists() and not target.exists():target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(file,target)
def load(path):
    obj=u.load_asset(path)
    if not obj:raise RuntimeError('Missing '+path)
    return obj
def save(obj):
    if isinstance(obj,u.Material):
        errors=L.recompile_material(obj)
        if errors:raise RuntimeError(str(errors))
    E.set_metadata_tag(obj,'FleshHand.ChargeVisual',TAG)
    if not E.save_loaded_asset(obj,False):raise RuntimeError('Save failed: '+obj.get_path_name())
    report['saved'].append(obj.get_path_name());record()
def node(m,cls):return L.create_material_expression(m,cls)
def wire(a,b,pin):
    obj,out=a if isinstance(a,tuple) else (a,'')
    if not L.connect_material_expressions(obj,out,b,pin):raise RuntimeError('Cannot connect '+pin)
def prop(m,a,name):
    if not L.connect_material_property(a,'',getattr(u.MaterialProperty,'MP_'+name)):raise RuntimeError('Cannot connect '+name)
def constant(m,v):
    n=node(m,u.MaterialExpressionConstant);n.set_editor_property('r',v);return n
def custom(m,code,inputs,width=1):
    n=node(m,u.MaterialExpressionCustom);n.set_editor_property('code',code);n.set_editor_property('description',TAG)
    n.set_editor_property('output_type',getattr(u.CustomMaterialOutputType,'CMOT_FLOAT'+str(width)))
    pins=[]
    for key in inputs:
        pin=u.CustomInput();pin.set_editor_property('input_name',key);pins.append(pin)
    n.set_editor_property('inputs',pins)
    for key,value in inputs.items():wire(value,n,key)
    return n
def data(m,index,default=0):
    n=node(m,u.MaterialExpressionPerInstanceCustomData);n.set_editor_property('data_index',index);n.set_editor_property('const_default_value',default)
    interp=node(m,u.MaterialExpressionVertexInterpolator);wire(n,interp,str(L.get_material_expression_input_names(interp)[0]));return interp
def scalar(m,name,value):
    n=node(m,u.MaterialExpressionScalarParameter);n.set_editor_property('parameter_name',name);n.set_editor_property('default_value',value);return n
def texture(m,name,path,kind):
    n=node(m,u.MaterialExpressionTextureObjectParameter);n.set_editor_property('parameter_name',name);n.set_editor_property('texture',load(path));n.set_editor_property('sampler_type',kind);return n
def material(name,lit=False,opaque=False,skin=False):
    path=DEST+'/'+name
    if E.does_asset_exist(path):
        m=load(path)
        if E.get_metadata_tag(m,'FleshHand.ChargeVisual')!=TAG:raise RuntimeError('Unowned material: '+path)
        backup(path)
        return m,False
    m=TOOLS.create_asset(name,DEST,u.Material,u.MaterialFactoryNew());m.set_editor_property('two_sided',True)
    m.set_editor_property('blend_mode',u.BlendMode.BLEND_OPAQUE if opaque else u.BlendMode.BLEND_TRANSLUCENT)
    m.set_editor_property('shading_model',u.MaterialShadingModel.MSM_DEFAULT_LIT if lit else u.MaterialShadingModel.MSM_UNLIT)
    if not opaque:
        m.set_editor_property('disable_depth_test',False);m.set_editor_property('output_translucent_velocity',False)
        m.set_editor_property('allow_front_layer_translucency',False)
        m.set_editor_property('translucency_lighting_mode',u.TranslucencyLightingMode.TLM_VOLUMETRIC_NON_DIRECTIONAL)
    L.set_base_material_usage(m,u.MaterialUsage.MATUSAGE_SKELETAL_MESH if skin else u.MaterialUsage.MATUSAGE_INSTANCED_STATIC_MESHES,True)
    return m,True
def surface(m,color,alpha,lit=False):
    slab=node(m,u.MaterialExpressionSubstrateShadingModels)
    slab.set_editor_property('shading_model_override',u.MaterialShadingModel.MSM_DEFAULT_LIT if lit else u.MaterialShadingModel.MSM_UNLIT)
    wire(color,slab,'BaseColor' if lit else 'Emissive Color');prop(m,color,'BASE_COLOR' if lit else 'EMISSIVE_COLOR')
    wire(alpha,slab,'Opacity');prop(m,alpha,'OPACITY')
    wire(constant(m,.95),slab,'Roughness');wire(constant(m,0),slab,'Specular');prop(m,slab,'FRONT_MATERIAL')
record()
dust,new=material('M_HandChargeDust',lit=True)
if new:
    uv=node(dust,u.MaterialExpressionTextureCoordinate)
    atlas=texture(dust,'DensityAtlas','/Game/Weapons/GunplayFX/T_MuzzleSmokeMantaflowV14',u.MaterialSamplerType.SAMPLERTYPE_MASKS)
    code=(PROJECT/'SourceAssets/ImpactSmokeCorrosion20260924/RollingSmoke.hlsl').read_text(encoding='utf-8')
    alpha=custom(dust,code,{'UV':uv,'Atlas':atlas,'Age':data(dust,2),'Seed':data(dust,1),'Alpha':data(dust,0)})
    fade=node(dust,u.MaterialExpressionDepthFade);fade.set_editor_property('fade_distance_default',12.)
    wire(alpha,fade,str(L.get_material_expression_input_names(fade)[0]))
    color=custom(dust,'return float3(.19,.155,.10);',{},3);surface(dust,color,fade,True)
save(dust)
air,new=material('M_HandChargeAir')
code=(ROOT/'ChargeAir.hlsl').read_text(encoding='utf-8')
if new:
    uv=node(air,u.MaterialExpressionTextureCoordinate)
    alpha=custom(air,code,{'UV':uv,'Alpha':data(air,0),'Clock':data(air,1),'Mode':data(air,2)})
    color=custom(air,'return float3(.42,.49,.36);',{},3);surface(air,color,alpha)
else:
    masks=[n for n in L.get_material_expressions(air) if isinstance(n,u.MaterialExpressionCustom)
           and n.get_editor_property('description') in (TAG,'FleshHandChargeAirMaskV3')
           and {str(pin.get_editor_property('input_name')) for pin in n.get_editor_property('inputs')}=={'UV','Alpha','Clock','Mode'}]
    if len(masks)!=1:raise RuntimeError('Expected one owned charge air mask; preserving material graph')
    alpha=masks[0];alpha.modify();alpha.set_editor_property('code',code)
alpha.set_editor_property('description','FleshHandChargeAirMaskV3')
save(air)
skin,new=material('M_HandChargeTension',skin=True)
if new:
    uv=node(skin,u.MaterialExpressionTextureCoordinate);tension=scalar(skin,'Tension',0)
    albedo=texture(skin,'SkinColor','/Game/Monsters/FleshHand/Textures/T_FleshHand_BaseColor',u.MaterialSamplerType.SAMPLERTYPE_COLOR)
    code='''float3 c=Texture2DSample(SkinColor,SkinColorSampler,UV).rgb;
float darkDetail=pow(saturate(1-dot(c,float3(.2126,.7152,.0722))*3.2),4);
return darkDetail*Tension*.14;'''
    alpha=custom(skin,code,{'UV':uv,'SkinColor':albedo,'Tension':tension})
    color=custom(skin,'return float3(.24,.33,.045);',{},3);surface(skin,color,alpha)
save(skin)
chip,new=material('M_HandChargeChip',lit=True,opaque=True)
if new:surface(chip,custom(chip,'return float3(.12,.10,.075);',{},3),constant(chip,1),True)
save(chip)
warning,new=material('M_HandChargeWarning')
if new:
    uv=node(warning,u.MaterialExpressionTextureCoordinate);progress=scalar(warning,'Progress',0)
    code='''float2 p=(UV-.5)*2;float r=length(p);float pulse=.84+.16*sin(6.283185*(2*Progress+2*Progress*Progress));
float ring=(1-smoothstep(.025,.060,abs(r-.66)))*.7;
float arrow=(1-smoothstep(.035,.065,abs(p.x-(.88-abs(p.y)*1.05))))*(1-smoothstep(.20,.27,abs(p.y)));
return saturate(max(ring,arrow)*pulse);'''
    alpha=custom(warning,code,{'UV':uv,'Progress':progress});color=custom(warning,'return float3(1,.20,.025)*(1+.25*Progress);',{'Progress':progress},3)
    surface(warning,color,alpha)
save(warning)
sounds={}
for name in ['S_HandChargeWindup','S_HandChargeRush']:
    path=DEST+'/'+name
    if E.does_asset_exist(path):sound=load(path)
    else:
        task=u.AssetImportTask();task.filename=str(OUT/(name+'.wav'));task.destination_path=DEST;task.destination_name=name
        task.automated=True;task.replace_existing=False;task.save=False;TOOLS.import_asset_tasks([task]);sound=load(path)
    sound.set_editor_property('looping',False);save(sound);sounds[name]=sound
backup(bp_path);bp.modify();cdo.modify()
for prop_name,value in {'charge_dust_material':dust,'charge_air_material':air,'charge_skin_material':skin,
    'charge_chip_material':chip,'charge_warning_material':warning,
    'charge_fx_plane':load('/Engine/BasicShapes/Plane'),'charge_fx_cube':load('/Engine/BasicShapes/Cube'),
    'charge_windup_sound':sounds['S_HandChargeWindup'],'charge_rush_sound':sounds['S_HandChargeRush']}.items():cdo.set_editor_property(prop_name,value)
save(bp);report['state']='assets_saved_and_bound';record();print('FLESHHAND_CHARGE_VISUAL_SAVED '+str(OUT/'installation.json'))
