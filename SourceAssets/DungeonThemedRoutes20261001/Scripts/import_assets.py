"""Import new freight geometry and capture the accepted warehouse without running it."""
import hashlib,json,re,copy
from pathlib import Path
import unreal as u
ROOT=Path(__file__).resolve().parents[1];PROJECT=ROOT.parents[1]
HALL=PROJECT/'SourceAssets/DungeonCargoWarehouse20261001'
BASE='/Game/Dungeons/ThemedRoutes20261001'
if Path(u.Paths.project_dir()).resolve()!=PROJECT.resolve():raise RuntimeError('Wrong project')
initial_dirty={p.get_name() for p in list(u.EditorLoadingAndSavingUtils.get_dirty_content_packages())+list(u.EditorLoadingAndSavingUtils.get_dirty_map_packages())}
manifest=json.loads((ROOT/'Authored/manifest.json').read_text('utf-8'))
sub=u.get_editor_subsystem(u.StaticMeshEditorSubsystem) or u.new_object(u.StaticMeshEditorSubsystem)
E=u.EditorAssetLibrary;report=dict(stage='importing',assets=[],tests_run=False,rendered=False)
for item in manifest['objects']:
    path=item['asset']
    if path in initial_dirty:raise RuntimeError('Unsaved target asset '+path)
    task=u.AssetImportTask();task.filename=item['fbx'];task.destination_path=path.rsplit('/',1)[0];task.destination_name=item['name']
    task.automated=True;task.replace_existing=True;task.replace_existing_settings=True;task.save=False
    opts=u.FbxImportUI();opts.import_mesh=True;opts.import_materials=False;opts.import_textures=False;opts.import_as_skeletal=False
    opts.automated_import_should_detect_type=False;opts.mesh_type_to_import=u.FBXImportType.FBXIT_STATIC_MESH
    data=opts.static_mesh_import_data;data.combine_meshes=True;data.convert_scene=True;data.convert_scene_unit=True
    data.transform_vertex_to_absolute=True;data.auto_generate_collision=False;data.generate_lightmap_u_vs=False
    data.normal_import_method=u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS;data.vertex_color_import_option=u.VertexColorImportOption.REPLACE
    task.options=opts;task.factory=u.FbxFactory();u.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
    mesh=u.load_asset(path)
    if not mesh:raise RuntimeError('Import failed '+path)
    for i,slot in enumerate(mesh.get_editor_property('static_materials')):
        key=re.sub(r'[._][0-9]{3}$','',str(slot.material_slot_name));mat=u.load_asset(item['materials'][key])
        if not mat:raise RuntimeError('Missing surface '+key)
        mesh.set_material(i,mat)
    mesh.get_editor_property('body_setup').set_editor_property('collision_trace_flag',u.CollisionTraceFlag.CTF_USE_COMPLEX_AS_SIMPLE)
    build=sub.get_lod_build_settings(mesh,0);build.set_editor_property('use_full_precision_u_vs',True)
    build.set_editor_property('use_high_precision_tangent_basis',True);build.set_editor_property('recompute_tangents',True);sub.set_lod_build_settings(mesh,0,build)
    n=mesh.get_editor_property('nanite_settings').copy();n.enabled=item['nanite'];n.explicit_tangents=True
    n.generate_fallback=u.NaniteGenerateFallback.ENABLED;n.fallback_target=u.NaniteFallbackTarget.PERCENT_TRIANGLES;n.fallback_percent_triangles=1.;n.fallback_relative_error=0
    mesh.set_editor_property('nanite_settings',n)
    if n.enabled and not u.PlazaInstanceTools.build_nanite_data(mesh):raise RuntimeError('Nanite build failed '+path)
    if not E.save_loaded_asset(mesh,False):raise RuntimeError('Asset save failed '+path)
    report['assets'].append(path)
    (ROOT/'Receipts/assets-import.json').write_text(json.dumps(report,indent=2),encoding='utf-8')


report.update(stage='assets_saved');(ROOT/'Receipts/assets-import.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
