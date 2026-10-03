"""Actual background import/build/save of this batch's workshop meshes and materials."""
import json,re,hashlib,sys
from pathlib import Path
import unreal as u
refine_root=Path(__file__).resolve().parents[1]/'RefineV2'
refine_receipt=refine_root/'Receipts/install.json'
if __name__=='__main__' and refine_receipt.exists() and json.loads(refine_receipt.read_text('utf8')).get('stage')=='maps_saved':
    import runpy
    runpy.run_path(str(refine_root/'Scripts/import_assets.py'),run_name='__main__')
    runpy.run_path(str(refine_root/'Scripts/build_preview_chest.py'),run_name='__main__')
    raise SystemExit(0)
ROOT=Path(__file__).resolve().parents[1];PROJECT=ROOT.parents[1];BASE='/Game/Dungeons/StationWorkshop20261003'
if Path(u.Paths.project_dir()).resolve()!=PROJECT.resolve():raise RuntimeError('Wrong project')
if '-run=pythonscript' not in u.SystemLibrary.get_command_line().lower() and not globals().get('STATION_WORKSHOP_EXISTING_EDITOR_IMPORT',False):raise RuntimeError('Background commandlet or existing editor bridge required')
E=u.EditorAssetLibrary;A=u.AssetToolsHelpers.get_asset_tools();RP=ROOT/'Receipts/assets.json'
report=json.loads(RP.read_text('utf8')) if RP.exists() else dict(meshes={},materials=[],tests_run=False,rendered=False)
def record():RP.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf8')
sys.path.insert(0,str(ROOT/'Scripts'))
from materials import create
create(ROOT,BASE,report);record()
u.SystemLibrary.execute_console_command(None,'Interchange.FeatureFlags.Import.FBX 0')
sub=u.get_editor_subsystem(u.StaticMeshEditorSubsystem) or u.new_object(u.StaticMeshEditorSubsystem)
manifest=json.loads((ROOT/'Authored/manifest.json').read_text('utf8'))
for item in manifest['objects']:
    path=item['asset'];digest=hashlib.sha256(Path(item['fbx']).read_bytes()).hexdigest();mesh=u.load_asset(path)
    if mesh and report['meshes'].get(item['name'],{}).get('source_sha256')!=digest:raise RuntimeError('Preserve differing existing workshop '+path)
    if not mesh:
        task=u.AssetImportTask();task.filename=item['fbx'];task.destination_path=BASE+'/Meshes';task.destination_name=item['name']
        task.automated=True;task.replace_existing=False;task.save=False
        opts=u.FbxImportUI();opts.import_mesh=True;opts.import_materials=False;opts.import_textures=False;opts.import_as_skeletal=False
        opts.automated_import_should_detect_type=False;opts.mesh_type_to_import=u.FBXImportType.FBXIT_STATIC_MESH
        d=opts.static_mesh_import_data;d.combine_meshes=True;d.convert_scene=True;d.convert_scene_unit=True
        d.transform_vertex_to_absolute=True;d.auto_generate_collision=False;d.generate_lightmap_u_vs=False
        d.normal_import_method=u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS_AND_TANGENTS
        task.options=opts;A.import_asset_tasks([task]);mesh=u.load_asset(path)
        if not mesh:raise RuntimeError('Workshop import failed '+path)
        for i,slot in enumerate(mesh.get_editor_property('static_materials')):
            key=re.sub(r'[._][0-9]{3}$','',str(slot.material_slot_name));mat=u.load_asset(item['materials'][key])
            if not mat:raise RuntimeError('Workshop surface unavailable '+key)
            mesh.set_material(i,mat)
        build=sub.get_lod_build_settings(mesh,0);build.set_editor_property('use_full_precision_u_vs',True)
        build.set_editor_property('use_high_precision_tangent_basis',True);build.set_editor_property('recompute_tangents',True)
        sub.set_lod_build_settings(mesh,0,build)
        n=mesh.get_editor_property('nanite_settings').copy();n.enabled=item['nanite'];n.explicit_tangents=True
        n.generate_fallback=u.NaniteGenerateFallback.ENABLED;n.fallback_target=u.NaniteFallbackTarget.PERCENT_TRIANGLES
        n.fallback_percent_triangles=1.;n.fallback_relative_error=0.;mesh.set_editor_property('nanite_settings',n)
        if item['nanite'] and not u.PlazaInstanceTools.build_nanite_data(mesh):raise RuntimeError('Workshop Nanite build failed '+path)
        if not E.save_loaded_asset(mesh,False):raise RuntimeError('Workshop mesh save failed '+path)
        report['meshes'][item['name']]=dict(path=path,source_sha256=digest,triangles=item['triangles']);record()
report['stage']='assets_saved';record();print('STATION_WORKSHOP_ASSETS_SAVED',len(report['meshes']),flush=True)
