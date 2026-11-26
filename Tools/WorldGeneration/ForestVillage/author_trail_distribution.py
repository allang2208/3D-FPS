"""Apply the metric road fields and distant grass colour only to the village-region ground."""
import os
from pathlib import Path
import unreal as u

ed=u.MaterialEditingLibrary
lib=u.EditorAssetLibrary
folder='/Game/ForestPathStudy/VillageRegion/Reference'
mat=u.load_asset(folder+'/M_ForestReferenceMesh')
source=Path(os.environ['FPS_FOREST_REFERENCE_SOURCE'])/'Grass/T_HillsTrailField.png'
task=u.AssetImportTask()
task.filename=str(source)
task.destination_path=folder
task.destination_name='T_HillsTrailField'
task.automated=True
task.replace_existing=True
u.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
texture=u.load_asset(folder+'/T_HillsTrailField')
texture.set_editor_property('srgb',False)
texture.set_editor_property('compression_settings',u.TextureCompressionSettings.TC_BC7)
for k in ('address_x','address_y'):texture.set_editor_property(k,u.TextureAddress.TA_CLAMP)

def save(obj):
    if not lib.save_loaded_asset(obj,False):raise RuntimeError(obj.get_path_name())

def wire(a,out,b,pin):
    if not ed.connect_material_expressions(a,out,b,pin):raise RuntimeError(b.get_name()+'.'+pin)

def node(parent,kind,x,y):
    if isinstance(parent,u.Material):return ed.create_material_expression(parent,kind,x,y)
    return ed.create_material_expression_in_function(parent,kind,x,y)

def custom(parent,code,args,type_,x,y):
    n=node(parent,u.MaterialExpressionCustom,x,y)
    inputs=[]
    for name,src,pin in args:
        a=u.CustomInput();a.set_editor_property('input_name',name);inputs.append(a)
    n.set_editor_property('inputs',inputs);n.set_editor_property('code',code)
    n.set_editor_property('output_type',type_)
    for name,src,pin in args:wire(src,pin,n,name)
    return n

def inputs(n):
    return dict(zip(map(str,ed.get_material_expression_input_names(n)),ed.get_inputs_for_material_expression(mat,n)))

types=u.CustomMaterialOutputType
def atlas(parent):
    pos=node(parent,u.MaterialExpressionWorldPosition,-3700,2700)
    uv=custom(parent,'return (P.xy+float2(62400,32000))/102400.;',[('P',pos,'')],types.CMOT_FLOAT2,-3450,2700)
    n=node(parent,u.MaterialExpressionTextureSample,-3200,2700)
    n.set_editor_property('texture',texture)
    n.set_editor_property('sampler_type',u.MaterialSamplerType.SAMPLERTYPE_LINEAR_COLOR)
    n.set_editor_property('mip_value_mode',u.TextureMipValueMode.TMVM_MIP_LEVEL)
    wire(uv,'',n,'UVs')
    return n,pos

save(texture)
path=folder+'/MF_TrailDirt'
fn=u.load_asset(path) if lib.does_asset_exist(path) else lib.duplicate_asset('/Game/Landscape/Materials/Functions/MF_Material',path)
if not fn:raise RuntimeError(path)
nodes=list(ed.get_material_function_expressions(fn))
tag='R18 continuous road texture coordinates'
if not any(str(n.get_editor_property('desc'))==tag for n in nodes):
    field,_=atlas(fn)
    seen=set()
    for n in nodes:
        if not isinstance(n,u.MaterialExpressionMultiply):continue
        pins=inputs(n);scale=pins.get('B')
        if not isinstance(scale,u.MaterialExpressionFunctionInput):continue
        key=str(scale.get_editor_property('input_name'))
        if key not in ('Size','SizeFar'):continue
        original=pins['A']
        warp=custom(fn,'return UV + (Field.gb-.5)*7.0;', [('UV',original,''),('Field',field,'RGB')],types.CMOT_FLOAT2,-2750,2400+len(seen)*240)
        warp.set_editor_property('desc',tag);wire(warp,'',n,'A')
        seen.add(key)
    if seen!={'Size','SizeFar'}:raise RuntimeError('Road coordinate inputs '+str(seen))
    ed.update_material_function(fn);save(fn)
calls=[]
nodes=list(ed.get_material_expressions(mat))
for n in nodes:
    if not isinstance(n,u.MaterialExpressionMaterialFunctionCall):continue
    size=inputs(n).get('Size')
    if isinstance(size,u.MaterialExpressionScalarParameter) and str(size.get_editor_property('parameter_name'))=='Size C':
        calls.append(n)
if len(calls)!=1:raise RuntimeError('Road C function count '+str(len(calls)))
if calls[0].get_editor_property('material_function')!=fn and not calls[0].set_material_function(fn):raise RuntimeError('Road projection')
tag='R18 distant grass drifts and road wear'
if not any(str(n.get_editor_property('desc'))==tag for n in nodes):
    root=ed.get_material_property_input_node(mat,u.MaterialProperty.MP_MATERIAL_ATTRIBUTES)
    color=inputs(root)['BaseColor']
    field,pos=atlas(mat)
    cam=node(mat,u.MaterialExpressionCameraPositionWS,-3550,3330)
    weights=node(mat,u.MaterialExpressionTextureCoordinate,-3500,3600)
    weights.set_editor_property('coordinate_index',4)
    # Keep the original near material; the grass film retains the ground normal, detail and lighting.
    final=custom(mat,"""float d=distance(P.xyz,Eye.xyz);
        float grass=F.r*smoothstep(4500.,9000.,d)*(1.-smoothstep(18500.,23500.,d));
        float lum=dot(C,float3(.30,.59,.11));
        float3 turf=lum*float3(.70,1.15,.51);
        float road=saturate(W.x)*(F.g*.64+F.b*.36-.5);
        return lerp(C,turf,grass*.62)*(1.+road*.30);""",[('C',color,''),('F',field,'RGB'),('P',pos,''),('Eye',cam,''),('W',weights,'')],types.CMOT_FLOAT3,-2350,2940)
    final.set_editor_property('desc',tag);wire(final,'',root,'BaseColor')
errors=ed.recompile_material(mat)
if errors:raise RuntimeError(str(errors))
save(mat)
