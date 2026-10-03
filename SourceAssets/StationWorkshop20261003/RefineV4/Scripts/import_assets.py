"""Import and save a privately named fitted roof, retaining V3 concrete."""
import hashlib,json,re
from pathlib import Path
import unreal as u
ROOT=Path(__file__).resolve().parents[1];PROJECT=ROOT.parents[2]
BASE='/Game/Dungeons/StationWorkshop20261003/RefineV4'
if Path(u.Paths.project_dir()).resolve()!=PROJECT.resolve():raise RuntimeError('Wrong project')
if '-run=pythonscript' not in u.SystemLibrary.get_command_line().lower() and not globals().get('STATION_FIT_EXISTING_EDITOR',False):raise RuntimeError('Commandlet or existing editor bridge required')
editor=u.get_editor_subsystem(u.UnrealEditorSubsystem)
if editor and editor.get_game_world():raise RuntimeError('Preserve active game session before roof import')
dirty={p.get_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_map_packages()}
if dirty:raise RuntimeError('Preserve unsaved maps before roof import: '+str(sorted(dirty)))
E=u.EditorAssetLibrary;A=u.AssetToolsHelpers.get_asset_tools()
sub=u.get_editor_subsystem(u.StaticMeshEditorSubsystem) or u.new_object(u.StaticMeshEditorSubsystem)
report=dict(stage='importing',meshes={},tests_run=False,rendered=False,game_run=False,editor_opened=False)
receipt=ROOT/'Receipts/assets.json'
previous=json.loads(receipt.read_text('utf8')) if receipt.exists() else {}
u.SystemLibrary.execute_console_command(None,'Interchange.FeatureFlags.Import.FBX 0')
for item in json.loads((ROOT/'Authored/manifest.json').read_text('utf8'))['objects']:
    digest=hashlib.sha256(Path(item['fbx']).read_bytes()).hexdigest();mesh=u.load_asset(item['asset'])
    if mesh and previous.get('meshes',{}).get(item['name'],{}).get('source_sha256')!=digest:raise RuntimeError('Preserve differing existing mesh '+item['asset'])
    if not mesh:
        task=u.AssetImportTask();task.filename=item['fbx'];task.destination_path=BASE+'/Meshes';task.destination_name=item['name']
        task.automated=True;task.replace_existing=False;task.save=False
        opts=u.FbxImportUI();opts.import_mesh=True;opts.import_materials=False;opts.import_textures=False;opts.import_as_skeletal=False
        opts.automated_import_should_detect_type=False;opts.mesh_type_to_import=u.FBXImportType.FBXIT_STATIC_MESH
        d=opts.static_mesh_import_data;d.combine_meshes=True;d.convert_scene=True;d.convert_scene_unit=True
        d.transform_vertex_to_absolute=True;d.auto_generate_collision=False;d.generate_lightmap_u_vs=False
        d.normal_import_method=u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS_AND_TANGENTS
        task.options=opts;A.import_asset_tasks([task]);mesh=u.load_asset(item['asset'])
        if not mesh:raise RuntimeError('Roof import failed')
        for i,slot in enumerate(mesh.get_editor_property('static_materials')):
            key=re.sub(r'[._][0-9]{3}$','',str(slot.material_slot_name));mat=u.load_asset(item['materials'][key])
            if not mat:raise RuntimeError('Saved concrete material unavailable')
            mesh.set_material(i,mat)
        build=sub.get_lod_build_settings(mesh,0);build.set_editor_property('use_full_precision_u_vs',True)
        build.set_editor_property('use_high_precision_tangent_basis',True);build.set_editor_property('recompute_tangents',True)
        sub.set_lod_build_settings(mesh,0,build)
        n=mesh.get_editor_property('nanite_settings').copy();n.enabled=True;n.explicit_tangents=True
        n.generate_fallback=u.NaniteGenerateFallback.ENABLED;n.fallback_target=u.NaniteFallbackTarget.PERCENT_TRIANGLES
        n.fallback_percent_triangles=1.;n.fallback_relative_error=0.;mesh.set_editor_property('nanite_settings',n)
        if not u.PlazaInstanceTools.build_nanite_data(mesh):raise RuntimeError('Roof Nanite build failed')
        if not E.save_loaded_asset(mesh,False):raise RuntimeError('Roof asset save failed')
    report['meshes'][item['name']]=dict(path=item['asset'],source_sha256=digest,triangles=item['triangles'])
report['stage']='assets_saved';receipt.write_text(json.dumps(report,indent=2),encoding='utf8')
print('STATION_FITTED_ROOF_ASSET_SAVED',flush=True)
