import unreal as u,json
from pathlib import Path
O=Path(__file__).parent;D='/Game/Weapons/M4GridUnified20260919';E=u.EditorAssetLibrary;A=u.AssetToolsHelpers.get_asset_tools();report={}
u.SystemLibrary.execute_console_command(None,'Interchange.FeatureFlags.Import.FBX 0')
materials={'M4':'/Game/Weapons/ExtMagContinuity20260919/Materials/M_M4_Continuous'}
for gun,path in materials.items():
 name='SM_M4_ExtMag40_Grid';t=u.AssetImportTask();t.filename=str(O/'FBX'/(name+'.fbx'));t.destination_path=D;t.destination_name=name;t.automated=True;t.replace_existing=True;t.save=False
 opts=u.FbxImportUI();opts.automated_import_should_detect_type=False;opts.mesh_type_to_import=u.FBXImportType.FBXIT_STATIC_MESH;opts.import_materials=False;opts.import_textures=False;opts.import_animations=False
 data=opts.static_mesh_import_data;data.combine_meshes=True;data.convert_scene_unit=False;data.normal_import_method=u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS_AND_TANGENTS;data.generate_lightmap_u_vs=False;t.options=opts;t.factory=u.FbxFactory();A.import_asset_tasks([t])
 mesh=u.load_asset(D+'/'+name);material=u.load_asset(path)
 if not mesh or not material:raise RuntimeError('Missing '+name+' or '+path)
 slots=mesh.static_materials
 for i,slot in enumerate(slots):slot.material_interface=material;slots[i]=slot
 mesh.set_editor_property('static_materials',slots)
 if not E.save_loaded_asset(mesh,False):raise RuntimeError('Save failed '+name)
 report[gun]=dict(mesh=mesh.get_path_name(),materials=[s.material_interface.get_path_name() for s in mesh.static_materials],tested=False)
 (O/'installed.json').write_text(json.dumps(report,indent=2))
