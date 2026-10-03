"""Save fitted RSH meshes and their existing private single-action consumers."""
import unreal as u,json,runpy
from pathlib import Path
O=Path(__file__).parent;B=O.parent/'RSH12Integration20261003';SA=O.parent/'RSH12SingleAction20261003';P=O.parents[1]
if u.EditorLevelLibrary.get_game_world():raise RuntimeError('Existing PIE/game is active; preserve it and defer import')
E=u.EditorAssetLibrary;A=u.AssetToolsHelpers.get_asset_tools();dest='/Game/Weapons/RSH12'
skeleton=u.load_asset('/Game/Weapons/DanWesson715/Integrated20260913/SK_DW715_Manny_Skeleton')
mi=u.load_asset(dest+'/Materials/MI_RSH12_SourcePBR');bare=u.load_asset('/Game/Characters/ModularOutfit20260924/BarePalmV7/Materials/MI_BareNative_Default')
if not all((skeleton,mi,bare)):raise RuntimeError('Installed RSH dependency unavailable')
receipt=dict(complete=False,revision='registered-mechanical-axes-v3-full-skin',saved=[],meshes=[],scope='RSH full mixed-weight palm/finger contact, actual hammer-spur contact and ADS cock transition',game_started=False)
config=P/'Content/ColdSteelData/modular_outfits.json';original=config.read_text(encoding='utf-8-sig');catalog=json.loads(original);arm_slots={}
def record():(O/'import_receipt.json').write_text(json.dumps(receipt,indent=2))
def save(asset):
 if not E.save_loaded_asset(asset,False):raise RuntimeError('Asset save failed '+asset.get_path_name())
 receipt['saved'].append(asset.get_path_name());record()
flag='Interchange.FeatureFlags.Import.FBX';old=u.SystemLibrary.get_console_variable_int_value(flag);u.SystemLibrary.execute_console_command(None,flag+' 0')
try:
 for family,relative,folder in [('single','Single',dest),('r','Dual/r',dest+'/Dual/r'),('l','Dual/l',dest+'/Dual/l')]:
  source=B/relative;recipe=json.loads((source/'authoring.json').read_text());name=Path(recipe['mesh']).stem
  options=u.FbxImportUI();options.automated_import_should_detect_type=False;options.mesh_type_to_import=u.FBXImportType.FBXIT_SKELETAL_MESH
  options.import_as_skeletal=True;options.import_mesh=True;options.import_animations=False;options.import_materials=False;options.import_textures=False;options.create_physics_asset=False;options.skeleton=skeleton
  options.skeletal_mesh_import_data.set_editor_property('update_skeleton_reference_pose',False);options.skeletal_mesh_import_data.set_editor_property('use_t0_as_ref_pose',False)
  options.skeletal_mesh_import_data.normal_import_method=u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS
  task=u.AssetImportTask();task.filename=str(source/recipe['mesh']);task.destination_path=folder;task.destination_name=name;task.automated=True
  task.replace_existing=True;task.replace_existing_settings=True;task.save=False;task.options=options;task.factory=u.FbxFactory();A.import_asset_tasks([task])
  mesh=u.load_asset(folder+'/'+name)
  if not mesh:raise RuntimeError('Import failed '+name)
  slots=list(mesh.materials);arms=[]
  for i,slot in enumerate(slots):
   is_arm='Manny' in str(slot.material_slot_name);slot.material_interface=bare if is_arm else mi
   if is_arm:arms.append(i)
   slots[i]=slot
  mesh.set_editor_property('materials',slots);mesh.set_editor_property('physics_asset',None)
  subsystem=u.get_editor_subsystem(u.SkeletalMeshEditorSubsystem)
  for lod in range(subsystem.get_lod_count(mesh)):
   settings=subsystem.get_lod_build_settings(mesh,lod);settings.use_full_precision_u_vs=True;subsystem.set_lod_build_settings(mesh,lod,settings)
  E.set_metadata_tag(mesh,'GripContactRevision','RSH12Grip20261003 axes-v3: source grip registration, transported mechanical axes, full mixed-weight V7 palm/finger contact; five-bore/case fit retained')
  save(mesh);arm_slots[mesh.get_path_name()]=arms;receipt['meshes'].append(dict(family=family,asset=mesh.get_path_name(),arm_slots=arms))
  print('RSH12_GRIP_MESH_SAVED',family,flush=True)
finally:u.SystemLibrary.execute_console_command(None,flag+' '+str(old))
runpy.run_path(str(SA/'import_assets.py'),run_name='__main__')
animation=json.loads((SA/'import_receipt.json').read_text())
if not animation['complete']:raise RuntimeError('Private animation consumers not saved')
receipt['saved'].extend(animation['saved']);receipt['animation_assets']=animation['saved']
for path,arms in arm_slots.items():catalog['profiles'][path]['hide_source_materials']=arms
if json.loads(original)!=catalog:
 if config.read_text(encoding='utf-8-sig')!=original:raise RuntimeError('Outfit catalog changed concurrently; preserve it')
 (O/'BeforeSource/modular_outfits.json').write_text(original,encoding='utf8')
 config.write_text(json.dumps(catalog,ensure_ascii=False,indent=2),encoding='utf8')
receipt.update(complete=True,skeleton_saved=False,status='Three fitted meshes, four baked fire clips and three shared profiles saved')
record();print('RSH12_GRIP_ASSETS_SAVED',len(receipt['saved']),flush=True)
