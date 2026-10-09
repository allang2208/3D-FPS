"""Import owned text repairs and patch existing PowerTheme actors only. No PIE/render."""
import json,hashlib,re,traceback
from pathlib import Path
import unreal as u
ROOT=Path(__file__).resolve().parent;PROJECT=ROOT.parents[2]
DATA=json.loads((ROOT/'manifest.json').read_text('utf8'));BASE=DATA['base']
MAP='/Game/GameMaps/Design/L_PowerTheme20261004_Subject'
E=u.EditorAssetLibrary;A=u.AssetToolsHelpers.get_asset_tools();L=u.MaterialEditingLibrary
S=u.get_editor_subsystem(u.StaticMeshEditorSubsystem) or u.new_object(u.StaticMeshEditorSubsystem)
AA=u.get_editor_subsystem(u.EditorActorSubsystem) or u.new_object(u.EditorActorSubsystem)
report=dict(stage='preparing',map=MAP,saved_assets=[],actors=[],tests_run=False,rendered=False,game_run=False)
def record():
 (ROOT/'Receipts').mkdir(exist_ok=True)
 (ROOT/'Receipts/install.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf8')
def guard():
 if Path(u.Paths.project_dir()).resolve()!=PROJECT.resolve():raise RuntimeError('Wrong project')
 cmd=u.SystemLibrary.get_command_line().lower()
 if '-run=pythonscript' not in cmd:
  if u.get_editor_subsystem(u.LevelEditorSubsystem).is_in_play_in_editor():raise RuntimeError('PIE_ACTIVE: preserve running map; stop Play before this edit')
 if E.does_asset_exist(MAP) is False:raise RuntimeError('Existing PowerTheme subject is missing')
 if u.EditorLoadingAndSavingUtils.get_dirty_map_packages():raise RuntimeError('DIRTY_MAP: preserve existing unsaved editor work')
def saved(asset,key):
 E.set_metadata_tag(asset,'PowerText20261005.Source',key)
 if not E.save_loaded_asset(asset,False):raise RuntimeError('Save failed '+asset.get_path_name())
 report['saved_assets'].append(asset.get_path_name());record()
def reuse(path,key):
 if not E.does_asset_exist(path):return None
 obj=u.load_asset(path)
 if E.get_metadata_tag(obj,'PowerText20261005.Source')!=key:raise RuntimeError('Preserve existing different text revision '+path)
 return obj
def imported(path,filename,options=None):
 task=u.AssetImportTask();task.filename=str(filename);task.destination_path,task.destination_name=path.rsplit('/',1)
 task.automated=True;task.replace_existing=False;task.save=False
 if options:task.options=options;task.factory=u.FbxFactory()
 A.import_asset_tasks([task]);asset=u.load_asset(path)
 if not asset:raise RuntimeError('Import failed '+path)
 return asset
def patch_loaded_map():
 by={x['previous_mesh']:x for x in DATA['meshes']};changed=[]
 material=u.load_asset(BASE+'/Materials/M_Power_TextCards')
 for actor in AA.get_all_level_actors():
  if not actor.get_actor_label().startswith('PowerTheme_'):continue
  for comp in actor.get_components_by_class(u.StaticMeshComponent):
   old=comp.static_mesh
   if not old:continue
   path=old.get_path_name().split('.')[0];item=by.get(path)
   if not item:continue
   new=u.load_asset(item['mesh'])
   if not new:raise RuntimeError('Repaired mesh missing '+item['mesh'])
   prior=[comp.get_material(i) for i in range(comp.get_num_materials())]
   actor.modify();comp.modify();comp.set_static_mesh(new)
   for i,mat in enumerate(prior):
    if str(new.get_editor_property('static_materials')[i].material_slot_name).startswith('PW_Labels'):mat=material
    comp.set_material(i,mat)
   comp.set_material(item['text_slot'],material)
   changed.append(dict(actor=actor.get_actor_label(),component=comp.get_name(),old=path,new=item['mesh'],plates=item['plates']))
 return changed
def main():
 guard();record()
 png=Path(DATA['texture']);key=hashlib.sha256(png.read_bytes()).hexdigest()
 path=BASE+'/Textures/T_Power_TextCards';texture=reuse(path,key)
 if not texture:
  texture=imported(path,png);texture.set_editor_property('srgb',True)
  texture.set_editor_property('compression_settings',u.TextureCompressionSettings.TC_DEFAULT)
  texture.set_editor_property('lod_group',u.TextureGroup.TEXTUREGROUP_WORLD)
  saved(texture,key)
 path=BASE+'/Materials/M_Power_TextCards';mkey=key+':opaque-enamel-078-single-front'
 material=reuse(path,mkey)
 if not material:
  material=A.create_asset('M_Power_TextCards',BASE+'/Materials',u.Material,u.MaterialFactoryNew())
  material.set_editor_property('used_with_nanite',True);material.set_editor_property('used_with_instanced_static_meshes',True)
  material.set_editor_property('two_sided',False)
  sample=L.create_material_expression(material,u.MaterialExpressionTextureSampleParameter2D)
  sample.set_editor_property('parameter_name','CardAtlas');sample.set_editor_property('texture',texture)
  sample.set_editor_property('sampler_type',u.MaterialSamplerType.SAMPLERTYPE_COLOR)
  slab=L.create_material_expression(material,u.MaterialExpressionSubstrateShadingModels)
  slab.set_editor_property('shading_model_override',u.MaterialShadingModel.MSM_DEFAULT_LIT)
  L.connect_material_expressions(sample,'RGB',slab,'BaseColor');L.connect_material_property(sample,'RGB',u.MaterialProperty.MP_BASE_COLOR)
  for name,value,prop in [('Roughness',.78,u.MaterialProperty.MP_ROUGHNESS),('Metallic',0,u.MaterialProperty.MP_METALLIC)]:
   node=L.create_material_expression(material,u.MaterialExpressionConstant);node.set_editor_property('r',value)
   L.connect_material_expressions(node,'',slab,name);L.connect_material_property(node,'',prop)
  L.connect_material_property(slab,'',u.MaterialProperty.MP_FRONT_MATERIAL)
  errors=L.recompile_material(material)
  if errors:raise RuntimeError('Text material compilation failed '+str(errors))
  saved(material,mkey)
 for item in DATA['meshes']:
  fingerprint=item['sha256'];mesh=reuse(item['mesh'],fingerprint)
  if mesh:continue
  old=u.load_asset(item['previous_mesh'])
  if not old:raise RuntimeError('Existing source asset missing '+item['previous_mesh'])
  options=u.FbxImportUI();options.import_mesh=True;options.import_materials=False;options.import_textures=False
  options.import_as_skeletal=False;options.automated_import_should_detect_type=False;options.mesh_type_to_import=u.FBXImportType.FBXIT_STATIC_MESH
  data=options.static_mesh_import_data;data.combine_meshes=True;data.convert_scene=True;data.convert_scene_unit=True
  data.transform_vertex_to_absolute=True;data.auto_generate_collision=False;data.generate_lightmap_u_vs=False;data.one_convex_hull_per_ucx=True
  data.normal_import_method=u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS
  data.normal_generation_method=u.FBXNormalGenerationMethod.MIKK_T_SPACE;data.vertex_color_import_option=u.VertexColorImportOption.REPLACE
  mesh=imported(item['mesh'],item['fbx'],options)
  old_slots={str(s.material_slot_name):s.material_interface for s in old.get_editor_property('static_materials')}
  for i,slot in enumerate(mesh.get_editor_property('static_materials')):
   slot_name=re.sub(r'[._][0-9]{3}$','',str(slot.material_slot_name))
   mat=material if slot_name in ('PW_TextCards20261005','PW_Labels') else old_slots.get(slot_name)
   if mat is None:raise RuntimeError('Original material slot missing '+item['name']+' '+slot_name)
   mesh.set_material(i,mat)
   if slot_name=='PW_TextCards20261005':item['text_slot']=i
  build=S.get_lod_build_settings(mesh,0);build.set_editor_property('use_full_precision_u_vs',True)
  build.set_editor_property('use_high_precision_tangent_basis',True);build.set_editor_property('recompute_tangents',True)
  S.set_lod_build_settings(mesh,0,build)
  body=mesh.get_editor_property('body_setup');old_body=old.get_editor_property('body_setup')
  if old_body:
   body.set_editor_property('collision_trace_flag',old_body.get_editor_property('collision_trace_flag'))
   if not item['collision_hulls']:body.set_editor_property('agg_geom',old_body.get_editor_property('agg_geom').copy())
  settings=old.get_editor_property('nanite_settings').copy();settings.explicit_tangents=True
  mesh.set_editor_property('nanite_settings',settings)
  if settings.enabled and not u.PlazaInstanceTools.build_nanite_data(mesh):raise RuntimeError('Nanite build failed '+item['name'])
  saved(mesh,fingerprint)
 report['stage']='assets_saved';record()
 guard()
 # Preserve a different dirty map; guard above stops before changing map context.
 editor=u.get_editor_subsystem(u.UnrealEditorSubsystem)
 world=editor.get_editor_world() if editor else None
 if not world or world.get_path_name().split('.')[0]!=MAP:world=u.EditorLoadingAndSavingUtils.load_map(MAP)
 if not world:raise RuntimeError('Cannot load PowerTheme subject')
 report['actors']=patch_loaded_map()
 if not u.EditorLoadingAndSavingUtils.save_map(world,MAP):raise RuntimeError('PowerTheme map save failed')
 report['stage']='map_saved';report['physical_cards_updated']=sum(x['plates'] for x in report['actors']);record()
 (ROOT/'manifest.json').write_text(json.dumps(DATA,indent=2),encoding='utf8')
 u.log('POWER_TEXT_CARDS_MAP_SAVED '+str(len(report['actors'])))
if __name__=='__main__':
 try:main()
 except Exception:
  report['error']=traceback.format_exc();record();raise
