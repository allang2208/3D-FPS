"""Import only new equipment packages, with original PBR and authored UCX hulls."""
import json,hashlib
from pathlib import Path
import unreal as u
ROOT=Path(__file__).resolve().parents[1];PROJECT=ROOT.parents[2]
CFG=json.loads((ROOT/'Config/layout.json').read_text(encoding='utf-8'));MAN=json.loads((ROOT/'Authored/manifest.json').read_text(encoding='utf-8'))
BASE=CFG['ue_base'];E=u.EditorAssetLibrary;A=u.AssetToolsHelpers.get_asset_tools();L=u.MaterialEditingLibrary
allow_revision=globals().get('ALLOW_UNPUBLISHED_REVISION',False)
if Path(u.Paths.project_dir()).resolve()!=PROJECT.resolve():raise RuntimeError('Wrong project')
receipt=ROOT/'Receipts/import.json';report=json.loads(receipt.read_text(encoding='utf-8')) if receipt.exists() else dict(saved_assets=[],meshes={},textures={})
report.update(revision=CFG['revision'],tests_run=False)
def write():receipt.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
def save(asset):
 if not E.save_loaded_asset(asset,False):raise RuntimeError('Save failed '+asset.get_path_name())
 if asset.get_path_name() not in report['saved_assets']:report['saved_assets'].append(asset.get_path_name())
 write()
def digest(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
textures={}
for suffix in ('BaseColor','NormalDX','ORM'):
 name='T_ArchiveEquipment_'+suffix;path=BASE+'/Textures/'+name;source=ROOT/'Authored/Textures'/(name+'.png');sha=digest(source)
 tex=u.load_asset(path) if E.does_asset_exist(path) else None
 if tex:
  if report['textures'].get(suffix,{}).get('sha256')==sha:textures[suffix]=tex;continue
  if not allow_revision:raise RuntimeError('Existing texture differs; use the explicit unpublished revision installer '+path)
 task=u.AssetImportTask();task.filename=str(source);task.destination_path=BASE+'/Textures';task.destination_name=name;task.automated=True;task.replace_existing=bool(tex);task.save=False
 A.import_asset_tasks([task]);tex=u.load_asset(path)
 if not tex:raise RuntimeError('Missing imported texture '+path)
 tex.set_editor_property('srgb',suffix=='BaseColor');tex.set_editor_property('never_stream',False)
 tex.set_editor_property('compression_settings',u.TextureCompressionSettings.TC_BC7 if suffix=='BaseColor' else u.TextureCompressionSettings.TC_NORMALMAP if suffix=='NormalDX' else u.TextureCompressionSettings.TC_MASKS)
 if suffix=='NormalDX':tex.set_editor_property('flip_green_channel',False)
 report['textures'][suffix]=dict(path=path,sha256=sha);save(tex);textures[suffix]=tex
path=BASE+'/Materials/M_ArchiveEquipment_Atlas';mat=u.load_asset(path) if E.does_asset_exist(path) else None
if not mat:
 mat=A.create_asset('M_ArchiveEquipment_Atlas',BASE+'/Materials',u.Material,u.MaterialFactoryNew())
 mat.set_editor_property('blend_mode',u.BlendMode.BLEND_OPAQUE);mat.set_editor_property('two_sided',False)
 mat.set_editor_property('used_with_nanite',True);mat.set_editor_property('used_with_instanced_static_meshes',True)
 slab=L.create_material_expression(mat,u.MaterialExpressionSubstrateShadingModels);slab.set_editor_property('shading_model_override',u.MaterialShadingModel.MSM_DEFAULT_LIT)
 for suffix in ('BaseColor','NormalDX','ORM'):
  sample=L.create_material_expression(mat,u.MaterialExpressionTextureSampleParameter2D);sample.set_editor_property('parameter_name',suffix);sample.set_editor_property('texture',textures[suffix])
  sample.set_editor_property('sampler_type',u.MaterialSamplerType.SAMPLERTYPE_COLOR if suffix=='BaseColor' else u.MaterialSamplerType.SAMPLERTYPE_NORMAL if suffix=='NormalDX' else u.MaterialSamplerType.SAMPLERTYPE_MASKS)
  channels=[('RGB','BASE_COLOR','BaseColor')] if suffix=='BaseColor' else [('RGB','NORMAL','Normal')] if suffix=='NormalDX' else [('R','AMBIENT_OCCLUSION',None),('G','ROUGHNESS','Roughness'),('B','METALLIC','Metallic')]
  for output,prop,pin in channels:
   if not L.connect_material_property(sample,output,getattr(u.MaterialProperty,'MP_'+prop)):raise RuntimeError('Cannot connect '+prop)
   if pin and not L.connect_material_expressions(sample,output,slab,pin):raise RuntimeError('Cannot connect Substrate '+pin)
 if not L.connect_material_property(slab,'',u.MaterialProperty.MP_FRONT_MATERIAL):raise RuntimeError('Cannot connect surface')
 errors=L.recompile_material(mat)
 if errors:raise RuntimeError('Material compile failed '+str(errors))
 L.layout_material_expressions(mat);save(mat)
for item in MAN['objects']:
 name=item['name'];path=BASE+'/Meshes/'+name;sha=digest(item['fbx']);mesh=u.load_asset(path) if E.does_asset_exist(path) else None
 if mesh:
  if report['meshes'].get(name,{}).get('sha256')==sha:continue
  if not allow_revision:raise RuntimeError('Existing mesh differs; use the explicit unpublished revision installer '+path)
 task=u.AssetImportTask();task.filename=item['fbx'];task.destination_path=BASE+'/Meshes';task.destination_name=name;task.automated=True;task.replace_existing=bool(mesh);task.save=False
 options=u.FbxImportUI();options.import_mesh=True;options.import_materials=False;options.import_textures=False;options.import_as_skeletal=False
 options.automated_import_should_detect_type=False;options.mesh_type_to_import=u.FBXImportType.FBXIT_STATIC_MESH
 data=options.static_mesh_import_data;data.combine_meshes=True;data.convert_scene=True;data.convert_scene_unit=True;data.transform_vertex_to_absolute=True
 data.auto_generate_collision=False;data.one_convex_hull_per_ucx=True;data.generate_lightmap_u_vs=False
 data.normal_import_method=u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS;data.normal_generation_method=u.FBXNormalGenerationMethod.MIKK_T_SPACE
 data.vertex_color_import_option=u.VertexColorImportOption.REPLACE;task.options=options;task.factory=u.FbxFactory();A.import_asset_tasks([task]);mesh=u.load_asset(path)
 if not mesh:raise RuntimeError('Missing imported mesh '+path)
 mesh.set_material(0,mat);mesh.get_editor_property('body_setup').set_editor_property('collision_trace_flag',u.CollisionTraceFlag.CTF_USE_SIMPLE_AND_COMPLEX)
 n=mesh.get_editor_property('nanite_settings').copy();n.enabled=True;n.explicit_tangents=True;n.generate_fallback=u.NaniteGenerateFallback.ENABLED;n.fallback_target=u.NaniteFallbackTarget.PERCENT_TRIANGLES;n.fallback_percent_triangles=1.;n.fallback_relative_error=0
 mesh.set_editor_property('nanite_settings',n)
 if not u.PlazaInstanceTools.build_nanite_data(mesh):raise RuntimeError('Nanite build failed '+path)
 report['meshes'][name]=dict(path=path,sha256=sha,source_triangles=item['triangles'],collision_hulls=item['collision_hulls'],nanite=True);save(mesh)
 print('ARCHIVE_EQUIPMENT_ASSET_SAVED',name,flush=True)
report['stage']='assets_saved';write();print('ARCHIVE_EQUIPMENT_IMPORT_COMPLETE',flush=True)
