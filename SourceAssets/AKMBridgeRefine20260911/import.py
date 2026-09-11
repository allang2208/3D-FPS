import unreal as u,json
from pathlib import Path
O=Path(__file__).parent;P='/Game/Weapons/AKMIntegration/SovietFab/Optics';L=u.EditorAssetLibrary;report={};material=u.load_asset('/Game/Weapons/AKMIntegration/SovietFab/ArmSupport/M_AKM_Soviet_MountSteel');assert material
for f in O.glob('SM_AKM_Mount_*.fbx'):
 opt=u.FbxImportUI();opt.automated_import_should_detect_type=False;opt.mesh_type_to_import=u.FBXImportType.FBXIT_STATIC_MESH;opt.import_materials=False;opt.import_textures=False;opt.import_animations=False;opt.static_mesh_import_data.combine_meshes=True
 t=u.AssetImportTask();t.filename=str(f);t.destination_path=P;t.destination_name=f.stem;t.options=opt;t.automated=True;t.replace_existing=True;t.save=True;u.AssetToolsHelpers.get_asset_tools().import_asset_tasks([t]);m=u.load_asset(P+'/'+f.stem);assert m;m.set_material(0,material);assert L.save_loaded_asset(m,False);report[f.stem]={'bounds':str(m.get_bounds()),'triangles':m.get_num_triangles(0),'material':m.get_material(0).get_path_name()}
assert len(report)==3
# Existing AKM muzzle exports must remain in parity with the current M4 production meshes.
for k in ['suppressor','brake','titanium_brake']:
 a=u.load_asset('/Game/Weapons/AKMIntegration/SovietFab/Attachments/SM_AKM_'+k);m=u.load_asset('/Game/Weapons/M4MuzzlesV1/SM_M4_'+k);assert a and m
 assert a.get_num_triangles(0)==m.get_num_triangles(0),(k,a.get_num_triangles(0),m.get_num_triangles(0))
 assert [s.material_interface for s in a.static_materials]==[s.material_interface for s in m.static_materials],k
 report[k]={'triangles':a.get_num_triangles(0),'same_current_M4_materials':True}
(O/'import.json').write_text(json.dumps(report,indent=2));u.log('AKM_OPTICS_IMPORT_PASS')
