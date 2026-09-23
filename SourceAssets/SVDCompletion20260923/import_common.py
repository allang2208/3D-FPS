"""Short SVD integration batches, invoked with the existing project bridge."""
import unreal as u,json
from pathlib import Path
O=Path('D:/FPS3D/FPSGAME/SourceAssets/SVDCompletion20260923');BASE='/Game/Weapons/SVDDragunov20260922/Complete20260923';OLD='/Game/Weapons/SVDDragunov20260922'
E=u.EditorAssetLibrary;A=u.AssetToolsHelpers.get_asset_tools();receipt=json.loads((O/'import_receipt.json').read_text()) if (O/'import_receipt.json').exists() else {}
if u.get_editor_subsystem(u.UnrealEditorSubsystem).get_game_world():raise RuntimeError('SVD import needs the current play session stopped')
def saved(asset):
 if not E.save_loaded_asset(asset,False):raise RuntimeError('Save failed: '+asset.get_path_name())
 receipt[asset.get_path_name()]={'saved':True,'class':asset.get_class().get_name()};(O/'import_receipt.json').write_text(json.dumps(receipt,indent=2))
def safe(path):
 if path in {p.get_path_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()}:raise RuntimeError('Unsaved target: '+path)
def material(name,color,metal,rough,glass=False):
 path=BASE+'/Materials/'+name;safe(path);m=u.load_asset(path)
 if not m:m=A.create_asset(name,BASE+'/Materials',u.Material,u.MaterialFactoryNew())
 m.set_editor_property('used_with_skeletal_mesh',True)
 if glass:m.set_editor_property('blend_mode',u.BlendMode.BLEND_TRANSLUCENT);m.set_editor_property('two_sided',True)
 lib=u.MaterialEditingLibrary;lib.delete_all_material_expressions(m)
 c=lib.create_material_expression(m,u.MaterialExpressionConstant3Vector);c.set_editor_property('constant',u.LinearColor(*color,1));lib.connect_material_property(c,'',u.MaterialProperty.MP_BASE_COLOR)
 for prop,value in [(u.MaterialProperty.MP_METALLIC,metal),(u.MaterialProperty.MP_ROUGHNESS,rough)]+([(u.MaterialProperty.MP_OPACITY,.14)] if glass else []):
  n=lib.create_material_expression(m,u.MaterialExpressionConstant);n.set_editor_property('r',value);lib.connect_material_property(n,'',prop)
 lib.recompile_material(m);saved(m);return m
flag='Interchange.FeatureFlags.Import.FBX';prior=u.SystemLibrary.get_console_variable_int_value(flag);u.SystemLibrary.execute_console_command(None,flag+' 0')
try:
 sk=u.load_asset('/Game/Weapons/M4HK416Replica/SK_M4_HK416_Skeleton')
 if not sk:raise RuntimeError('Missing shared Manny skeleton')
 if JOB=='mesh':
  path=BASE+'/SK_SVD_Manny';safe(path)
  opts=u.FbxImportUI();opts.automated_import_should_detect_type=False;opts.mesh_type_to_import=u.FBXImportType.FBXIT_SKELETAL_MESH;opts.import_as_skeletal=True;opts.import_mesh=True;opts.import_animations=False;opts.import_materials=False;opts.import_textures=False;opts.create_physics_asset=False;opts.skeleton=sk
  t=u.AssetImportTask();t.filename=str(O/'Exports/SK_SVD_Manny.fbx');t.destination_path=BASE;t.destination_name='SK_SVD_Manny';t.options=opts;t.factory=u.FbxFactory();t.automated=True;t.replace_existing=True;t.save=False;A.import_asset_tasks([t]);mesh=u.load_asset(path)
  if not mesh:raise RuntimeError('Mesh import failed')
  lens=material('M_SVD_OpticalGlass',(.018,.038,.045),.05,.10,True);bolt=material('M_SVD_BoltCarrier',(.028,.033,.04),.85,.34)
  m4=u.load_asset('/Game/Weapons/M4HK416Replica/SK_M4_FoldingSights_HK416');arms={str(s.material_slot_name):s.material_interface for s in m4.materials}
  slots=list(mesh.materials);mapping={}
  for slot in slots:
   n=str(slot.material_slot_name);target=None
   if 'BoltCarrier' in n:target=bolt
   elif 'ScopeLens' in n:target=lens
   else:
    for key in ['ChargingHandle','SafetyLever','ScopeMount','ScopeBody','Magazine','Trigger','Body']:
     if key.lower() in n.lower().replace('_',''):target=u.load_asset(OLD+'/Materials/MI_SVD_'+key);break
   if target is None:
    for k,v in arms.items():
     if k.lower() in n.lower() or n.lower() in k.lower():target=v;break
   if target is None:raise RuntimeError('Unmapped SVD material slot '+n)
   slot.material_interface=target;mapping[n]=target.get_path_name()
  mesh.materials=slots;saved(mesh);(O/'installed_materials.json').write_text(json.dumps(mapping,indent=2))
 elif JOB.startswith('animations'):
  info=json.loads((O/'authoring.json').read_text())['clips'];keys=list(info);start=int(JOB.split('_')[1])*3
  compression=u.load_asset('/Game/Weapons/M4TacticalTossFinal/A_M4_HK416_reload').get_editor_property('bone_compression_settings')
  for key in keys[start:start+3]:
   name='A_SVD_'+key;safe(BASE+'/Animations/'+name);opts=u.FbxImportUI();opts.automated_import_should_detect_type=False;opts.mesh_type_to_import=u.FBXImportType.FBXIT_ANIMATION;opts.skeleton=sk;opts.import_mesh=False;opts.import_animations=True;opts.import_materials=False;opts.import_textures=False
   opts.anim_sequence_import_data.set_editor_property('use_default_sample_rate',False);opts.anim_sequence_import_data.set_editor_property('custom_sample_rate',120)
   t=u.AssetImportTask();t.filename=str(O/'Exports'/(name+'.fbx'));t.destination_path=BASE+'/Animations';t.destination_name=name;t.options=opts;t.factory=u.FbxFactory();t.automated=True;t.replace_existing=True;t.save=False;A.import_asset_tasks([t]);anim=u.load_asset(BASE+'/Animations/'+name)
   if not anim:raise RuntimeError('Missing imported clip '+name)
   anim.set_editor_property('bone_compression_settings',compression);saved(anim)
 elif JOB=='audio':
  for file in sorted((O/'Audio').glob('*.wav')):
   safe(BASE+'/Audio/'+file.stem);t=u.AssetImportTask();t.filename=str(file);t.destination_path=BASE+'/Audio';t.destination_name=file.stem;t.automated=True;t.replace_existing=True;t.save=False;A.import_asset_tasks([t]);asset=u.load_asset(BASE+'/Audio/'+file.stem)
   if not asset:raise RuntimeError('Missing sound '+file.stem)
   saved(asset)
finally:u.SystemLibrary.execute_console_command(None,flag+' '+str(prior))
print('SVD_BATCH_SAVED',JOB,len(receipt))
