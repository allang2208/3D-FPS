"""Save only the new cover tabs in the isolated authoring project."""
import unreal as u,json
from pathlib import Path
ROOT=Path('D:/FPS3D/FPSGAME/SourceAssets/AlchemyManualReadingFit20261016')
HOST=ROOT.parent/'PotionWorkbenchDesign20261015/IntegrationV1/UEImportHost'
if Path(u.Paths.project_dir()).resolve()!=HOST.resolve():raise RuntimeError('Use the isolated PotionWorkbenchImport project')
DEST='/Game/Building/PotionWorkbench20261015/ManualV6'
A=u.AssetToolsHelpers.get_asset_tools();E=u.EditorAssetLibrary;L=u.MaterialEditingLibrary
report=dict(complete=False,saved=[],runtime_tested=False,preview_rendered=False)
def record():(ROOT/'import-receipt.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
def save(obj):
    if not E.save_loaded_asset(obj,False):raise RuntimeError('Save failed '+obj.get_path_name())
    report['saved'].append(obj.get_path_name());record()
def node(mat,kind,**values):
    n=L.create_material_expression(mat,kind)
    for k,v in values.items():n.set_editor_property(k,v)
    return n
def scalar(mat,value,prop):L.connect_material_property(node(mat,u.MaterialExpressionConstant,r=value),'',prop)
textures={}
for spec in json.loads((ROOT/'textures.json').read_text()):
    task=u.AssetImportTask();task.filename=spec['file'];task.destination_path=DEST+'/Textures';task.destination_name=spec['name']
    task.automated=True;task.replace_existing=True;task.save=False;A.import_asset_tasks([task])
    tex=u.load_asset(DEST+'/Textures/'+spec['name'])
    if not tex:raise RuntimeError('Texture import failed')
    tex.set_editor_property('srgb',spec['kind']=='color')
    tex.set_editor_property('lod_group',u.TextureGroup.TEXTUREGROUP_UI if spec['kind']=='color' else u.TextureGroup.TEXTUREGROUP_WORLD)
    if spec['kind']=='normal':
        tex.set_editor_property('compression_settings',u.TextureCompressionSettings.TC_NORMALMAP);tex.set_editor_property('flip_green_channel',True)
    elif spec['kind']=='mask':tex.set_editor_property('compression_settings',u.TextureCompressionSettings.TC_MASKS)
    tex.set_editor_property('address_x',u.TextureAddress.TA_CLAMP);tex.set_editor_property('address_y',u.TextureAddress.TA_CLAMP)
    textures[spec['name']]=tex;save(tex)
def material(name):
    path=DEST+'/Materials/'+name
    m=u.load_asset(path) if E.does_asset_exist(path) else A.create_asset(name,DEST+'/Materials',u.Material,u.MaterialFactoryNew())
    L.delete_all_material_expressions(m);return m
cloth=material('M_ManualRibbonV6')
for name,mode,output,prop in [
    ('T_ManualRibbonV6',u.MaterialSamplerType.SAMPLERTYPE_COLOR,'RGB',u.MaterialProperty.MP_BASE_COLOR),
    ('T_ManualRibbonV6Normal',u.MaterialSamplerType.SAMPLERTYPE_NORMAL,'RGB',u.MaterialProperty.MP_NORMAL),
    ('T_ManualRibbonV6Roughness',u.MaterialSamplerType.SAMPLERTYPE_MASKS,'R',u.MaterialProperty.MP_ROUGHNESS)]:
    L.connect_material_property(node(cloth,u.MaterialExpressionTextureSample,texture=textures[name],sampler_type=mode),output,prop)
scalar(cloth,.28,u.MaterialProperty.MP_SPECULAR);L.recompile_material(cloth);save(cloth)
metal=material('M_ManualClaspV6')
L.connect_material_property(node(metal,u.MaterialExpressionConstant3Vector,constant=u.LinearColor(.33,.24,.12)),'',u.MaterialProperty.MP_BASE_COLOR)
scalar(metal,.85,u.MaterialProperty.MP_METALLIC);scalar(metal,.35,u.MaterialProperty.MP_ROUGHNESS);L.recompile_material(metal);save(metal)
flag='Interchange.FeatureFlags.Import.FBX';previous=u.SystemLibrary.get_console_variable_int_value(flag);u.SystemLibrary.execute_console_command(None,flag+' 0')
try:
    opt=u.FbxImportUI();opt.automated_import_should_detect_type=False;opt.import_mesh=True;opt.import_as_skeletal=False
    opt.import_materials=False;opt.import_textures=False;opt.mesh_type_to_import=u.FBXImportType.FBXIT_STATIC_MESH
    data=opt.static_mesh_import_data;data.combine_meshes=True;data.auto_generate_collision=False;data.convert_scene=True;data.convert_scene_unit=True
    data.generate_lightmap_u_vs=False;data.normal_import_method=u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS
    task=u.AssetImportTask();task.filename=str(ROOT/'Export/SM_AlchemyManualBookmarks.fbx');task.destination_name='SM_AlchemyManualBookmarks';task.destination_path=DEST+'/Meshes'
    task.automated=True;task.replace_existing=True;task.save=False;task.options=opt;A.import_asset_tasks([task])
    mesh=u.load_asset(DEST+'/Meshes/SM_AlchemyManualBookmarks')
    if not mesh:raise RuntimeError('Bookmark mesh import failed')
    materials={'ManualRibbonV6':cloth,'ManualClaspV6':metal}
    for i,slot in enumerate(mesh.static_materials):mesh.set_material(i,materials[str(slot.material_slot_name)])
    u.load_module('StaticMeshEditor');sm=u.get_editor_subsystem(u.StaticMeshEditorSubsystem)
    settings=sm.get_lod_build_settings(mesh,0);settings.use_full_precision_u_vs=True;settings.generate_lightmap_u_vs=False
    settings.recompute_normals=False;settings.recompute_tangents=True;sm.set_lod_build_settings(mesh,0,settings)
    E.set_metadata_tag(mesh,'AuthoringSource','AlchemyManualReadingFit20261016/author_bookmarks.py');save(mesh)
    report['complete']=True
finally:
    u.SystemLibrary.execute_console_command(None,flag+' '+str(previous));record()
u.log('MANUAL_READING_FIT_SAVED')
