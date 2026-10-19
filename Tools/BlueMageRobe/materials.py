"""Production PBR shaders, shared by all native robe bindings."""
import unreal as u
from pathlib import Path
P=Path('D:/FPS3D/FPSGAME');R=P/'SourceAssets/BlueMageRobe20261018';DEST='/Game/Characters/ModularOutfit20260924/BlueMageRobe20261018'
E=u.EditorAssetLibrary;A=u.AssetToolsHelpers.get_asset_tools();L=u.MaterialEditingLibrary
def save(asset):
    if not asset.get_path_name().startswith(DEST+'/'):raise RuntimeError('Material output outside robe scope')
    asset.modify()
    if not E.save_loaded_asset(asset,False):raise RuntimeError('Cannot save '+asset.get_path_name())
def load(path):
    asset=u.load_asset(path)
    if not asset:raise RuntimeError('Missing '+path)
    return asset
def textures():
    result={}
    for family in ('BlueMageFabric','BlueMageEmbroidery'):
        for channel in ('BaseColor','Normal','ORM'):
            name='T_'+family+'_'+channel;task=u.AssetImportTask();task.filename=str(R/'Textures'/(name+'.png'));task.destination_path=DEST+'/Textures';task.destination_name=name;task.automated=True;task.replace_existing=True;task.save=True
            A.import_asset_tasks([task]);asset=load(DEST+'/Textures/'+name)
            asset.set_editor_property('srgb',channel=='BaseColor')
            asset.set_editor_property('compression_settings',u.TextureCompressionSettings.TC_NORMALMAP if channel=='Normal' else u.TextureCompressionSettings.TC_MASKS if channel=='ORM' else u.TextureCompressionSettings.TC_DEFAULT)
            if channel=='Normal':asset.set_editor_property('flip_green_channel',True)
            if family=='BlueMageEmbroidery':asset.set_editor_property('address_y',u.TextureAddress.TA_CLAMP)
            save(asset);result[family+'_'+channel]=asset
    return result
def connect(a,b,pin,out=''):
    if not L.connect_material_expressions(a,out,b,pin):raise RuntimeError('Robe shader connection '+pin)
def material(name,tex,kind='fabric',length=90.):
    path=DEST+'/Materials/'+name;mat=u.load_asset(path) or A.create_asset(name,DEST+'/Materials',u.Material,u.MaterialFactoryNew())
    L.delete_all_material_expressions(mat);mat.set_editor_property('two_sided',kind=='skirt');L.set_material_usage(mat,u.MaterialUsage.MATUSAGE_SKELETAL_MESH)
    if kind=='skirt':L.set_material_usage(mat,u.MaterialUsage.MATUSAGE_CLOTHING)
    uv=L.create_material_expression(mat,u.MaterialExpressionTextureCoordinate);inputs={'UV':uv}
    wanted=['BlueMageEmbroidery'] if kind=='embroidery' else ['BlueMageFabric','BlueMageEmbroidery'] if kind=='skirt' else ['BlueMageFabric']
    for family in wanted:
        for channel in ('BaseColor','Normal','ORM'):
            key=family+'_'+channel;node=L.create_material_expression(mat,u.MaterialExpressionTextureObjectParameter);node.set_editor_property('parameter_name',key);node.set_editor_property('texture',tex[key]);node.set_editor_property('sampler_type',u.MaterialSamplerType.SAMPLERTYPE_NORMAL if channel=='Normal' else u.MaterialSamplerType.SAMPLERTYPE_COLOR if channel=='BaseColor' else u.MaterialSamplerType.SAMPLERTYPE_MASKS);inputs[key]=node
    if kind=='skirt':inputs['Side']=L.create_material_expression(mat,u.MaterialExpressionTwoSidedSign)
    family='BlueMageEmbroidery' if kind=='embroidery' else 'BlueMageFabric'
    coords='UV' if kind=='embroidery' else f'float2(UV.x*lerp(90.,205.,saturate(UV.y))/4.,(1-UV.y)*{length:.6f}/4.)' if kind=='skirt' else 'UV*6.25'
    code=f'''float2 fuv={coords};
float3 color=Texture2DSample({family}_BaseColor,{family}_BaseColorSampler,fuv).rgb;
float2 normal=Texture2DSample({family}_Normal,{family}_NormalSampler,fuv).rg*2-1;
float3 orm=Texture2DSample({family}_ORM,{family}_ORMSampler,fuv).rgb;
'''
    if kind=='lining':code+='color*=float3(.40,.43,.52);orm.g=max(orm.g,.9);normal*=.65;\n'
    elif kind=='hood':code+='color*=.85;\n'
    elif kind=='belt':code+='color*=float3(.22,.27,.34);orm.g=.52;normal*=.25;\n'
    elif kind=='skirt':
        code+=f'''float circumference=lerp(90.,205.,saturate(UV.y));
float arc=min(abs(frac(UV.x+.5)-.5),abs(UV.x-.5))*circumference;
float hemCm=(1-UV.y)*{length:.6f};
float hem=1-smoothstep(3.4,3.65,hemCm);
float rails=(1-smoothstep(.34,.44,abs(arc-1.5)))*smoothstep(0.,.025,UV.y);
float2 trimUV=hem>rails?float2(UV.x*circumference/44.,saturate(hemCm/3.5)):float2(UV.y*{length:.6f}/22.,saturate((arc-1.1)/.8));
float3 tc=Texture2DSample(BlueMageEmbroidery_BaseColor,BlueMageEmbroidery_BaseColorSampler,trimUV).rgb;
float2 tn=Texture2DSample(BlueMageEmbroidery_Normal,BlueMageEmbroidery_NormalSampler,trimUV).rg*2-1;
float3 to=Texture2DSample(BlueMageEmbroidery_ORM,BlueMageEmbroidery_ORMSampler,trimUV).rgb;
float trim=saturate(max(hem,rails));color=lerp(color,tc,trim);normal=lerp(normal,tn,trim);orm=lerp(orm,to,trim);
float inset=(1-smoothstep(.65,.95,arc))*smoothstep(.02,.10,UV.y);color*=1-.38*inset;
color*=Side<0?float3(.43,.45,.55):float3(1,1,1);
'''
    code+='OutNormal=normalize(float3(normal,sqrt(saturate(1-dot(normal,normal)))));OutRoughness=orm.g;OutMetallic=orm.b;OutAO=orm.r;return color;'
    custom=L.create_material_expression(mat,u.MaterialExpressionCustom);custom.set_editor_property('code',code);custom.set_editor_property('output_type',u.CustomMaterialOutputType.CMOT_FLOAT3)
    pins=[]
    for key in inputs:pin=u.CustomInput();pin.set_editor_property('input_name',key);pins.append(pin)
    custom.set_editor_property('inputs',pins);outs=[]
    for key,kind_type in [('OutNormal',u.CustomMaterialOutputType.CMOT_FLOAT3),('OutRoughness',u.CustomMaterialOutputType.CMOT_FLOAT1),('OutMetallic',u.CustomMaterialOutputType.CMOT_FLOAT1),('OutAO',u.CustomMaterialOutputType.CMOT_FLOAT1)]:out=u.CustomOutput();out.set_editor_property('output_name',key);out.set_editor_property('output_type',kind_type);outs.append(out)
    custom.set_editor_property('additional_outputs',outs)
    for key,node in inputs.items():connect(node,custom,key)
    for output,prop in [('',u.MaterialProperty.MP_BASE_COLOR),('OutNormal',u.MaterialProperty.MP_NORMAL),('OutRoughness',u.MaterialProperty.MP_ROUGHNESS),('OutMetallic',u.MaterialProperty.MP_METALLIC),('OutAO',u.MaterialProperty.MP_AMBIENT_OCCLUSION)]:
        if not L.connect_material_property(custom,output,prop):raise RuntimeError('Robe shader output')
    errors=[str(e) for e in (L.recompile_material(mat) or [])]
    if errors:raise RuntimeError('Robe material '+str(errors))
    save(mat);return mat
def solid(name,color,metallic,roughness):
    mat=u.load_asset(DEST+'/Materials/'+name) or A.create_asset(name,DEST+'/Materials',u.Material,u.MaterialFactoryNew());L.delete_all_material_expressions(mat);L.set_material_usage(mat,u.MaterialUsage.MATUSAGE_SKELETAL_MESH)
    node=L.create_material_expression(mat,u.MaterialExpressionConstant3Vector);node.set_editor_property('constant',u.LinearColor(*color,1.));L.connect_material_property(node,'',u.MaterialProperty.MP_BASE_COLOR)
    for value,prop in [(metallic,u.MaterialProperty.MP_METALLIC),(roughness,u.MaterialProperty.MP_ROUGHNESS)]:n=L.create_material_expression(mat,u.MaterialExpressionConstant);n.set_editor_property('r',value);L.connect_material_property(n,'',prop)
    L.recompile_material(mat);save(mat);return mat
def create(lengths):
    tex=textures();fabric=material('M_BlueMage_Fabric',tex);lining=material('M_BlueMage_Lining',tex,'lining');embroidery=material('M_BlueMage_Embroidery',tex,'embroidery');hood=material('M_BlueMage_Hood',tex,'hood');belt=material('M_BlueMage_Belt',tex,'belt');metal=solid('M_BlueMage_Silver',(.48,.46,.40),1.,.34);gem=solid('M_BlueMage_Gem',(.012,.08,.45),.45,.10)
    result={}
    for profile,length in lengths.items():
        skirt=material('M_BlueMage_Skirt_'+profile,tex,'skirt',length)
        result[profile]=[fabric,fabric,embroidery,lining,skirt,hood,embroidery,belt,metal,lining,lining,gem]
    result['FP']=[fabric,fabric,embroidery,lining,fabric,hood,embroidery,belt,metal,lining,lining,gem]
    return result
