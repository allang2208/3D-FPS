"""Save only corrected RSH-12 geometry and its current animation consumers."""
import unreal as u,json,runpy
from pathlib import Path
O=Path(__file__).parent;B=O.parent/'RSH12Integration20261003';SA=O.parent/'RSH12SingleAction20261003';P=O.parents[1]
if u.EditorLevelLibrary.get_game_world():raise RuntimeError('Existing game/PIE is active; preserve it and defer this import')
E=u.EditorAssetLibrary;A=u.AssetToolsHelpers.get_asset_tools();dest='/Game/Weapons/RSH12'
skeleton=u.load_asset('/Game/Weapons/DanWesson715/Integrated20260913/SK_DW715_Manny_Skeleton')
mi=u.load_asset(dest+'/Materials/MI_RSH12_SourcePBR');bare=u.load_asset('/Game/Characters/ModularOutfit20260924/BarePalmV7/Materials/MI_BareNative_Default')
if not all([skeleton,mi,bare]):raise RuntimeError('An installed RSH-12 dependency is unavailable')
receipt=dict(complete=False,saved=[],meshes=[],animation_assets=[],scope='Cylinder mechanical binding and measured cartridge/bore fit',game_started=False)
config=P/'Content/ColdSteelData/modular_outfits.json';original=config.read_text(encoding='utf-8-sig');catalog=json.loads(original);arm_slots={}
def record():(O/'import_receipt.json').write_text(json.dumps(receipt,indent=2),encoding='utf8')
def save(a):
 if not E.save_loaded_asset(a,False):raise RuntimeError('Asset save failed '+a.get_path_name())
 receipt['saved'].append(a.get_path_name());record()
def imported(file,folder,name,options):
 task=u.AssetImportTask();task.filename=str(file);task.destination_path=folder;task.destination_name=name;task.automated=True
 task.replace_existing=True;task.replace_existing_settings=True;task.save=False;task.options=options;task.factory=u.FbxFactory()
 A.import_asset_tasks([task]);asset=u.load_asset(folder+'/'+name)
 if not asset:raise RuntimeError('Import failed '+name)
 E.set_metadata_tag(asset,'MechanicalFitRevision','RSH12Fit20261003: measured five bores; extractor plate and front rod follow extractor; right release button fixed to frame; rim seat and polygon facets aligned')
 return asset
flag='Interchange.FeatureFlags.Import.FBX';old=u.SystemLibrary.get_console_variable_int_value(flag);u.SystemLibrary.execute_console_command(None,flag+' 0')
try:
 for family,relative,folder in [('single','Single',dest),('r','Dual/r',dest+'/Dual/r'),('l','Dual/l',dest+'/Dual/l')]:
  source=B/relative;recipe=json.loads((source/'authoring.json').read_text())
  options=u.FbxImportUI();options.automated_import_should_detect_type=False;options.mesh_type_to_import=u.FBXImportType.FBXIT_SKELETAL_MESH
  options.import_as_skeletal=True;options.import_mesh=True;options.import_animations=False;options.import_materials=False;options.import_textures=False;options.create_physics_asset=False;options.skeleton=skeleton
  options.skeletal_mesh_import_data.set_editor_property('update_skeleton_reference_pose',False);options.skeletal_mesh_import_data.set_editor_property('use_t0_as_ref_pose',False)
  options.skeletal_mesh_import_data.normal_import_method=u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS
  mesh=imported(source/recipe['mesh'],folder,Path(recipe['mesh']).stem,options);slots=list(mesh.materials);arms=[]
  for i,slot in enumerate(slots):
   is_arm='Manny' in str(slot.material_slot_name);slot.material_interface=bare if is_arm else mi
   if is_arm:arms.append(i)
   slots[i]=slot
  mesh.set_editor_property('materials',slots);mesh.set_editor_property('physics_asset',None)
  subsystem=u.get_editor_subsystem(u.SkeletalMeshEditorSubsystem)
  for lod in range(subsystem.get_lod_count(mesh)):
   settings=subsystem.get_lod_build_settings(mesh,lod);settings.use_full_precision_u_vs=True;subsystem.set_lod_build_settings(mesh,lod,settings)
  save(mesh);arm_slots[mesh.get_path_name()]=arms;receipt['meshes'].append(dict(family=family,asset=mesh.get_path_name(),arm_slots=arms))
  print('RSH12_FIT_MESH_SAVED',family,flush=True)
 options=u.FbxImportUI();options.automated_import_should_detect_type=False;options.mesh_type_to_import=u.FBXImportType.FBXIT_STATIC_MESH
 options.import_mesh=True;options.import_as_skeletal=False;options.import_materials=False;options.import_textures=False;options.static_mesh_import_data.combine_meshes=True
 cartridge=imported(B/'SM_RSH12_Cartridge.fbx',dest,'SM_RSH12_Cartridge',options);slots=list(cartridge.static_materials)
 for s in slots:s.material_interface=mi
 cartridge.set_editor_property('static_materials',slots);save(cartridge)
finally:u.SystemLibrary.execute_console_command(None,flag+' '+str(old))
# A single bridge batch publishes the current three profiles and all four baked fire clips.
runpy.run_path(str(SA/'import_assets.py'),run_name='__main__')
animation_receipt=json.loads((SA/'import_receipt.json').read_text())
if not animation_receipt['complete']:raise RuntimeError('Current RSH-12 animation consumers were not saved')
receipt['animation_assets']=animation_receipt['saved'];receipt['saved'].extend(animation_receipt['saved'])
for path,arms in arm_slots.items():catalog['profiles'][path]['hide_source_materials']=arms
updated=json.dumps(catalog,ensure_ascii=False,indent=2)
if json.loads(original)!=catalog:
 if config.read_text(encoding='utf-8-sig')!=original:raise RuntimeError('Outfit catalog changed during import; preserve concurrent changes')
 backup=O/'BeforeSource/modular_outfits.json'
 if not backup.exists():backup.write_text(original,encoding='utf8')
 config.write_text(updated,encoding='utf8')
receipt.update(complete=True,status='Corrected geometry, current profiles and baked fire clips saved',skeleton_saved=False)
record();print('RSH12_FIT_ASSETS_SAVED',len(receipt['saved']),flush=True)
