"""Import the derived folio in the isolated content host; save only new packages."""
import unreal as u, json
from pathlib import Path
ROOT=Path('D:/FPS3D/FPSGAME/SourceAssets/PotionWorkbenchDesign20261015/ManualV3')
HOST=ROOT.parent/'IntegrationV1/UEImportHost'
if Path(u.Paths.project_dir()).resolve()!=HOST.resolve():raise RuntimeError('Use the isolated potion import host')
DEST='/Game/Building/PotionWorkbench20261015/ManualV3'
ORIGINAL='/Game/Weapons/SpellbookEvildeer20261009'
A=u.AssetToolsHelpers.get_asset_tools();E=u.EditorAssetLibrary;L=u.MaterialEditingLibrary
report={'complete':False,'saved':[],'runtime_tested':False,'rendered':False}
def save(obj):
    E.set_metadata_tag(obj,'SourceAuthor','evildeer')
    E.set_metadata_tag(obj,'SourceLicense','CC BY 4.0')
    if not E.save_loaded_asset(obj,False):raise RuntimeError('Save failed '+obj.get_path_name())
    report['saved'].append(obj.get_path_name())
    (ROOT/'import-receipt.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
def node(mat,kind,**values):
    obj=L.create_material_expression(mat,kind)
    for key,value in values.items():obj.set_editor_property(key,value)
    return obj
def connect(a,out,b,slot):
    names=[str(n) for n in L.get_material_expression_input_names(b)]
    if slot not in names and len(names)==1:slot=names[0]
    if not L.connect_material_expressions(a,out,b,slot):raise RuntimeError('Material connection failed')
mat=A.create_asset('M_AlchemyManualPaper',DEST+'/Materials',u.Material,u.MaterialFactoryNew())
if not mat:mat=u.load_asset(DEST+'/Materials/M_AlchemyManualPaper')
L.delete_all_material_expressions(mat)
region=node(mat,u.MaterialExpressionVectorParameter,parameter_name='PageOffset',default_value=u.LinearColor(0,0,0,1))
scale=node(mat,u.MaterialExpressionConstant2Vector,r=.5,g=1.)
offset=node(mat,u.MaterialExpressionComponentMask,r=True,g=True,b=False,a=False)
connect(region,'RGB',offset,'Input')
uv=node(mat,u.MaterialExpressionTextureCoordinate)
mul=node(mat,u.MaterialExpressionMultiply);connect(uv,'',mul,'A');connect(scale,'',mul,'B')
add=node(mat,u.MaterialExpressionAdd);connect(mul,'',add,'A');connect(offset,'',add,'B')
paper=node(mat,u.MaterialExpressionTextureSampleParameter2D,parameter_name='PageTexture',
    texture=u.load_asset('/Engine/EngineResources/WhiteSquareTexture'),sampler_type=u.MaterialSamplerType.SAMPLERTYPE_COLOR)
connect(add,'',paper,'UVs')
L.connect_material_property(paper,'RGB',u.MaterialProperty.MP_BASE_COLOR)
rough=node(mat,u.MaterialExpressionConstant,r=.88);L.connect_material_property(rough,'',u.MaterialProperty.MP_ROUGHNESS)
glow=node(mat,u.MaterialExpressionMultiply,const_b=.08);connect(paper,'RGB',glow,'A');L.connect_material_property(glow,'',u.MaterialProperty.MP_EMISSIVE_COLOR)
L.recompile_material(mat);save(mat)
materials={'RecipeLeft':mat,'RecipeRight':mat}
for name in ('M_BookCover','M_BookPages'):
    materials[name]=u.load_asset(ORIGINAL+'/Materials/'+name)
for group in ('Herbal','Alchemy','Celestial','Arcane'):
    name='M_SpellbookPages_'+group;materials[name]=u.load_asset(ORIGINAL+'/PagesV1/Materials/'+name)
flag='Interchange.FeatureFlags.Import.FBX';previous=u.SystemLibrary.get_console_variable_int_value(flag)
u.SystemLibrary.execute_console_command(None,flag+' 0')
try:
    opt=u.FbxImportUI();opt.automated_import_should_detect_type=False
    opt.import_mesh=True;opt.import_as_skeletal=False;opt.import_materials=False;opt.import_textures=False
    opt.mesh_type_to_import=u.FBXImportType.FBXIT_STATIC_MESH
    data=opt.static_mesh_import_data;data.combine_meshes=True;data.auto_generate_collision=False
    data.convert_scene=True;data.convert_scene_unit=True;data.generate_lightmap_u_vs=False
    data.normal_import_method=u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS
    u.load_module('StaticMeshEditor');sm=u.get_editor_subsystem(u.StaticMeshEditorSubsystem)
    for spec in json.loads((ROOT/'manifest.json').read_text())['parts']:
        task=u.AssetImportTask();task.filename=str(ROOT/'Export'/(spec['name']+'.fbx'))
        task.destination_name=spec['name'];task.destination_path=DEST+'/Meshes'
        task.automated=True;task.replace_existing=True;task.save=False;task.options=opt
        A.import_asset_tasks([task]);mesh=u.load_asset(DEST+'/Meshes/'+spec['name'])
        if not mesh:raise RuntimeError('Mesh import failed '+spec['name'])
        for i,slot in enumerate(mesh.static_materials):
            material=materials.get(str(slot.material_slot_name))
            if not material:raise RuntimeError('Missing material '+str(slot.material_slot_name))
            mesh.set_material(i,material)
        settings=sm.get_lod_build_settings(mesh,0);settings.use_full_precision_u_vs=True
        settings.generate_lightmap_u_vs=False;settings.recompute_normals=False;settings.recompute_tangents=True
        sm.set_lod_build_settings(mesh,0,settings)
        save(mesh)
    report['complete']=True
finally:
    u.SystemLibrary.execute_console_command(None,flag+' '+str(previous))
    (ROOT/'import-receipt.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
u.log('ALCHEMY_MANUAL_SAVED')
