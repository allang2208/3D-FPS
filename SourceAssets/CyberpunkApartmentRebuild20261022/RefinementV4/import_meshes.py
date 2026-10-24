"""Import only upgraded cabinet pieces; all other meshes remain referenced in place."""
from pathlib import Path
import sys,json,re,hashlib,traceback
import unreal as u
sys.path.insert(0,str(Path(__file__).resolve().parent))
from surface_specs import *
E=u.EditorAssetLibrary;A=u.AssetToolsHelpers.get_asset_tools()
SM=u.get_editor_subsystem(u.StaticMeshEditorSubsystem) or u.new_object(u.StaticMeshEditorSubsystem)
manifest=json.loads((ROOT/'assembly.json').read_text('utf8'));report={'stage':'importing','meshes':{}}
receipt=ROOT/'meshes_saved.json'
old=json.loads(receipt.read_text()) if receipt.exists() else {}
def record():receipt.write_text(json.dumps(report,indent=2),encoding='utf8')
def load(path):
 o=u.load_asset(path)
 if not o:raise RuntimeError('Missing cabinet asset '+path)
 return o
def mat(role):
 role=role.removeprefix('AP_');role=ALIASES.get(role,role)
 if role in SPECS:return load(BASE+'/Materials/MI_AP4_'+role)
 return load('/Game/Props/CyberpunkApartmentRebuild20261022/RefinementV3/Materials/M_AP_'+role)
try:
 u.SystemLibrary.execute_console_command(None,'Interchange.FeatureFlags.Import.FBX 0')
 for row in manifest['meshes']:
  if row.get('reused_revision'):continue
  digest=hashlib.file_digest(Path(row['fbx']).open('rb'),'sha256').hexdigest()
  if E.does_asset_exist(row['asset']) and old.get('meshes',{}).get(row['key'],{}).get('sha256')==digest:
   report['meshes'][row['key']]=old['meshes'][row['key']];continue
  t=u.AssetImportTask();t.filename=row['fbx'];t.destination_path=BASE+'/Meshes';t.destination_name=row['name']
  t.automated=True;t.replace_existing=True;t.replace_existing_settings=True;t.save=False;t.factory=u.FbxFactory()
  opt=u.FbxImportUI();opt.automated_import_should_detect_type=False;opt.mesh_type_to_import=u.FBXImportType.FBXIT_STATIC_MESH
  opt.import_mesh=True;opt.import_materials=False;opt.import_textures=False;opt.import_animations=False;opt.import_as_skeletal=False
  d=opt.static_mesh_import_data
  for key,value in dict(combine_meshes=True,convert_scene=True,convert_scene_unit=True,transform_vertex_to_absolute=True,
    auto_generate_collision=False,generate_lightmap_u_vs=False,one_convex_hull_per_ucx=True,import_uniform_scale=1.).items():d.set_editor_property(key,value)
  d.normal_import_method=u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS
  d.normal_generation_method=u.FBXNormalGenerationMethod.MIKK_T_SPACE;t.options=opt;A.import_asset_tasks([t]);mesh=load(row['asset'])
  for i,s in enumerate(mesh.get_editor_property('static_materials')):mesh.set_material(i,mat(re.sub(r'[._][0-9]{3}$','',str(s.material_slot_name))))
  b=SM.get_lod_build_settings(mesh,0)
  for k,v in dict(use_full_precision_u_vs=True,use_high_precision_tangent_basis=True,use_mikk_t_space=True,recompute_tangents=True,recompute_normals=False).items():b.set_editor_property(k,v)
  SM.set_lod_build_settings(mesh,0,b)
  settings=mesh.get_editor_property('nanite_settings').copy();settings.enabled=row['nanite'];settings.explicit_tangents=True
  settings.generate_fallback=u.NaniteGenerateFallback.ENABLED;settings.fallback_target=u.NaniteFallbackTarget.PERCENT_TRIANGLES
  settings.fallback_percent_triangles=1.;settings.fallback_relative_error=0.;mesh.set_editor_property('nanite_settings',settings)
  if row['nanite'] and not u.PlazaInstanceTools.build_nanite_data(mesh):raise RuntimeError('Nanite build '+row['key'])
  body=mesh.get_editor_property('body_setup');body.set_editor_property('collision_trace_flag',u.CollisionTraceFlag.CTF_USE_SIMPLE_AND_COMPLEX)
  if not E.save_loaded_asset(mesh,False):raise RuntimeError('Mesh save '+row['key'])
  report['meshes'][row['key']]={'path':row['asset'],'sha256':digest,'triangles':row['triangles'],'hulls':row['hulls'],'nanite':row['nanite']};record()
 report['stage']='meshes_saved';record();print('APARTMENT_CABINET_MESHES_SAVED',len(report['meshes']))
except Exception:
 report['error']=traceback.format_exc();record();raise
