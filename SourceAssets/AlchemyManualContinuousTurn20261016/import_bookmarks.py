"""Save only the adopted V8 proportional bookmark print and interactive materials."""
import json
from pathlib import Path
import unreal as u
ROOT=Path('D:/FPS3D/FPSGAME/SourceAssets/AlchemyManualContinuousTurn20261016')
HOST=ROOT.parent/'PotionWorkbenchDesign20261015/IntegrationV1/UEImportHost'
if Path(u.Paths.project_dir()).resolve()!=HOST.resolve():raise RuntimeError('Use the isolated manual import host')
DEST='/Game/Building/PotionWorkbench20261015/ManualV8'
V5='/Game/Building/PotionWorkbench20261015/ManualV5/Textures/'
V6='/Game/Building/PotionWorkbench20261015/ManualV6/Textures/'
A=u.AssetToolsHelpers.get_asset_tools();E=u.EditorAssetLibrary;L=u.MaterialEditingLibrary
report=dict(complete=False,saved=[],compile_errors={},runtime_tested=False)
def record():(ROOT/'import-receipt.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
def save(obj):
    if not E.save_loaded_asset(obj,False):raise RuntimeError('Save failed '+obj.get_path_name())
    report['saved'].append(obj.get_path_name());record()
def node(m,kind,**values):
    n=L.create_material_expression(m,kind)
    for key,value in values.items():n.set_editor_property(key,value)
    return n
def wire(a,out,b,pin):
    names=[str(x) for x in L.get_material_expression_input_names(b)]
    if pin not in names and len(names)==1:pin=names[0]
    if not L.connect_material_expressions(a,out,b,pin):raise RuntimeError('Cannot connect '+pin)
def prop(n,p,out=''):
    if not L.connect_material_property(n,out,p):raise RuntimeError('Cannot connect material property')
def scalar(m,v,p):prop(node(m,u.MaterialExpressionConstant,r=v),p)
def parameter(m,name,value):return node(m,u.MaterialExpressionScalarParameter,parameter_name=name,default_value=value)
def texture(m,path,kind='color'):
    t=u.load_asset(path)
    if not t:raise RuntimeError('Missing '+path)
    return node(m,u.MaterialExpressionTextureSample,texture=t,sampler_type={'color':u.MaterialSamplerType.SAMPLERTYPE_COLOR,'normal':u.MaterialSamplerType.SAMPLERTYPE_NORMAL,'mask':u.MaterialSamplerType.SAMPLERTYPE_MASKS}[kind])
def custom(m,code,args,vector=False):
    inputs=[]
    for name,_ in args:
        pin=u.CustomInput();pin.set_editor_property('input_name',name);inputs.append(pin)
    n=node(m,u.MaterialExpressionCustom,code=code,inputs=inputs,output_type=u.CustomMaterialOutputType.CMOT_FLOAT3 if vector else u.CustomMaterialOutputType.CMOT_FLOAT1)
    for name,value in args:wire(value,'',n,name)
    return n
def material(name):
    m=u.load_asset(DEST+'/Materials/'+name) if E.does_asset_exist(DEST+'/Materials/'+name) else A.create_asset(name,DEST+'/Materials',u.Material,u.MaterialFactoryNew())
    L.delete_all_material_expressions(m);return m
def finish(m):
    errors=[str(x) for x in L.recompile_material(m)];report['compile_errors'][m.get_name()]=errors;record()
    if errors:raise RuntimeError(str(errors))
    save(m)
def offset(m,expression):
    world=node(m,u.MaterialExpressionTransform,transform_source_type=u.MaterialVectorCoordTransformSource.TRANSFORMSOURCE_LOCAL,transform_type=u.MaterialVectorCoordTransform.TRANSFORM_WORLD)
    wire(expression,'',world,'Input');prop(world,u.MaterialProperty.MP_WORLD_POSITION_OFFSET)
task=u.AssetImportTask();task.filename=str(ROOT/'Textures/T_ManualRibbonProportional.png')
task.destination_path=DEST+'/Textures';task.destination_name='T_ManualRibbonProportional'
task.automated=True;task.replace_existing=True;task.save=False;A.import_asset_tasks([task])
print_texture=u.load_asset(DEST+'/Textures/T_ManualRibbonProportional')
if not print_texture:raise RuntimeError('Bookmark print import failed')
print_texture.set_editor_property('srgb',True);print_texture.set_editor_property('lod_group',u.TextureGroup.TEXTUREGROUP_UI)
print_texture.set_editor_property('mip_gen_settings',u.TextureMipGenSettings.TMGS_NO_MIPMAPS)
print_texture.set_editor_property('never_stream',True)
print_texture.set_editor_property('address_x',u.TextureAddress.TA_CLAMP);print_texture.set_editor_property('address_y',u.TextureAddress.TA_CLAMP);save(print_texture)

for name,cloth in [('M_ManualRibbonInteractive',True),('M_ManualClaspInteractive',False)]:
    m=material(name);position=node(m,u.MaterialExpressionPreSkinnedPosition)
    lift=custom(m,'return float3(0,0,lerp(L,R,step(0,P.x)));',[('P',position),('L',parameter(m,'BookmarkLiftLeft',0.)),('R',parameter(m,'BookmarkLiftRight',0.))],True);offset(m,lift)
    fade=custom(m,'return lerp(L,R,step(0,P.x));',[('P',position),('L',parameter(m,'BookmarkFadeLeft',1.)),('R',parameter(m,'BookmarkFadeRight',1.))])
    pixel=node(m,u.MaterialExpressionVertexInterpolator,desc='Bookmark side fade: vertex to pixel');wire(fade,'',pixel,'Input')
    if cloth:
        color=texture(m,DEST+'/Textures/T_ManualRibbonProportional');out='RGB'
        prop(texture(m,V6+'T_ManualRibbonV6Normal','normal'),u.MaterialProperty.MP_NORMAL,'RGB')
        prop(texture(m,V6+'T_ManualRibbonV6Roughness','mask'),u.MaterialProperty.MP_ROUGHNESS,'R');scalar(m,.28,u.MaterialProperty.MP_SPECULAR)
    else:
        color=node(m,u.MaterialExpressionConstant3Vector,constant=u.LinearColor(.33,.24,.12));out=''
        scalar(m,.68,u.MaterialProperty.MP_METALLIC);scalar(m,.44,u.MaterialProperty.MP_ROUGHNESS)
    tinted=node(m,u.MaterialExpressionMultiply);wire(color,out,tinted,'A');wire(pixel,'',tinted,'B');prop(tinted,u.MaterialProperty.MP_BASE_COLOR)
    readable=node(m,u.MaterialExpressionMultiply,desc='Bookmark shadow readability fill');wire(tinted,'',readable,'A');wire(parameter(m,'BookmarkReadFill',.42 if cloth else .22),'',readable,'B');prop(readable,u.MaterialProperty.MP_EMISSIVE_COLOR);finish(m)


report['complete']=True
record()
u.log('MANUAL_BOOKMARK_ASSETS_SAVED')
