"""Save the fine-press revision in the existing isolated authoring project."""
import unreal as u,json
from pathlib import Path
ROOT=Path('D:/FPS3D/FPSGAME/SourceAssets/AlchemyManualFinePress20261016')
HOST=ROOT.parent/'PotionWorkbenchDesign20261015/IntegrationV1/UEImportHost'
if Path(u.Paths.project_dir()).resolve()!=HOST.resolve():raise RuntimeError('Use PotionWorkbenchImport.uproject')
DEST='/Game/Building/PotionWorkbench20261015/ManualV5';ORIGINAL='/Game/Weapons/SpellbookEvildeer20261009'
A=u.AssetToolsHelpers.get_asset_tools();E=u.EditorAssetLibrary;L=u.MaterialEditingLibrary
report=dict(complete=False,saved=[],runtime_tested=False,preview_rendered=False)
def record():(ROOT/'import-receipt.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
def save(obj):
    if not E.save_loaded_asset(obj,False):raise RuntimeError('Save failed '+obj.get_path_name())
    report['saved'].append(obj.get_path_name());record()
def node(mat,kind,**values):
    obj=L.create_material_expression(mat,kind)
    for key,value in values.items():obj.set_editor_property(key,value)
    return obj
def wire(a,out,b,pin):
    names=[str(n) for n in L.get_material_expression_input_names(b)]
    if pin not in names and len(names)==1:pin=names[0]
    if not L.connect_material_expressions(a,out,b,pin):raise RuntimeError('Cannot connect '+pin)
def material(name):
    path=DEST+'/Materials/'+name
    obj=u.load_asset(path) if E.does_asset_exist(path) else A.create_asset(name,DEST+'/Materials',u.Material,u.MaterialFactoryNew())
    L.delete_all_material_expressions(obj);return obj
def finish(mat):L.recompile_material(mat);save(mat)
def scalar(mat,value,prop):L.connect_material_property(node(mat,u.MaterialExpressionConstant,r=value),'',prop)
def bend(mat,uv):
    curl=node(mat,u.MaterialExpressionScalarParameter,parameter_name='TurnCurl',default_value=0.)
    pins=[]
    for name in ('UV','Curl'):
        p=u.CustomInput();p.set_editor_property('input_name',name);pins.append(p)
    code=node(mat,u.MaterialExpressionCustom,code='return float3(0,0,sin(saturate(UV.x)*3.14159265)*Curl);',output_type=u.CustomMaterialOutputType.CMOT_FLOAT3,inputs=pins)
    wire(uv,'',code,'UV');wire(curl,'',code,'Curl')
    world=node(mat,u.MaterialExpressionTransform,transform_source_type=u.MaterialVectorCoordTransformSource.TRANSFORMSOURCE_LOCAL,transform_type=u.MaterialVectorCoordTransform.TRANSFORM_WORLD)
    wire(code,'',world,'Input');L.connect_material_property(world,'',u.MaterialProperty.MP_WORLD_POSITION_OFFSET)

textures={}
for spec in json.loads((ROOT/'artwork.json').read_text()):
    task=u.AssetImportTask();task.filename=spec['file'];task.destination_path=DEST+'/Textures';task.destination_name=spec['name']
    task.automated=True;task.replace_existing=True;task.save=False;A.import_asset_tasks([task])
    tex=u.load_asset(DEST+'/Textures/'+spec['name'])
    if not tex:raise RuntimeError('Texture import failed '+spec['name'])
    tex.set_editor_property('srgb',spec['kind']=='color')
    tex.set_editor_property('lod_group',u.TextureGroup.TEXTUREGROUP_UI if spec['ui'] else u.TextureGroup.TEXTUREGROUP_WORLD)
    if spec['kind']=='normal':
        tex.set_editor_property('compression_settings',u.TextureCompressionSettings.TC_NORMALMAP);tex.set_editor_property('flip_green_channel',True)
    elif spec['kind']=='mask':tex.set_editor_property('compression_settings',u.TextureCompressionSettings.TC_MASKS)
    else:tex.set_editor_property('compression_settings',u.TextureCompressionSettings.TC_DEFAULT)
    tex.set_editor_property('address_x',u.TextureAddress.TA_CLAMP);tex.set_editor_property('address_y',u.TextureAddress.TA_CLAMP)
    save(tex);textures[spec['name']]=tex
def texture(mat,name,kind='color'):
    mode={'color':u.MaterialSamplerType.SAMPLERTYPE_COLOR,'normal':u.MaterialSamplerType.SAMPLERTYPE_NORMAL,'mask':u.MaterialSamplerType.SAMPLERTYPE_MASKS}[kind]
    return node(mat,u.MaterialExpressionTextureSample,texture=textures[name],sampler_type=mode)
def surface(mat,color,normal,rough):
    L.connect_material_property(texture(mat,color),'RGB',u.MaterialProperty.MP_BASE_COLOR)
    L.connect_material_property(texture(mat,normal,'normal'),'RGB',u.MaterialProperty.MP_NORMAL)
    if isinstance(rough,str):L.connect_material_property(texture(mat,rough,'mask'),'R',u.MaterialProperty.MP_ROUGHNESS)
    else:scalar(mat,rough,u.MaterialProperty.MP_ROUGHNESS)

paper=material('M_AlchemyManualPaper');uv=node(paper,u.MaterialExpressionTextureCoordinate)
region=node(paper,u.MaterialExpressionVectorParameter,parameter_name='PageOffset',default_value=u.LinearColor(0,0,0,1))
mask=node(paper,u.MaterialExpressionComponentMask,r=True,g=True,b=False,a=False);wire(region,'RGB',mask,'Input')
scale=node(paper,u.MaterialExpressionConstant2Vector,r=.5,g=1.)
mul=node(paper,u.MaterialExpressionMultiply);wire(uv,'',mul,'A');wire(scale,'',mul,'B')
add=node(paper,u.MaterialExpressionAdd);wire(mul,'',add,'A');wire(mask,'',add,'B')
sample=node(paper,u.MaterialExpressionTextureSampleParameter2D,parameter_name='PageTexture',texture=textures['T_ManualPaper'],sampler_type=u.MaterialSamplerType.SAMPLERTYPE_COLOR)
wire(add,'',sample,'UVs');L.connect_material_property(sample,'RGB',u.MaterialProperty.MP_BASE_COLOR)
L.connect_material_property(texture(paper,'T_ManualPaperNormal','normal'),'RGB',u.MaterialProperty.MP_NORMAL)
L.connect_material_property(texture(paper,'T_ManualPaperRoughness','mask'),'R',u.MaterialProperty.MP_ROUGHNESS)
glow=node(paper,u.MaterialExpressionMultiply,const_b=.025);wire(sample,'RGB',glow,'A');L.connect_material_property(glow,'',u.MaterialProperty.MP_EMISSIVE_COLOR)
scalar(paper,.22,u.MaterialProperty.MP_SPECULAR);bend(paper,uv);finish(paper)

edge=material('M_ManualLeafEdge');surface(edge,'T_ManualPageEdges','T_ManualEdgeNormal',.87);bend(edge,node(edge,u.MaterialExpressionTextureCoordinate));finish(edge)
tabs=material('M_ManualBookmarks');surface(tabs,'T_ManualBookmarks','T_ManualRibbonNormal','T_ManualRibbonRoughness');scalar(tabs,.30,u.MaterialProperty.MP_SPECULAR);finish(tabs)
brass=material('M_ManualAntiqueBrass');color=node(brass,u.MaterialExpressionConstant3Vector,constant=u.LinearColor(.30,.20,.085))
L.connect_material_property(color,'',u.MaterialProperty.MP_BASE_COLOR);scalar(brass,.82,u.MaterialProperty.MP_METALLIC);scalar(brass,.43,u.MaterialProperty.MP_ROUGHNESS);finish(brass)
binding=material('M_ManualLeatherBinding');color=node(binding,u.MaterialExpressionConstant3Vector,constant=u.LinearColor(.036,.019,.012))
L.connect_material_property(color,'',u.MaterialProperty.MP_BASE_COLOR);scalar(binding,.61,u.MaterialProperty.MP_ROUGHNESS)
L.connect_material_property(texture(binding,'T_ManualPaperNormal','normal'),'RGB',u.MaterialProperty.MP_NORMAL);finish(binding)

materials={'RecipeLeft':paper,'RecipeRight':paper,'M_BookPages':edge,'ManualBookmarks':tabs,'ManualAntiqueBrass':brass,'ManualLeatherBinding':binding}
materials['M_BookCover']=u.load_asset(ORIGINAL+'/Materials/M_BookCover')
for group in ('Herbal','Alchemy','Celestial','Arcane'):materials['M_SpellbookPages_'+group]=edge
flag='Interchange.FeatureFlags.Import.FBX';previous=u.SystemLibrary.get_console_variable_int_value(flag);u.SystemLibrary.execute_console_command(None,flag+' 0')
try:
    opt=u.FbxImportUI();opt.automated_import_should_detect_type=False;opt.import_mesh=True;opt.import_as_skeletal=False
    opt.import_materials=False;opt.import_textures=False;opt.mesh_type_to_import=u.FBXImportType.FBXIT_STATIC_MESH
    data=opt.static_mesh_import_data;data.combine_meshes=True;data.auto_generate_collision=False;data.convert_scene=True;data.convert_scene_unit=True
    data.generate_lightmap_u_vs=False;data.normal_import_method=u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS
    u.load_module('StaticMeshEditor');sm=u.get_editor_subsystem(u.StaticMeshEditorSubsystem)
    for spec in json.loads((ROOT/'model.json').read_text())['parts']:
        task=u.AssetImportTask();task.filename=str(ROOT/'Export'/(spec['name']+'.fbx'));task.destination_name=spec['name'];task.destination_path=DEST+'/Meshes'
        task.automated=True;task.replace_existing=True;task.save=False;task.options=opt;A.import_asset_tasks([task])
        mesh=u.load_asset(DEST+'/Meshes/'+spec['name'])
        if not mesh:raise RuntimeError('Mesh import failed '+spec['name'])
        for i,slot in enumerate(mesh.static_materials):
            key=str(slot.material_slot_name);mat=materials.get(key)
            if not mat:raise RuntimeError('Missing material '+key)
            mesh.set_material(i,mat)
        settings=sm.get_lod_build_settings(mesh,0);settings.use_full_precision_u_vs=True;settings.generate_lightmap_u_vs=False
        settings.recompute_normals=False;settings.recompute_tangents=True;sm.set_lod_build_settings(mesh,0,settings)
        E.set_metadata_tag(mesh,'SourceAuthor','evildeer');E.set_metadata_tag(mesh,'SourceLicense','CC BY 4.0');save(mesh)
    report['complete']=True
finally:
    u.SystemLibrary.execute_console_command(None,flag+' '+str(previous));record()
u.log('MANUAL_FINE_PRESS_SAVED')
