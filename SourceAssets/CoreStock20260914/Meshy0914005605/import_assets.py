"""Import the independent Meshy revision and author its final per-rifle materials."""
import unreal as u,json
from pathlib import Path
P=Path(__file__).resolve().parent;D='/Game/Weapons/CoreStock20260914/Meshy0914005605'
A=u.AssetToolsHelpers.get_asset_tools();E=u.EditorAssetLibrary;M=u.MaterialEditingLibrary
report={'stage':'import and save only','runtime_tested':False,'assets':{}}
def save(asset):
    if not E.save_loaded_asset(asset,False):raise RuntimeError('Save failed: '+asset.get_path_name())
def load(path):
    result=u.load_asset(path)
    if not result:raise RuntimeError('Required dependency missing: '+path)
    return result
def import_file(file,name,dest,options=None):
    t=u.AssetImportTask();t.filename=str(file);t.destination_path=dest;t.destination_name=name;t.options=options;t.automated=True;t.replace_existing=True;t.save=False
    A.import_asset_tasks([t]);return load(dest+'/'+name)
def material(name,dest):
    m=load(dest+'/'+name) if E.does_asset_exist(dest+'/'+name) else A.create_asset(name,dest,u.Material,u.MaterialFactoryNew())
    M.delete_all_material_expressions(m);return m
def uvcoord(m,index):
    n=M.create_material_expression(m,u.MaterialExpressionTextureCoordinate);n.coordinate_index=index;return n
def sample(m,tex,uv,sampler):
    n=M.create_material_expression(m,u.MaterialExpressionTextureSample);n.texture=tex;n.sampler_type=sampler;M.connect_material_expressions(uv,'',n,'UVs');return n
def scalar(m,v):
    n=M.create_material_expression(m,u.MaterialExpressionConstant);n.r=v;return n
def blend(m,a,ap,b,bp,mask):
    n=M.create_material_expression(m,u.MaterialExpressionLinearInterpolate);M.connect_material_expressions(a,ap,n,'A');M.connect_material_expressions(b,bp,n,'B');M.connect_material_expressions(mask,'R',n,'Alpha');return n

textures={}
for key in ['BaseColor','Normal_Game','Roughness','Metallic']:
    t=import_file(P/'Textures'/(key+'.png'),'T_CoreStock_'+key,D+'/Textures')
    t.srgb=key=='BaseColor';t.lod_group=u.TextureGroup.TEXTUREGROUP_WEAPON;t.lod_bias=0
    t.compression_settings=u.TextureCompressionSettings.TC_NORMALMAP if key=='Normal_Game' else u.TextureCompressionSettings.TC_DEFAULT if key=='BaseColor' else u.TextureCompressionSettings.TC_MASKS
    if key=='Normal_Game':t.flip_green_channel=True
    save(t);textures[key]=t

def finish(m,family):
    uv=uvcoord(m,1);result={}
    if family=='M4':
        root='/Game/Weapons/AttachmentFinish20260913/M4/Textures/T_M4_Receiver_'
        base=sample(m,load(root+'BaseColor'),uv,u.MaterialSamplerType.SAMPLERTYPE_COLOR)
        rough=sample(m,load(root+'Roughness'),uv,u.MaterialSamplerType.SAMPLERTYPE_COLOR)
        fn=M.create_material_expression(m,u.MaterialExpressionMaterialFunctionCall);fn.set_editor_property('material_function',load('/InterchangeAssets/Functions/MF_PhongToMetalRoughness'))
        M.connect_material_expressions(base,'RGB',fn,'DiffuseColor');M.connect_material_expressions(rough,'R',fn,'Shininess')
        for pin,v in [('SpecularColor',.2),('AmbientColor',0.)]:
            c=M.create_material_expression(m,u.MaterialExpressionConstant3Vector);c.constant=u.LinearColor(v,v,v,1);M.connect_material_expressions(c,'',fn,pin)
        result={key:(fn,key) for key in ['BaseColor','Roughness','Metallic','Specular']}
    elif family=='AKM':
        for key,label in [('BaseColor','Base_color'),('Metallic','Metallic'),('Roughness','Roughness')]:
            n=sample(m,load('/Game/Weapons/AKMIntegration/SovietFab/ArmSupport/Textures/T_AKM_Mount_'+label),uv,u.MaterialSamplerType.SAMPLERTYPE_COLOR if key=='BaseColor' else u.MaterialSamplerType.SAMPLERTYPE_LINEAR_GRAYSCALE)
            result[key]=(n,'RGB' if key=='BaseColor' else 'R')
    else:
        for label in ['BaseColor','ORM']:
            name='T_QBZ191_StableCollar_'+label
            t=import_file(Path('D:/FPS3D/FPSGAME/SourceAssets/StableAntiSlipRearGrip20260913/Selected91727/Textures')/(name+'.png'),name,D+'/QBZ191/Textures')
            t.srgb=label=='BaseColor';t.compression_settings=u.TextureCompressionSettings.TC_DEFAULT if label=='BaseColor' else u.TextureCompressionSettings.TC_MASKS;save(t)
            n=sample(m,t,uv,u.MaterialSamplerType.SAMPLERTYPE_COLOR if label=='BaseColor' else u.MaterialSamplerType.SAMPLERTYPE_MASKS)
            if label=='BaseColor':result[label]=(n,'RGB')
            else:result['Roughness']=(n,'G');result['Metallic']=(n,'B')
    if 'Specular' not in result:result['Specular']=(scalar(m,.5),'')
    E.set_metadata_tag(m,'ReceiverReference',{'M4':'/Game/Weapons/M4InfimaV3/Body_001','AKM':'/Game/Weapons/AKMIntegration/SovietFab/M_AKM_Soviet_PBR','QBZ191':'QBZ191MetalCoat20260913 receiver coating'}[family])
    return result

def add_normal(m,uv):
    n=sample(m,textures['Normal_Game'],uv,u.MaterialSamplerType.SAMPLERTYPE_NORMAL);M.connect_material_property(n,'RGB',u.MaterialProperty.MP_NORMAL)
props={'BaseColor':u.MaterialProperty.MP_BASE_COLOR,'Roughness':u.MaterialProperty.MP_ROUGHNESS,'Metallic':u.MaterialProperty.MP_METALLIC,'Specular':u.MaterialProperty.MP_SPECULAR}
rubber=material('M_CoreStock_Rubber',D);uv=uvcoord(rubber,0)
n=sample(rubber,textures['BaseColor'],uv,u.MaterialSamplerType.SAMPLERTYPE_COLOR);M.connect_material_property(n,'RGB',u.MaterialProperty.MP_BASE_COLOR)
n=sample(rubber,textures['Roughness'],uv,u.MaterialSamplerType.SAMPLERTYPE_MASKS)
c=M.create_material_expression(rubber,u.MaterialExpressionClamp);c.set_editor_property('min_default',.75);c.set_editor_property('max_default',1.);M.connect_material_expressions(n,'R',c,'Input');M.connect_material_property(c,'',u.MaterialProperty.MP_ROUGHNESS)
M.connect_material_property(scalar(rubber,0),'',u.MaterialProperty.MP_METALLIC);add_normal(rubber,uv);M.recompile_material(rubber);save(rubber)

for family in ['M4','AKM','QBZ191']:
    dest=D+'/'+family;body=material('M_CoreStock_Body_'+family,dest);coat=finish(body,family);uv=uvcoord(body,0)
    mask=sample(body,textures['Metallic'],uv,u.MaterialSamplerType.SAMPLERTYPE_MASKS)
    base=sample(body,textures['BaseColor'],uv,u.MaterialSamplerType.SAMPLERTYPE_COLOR)
    rough=sample(body,textures['Roughness'],uv,u.MaterialSamplerType.SAMPLERTYPE_MASKS)
    source={'BaseColor':(base,'RGB'),'Roughness':(rough,'R'),'Metallic':(scalar(body,0),''),'Specular':(scalar(body,.5),'')}
    for key,prop in props.items():
        node=blend(body,*source[key],*coat[key],mask);M.connect_material_property(node,'',prop)
    add_normal(body,uv);E.set_metadata_tag(body,'MetalMask','Selected Meshy Metallic map on retained UV0; coating on UV1')
    M.recompile_material(body);save(body)
    adapter=material('M_CoreStock_Adapter_'+family,dest)
    for key,(node,pin) in finish(adapter,family).items():M.connect_material_property(node,pin,props[key])
    M.recompile_material(adapter);save(adapter)
    opt=u.FbxImportUI();opt.automated_import_should_detect_type=False;opt.mesh_type_to_import=u.FBXImportType.FBXIT_STATIC_MESH;opt.import_as_skeletal=False;opt.import_materials=False;opt.import_textures=False;opt.import_animations=False
    data=opt.static_mesh_import_data;data.combine_meshes=True;data.auto_generate_collision=False;data.generate_lightmap_u_vs=False;data.normal_import_method=u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS_AND_TANGENTS
    mesh=import_file(P/family/'SM_CoreStock.fbx','SM_CoreStock',dest,opt)
    for i,slot in enumerate(mesh.static_materials):
        name=str(slot.material_slot_name);mesh.set_material(i,adapter if 'Adapter' in name else rubber if 'Rubber' in name else body)
    E.set_metadata_tag(mesh,'SourceAsset','Meshy_AI_Rifle_Stock_0914005605_image-to-3d-texture_fbx.zip')
    E.set_metadata_tag(mesh,'AttachmentId','core_stock');E.set_metadata_tag(mesh,'AuthoringStage','80k game derivative, source normal bake, per-rifle mount and finish; not runtime tested')
    save(mesh);report['assets'][family]=mesh.get_path_name();print('CORE_STOCK_MESHY_SAVED',family,flush=True)
(P/'import_results.json').write_text(json.dumps(report,indent=2));u.log('CORE_STOCK_MESHY_IMPORT_COMPLETE')
