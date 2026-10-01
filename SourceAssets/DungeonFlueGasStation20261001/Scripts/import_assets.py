"""Author and save only new flue-gas packages in a headless UE commandlet.

No generation, PIE, render or test. Shared dependencies are never saved here.
"""
import hashlib,json,re
from pathlib import Path
import unreal as u
ROOT=Path(__file__).resolve().parents[1];PROJECT=ROOT.parents[1]
CFG=json.loads((ROOT/'Config/room.json').read_text('utf-8'))
MAN=json.loads((ROOT/'Authored/manifest.json').read_text('utf-8'))
BASE=CFG['ue_base'];MAP=CFG.get('sample_map');E=u.EditorAssetLibrary;A=u.AssetToolsHelpers.get_asset_tools();L=u.MaterialEditingLibrary
if Path(u.Paths.project_dir()).resolve()!=PROJECT.resolve():raise RuntimeError('Wrong project')
if '-run=pythonscript' not in u.SystemLibrary.get_command_line().lower():raise RuntimeError('Use a background commandlet; preserve the live editor world')
report_path=ROOT/'Receipts/install.json'
report=json.loads(report_path.read_text('utf-8')) if report_path.exists() else dict(meshes={},saved_assets=[])
report.update(revision=CFG['revision'],tests_run=False,rendered=False,random_pool_registered=False)
def record():report_path.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
def save(asset):
    if not asset.get_path_name().startswith(BASE+'/'):raise RuntimeError('Save outside owned asset namespace')
    if not E.save_loaded_asset(asset,False):raise RuntimeError('Cannot save '+asset.get_path_name())
    if asset.get_path_name() not in report['saved_assets']:report['saved_assets'].append(asset.get_path_name())
    record()

tex_path=BASE+'/Textures/T_FlueGas_Labels_BaseColor'
texture=u.load_asset(tex_path) if E.does_asset_exist(tex_path) else None
if not texture:
    task=u.AssetImportTask();task.filename=str(ROOT/'Authored/T_FlueGas_Labels_BaseColor.png')
    task.destination_path=BASE+'/Textures';task.destination_name='T_FlueGas_Labels_BaseColor'
    task.automated=True;task.replace_existing=False;task.save=False;A.import_asset_tasks([task]);texture=u.load_asset(tex_path)
    if not texture:raise RuntimeError('Texture import failed')
    texture.set_editor_property('srgb',True);texture.set_editor_property('never_stream',False)
    texture.set_editor_property('compression_settings',u.TextureCompressionSettings.TC_BC7);save(texture)
mat_path=BASE+'/Materials/M_FlueGas_Labels'
if not E.does_asset_exist(mat_path):
    m=A.create_asset('M_FlueGas_Labels',BASE+'/Materials',u.Material,u.MaterialFactoryNew())
    m.set_editor_property('used_with_nanite',True);m.set_editor_property('used_with_instanced_static_meshes',True)
    slab=L.create_material_expression(m,u.MaterialExpressionSubstrateShadingModels)
    slab.set_editor_property('shading_model_override',u.MaterialShadingModel.MSM_DEFAULT_LIT)
    sample=L.create_material_expression(m,u.MaterialExpressionTextureSampleParameter2D)
    sample.set_editor_property('parameter_name','BaseColor');sample.set_editor_property('texture',texture)
    sample.set_editor_property('sampler_type',u.MaterialSamplerType.SAMPLERTYPE_COLOR)
    L.connect_material_property(sample,'RGB',u.MaterialProperty.MP_BASE_COLOR)
    L.connect_material_expressions(sample,'RGB',slab,'BaseColor')
    for prop,pin,value in [('ROUGHNESS','Roughness',.69),('METALLIC','Metallic',.12)]:
        n=L.create_material_expression(m,u.MaterialExpressionConstant);n.set_editor_property('r',value)
        L.connect_material_property(n,'',getattr(u.MaterialProperty,'MP_'+prop));L.connect_material_expressions(n,'',slab,pin)
    L.connect_material_property(slab,'',u.MaterialProperty.MP_FRONT_MATERIAL)
    errors=L.recompile_material(m)
    if errors:raise RuntimeError('Material compile failed: '+str(errors))
    L.layout_material_expressions(m);save(m)

meshes={};subsystem=u.get_editor_subsystem(u.StaticMeshEditorSubsystem)
if subsystem is None:subsystem=u.new_object(u.StaticMeshEditorSubsystem)
for item in MAN['objects']:
    path=BASE+'/Meshes/'+item['name'];digest=hashlib.sha256(Path(item['fbx']).read_bytes()).hexdigest()
    previous=report['meshes'].get(item['name']);mesh=u.load_asset(path) if E.does_asset_exist(path) else None
    if mesh:
        if not previous or previous.get('source_sha256')!=digest:raise RuntimeError('Existing asset differs; preserve it and author a new revision: '+path)
        meshes[item['kind']]=mesh;continue
    task=u.AssetImportTask();task.filename=item['fbx'];task.destination_path=BASE+'/Meshes';task.destination_name=item['name']
    task.automated=True;task.replace_existing=False;task.save=False
    opts=u.FbxImportUI();opts.import_mesh=True;opts.import_materials=False;opts.import_textures=False;opts.import_as_skeletal=False
    opts.automated_import_should_detect_type=False;opts.mesh_type_to_import=u.FBXImportType.FBXIT_STATIC_MESH
    data=opts.static_mesh_import_data;data.combine_meshes=True;data.convert_scene=True;data.convert_scene_unit=True
    data.transform_vertex_to_absolute=True;data.auto_generate_collision=False;data.generate_lightmap_u_vs=False
    data.normal_import_method=u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS;data.normal_generation_method=u.FBXNormalGenerationMethod.MIKK_T_SPACE
    data.vertex_color_import_option=u.VertexColorImportOption.REPLACE;task.options=opts;task.factory=u.FbxFactory()
    A.import_asset_tasks([task]);mesh=u.load_asset(path)
    if not mesh:raise RuntimeError('Mesh import failed '+path)
    for index,slot in enumerate(mesh.get_editor_property('static_materials')):
        key=re.sub(r'[._][0-9]{3}$','',str(slot.material_slot_name));material=u.load_asset(item['materials'][key])
        if not material:raise RuntimeError('Missing shared material '+item['materials'][key])
        mesh.set_material(index,material)
    build=subsystem.get_lod_build_settings(mesh,0)
    build.set_editor_property('use_full_precision_u_vs',True);build.set_editor_property('use_high_precision_tangent_basis',True)
    build.set_editor_property('recompute_tangents',True);subsystem.set_lod_build_settings(mesh,0,build)
    mesh.get_editor_property('body_setup').set_editor_property('collision_trace_flag',u.CollisionTraceFlag.CTF_USE_COMPLEX_AS_SIMPLE)
    settings=mesh.get_editor_property('nanite_settings').copy();settings.enabled=item['nanite'];settings.explicit_tangents=True
    settings.generate_fallback=u.NaniteGenerateFallback.ENABLED;settings.fallback_target=u.NaniteFallbackTarget.PERCENT_TRIANGLES
    settings.fallback_percent_triangles=1.;settings.fallback_relative_error=0
    mesh.set_editor_property('nanite_settings',settings)
    if item['nanite'] and not u.PlazaInstanceTools.build_nanite_data(mesh):raise RuntimeError('Nanite build failed '+path)
    report['meshes'][item['name']]=dict(path=path,source_sha256=digest,source_triangles=item['triangles'],collision=item['collision'],nanite=item['nanite'])
    save(mesh);meshes[item['kind']]=mesh
    u.log('FLUE_GAS_MESH_SAVED '+item['kind'])
report['stage']='meshes_saved';record()

u.log('FLUE_GAS_PRODUCTION_ASSETS_SAVED')
