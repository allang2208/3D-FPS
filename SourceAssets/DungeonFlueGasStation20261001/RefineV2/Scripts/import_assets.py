"""Scoped new-name import and replacement in the existing subject map. No PIE."""
import json,re,hashlib
from pathlib import Path
import unreal as u
ROOT=Path(__file__).resolve().parents[1];HALL=ROOT.parent;PROJECT=HALL.parents[1]
C=json.loads((HALL/'Config/room.json').read_text('utf-8'));MAN=json.loads((ROOT/'Authored/manifest.json').read_text('utf-8'))
BASE=C['ue_base']+'/RefineV2';MAP=C.get('sample_map');E=u.EditorAssetLibrary;A=u.AssetToolsHelpers.get_asset_tools();L=u.MaterialEditingLibrary
if Path(u.Paths.project_dir()).resolve()!=PROJECT.resolve():raise RuntimeError('Wrong project')
background='-run=pythonscript' in u.SystemLibrary.get_command_line().lower()
if not background and u.get_editor_subsystem(u.LevelEditorSubsystem).is_in_play_in_editor():raise RuntimeError('End PIE before installing this revision')
receipt=ROOT/'Receipts/install.json';report=json.loads(receipt.read_text('utf-8')) if receipt.exists() else dict(meshes={},saved=[])
def record():receipt.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
def save(o):
    if not E.save_loaded_asset(o,False):raise RuntimeError('Cannot save '+o.get_path_name())
    if o.get_path_name() not in report['saved']:report['saved'].append(o.get_path_name())
    record()
path=BASE+'/Textures/T_FlueGas_Labels_V2';tex=u.load_asset(path) if E.does_asset_exist(path) else None
if not tex:
    task=u.AssetImportTask();task.filename=str(ROOT/'Authored/T_FlueGas_Labels_BaseColor.png')
    task.destination_path=BASE+'/Textures';task.destination_name='T_FlueGas_Labels_V2';task.automated=True;task.save=False
    A.import_asset_tasks([task]);tex=u.load_asset(path)
    if not tex:raise RuntimeError('Labels texture import failed')
    tex.set_editor_property('srgb',True);tex.set_editor_property('compression_settings',u.TextureCompressionSettings.TC_BC7)
    tex.set_editor_property('never_stream',False);save(tex)
path=BASE+'/Materials/M_FlueGas_Labels_V2'
if not E.does_asset_exist(path):
    m=A.create_asset('M_FlueGas_Labels_V2',BASE+'/Materials',u.Material,u.MaterialFactoryNew())
    m.set_editor_property('used_with_instanced_static_meshes',True);m.set_editor_property('used_with_nanite',True)
    slab=L.create_material_expression(m,u.MaterialExpressionSubstrateShadingModels);slab.set_editor_property('shading_model_override',u.MaterialShadingModel.MSM_DEFAULT_LIT)
    sample=L.create_material_expression(m,u.MaterialExpressionTextureSampleParameter2D)
    sample.set_editor_property('parameter_name','BaseColor');sample.set_editor_property('texture',tex);sample.set_editor_property('sampler_type',u.MaterialSamplerType.SAMPLERTYPE_COLOR)
    L.connect_material_property(sample,'RGB',u.MaterialProperty.MP_BASE_COLOR);L.connect_material_expressions(sample,'RGB',slab,'BaseColor')
    for prop,pin,value in [('ROUGHNESS','Roughness',.65),('METALLIC','Metallic',.05)]:
        n=L.create_material_expression(m,u.MaterialExpressionConstant);n.set_editor_property('r',value)
        L.connect_material_property(n,'',getattr(u.MaterialProperty,'MP_'+prop));L.connect_material_expressions(n,'',slab,pin)
    L.connect_material_property(slab,'',u.MaterialProperty.MP_FRONT_MATERIAL)
    errors=L.recompile_material(m)
    if errors:raise RuntimeError(str(errors))
    save(m)
sub=u.get_editor_subsystem(u.StaticMeshEditorSubsystem)
if sub is None:sub=u.new_object(u.StaticMeshEditorSubsystem)
meshes={}
for item in MAN['objects']:
    path=BASE+'/Meshes/'+item['name'];sha=hashlib.sha256(Path(item['fbx']).read_bytes()).hexdigest()
    mesh=u.load_asset(path) if E.does_asset_exist(path) else None
    if mesh:
        if report['meshes'].get(item['kind'],{}).get('sha256')!=sha:raise RuntimeError('Preserve different existing revision '+path)
        meshes[item['kind']]=mesh;continue
    task=u.AssetImportTask();task.filename=item['fbx'];task.destination_path=BASE+'/Meshes';task.destination_name=item['name']
    task.automated=True;task.replace_existing=False;task.save=False
    opts=u.FbxImportUI();opts.import_mesh=True;opts.import_materials=False;opts.import_textures=False;opts.import_as_skeletal=False
    opts.automated_import_should_detect_type=False;opts.mesh_type_to_import=u.FBXImportType.FBXIT_STATIC_MESH
    data=opts.static_mesh_import_data;data.combine_meshes=True;data.convert_scene=True;data.convert_scene_unit=True
    data.transform_vertex_to_absolute=True;data.auto_generate_collision=False;data.generate_lightmap_u_vs=False
    data.one_convex_hull_per_ucx=True;data.normal_import_method=u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS
    data.normal_generation_method=u.FBXNormalGenerationMethod.MIKK_T_SPACE;data.vertex_color_import_option=u.VertexColorImportOption.REPLACE
    task.options=opts;task.factory=u.FbxFactory();A.import_asset_tasks([task]);mesh=u.load_asset(path)
    if not mesh:raise RuntimeError('Cannot import '+path)
    for i,slot in enumerate(mesh.get_editor_property('static_materials')):
        key=re.sub(r'[._][0-9]{3}$','',str(slot.material_slot_name));mat=u.load_asset(item['materials'][key])
        if not mat:raise RuntimeError('Missing material '+item['materials'][key])
        mesh.set_material(i,mat)
    build=sub.get_lod_build_settings(mesh,0);build.set_editor_property('use_full_precision_u_vs',True)
    build.set_editor_property('recompute_tangents',True);build.set_editor_property('use_high_precision_tangent_basis',True);sub.set_lod_build_settings(mesh,0,build)
    body=mesh.get_editor_property('body_setup');body.set_editor_property('collision_trace_flag',
        u.CollisionTraceFlag.CTF_USE_SIMPLE_AND_COMPLEX if item['guardrail_drop'] else u.CollisionTraceFlag.CTF_USE_COMPLEX_AS_SIMPLE)
    n=mesh.get_editor_property('nanite_settings').copy();n.enabled=item['nanite'];n.explicit_tangents=True
    n.generate_fallback=u.NaniteGenerateFallback.ENABLED;n.fallback_target=u.NaniteFallbackTarget.PERCENT_TRIANGLES
    n.fallback_percent_triangles=1.;n.fallback_relative_error=0
    mesh.set_editor_property('nanite_settings',n)
    if item['nanite'] and not u.PlazaInstanceTools.build_nanite_data(mesh):raise RuntimeError('Nanite build failed '+path)
    hulls=sub.get_convex_collision_count(mesh) if item['guardrail_drop'] else 0
    if item['guardrail_drop'] and hulls!=item['simple_collision_hulls']:raise RuntimeError('Railing convex import incomplete: '+path)
    report['meshes'][item['kind']]=dict(path=path,sha256=sha,nanite=item['nanite'],simple_collision_hulls=hulls)
    save(mesh);meshes[item['kind']]=mesh
report['stage']='meshes_saved';record()

u.log('FLUE_GAS_PRODUCTION_ASSETS_SAVED')
