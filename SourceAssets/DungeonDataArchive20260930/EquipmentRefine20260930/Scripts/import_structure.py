"""Import the four revised architecture meshes into dedicated V2 packages."""
import json,hashlib,re
from pathlib import Path
import unreal as u
ROOT=Path(__file__).resolve().parents[1]
C=json.loads((ROOT/'Config/layout.json').read_text('utf-8'));M=json.loads((ROOT/'Structure/manifest.json').read_text('utf-8'))
BASE=C['ue_base']+'/Structure';E=u.EditorAssetLibrary;A=u.AssetToolsHelpers.get_asset_tools()
receipt=ROOT/'Receipts/structure-import.json';report=json.loads(receipt.read_text('utf-8')) if receipt.exists() else dict(meshes={},tests_run=False)
for item in M['objects']:
 path=BASE+'/'+item['name'];sha=hashlib.sha256(Path(item['fbx']).read_bytes()).hexdigest()
 if E.does_asset_exist(path):
  if report['meshes'].get(item['kind'],{}).get('sha256')==sha:continue
  raise RuntimeError('Preserve a different existing revision '+path)
 t=u.AssetImportTask();t.filename=item['fbx'];t.destination_path=BASE;t.destination_name=item['name'];t.automated=True;t.replace_existing=False;t.save=False
 o=u.FbxImportUI();o.import_mesh=True;o.import_materials=False;o.import_textures=False;o.import_as_skeletal=False;o.automated_import_should_detect_type=False;o.mesh_type_to_import=u.FBXImportType.FBXIT_STATIC_MESH
 d=o.static_mesh_import_data;d.combine_meshes=True;d.convert_scene=True;d.convert_scene_unit=True;d.transform_vertex_to_absolute=True;d.auto_generate_collision=False;d.generate_lightmap_u_vs=False
 d.normal_import_method=u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS;d.normal_generation_method=u.FBXNormalGenerationMethod.MIKK_T_SPACE;d.vertex_color_import_option=u.VertexColorImportOption.REPLACE
 t.options=o;t.factory=u.FbxFactory();A.import_asset_tasks([t]);mesh=u.load_asset(path)
 if not mesh:raise RuntimeError('Import failed '+path)
 for i,slot in enumerate(mesh.get_editor_property('static_materials')):
  key=re.sub(r'[._][0-9]{3}$','',str(slot.material_slot_name));mat=u.load_asset(item['materials'][key])
  if not mat:raise RuntimeError('Missing shared material '+key)
  mesh.set_material(i,mat)
 mesh.get_editor_property('body_setup').set_editor_property('collision_trace_flag',u.CollisionTraceFlag.CTF_USE_COMPLEX_AS_SIMPLE)
 n=mesh.get_editor_property('nanite_settings').copy();n.enabled=True;n.explicit_tangents=True;n.generate_fallback=u.NaniteGenerateFallback.ENABLED;n.fallback_target=u.NaniteFallbackTarget.PERCENT_TRIANGLES;n.fallback_percent_triangles=1.;n.fallback_relative_error=0
 mesh.set_editor_property('nanite_settings',n)
 if not u.PlazaInstanceTools.build_nanite_data(mesh):raise RuntimeError('Nanite build failed '+path)
 if not E.save_loaded_asset(mesh,False):raise RuntimeError('Save failed '+path)
 report['meshes'][item['kind']]=dict(path=path,sha256=sha,triangles=item['triangles'])
 receipt.write_text(json.dumps(report,indent=2),encoding='utf-8');print('ARCHIVE_STRUCTURE_V2_SAVED',item['kind'],flush=True)
report['stage']='structure_saved';receipt.write_text(json.dumps(report,indent=2),encoding='utf-8')
