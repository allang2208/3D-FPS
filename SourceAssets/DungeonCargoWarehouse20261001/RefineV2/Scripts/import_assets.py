"""Scoped import, label repair and placement update through the existing editor bridge."""
import hashlib,json,re
from pathlib import Path
import unreal as u
ROOT=Path(__file__).resolve().parents[1];HALL=ROOT.parent;PROJECT=HALL.parents[1]
C=json.loads((HALL/'Config/room.json').read_text('utf-8'));MAN=json.loads((ROOT/'Authored/manifest.json').read_text('utf-8'))
BASE=C['ue_base']+'/RefineV2';MAP=C['sample_map'];E=u.EditorAssetLibrary;A=u.AssetToolsHelpers.get_asset_tools();L=u.MaterialEditingLibrary
if Path(u.Paths.project_dir()).resolve()!=PROJECT.resolve():raise RuntimeError('Wrong project')
if '-run=pythonscript' not in u.SystemLibrary.get_command_line().lower() and u.get_editor_subsystem(u.LevelEditorSubsystem).is_in_play_in_editor():raise RuntimeError('End PIE before importing')
initial_dirty={p.get_name() for p in list(u.EditorLoadingAndSavingUtils.get_dirty_content_packages())+list(u.EditorLoadingAndSavingUtils.get_dirty_map_packages())}
targets=[BASE+'/Meshes/'+o['name'] for o in MAN['objects']]+['/Game/Dungeons/FacilityScenes20260927/Meshes/SM_Facility_CargoStack',BASE+'/Materials/M_CargoWarehouse_FloorPaint']
conflicts=initial_dirty.intersection(targets)
if conflicts:raise RuntimeError('Preserve unsaved target assets '+str(sorted(conflicts)))
receipt=ROOT/'Receipts/install.json';report=json.loads(receipt.read_text('utf-8')) if receipt.exists() else dict(meshes={},saved_assets=[],tests_run=False,rendered=False)
def record():receipt.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
def save(asset):
    if not E.save_loaded_asset(asset,False):raise RuntimeError('Save failed '+asset.get_path_name())
    if asset.get_path_name() not in report['saved_assets']:report['saved_assets'].append(asset.get_path_name())
    record()
mat_path=BASE+'/Materials/M_CargoWarehouse_FloorPaint'
if not E.does_asset_exist(mat_path):
    m=A.create_asset('M_CargoWarehouse_FloorPaint',BASE+'/Materials',u.Material,u.MaterialFactoryNew())
    m.set_editor_property('used_with_instanced_static_meshes',True)
    slab=L.create_material_expression(m,u.MaterialExpressionSubstrateShadingModels)
    slab.set_editor_property('shading_model_override',u.MaterialShadingModel.MSM_DEFAULT_LIT)
    color=L.create_material_expression(m,u.MaterialExpressionConstant3Vector);color.set_editor_property('constant',u.LinearColor(.58,.39,.055,1))
    age=L.create_material_expression(m,u.MaterialExpressionVertexColor)
    fade=L.create_material_expression(m,u.MaterialExpressionMultiply);fade.set_editor_property('const_b',.45);L.connect_material_expressions(age,'R',fade,'A')
    lift=L.create_material_expression(m,u.MaterialExpressionAdd);lift.set_editor_property('const_b',.8);L.connect_material_expressions(fade,'',lift,'A')
    result=L.create_material_expression(m,u.MaterialExpressionMultiply);L.connect_material_expressions(color,'',result,'A');L.connect_material_expressions(lift,'',result,'B')
    L.connect_material_property(result,'',u.MaterialProperty.MP_BASE_COLOR);L.connect_material_expressions(result,'',slab,'BaseColor')
    for prop,pin,val in [('ROUGHNESS','Roughness',.88),('METALLIC','Metallic',0),('SPECULAR','Specular',.18)]:
        node=L.create_material_expression(m,u.MaterialExpressionConstant);node.set_editor_property('r',val)
        L.connect_material_property(node,'',getattr(u.MaterialProperty,'MP_'+prop));L.connect_material_expressions(node,'',slab,pin)
    L.connect_material_property(slab,'',u.MaterialProperty.MP_FRONT_MATERIAL);L.recompile_material(m);save(m)
sub=u.get_editor_subsystem(u.StaticMeshEditorSubsystem)
if sub is None:sub=u.new_object(u.StaticMeshEditorSubsystem)
def import_mesh(item,path,shared=False):
    sha=hashlib.sha256(Path(item['fbx']).read_bytes()).hexdigest()
    previous=report['meshes'].get(path);mesh=u.load_asset(path) if E.does_asset_exist(path) else None
    if mesh and previous and previous['source_sha256']==sha:return mesh
    if mesh and not previous and not shared:raise RuntimeError('New revision path already exists with unknown source '+path)
    task=u.AssetImportTask();task.filename=item['fbx'];task.destination_path=path.rsplit('/',1)[0];task.destination_name=path.rsplit('/',1)[1]
    task.automated=True;task.replace_existing=bool(mesh);task.replace_existing_settings=bool(mesh);task.save=False
    opts=u.FbxImportUI();opts.import_mesh=True;opts.import_materials=False;opts.import_textures=False;opts.import_as_skeletal=False
    opts.automated_import_should_detect_type=False;opts.mesh_type_to_import=u.FBXImportType.FBXIT_STATIC_MESH
    data=opts.static_mesh_import_data;data.combine_meshes=True;data.convert_scene=True;data.convert_scene_unit=True
    data.transform_vertex_to_absolute=True;data.auto_generate_collision=False;data.one_convex_hull_per_ucx=True;data.generate_lightmap_u_vs=False
    data.normal_import_method=u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS;data.normal_generation_method=u.FBXNormalGenerationMethod.MIKK_T_SPACE
    data.vertex_color_import_option=u.VertexColorImportOption.REPLACE;task.options=opts;task.factory=u.FbxFactory();A.import_asset_tasks([task])
    mesh=u.load_asset(path)
    if not mesh:raise RuntimeError('Import failed '+path)
    for i,slot in enumerate(mesh.get_editor_property('static_materials')):
        key=re.sub(r'[._][0-9]{3}$','',str(slot.material_slot_name));mat=u.load_asset(item['materials'][key])
        if not mat:raise RuntimeError('Missing material '+item['materials'][key])
        mesh.set_material(i,mat)
    mesh.get_editor_property('body_setup').set_editor_property('collision_trace_flag',u.CollisionTraceFlag.CTF_USE_SIMPLE_AND_COMPLEX if shared or item.get('guardrail_drop') else u.CollisionTraceFlag.CTF_USE_COMPLEX_AS_SIMPLE)
    build=sub.get_lod_build_settings(mesh,0);build.set_editor_property('use_full_precision_u_vs',True);build.set_editor_property('use_high_precision_tangent_basis',True)
    build.set_editor_property('recompute_tangents',True);sub.set_lod_build_settings(mesh,0,build)
    n=mesh.get_editor_property('nanite_settings').copy();n.enabled=item.get('nanite',True);n.explicit_tangents=True
    n.generate_fallback=u.NaniteGenerateFallback.ENABLED;n.fallback_target=u.NaniteFallbackTarget.PERCENT_TRIANGLES
    n.fallback_percent_triangles=1.;n.fallback_relative_error=0;mesh.set_editor_property('nanite_settings',n)
    if n.enabled and not u.PlazaInstanceTools.build_nanite_data(mesh):raise RuntimeError('Nanite build failed '+path)
    report['meshes'][path]=dict(source_sha256=sha,source_triangles=item['triangles'],nanite=n.enabled,shared_cargo=shared)
    save(mesh);return mesh
meshes={o['kind']:import_mesh(o,BASE+'/Meshes/'+o['name']) for o in MAN['objects']}
cargo=json.loads((ROOT/'Cargo/manifest.json').read_text('utf-8'))['objects'][0]
import_mesh(cargo,'/Game/Dungeons/FacilityScenes20260927/Meshes/SM_Facility_CargoStack',True)

report.update(stage='production_assets_saved');record()
