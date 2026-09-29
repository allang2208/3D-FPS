"""User-requested read-only glove/viewmodel geometry and material inspection.

Reads the active catalog, saved RenderData statistics and source sections. Does not save
assets, modify quality settings, launch PIE or measure frame rate.
"""
import json
from pathlib import Path
from collections import Counter
import unreal as u

P=Path('D:/FPS3D/FPSGAME')
OUT=P/'Saved/Performance/GloveViewmodelBudget20260928';OUT.mkdir(parents=True,exist_ok=True)
cfg=json.loads((P/'Content/ColdSteelData/modular_outfits.json').read_text(encoding='utf-8-sig'))
S=u.get_editor_subsystem(u.SkeletalMeshEditorSubsystem) or u.new_object(u.SkeletalMeshEditorSubsystem)
G=u.GeometryScript_AssetUtils;M=u.GeometryScript_Materials;L=u.MaterialEditingLibrary
report=dict(scope='active asset registry RenderData counts and source material sections; no PIE / frame-time measurement',meshes={},materials={},recipes={},errors=[])

def emit(): (OUT/'report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')

def inspect_mesh(path,all_lods=True):
 if path in report['meshes']:return
 asset=u.load_asset(path)
 if not asset:report['errors'].append('Missing '+path);return
 row=dict(path=path,materials=[dict(index=i,slot=str(s.material_slot_name),material=s.material_interface.get_path_name() if s.material_interface else '') for i,s in enumerate(asset.get_editor_property('materials'))],lods=[])
 count=S.get_lod_count(asset);row['lod_count']=count
 tags=u.EditorAssetLibrary.get_tag_values(path)
 row['saved_render_tags']={str(k):str(v) for k,v in tags.items() if str(k) in ('Triangles','Vertices','LODs','NaniteEnabled','MaxBoneInfluences')}
 # RenderData conversion reads CPU index buffers which may already be
 # discarded by streaming. Registry triangles are generated from the actual
 # LOD0 render sections by USkeletalMesh::GetAssetRegistryTags. SourceModel is
 # sufficient to identify material sections without touching GPU buffers.
 opt=u.GeometryScriptMeshReadLOD();opt.lod_type=u.GeometryScriptLODType.SOURCE_MODEL;opt.lod_index=0
 dm,status=G.copy_mesh_from_skeletal_mesh(asset,u.DynamicMesh(),u.GeometryScriptCopyMeshFromAssetOptions(request_tangents=False),opt)
 if status!=u.GeometryScriptOutcomePins.SUCCESS:raise RuntimeError('Cannot read source sections '+path)
 read_ids=next(getattr(M,n) for n in dir(M) if n.startswith('get_all_triangle_material'))
 _,ids,has=read_ids(dm);material_ids=u.GeometryScript_List.convert_index_list_to_array(ids) if has else []
 for index in range(count if all_lods else min(1,count)):
  lod=dict(index=index,render_vertices=S.get_num_verts(asset,index),sections=S.get_num_sections(asset,index))
  if index==0:lod.update(triangles=int(row['saved_render_tags']['Triangles']),source_triangles=dm.get_triangle_count(),triangles_by_material=dict(Counter(int(i) for i in material_ids)))
  row['lods'].append(lod)
 del dm
 report['meshes'][path]=row;emit()
 print('GLOVE_BUDGET_MESH',asset.get_name(),row['lods'][0]['triangles'],count,flush=True)

def inspect_material(path):
 if not path or path in report['materials']:return
 mat=u.load_asset(path)
 if not mat:report['errors'].append('Missing material '+path);return
 stats=L.get_statistics(mat)
 row=dict(path=path,statistics={k:stats.get_editor_property(k) for k in ['num_vertex_shader_instructions','num_pixel_shader_instructions','num_samplers','num_vertex_texture_samples','num_pixel_texture_samples','num_virtual_texture_samples']},textures=[])
 parent=mat
 while isinstance(parent,u.MaterialInstanceConstant):parent=parent.get_editor_property('parent')
 row['shading_model']=str(parent.get_editor_property('shading_model'));row['blend_mode']=str(parent.get_editor_property('blend_mode'));row['two_sided']=parent.get_editor_property('two_sided')
 for tex in L.get_used_textures(parent):
  if not isinstance(tex,u.Texture2D):continue
  row['textures'].append(dict(path=tex.get_path_name(),width=tex.blueprint_get_size_x(),height=tex.blueprint_get_size_y(),compression=str(tex.get_editor_property('compression_settings')),srgb=tex.get_editor_property('srgb'),never_stream=tex.get_editor_property('never_stream'),lod_bias=tex.get_editor_property('lod_bias'),max_texture_size=tex.get_editor_property('max_texture_size'),compression_no_alpha=tex.get_editor_property('compression_no_alpha')))
 report['materials'][path]=row;emit();print('GLOVE_BUDGET_MATERIAL',path,row['statistics'],flush=True)

gloves=['ue_field_gloves','ue_field_gloves_black','ue_original_gloves','ue_steel_gauntlets']
shirts=['ue_field_sweater','ue_chainmail_shirt']
profiles=['M4','M1911','DW715','Body']
try:
 for item in gloves+shirts:
  recipe=cfg['items'][item];report['recipes'][item]=recipe
  for name in profiles:
   path=recipe.get('rig_meshes',{}).get(name)
   if path:inspect_mesh(path)
   skin=recipe.get('skin_meshes',{}).get(name)
   if skin:inspect_mesh(skin)
 for path,profile in cfg['profiles'].items():
  if path.startswith('/Game/Weapons/'):
   inspect_mesh(path,profile['rig_profile'] in profiles)
  if path.startswith('/Game/Weapons/') and profile['rig_profile'] in profiles:
   inspect_mesh(profile.get('native_bare_skin',profile['base']))
 report['profiles']=cfg['profiles']
 # Inspect production materials once for the representative first-person rig.
 for item in gloves+shirts:
  recipe=cfg['items'][item];path=recipe['rig_meshes']['M4']
  if recipe.get('material'):inspect_material(recipe['material'])
  else:
   for slot in report['meshes'][path]['materials']:inspect_material(slot['material'])
 emit();print('GLOVE_VIEWMODEL_BUDGET_COMPLETE',len(report['meshes']),len(report['materials']),flush=True)
except Exception as e:
 report['errors'].append(str(e));emit();raise
