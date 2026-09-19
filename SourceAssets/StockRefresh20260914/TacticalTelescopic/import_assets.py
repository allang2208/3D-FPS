"""Import the user-selected tactical telescopic stock and its three receiver finishes."""
import unreal as u,json
from pathlib import Path
P=Path(__file__).resolve().parent;D='/Game/Weapons/TacticalTelescopicStock20260914'
A=u.AssetToolsHelpers.get_asset_tools();E=u.EditorAssetLibrary;M=u.MaterialEditingLibrary
report={'stage':'import and save','gameplay_tested':False,'assets':{}}
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

textures={}
for key in ['BaseColor','Normal_Game','Roughness','Metallic']:
    t=import_file(P/'Textures'/(key+'.png'),'T_TacticalStock_'+key,D+'/Textures')
    t.srgb=key=='BaseColor';t.lod_group=u.TextureGroup.TEXTUREGROUP_WEAPON;t.lod_bias=0
    t.compression_settings=u.TextureCompressionSettings.TC_NORMALMAP if key=='Normal_Game' else u.TextureCompressionSettings.TC_DEFAULT if key=='BaseColor' else u.TextureCompressionSettings.TC_MASKS
    if key=='Normal_Game':t.flip_green_channel=True
    save(t);textures[key]=t

def add_normal(m):
    n=sample(m,textures['Normal_Game'],uvcoord(m,0),u.MaterialSamplerType.SAMPLERTYPE_NORMAL)
    M.connect_material_property(n,'RGB',u.MaterialProperty.MP_NORMAL)
props={'BaseColor':u.MaterialProperty.MP_BASE_COLOR,'Roughness':u.MaterialProperty.MP_ROUGHNESS,'Metallic':u.MaterialProperty.MP_METALLIC,'Specular':u.MaterialProperty.MP_SPECULAR}
surfaces={}
for kind in ['Polymer','Rubber']:
    m=material('M_TacticalStock_'+kind,D);uv=uvcoord(m,0)
    for key,prop in [('BaseColor',u.MaterialProperty.MP_BASE_COLOR),('Roughness',u.MaterialProperty.MP_ROUGHNESS)]:
        n=sample(m,textures[key],uv,u.MaterialSamplerType.SAMPLERTYPE_COLOR if key=='BaseColor' else u.MaterialSamplerType.SAMPLERTYPE_MASKS)
        M.connect_material_property(n,'RGB' if key=='BaseColor' else 'R',prop)
    M.connect_material_property(scalar(m,0),'',u.MaterialProperty.MP_METALLIC);add_normal(m)
    M.recompile_material(m);save(m);surfaces[kind]=m
for family in ['M4','AKM','QBZ191']:
    dest=D+'/'+family;bindings=dict(surfaces)
    for kind in ['Metal','Adapter']:
        m=material('M_TacticalStock_'+kind+'_'+family,dest)
        for key,(node,pin) in finish(m,family).items():M.connect_material_property(node,pin,props[key])
        if kind=='Metal':add_normal(m)
        M.recompile_material(m);save(m);bindings[kind]=m
    opt=u.FbxImportUI();opt.automated_import_should_detect_type=False;opt.mesh_type_to_import=u.FBXImportType.FBXIT_STATIC_MESH;opt.import_as_skeletal=False;opt.import_materials=False;opt.import_textures=False;opt.import_animations=False
    data=opt.static_mesh_import_data;data.combine_meshes=True;data.auto_generate_collision=False;data.generate_lightmap_u_vs=False;data.normal_import_method=u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS
    mesh=import_file(P/family/'SM_TacticalTelescopicStock.fbx','SM_TacticalTelescopicStock',dest,opt)
    for i,slot in enumerate(mesh.static_materials):
        name=str(slot.material_slot_name);kind=next(k for k in bindings if k in name);mesh.set_material(i,bindings[kind])
    E.set_metadata_tag(mesh,'SourceAsset','Meshy_AI_Adjustable_Rifle_Stoc_0914030720_generate.fbx')
    E.set_metadata_tag(mesh,'AttachmentId','tactical_telescopic')
    E.set_metadata_tag(mesh,'Authoring','80k game derivative; authored UV0 and PBR, selected high normal bake, receiver coating on UV1, per-rifle mounts')
    save(mesh);report['assets'][family]={'path':mesh.get_path_name(),'triangles':mesh.get_num_triangles(0),'materials':{str(s.material_slot_name):s.material_interface.get_path_name() for s in mesh.static_materials}}
    print('TACTICAL_STOCK_SAVED',family,flush=True)
(P/'import_results.json').write_text(json.dumps(report,indent=2));u.log('TACTICAL_STOCK_IMPORT_COMPLETE')
