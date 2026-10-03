"""Import, build and save this batch's original hospital container assets."""
import hashlib
import json
import re
import sys
import traceback
from pathlib import Path
import unreal as u

ROOT=Path(__file__).resolve().parents[1]
PROJECT=ROOT.parents[1]
BASE='/Game/Dungeons/HospitalContainers20261003'
if Path(u.Paths.project_dir()).resolve()!=PROJECT.resolve():raise RuntimeError('Wrong project')
if '-run=pythonscript' not in u.SystemLibrary.get_command_line().lower() and not globals().get('HOSPITAL_CONTAINERS_EXISTING_EDITOR',False):
    raise RuntimeError('Background commandlet or existing editor bridge required')
E=u.EditorAssetLibrary
A=u.AssetToolsHelpers.get_asset_tools()
RP=ROOT/'Receipts/assets.json'
report=json.loads(RP.read_text('utf8')) if RP.exists() else dict(meshes={},materials=[],tests_run=False,rendered=False,game_run=False)

def record():RP.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf8')

try:
    report['stage']='importing';report.pop('error',None);record()
    sys.path.insert(0,str(ROOT/'Scripts'))
    from materials import create
    create(ROOT,BASE,report);record()
    u.SystemLibrary.execute_console_command(None,'Interchange.FeatureFlags.Import.FBX 0')
    sub=u.get_editor_subsystem(u.StaticMeshEditorSubsystem) or u.new_object(u.StaticMeshEditorSubsystem)
    manifest=json.loads((ROOT/'Authored/manifest.json').read_text('utf8'))
    for item in manifest['objects']:
        path=item['asset'];digest=hashlib.sha256(Path(item['fbx']).read_bytes()).hexdigest();mesh=u.load_asset(path)
        previous=report['meshes'].get(item['name'],{})
        if mesh and previous.get('source_sha256')!=digest:raise RuntimeError('Preserve differing existing hospital mesh '+path)
        if not mesh:
            task=u.AssetImportTask();task.filename=item['fbx'];task.destination_path=BASE+'/Meshes';task.destination_name=item['name']
            task.automated=True;task.replace_existing=False;task.save=False
            opts=u.FbxImportUI();opts.import_mesh=True;opts.import_materials=False;opts.import_textures=False;opts.import_as_skeletal=False
            opts.automated_import_should_detect_type=False;opts.mesh_type_to_import=u.FBXImportType.FBXIT_STATIC_MESH
            data=opts.static_mesh_import_data;data.combine_meshes=True;data.convert_scene=True;data.convert_scene_unit=True
            data.transform_vertex_to_absolute=True;data.auto_generate_collision=False;data.generate_lightmap_u_vs=False
            data.normal_import_method=u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS_AND_TANGENTS
            data.vertex_color_import_option=u.VertexColorImportOption.REPLACE
            task.options=opts;A.import_asset_tasks([task]);mesh=u.load_asset(path)
            if not mesh:raise RuntimeError('Hospital mesh import failed '+path)
            for index,slot in enumerate(mesh.get_editor_property('static_materials')):
                key=re.sub(r'[._][0-9]{3}$','',str(slot.material_slot_name));material=u.load_asset(item['materials'][key])
                if not material:raise RuntimeError('Hospital material unavailable '+key)
                mesh.set_material(index,material)
            build=sub.get_lod_build_settings(mesh,0);build.set_editor_property('use_full_precision_u_vs',True)
            build.set_editor_property('use_high_precision_tangent_basis',True);build.set_editor_property('recompute_tangents',True)
            sub.set_lod_build_settings(mesh,0,build)
            nanite=mesh.get_editor_property('nanite_settings').copy();nanite.enabled=item['nanite']
            if item['nanite']:
                nanite.explicit_tangents=True;nanite.generate_fallback=u.NaniteGenerateFallback.ENABLED
                nanite.fallback_target=u.NaniteFallbackTarget.PERCENT_TRIANGLES;nanite.fallback_percent_triangles=1.;nanite.fallback_relative_error=0.
            mesh.set_editor_property('nanite_settings',nanite)
            if item['nanite'] and not u.PlazaInstanceTools.build_nanite_data(mesh):raise RuntimeError('Hospital Nanite build failed '+path)
            if not E.save_loaded_asset(mesh,False):raise RuntimeError('Hospital mesh save failed '+path)
            report['meshes'][item['name']]=dict(path=path,source_sha256=digest,triangles=item['triangles'],nanite=item['nanite'],collision=item['collision']);record()
        print('HOSPITAL_CONTAINER_MESH_SAVED '+item['name'],flush=True)
    report['stage']='assets_saved';record();print('HOSPITAL_CONTAINER_ASSETS_SAVED '+str(len(report['meshes'])),flush=True)
except Exception:
    report.update(stage='import_failed',error=traceback.format_exc());record();raise
