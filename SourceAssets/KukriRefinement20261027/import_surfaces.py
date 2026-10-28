import json,sys
from pathlib import Path
import unreal as u
P=Path(r'D:/FPS3D/FPSGAME/SourceAssets/KukriRefinement20261027')
sys.path.insert(0,str(P))
from import_mesh import import_mesh
data=json.loads((P/'surfaces.json').read_text(encoding='utf-8'))
A=u.AssetToolsHelpers.get_asset_tools();E=u.MaterialEditingLibrary
receipt={'complete':False,'saved_assets':[],'runtime_tested':False,'numeric_changes':False}
def save(asset):
    if not u.EditorLoadingAndSavingUtils.save_packages([asset.get_outermost()],False):raise RuntimeError('Save failed '+asset.get_path_name())
    receipt['saved_assets'].append(asset.get_path_name())
    (P/'Receipts/import-surfaces.json').write_text(json.dumps(receipt,indent=2),encoding='utf-8')
    return asset
def node(m,cls,**kw):
    n=E.create_material_expression(m,cls)
    for k,v in kw.items():n.set_editor_property(k,v)
    return n
def link(a,pin,b,target):
    if not E.connect_material_expressions(a,pin,b,target):raise RuntimeError('Material link '+target)
def out(a,pin,prop):
    if not E.connect_material_property(a,pin,prop):raise RuntimeError('Material output '+str(prop))
def custom(m,code,inputs):
    n=node(m,u.MaterialExpressionCustom,code=code,output_type=u.CustomMaterialOutputType.CMOT_FLOAT3)
    fields=[]
    for name,_,_ in inputs:
        entry=u.CustomInput();entry.set_editor_property('input_name',name);fields.append(entry)
    n.set_editor_property('inputs',fields)
    for name,src,pin in inputs:link(src,pin,n,name)
    return n
def transform(m,source,pin,src,dst):
    n=node(m,u.MaterialExpressionTransform,transform_source_type=src,transform_type=dst);link(source,pin,n,'');return n
def texture(filename,dest,channel):
    task=u.AssetImportTask();task.filename=filename;task.destination_path=dest;task.destination_name=Path(filename).stem
    task.factory=u.TextureFactory();task.automated=True;task.replace_existing=True;task.replace_existing_settings=True;task.save=False
    A.import_asset_tasks([task]);tex=u.load_asset(dest+'/'+task.destination_name)
    if not task.imported_object_paths or not tex:raise RuntimeError('Import failed '+filename)
    tex.set_editor_properties({'srgb':channel=='BaseColor','compression_settings':{
        'BaseColor':u.TextureCompressionSettings.TC_BC7,'ORM':u.TextureCompressionSettings.TC_MASKS,'Normal':u.TextureCompressionSettings.TC_NORMALMAP}[channel],
        'lod_group':{'BaseColor':u.TextureGroup.TEXTUREGROUP_WEAPON,'ORM':u.TextureGroup.TEXTUREGROUP_WEAPON_SPECULAR,'Normal':u.TextureGroup.TEXTUREGROUP_WEAPON_NORMAL_MAP}[channel],
        'flip_green_channel':channel=='Normal','never_stream':False,'max_texture_size':2048,
        'mip_gen_settings':u.TextureMipGenSettings.TMGS_FROM_TEXTURE_GROUP})
    return save(tex)

def hanging_material(entry,maps):
    package=entry['material'].split('.')[0];folder,name=package.rsplit('/',1)
    m=u.load_asset(package) or A.create_asset(name,folder,u.Material,u.MaterialFactoryNew())
    E.delete_all_material_expressions(m);m.set_editor_property('tangent_space_normal',False)
    m.set_editor_property('used_with_skeletal_mesh',False);m.set_editor_property('two_sided',False)
    base=node(m,u.MaterialExpressionTextureSample,texture=maps['BaseColor'],sampler_type=u.MaterialSamplerType.SAMPLERTYPE_COLOR)
    orm=node(m,u.MaterialExpressionTextureSample,texture=maps['ORM'],sampler_type=u.MaterialSamplerType.SAMPLERTYPE_MASKS)
    normal=node(m,u.MaterialExpressionTextureSample,texture=maps['Normal'],sampler_type=u.MaterialSamplerType.SAMPLERTYPE_NORMAL)
    spec=entry['dynamics']
    skin=node(m,u.MaterialExpressionTextureCoordinate,coordinate_index=spec['skin_uv_channel'])
    active=node(m,u.MaterialExpressionScalarParameter,parameter_name='TasselActive',default_value=0.)
    bindings=[('Skin',skin,''),('Active',active,'')]
    for i,rest in enumerate(spec['guides_cm'][:7]):
        r=node(m,u.MaterialExpressionConstant3Vector,constant=u.LinearColor(*rest,0))
        p=node(m,u.MaterialExpressionVectorParameter,parameter_name='TasselP'+str(i),default_value=u.LinearColor(*rest,0))
        q=node(m,u.MaterialExpressionVectorParameter,parameter_name='TasselQ'+str(i),default_value=u.LinearColor(0,0,0,1))
        qa=node(m,u.MaterialExpressionAppendVector);link(q,'RGB',qa,'A');link(q,'A',qa,'B')
        bindings.extend([('R'+str(i),r,''),('P'+str(i),p,'RGB'),('Q'+str(i),qa,'')])
    wp=node(m,u.MaterialExpressionWorldPosition,world_position_shader_offset=u.WorldPositionIncludedOffsets.WPT_EXCLUDE_ALL_SHADER_OFFSETS)
    lp=node(m,u.MaterialExpressionTransformPosition,transform_source_type=u.MaterialPositionTransformSource.TRANSFORMPOSSOURCE_WORLD,transform_type=u.MaterialPositionTransformSource.TRANSFORMPOSSOURCE_LOCAL);link(wp,'',lp,'')
    prefix='float3 R[7]={R0,R1,R2,R3,R4,R5,R6}; float3 P[7]={P0,P1,P2,P3,P4,P5,P6}; float4 Q[7]={Q0,Q1,Q2,Q3,Q4,Q5,Q6}; int a=clamp((int)floor(Skin.x+0.01),0,6); int b=min(a+1,6); float w=saturate(1.0-Skin.y); '
    code='if(V.z>=R0.z)return float3(0,0,0); '+prefix+'float3 va=V-R[a],vb=V-R[b]; float3 pa=va+2*cross(Q[a].xyz,cross(Q[a].xyz,va)+Q[a].w*va)+P[a]; float3 pb=vb+2*cross(Q[b].xyz,cross(Q[b].xyz,vb)+Q[b].w*vb)+P[b]; return (lerp(pa,pb,w)-V)*Active;'
    deform=custom(m,code,bindings+[('V',lp,'')])
    offset=transform(m,deform,'',u.MaterialVectorCoordTransformSource.TRANSFORMSOURCE_LOCAL,u.MaterialVectorCoordTransform.TRANSFORM_WORLD)
    out(offset,'',u.MaterialProperty.MP_WORLD_POSITION_OFFSET)
    local_n=transform(m,normal,'RGB',u.MaterialVectorCoordTransformSource.TRANSFORMSOURCE_TANGENT,u.MaterialVectorCoordTransform.TRANSFORM_LOCAL)
    code_n='if(Pos.z>=R0.z)return normalize(V); '+prefix+'float3 na=V+2*cross(Q[a].xyz,cross(Q[a].xyz,V)+Q[a].w*V); float3 nb=V+2*cross(Q[b].xyz,cross(Q[b].xyz,V)+Q[b].w*V); return normalize(lerp(V,lerp(na,nb,w),Active));'
    turned=custom(m,code_n,bindings+[('V',local_n,''),('Pos',lp,'')])
    world_n=transform(m,turned,'',u.MaterialVectorCoordTransformSource.TRANSFORMSOURCE_LOCAL,u.MaterialVectorCoordTransform.TRANSFORM_WORLD)
    slab=node(m,u.MaterialExpressionSubstrateShadingModels,shading_model_override=u.MaterialShadingModel.MSM_DEFAULT_LIT)
    for src,pin,prop,target in [(base,'RGB',u.MaterialProperty.MP_BASE_COLOR,'BaseColor'),(orm,'G',u.MaterialProperty.MP_ROUGHNESS,'Roughness'),(orm,'B',u.MaterialProperty.MP_METALLIC,'Metallic'),(world_n,'',u.MaterialProperty.MP_NORMAL,'Normal')]:
        link(src,pin,slab,target);out(src,pin,prop)
    out(orm,'R',u.MaterialProperty.MP_AMBIENT_OCCLUSION);out(slab,'',u.MaterialProperty.MP_FRONT_MATERIAL)
    E.layout_material_expressions(m);E.recompile_material(m)
    u.EditorAssetLibrary.set_metadata_tag(m,'Kukri.Refinement','Eight-guide WPO with deformed world normals; UV2 skin; fixed root; PBR UV0')
    return save(m)

for entry in data['variants']:
    maps={k:texture(f,entry['texture_root'],k) for k,f in entry['textures'].items()}
    if 'dynamics' in entry:
        material=hanging_material(entry,maps)
        mesh=import_mesh(entry['fbx'],entry['mesh'],material)
        u.EditorAssetLibrary.set_metadata_tag(mesh,'Kukri.Source',str(P/'Kukri_Refinement_Editable.blend'))
        save(mesh)

# Preserve each blade's material and tint while making the three optional marks
# read as shallow engraved inlays. Existing instances continue to select RuneMask.
root='/Game/Weapons/Kukri20261020/ComponentVariants20261026/Runes'
for kind in ('Factory','Swift','HeavyBack','FoldedBalanced'):
    m=u.load_asset(root+'/Materials/M_KukriMark_'+kind)
    nodes=E.get_material_expressions(m)
    normal=next(n for n in nodes if isinstance(n,u.MaterialExpressionTextureSample) and n.get_editor_property('sampler_type')==u.MaterialSamplerType.SAMPLERTYPE_NORMAL)
    slab=next(n for n in nodes if isinstance(n,u.MaterialExpressionSubstrateShadingModels))
    height=node(m,u.MaterialExpressionTextureObjectParameter,parameter_name='RuneMask',texture=u.load_asset(root+'/Textures/T_KukriMask_RuneWing'),sampler_type=u.MaterialSamplerType.SAMPLERTYPE_MASKS)
    uv=node(m,u.MaterialExpressionTextureCoordinate,coordinate_index=0)
    code='float2 d=float2(1.0/2048.0,0); float l=Texture2DSample(HeightTex,HeightTexSampler,UV-d.xy).r; float r=Texture2DSample(HeightTex,HeightTexSampler,UV+d.xy).r; float b=Texture2DSample(HeightTex,HeightTexSampler,UV-d.yx).r; float t=Texture2DSample(HeightTex,HeightTexSampler,UV+d.yx).r; return normalize(float3(BaseNormal.xy+float2(r-l,t-b)*0.32,BaseNormal.z));'
    relief=custom(m,code,[('HeightTex',height,''),('UV',uv,''),('BaseNormal',normal,'RGB')])
    link(relief,'',slab,'Normal');out(relief,'',u.MaterialProperty.MP_NORMAL)
    E.layout_material_expressions(m);E.recompile_material(m);save(m)
receipt['complete']=True
(P/'Receipts/import-surfaces.json').write_text(json.dumps(receipt,indent=2),encoding='utf-8')
u.log('KUKRI_REFINEMENT_SURFACES_SAVED '+str(len(receipt['saved_assets'])))
