"""Import and save the ward details through the existing editor or guarded commandlet."""
import hashlib
import json
import re
import traceback
from pathlib import Path
import unreal as u
ROOT=Path(__file__).resolve().parents[1];PROJECT=ROOT.parents[1];BASE='/Game/Dungeons/HospitalDoctorOffice20261003/Meshes'
if Path(u.Paths.project_dir()).resolve()!=PROJECT.resolve():raise RuntimeError('Wrong project')
if '-run=pythonscript' not in u.SystemLibrary.get_command_line().lower() and not globals().get('HOSPITAL_OFFICE_EXISTING_EDITOR',False):
    raise RuntimeError('Existing editor bridge or guarded commandlet required')
editor=u.get_editor_subsystem(u.UnrealEditorSubsystem)
if editor and editor.get_game_world():raise RuntimeError('Preserve active Play/PIE before hospital asset save')
receipt=ROOT/'Receipts/assets.json'
report=json.loads(receipt.read_text('utf8')) if receipt.exists() else dict(meshes={},tests_run=False,rendered=False,game_run=False)
def record():receipt.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf8')
try:
    report['stage']='importing';record()
    u.SystemLibrary.execute_console_command(None,'Interchange.FeatureFlags.Import.FBX 0')
    tools=u.AssetToolsHelpers.get_asset_tools();sub=u.get_editor_subsystem(u.StaticMeshEditorSubsystem) or u.new_object(u.StaticMeshEditorSubsystem)
    manifest=json.loads((ROOT/'Authored/manifest.json').read_text('utf8'))
    for item in manifest['objects']:
        mesh=u.load_asset(item['asset']);digest=hashlib.sha256(Path(item['fbx']).read_bytes()).hexdigest()
        if mesh and report['meshes'].get(item['name'],{}).get('source_sha256')!=digest:
            raise RuntimeError('Preserve differing existing fixture '+item['asset'])
        if not mesh:
            task=u.AssetImportTask();task.filename=item['fbx'];task.destination_path=BASE;task.destination_name=item['name']
            task.automated=True;task.replace_existing=False;task.save=False
            options=u.FbxImportUI();options.import_mesh=True;options.import_materials=False;options.import_textures=False;options.import_as_skeletal=False
            options.automated_import_should_detect_type=False;options.mesh_type_to_import=u.FBXImportType.FBXIT_STATIC_MESH
            data=options.static_mesh_import_data;data.combine_meshes=True;data.convert_scene=True;data.convert_scene_unit=True
            data.transform_vertex_to_absolute=True;data.auto_generate_collision=False;data.generate_lightmap_u_vs=False
            data.normal_import_method=u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS_AND_TANGENTS;data.vertex_color_import_option=u.VertexColorImportOption.REPLACE
            task.options=options;tools.import_asset_tasks([task]);mesh=u.load_asset(item['asset'])
            if not mesh:raise RuntimeError('Hospital fixture import failed')
            for index,slot in enumerate(mesh.get_editor_property('static_materials')):
                key=re.sub(r'[._][0-9]{3}$','',str(slot.material_slot_name));material=u.load_asset(item['materials'][key])
                if not material:raise RuntimeError('Required hospital fixture material unavailable '+key)
                mesh.set_material(index,material)
            build=sub.get_lod_build_settings(mesh,0);build.set_editor_property('use_full_precision_u_vs',True)
            build.set_editor_property('use_high_precision_tangent_basis',True);build.set_editor_property('recompute_tangents',True)
            sub.set_lod_build_settings(mesh,0,build)
            settings=mesh.get_editor_property('nanite_settings').copy();settings.enabled=True;settings.explicit_tangents=True
            settings.generate_fallback=u.NaniteGenerateFallback.ENABLED;settings.fallback_target=u.NaniteFallbackTarget.PERCENT_TRIANGLES
            settings.fallback_percent_triangles=1.;settings.fallback_relative_error=0.;mesh.set_editor_property('nanite_settings',settings)
            if not u.PlazaInstanceTools.build_nanite_data(mesh):raise RuntimeError('Hospital fixture Nanite build failed')
            if not u.EditorAssetLibrary.save_loaded_asset(mesh,False):raise RuntimeError('Hospital fixture save failed')
            report['meshes'][item['name']]=dict(path=item['asset'],source_sha256=digest,triangles=item['triangles']);record()
    report.update(stage='assets_saved');report.pop('error',None);record();print('HOSPITAL_FIXTURES_SAVED '+str(len(report['meshes'])),flush=True)
except Exception:
    report.update(stage='import_failed',error=traceback.format_exc());record();raise
