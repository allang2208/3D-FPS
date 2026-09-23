import unreal as u,json,sys
from pathlib import Path
O=Path(__file__).parent;P='/Game/Weapons/PKMLowpoly20260922';L=u.EditorAssetLibrary
if u.get_editor_subsystem(u.LevelEditorSubsystem).is_in_play_in_editor():raise RuntimeError('End PIE before PKM integration; no asset was changed')
mesh=u.load_asset(P+'/SK_PKM_Manny')
filename=mesh.get_editor_property('asset_import_data').get_first_filename().replace('\\','/')
if '/Belt08/' not in filename:
 exec(compile((O/'reimport_mesh.py').read_text(),str(O/'reimport_mesh.py'),'exec'))
else:
 sys.path.insert(0,str(O))
 from material_binding import capture_bindings,bind_materials
 bind_materials(mesh,json.loads((O/'surface_import.json').read_text())['bindings'],capture_bindings(mesh))
 for asset in [mesh,mesh.skeleton]:
  if not L.save_loaded_asset(asset,False):raise RuntimeError('PKM asset save failed: '+asset.get_path_name())
 (O/'mesh_reimport.json').write_text(json.dumps({'mesh':mesh.get_path_name(),'skeleton':mesh.skeleton.get_path_name(),'updated_skeleton_reference_pose':True,'source':filename,'saved':True},indent=2))
 print('PKM08 mesh and skeleton saved.')
exec(compile((O/'import_motion.py').read_text(),str(O/'import_motion.py'),'exec'))
(O/'integration_complete.json').write_text(json.dumps({'mesh':P+'/SK_PKM_Manny','animations':list(json.loads((O/'motion_import.json').read_text())),'materials_saved':True,'mesh_saved':True,'animation_set_saved':True,'runtime_tested':False},indent=2))
print('PKM08 mesh, private skeleton and all 12 animations saved; no PIE test.')
