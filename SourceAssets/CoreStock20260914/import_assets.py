"""Import independent stock revisions and per-rifle finish materials. No runtime tests."""
import unreal as u,json
from pathlib import Path
P=Path(__file__).resolve().parent;D='/Game/Weapons/CoreStock20260914'
A=u.AssetToolsHelpers.get_asset_tools();E=u.EditorAssetLibrary;M=u.MaterialEditingLibrary
report={'stage':'asset import and save only','tested':False,'assets':{}}

def save(asset):
    if not E.save_loaded_asset(asset,False):raise RuntimeError('Asset save failed: '+asset.get_path_name())
def load(path):
    a=u.load_asset(path)
    if not a:raise RuntimeError('Required authoring dependency missing: '+path)
    return a
def import_file(file,name,dest,options=None):
    t=u.AssetImportTask();t.filename=str(file);t.destination_path=dest;t.destination_name=name;t.options=options;t.automated=True;t.replace_existing=True;t.save=False
    A.import_asset_tasks([t]);return load(dest+'/'+name)
def material(name,dest):
    m=u.load_asset(dest+'/'+name) or A.create_asset(name,dest,u.Material,u.MaterialFactoryNew());M.delete_all_material_expressions(m);return m
def sample(m,tex,uv,sampler):
    n=M.create_material_expression(m,u.MaterialExpressionTextureSample);n.texture=tex;n.sampler_type=sampler
    M.connect_material_expressions(uv,'',n,'UVs');return n
def uvcoord(m,index):
    uv=M.create_material_expression(m,u.MaterialExpressionTextureCoordinate);uv.coordinate_index=index;return uv

textures={}
for key in ['BaseColor','MetalRough','Normal']:
    t=import_file(P/'Textures'/(key+'.png'),'T_CoreStock_'+key,D+'/Textures')
    t.srgb=key=='BaseColor';t.lod_group=u.TextureGroup.TEXTUREGROUP_WEAPON;t.lod_bias=0
    t.compression_settings=u.TextureCompressionSettings.TC_NORMALMAP if key=='Normal' else u.TextureCompressionSettings.TC_DEFAULT if key=='BaseColor' else u.TextureCompressionSettings.TC_MASKS
    if key=='Normal':t.flip_green_channel=True
    save(t);textures[key]=t

def finish(m,family):
    uv=uvcoord(m,2)
    if family=='M4':
        root='/Game/Weapons/AttachmentFinish20260913/M4/Textures/T_M4_Receiver_'
        base=sample(m,load(root+'BaseColor'),uv,u.MaterialSamplerType.SAMPLERTYPE_COLOR)
        rough=sample(m,load(root+'Roughness'),uv,u.MaterialSamplerType.SAMPLERTYPE_COLOR)
        fn=M.create_material_expression(m,u.MaterialExpressionMaterialFunctionCall);fn.set_editor_property('material_function',load('/InterchangeAssets/Functions/MF_PhongToMetalRoughness'))
        M.connect_material_expressions(base,'RGB',fn,'DiffuseColor');M.connect_material_expressions(rough,'R',fn,'Shininess')
        for pin,v in [('SpecularColor',.2),('AmbientColor',0.)]:
            c=M.create_material_expression(m,u.MaterialExpressionConstant3Vector);c.constant=u.LinearColor(v,v,v,1);M.connect_material_expressions(c,'',fn,pin)
        for pin,prop in [('BaseColor',u.MaterialProperty.MP_BASE_COLOR),('Roughness',u.MaterialProperty.MP_ROUGHNESS),('Metallic',u.MaterialProperty.MP_METALLIC),('Specular',u.MaterialProperty.MP_SPECULAR)]:M.connect_material_property(fn,pin,prop)
    elif family=='AKM':
        for label,prop in [('Base_color',u.MaterialProperty.MP_BASE_COLOR),('Metallic',u.MaterialProperty.MP_METALLIC),('Roughness',u.MaterialProperty.MP_ROUGHNESS)]:
            n=sample(m,load('/Game/Weapons/AKMIntegration/SovietFab/ArmSupport/Textures/T_AKM_Mount_'+label),uv,u.MaterialSamplerType.SAMPLERTYPE_COLOR if label=='Base_color' else u.MaterialSamplerType.SAMPLERTYPE_LINEAR_GRAYSCALE)
            M.connect_material_property(n,'RGB' if label=='Base_color' else 'R',prop)
    else:
        for label in ['BaseColor','ORM']:
            name='T_QBZ191_StableCollar_'+label
            t=import_file(Path('D:/FPS3D/FPSGAME/SourceAssets/StableAntiSlipRearGrip20260913/Selected91727/Textures')/(name+'.png'),name,D+'/QBZ191/Textures')
            t.srgb=label=='BaseColor';t.compression_settings=u.TextureCompressionSettings.TC_DEFAULT if label=='BaseColor' else u.TextureCompressionSettings.TC_MASKS;save(t)
            n=sample(m,t,uv,u.MaterialSamplerType.SAMPLERTYPE_COLOR if label=='BaseColor' else u.MaterialSamplerType.SAMPLERTYPE_MASKS)
            if label=='BaseColor':M.connect_material_property(n,'RGB',u.MaterialProperty.MP_BASE_COLOR)
            else:M.connect_material_property(n,'G',u.MaterialProperty.MP_ROUGHNESS);M.connect_material_property(n,'B',u.MaterialProperty.MP_METALLIC)
    E.set_metadata_tag(m,'ReceiverReference',{'M4':'/Game/Weapons/M4InfimaV3/Body_001','AKM':'/Game/Weapons/AKMIntegration/SovietFab/M_AKM_Soviet_PBR','QBZ191':'QBZ191MetalCoat20260913 receiver coat'}[family])

def normal(m):
    n=sample(m,textures['Normal'],uvcoord(m,0),u.MaterialSamplerType.SAMPLERTYPE_NORMAL);M.connect_material_property(n,'RGB',u.MaterialProperty.MP_NORMAL)

nonmetal={}
for kind in ['Polymer','Rubber']:
    m=material('M_CoreStock_'+kind,D);uv=uvcoord(m,0)
    base=sample(m,textures['BaseColor'],uv,u.MaterialSamplerType.SAMPLERTYPE_COLOR);M.connect_material_property(base,'RGB',u.MaterialProperty.MP_BASE_COLOR)
    rough=sample(m,textures['MetalRough'],uv,u.MaterialSamplerType.SAMPLERTYPE_MASKS)
    if kind=='Rubber':
        clamp=M.create_material_expression(m,u.MaterialExpressionClamp);clamp.set_editor_property('min_default',.75);clamp.set_editor_property('max_default',1.);M.connect_material_expressions(rough,'G',clamp,'Input');M.connect_material_property(clamp,'',u.MaterialProperty.MP_ROUGHNESS)
    else:M.connect_material_property(rough,'G',u.MaterialProperty.MP_ROUGHNESS)
    c=M.create_material_expression(m,u.MaterialExpressionConstant);c.r=0;M.connect_material_property(c,'',u.MaterialProperty.MP_METALLIC)
    normal(m);M.recompile_material(m);save(m);nonmetal[kind]=m

front=material('M_CoreStock_FrontPolymer',D)
c=M.create_material_expression(front,u.MaterialExpressionConstant3Vector);c.constant=u.LinearColor(.025,.026,.028,1);M.connect_material_property(c,'',u.MaterialProperty.MP_BASE_COLOR)
for value,prop in [(.56,u.MaterialProperty.MP_ROUGHNESS),(0.,u.MaterialProperty.MP_METALLIC)]:
    c=M.create_material_expression(front,u.MaterialExpressionConstant);c.r=value;M.connect_material_property(c,'',prop)
M.recompile_material(front);save(front)

for family in ['M4','AKM','QBZ191']:
    dest=D+'/'+family;metal=material('M_CoreStock_Metal_'+family,dest);finish(metal,family);normal(metal);M.recompile_material(metal);save(metal)
    adapter=material('M_CoreStock_Adapter_'+family,dest);finish(adapter,family);M.recompile_material(adapter);save(adapter)
    opt=u.FbxImportUI();opt.automated_import_should_detect_type=False;opt.mesh_type_to_import=u.FBXImportType.FBXIT_STATIC_MESH;opt.import_as_skeletal=False;opt.import_materials=False;opt.import_textures=False;opt.import_animations=False
    data=opt.static_mesh_import_data;data.combine_meshes=True;data.auto_generate_collision=False;data.generate_lightmap_u_vs=False;data.normal_import_method=u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS_AND_TANGENTS
    mesh=import_file(P/family/'SM_CoreStock.fbx','SM_CoreStock',dest,opt)
    for i,slot in enumerate(mesh.static_materials):
        name=str(slot.material_slot_name);mesh.set_material(i,front if 'FrontPolymer' in name else adapter if 'FrontMetal' in name or 'Adapter' in name else nonmetal['Polymer'] if 'Polymer' in name else nonmetal['Rubber'] if 'Rubber' in name else metal)
    E.set_metadata_tag(mesh,'SourceCandidate','ReferenceSkeletonStock5080_20260913/seed_91379')
    E.set_metadata_tag(mesh,'AuthoringStage','Independent core_stock option with rebuilt smooth front and retained rear bakes; not runtime tested')
    save(mesh);report['assets'][family]=mesh.get_path_name();print('STOCK_REVISION_SAVED',family,flush=True)
(P/'import_results.json').write_text(json.dumps(report,indent=2));u.log('CORE_STOCK_IMPORT_COMPLETE')
