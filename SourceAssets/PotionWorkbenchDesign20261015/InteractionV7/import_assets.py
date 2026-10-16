"""Author V7 packages in an isolated host; no interactive editor or runtime test."""
import json,re
from pathlib import Path
import unreal as u
ROOT=Path(__file__).resolve().parent
if Path(u.Paths.project_dir()).resolve()!=(ROOT/'UEImportHost').resolve():raise RuntimeError('Wrong import host')
DEST='/Game/Building/PotionWorkbench20261015/InteractionV7'
A=u.AssetToolsHelpers.get_asset_tools();E=u.EditorAssetLibrary;M=u.MaterialEditingLibrary
report={'stage':'importing','packages':[],'runtime_tested':False}
def save(obj):
    E.set_metadata_tag(obj,'Alchemy.Owner','InteractionV7')
    if not E.save_loaded_asset(obj,False):raise RuntimeError('Save failed '+obj.get_path_name())
    report['packages'].append(obj.get_path_name())
    (ROOT/'import-receipt.json').write_text(json.dumps(report,indent=2),'utf8')
def material(name):
    path=DEST+'/'+name
    if E.does_asset_exist(path):
        obj=u.load_asset(path)
        if E.get_metadata_tag(obj,'Alchemy.Owner')!='InteractionV7':raise RuntimeError('Not owned '+path)
        M.delete_all_material_expressions(obj)
        return obj
    return A.create_asset(name,DEST,u.Material,u.MaterialFactoryNew())
def node(mat,cls,**props):
    n=M.create_material_expression(mat,cls)
    for k,v in props.items():n.set_editor_property(k,v)
    return n
def wire(a,b,pin):
    if not M.connect_material_expressions(a,'',b,pin):raise RuntimeError('Wire '+pin)
def prop(n,p):
    if not M.connect_material_property(n,'',p):raise RuntimeError('Material property')
def compile_save(mat):
    errors=M.recompile_material(mat)
    if errors:raise RuntimeError(str(errors))
    M.get_statistics(mat);save(mat)
for name,fluid in [('M_AlchemyTransferFluid',True),('M_AlchemyTransferGrain',False)]:
    mat=material(name)
    mat.set_editor_property('used_with_spline_meshes',True)
    mat.set_editor_property('used_with_instanced_static_meshes',True)
    if fluid:
        mat.set_editor_property('blend_mode',u.BlendMode.BLEND_TRANSLUCENT)
        mat.set_editor_property('translucency_lighting_mode',u.TranslucencyLightingMode.TLM_SURFACE_PER_PIXEL_LIGHTING)
    color=node(mat,u.MaterialExpressionVectorParameter,parameter_name='PotionColor',default_value=u.LinearColor(.08,.3,.18,1))
    prop(color,u.MaterialProperty.MP_BASE_COLOR)
    prop(node(mat,u.MaterialExpressionConstant,r=.1 if fluid else .26),u.MaterialProperty.MP_ROUGHNESS)
    prop(node(mat,u.MaterialExpressionConstant,r=.65),u.MaterialProperty.MP_SPECULAR)
    if fluid:
        fresnel=node(mat,u.MaterialExpressionFresnel,exponent=3.0,base_reflect_fraction=.08)
        rim=node(mat,u.MaterialExpressionMultiply,const_b=.3);wire(fresnel,rim,'A')
        alpha=node(mat,u.MaterialExpressionAdd,const_b=.4);wire(rim,alpha,'A')
        flow=node(mat,u.MaterialExpressionScalarParameter,parameter_name='Flow',default_value=1)
        opacity=node(mat,u.MaterialExpressionMultiply);wire(alpha,opacity,'A');wire(flow,opacity,'B');prop(opacity,u.MaterialProperty.MP_OPACITY)
    compile_save(mat)
mat=material('M_AlchemyHoverOutline')
mat.set_editor_property('material_domain',u.MaterialDomain.MD_POST_PROCESS)
mat.set_editor_property('blendable_location',u.BlendableLocation.BL_SCENE_COLOR_AFTER_TONEMAPPING)
mat.set_editor_property('blendable_priority',40)
expressions=[]
for pin,sceneid in [('ColorInput',u.SceneTextureId.PPI_POST_PROCESS_INPUT0),('StencilInput',u.SceneTextureId.PPI_CUSTOM_STENCIL),('DepthInput',u.SceneTextureId.PPI_CUSTOM_DEPTH),('SceneDepthInput',u.SceneTextureId.PPI_SCENE_DEPTH)]:
    expressions.append((pin,node(mat,u.MaterialExpressionSceneTexture,scene_texture_id=sceneid)))
expressions.append(('Gold',node(mat,u.MaterialExpressionVectorParameter,parameter_name='Gold',default_value=u.LinearColor(1,.68,.16,1))))
expressions.append(('Width',node(mat,u.MaterialExpressionScalarParameter,parameter_name='Width',default_value=2.3)))
custom=node(mat,u.MaterialExpressionCustom,code=(ROOT/'hover_outline.hlsl').read_text('utf8'),output_type=u.CustomMaterialOutputType.CMOT_FLOAT3)
inputs=[]
for pin,n in expressions:
    i=u.CustomInput();i.set_editor_property('input_name',pin);inputs.append(i)
custom.set_editor_property('inputs',inputs)
for pin,n in expressions:wire(n,custom,pin)
prop(custom,u.MaterialProperty.MP_EMISSIVE_COLOR);compile_save(mat)
u.load_module('StaticMeshEditor');SM=u.get_editor_subsystem(u.StaticMeshEditorSubsystem) or u.new_object(u.StaticMeshEditorSubsystem)
u.SystemLibrary.execute_console_command(None,'Interchange.FeatureFlags.Import.FBX 0')
opt=u.FbxImportUI();opt.import_mesh=True;opt.import_as_skeletal=False;opt.import_materials=False;opt.import_textures=False
opt.automated_import_should_detect_type=False;opt.mesh_type_to_import=u.FBXImportType.FBXIT_STATIC_MESH
d=opt.static_mesh_import_data;d.combine_meshes=True;d.auto_generate_collision=False;d.generate_lightmap_u_vs=False
d.convert_scene=True;d.convert_scene_unit=True;d.transform_vertex_to_absolute=True
d.normal_import_method=u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS;d.remove_degenerates=False
canon=lambda s:re.sub('[^a-z0-9]','',str(s).lower())
for spec in json.loads((ROOT/'asset-manifest.json').read_text('utf8'))['meshes']:
    task=u.AssetImportTask();task.filename=spec['source'];task.destination_path=DEST;task.destination_name=spec['name']
    task.automated=True;task.replace_existing=True;task.save=False;task.options=opt
    A.import_asset_tasks([task]);mesh=next((o for o in task.get_objects() if isinstance(o,u.StaticMesh)),None)
    if not mesh:raise RuntimeError('Import failed '+spec['name'])
    mats={canon(k):u.load_asset(v) for k,v in spec['materials'].items()}
    for i,s in enumerate(mesh.static_materials):
        m=mats.get(canon(s.material_slot_name))
        if not m:raise RuntimeError('Missing material '+str(s.material_slot_name))
        mesh.set_material(i,m)
    settings=SM.get_lod_build_settings(mesh,0);settings.use_full_precision_u_vs=True;settings.use_high_precision_tangent_basis=True
    settings.generate_lightmap_u_vs=False;settings.recompute_normals=False;settings.recompute_tangents=True;settings.remove_degenerates=False
    SM.set_lod_build_settings(mesh,0,settings)
    nan=mesh.get_editor_property('nanite_settings');nan.enabled=False;SM.set_nanite_settings(mesh,nan,True)
    save(mesh)
report['stage']='assets_saved';(ROOT/'import-receipt.json').write_text(json.dumps(report,indent=2),'utf8')
u.log('ALCHEMY_V7_ASSETS_SAVED')
