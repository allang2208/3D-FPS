import unreal as u,json,runpy
from pathlib import Path
O=Path(__file__).parent;D='/Game/Weapons/ASH12/MagazineFinish20260919';E=u.EditorAssetLibrary;A=u.AssetToolsHelpers.get_asset_tools()
u.SystemLibrary.execute_console_command(None,'Interchange.FeatureFlags.Import.FBX 0')
name='SM_ASH12_ExtMag30_Finish';t=u.AssetImportTask();t.filename=str(O/(name+'.fbx'));t.destination_path=D;t.destination_name=name;t.automated=True;t.replace_existing=True;t.save=False
opts=u.FbxImportUI();opts.automated_import_should_detect_type=False;opts.mesh_type_to_import=u.FBXImportType.FBXIT_STATIC_MESH;opts.import_materials=False;opts.import_textures=False;opts.import_animations=False
imp=opts.static_mesh_import_data;imp.combine_meshes=True;imp.convert_scene_unit=False;imp.normal_import_method=u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS_AND_TANGENTS;imp.generate_lightmap_u_vs=False;imp.vertex_color_import_option=u.VertexColorImportOption.REPLACE;t.options=opts;t.factory=u.FbxFactory();A.import_asset_tasks([t])
mesh=u.load_asset(D+'/'+name)
if not mesh:raise RuntimeError('ASH magazine import failed')
slots=mesh.static_materials
for i,slot in enumerate(slots):
 path='/Game/Weapons/ASH12/Surface20260919/Materials/M_ASH12_Magazine_Base' if 'Base' in str(slot.material_slot_name) else '/Game/Weapons/ASH12/ExtendedMagazine20260919/Materials/M_ASH12_Continuous_Graph'
 mat=u.load_asset(path)
 if not mat:raise RuntimeError('Missing '+path)
 slot.material_interface=mat;slots[i]=slot
mesh.set_editor_property('static_materials',slots)
if not E.save_loaded_asset(mesh,False):raise RuntimeError('ASH magazine save failed')
(O/'installed.json').write_text(json.dumps(dict(mesh=mesh.get_path_name(),slots=[s.material_interface.get_path_name() for s in mesh.static_materials],vertex_color_import='REPLACE',region_mask=[0,0,0,1]),indent=2))
runpy.run_path(str(O/'install_icon.py'),run_name='__main__')
