"""Install mouth completion and real per-rifle material bindings in new packages."""
import unreal as u,json
from pathlib import Path
O=Path(__file__).parent;DEST='/Game/Weapons/MagazineMouthFinish20260919'
E=u.EditorAssetLibrary;A=u.AssetToolsHelpers.get_asset_tools();L=u.MaterialEditingLibrary
u.SystemLibrary.execute_console_command(None,'Interchange.FeatureFlags.Import.FBX 0')
jobs={
 'M4':('SM_ExtMag_M440',O.parent/'ExtMagPattern20260919/FBX/SM_ExtMag_M440.fbx','/Game/Weapons/M4HK416Replica/SK_M4_FoldingSights_HK416','Magazine_Light_001'),
 'QBZ':('SM_ExtMag_QBZ40',O.parent/'ExtMagPattern20260919/FBX/SM_ExtMag_QBZ40.fbx','/Game/Weapons/QBZ191/RearGrip20260913/SK_QBZ191_Manny','M_QBZ191_Wear_Magazine'),
 'AKM':('SM_ExtMag_AKM40_Mouth',O/'FBX/SM_ExtMag_AKM40_Mouth.fbx','/Game/Weapons/AKMIntegration/SovietFab/RearGrip20260913/SK_AKM_MannyNative','M_AKM_Soviet_Magazine')}
def save(a):
 if not E.save_loaded_asset(a,False):raise RuntimeError('Save failed '+a.get_path_name())
report={}
for gun,(name,file,hostpath,label) in jobs.items():
 host=u.load_asset(hostpath);material=next(s.material_interface for s in host.materials if str(s.material_slot_name)==label)
 task=u.AssetImportTask();task.filename=str(file);task.destination_path=DEST;task.destination_name=name;task.automated=True;task.replace_existing=True;task.save=False
 opts=u.FbxImportUI();opts.automated_import_should_detect_type=False;opts.mesh_type_to_import=u.FBXImportType.FBXIT_STATIC_MESH;opts.import_materials=False;opts.import_textures=False;opts.import_animations=False
 data=opts.static_mesh_import_data;data.combine_meshes=True;data.convert_scene_unit=False;data.normal_import_method=u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS_AND_TANGENTS;data.generate_lightmap_u_vs=False
 task.options=opts;task.factory=u.FbxFactory();A.import_asset_tasks([task])
 if not task.imported_object_paths:raise RuntimeError('No imported mesh '+name)
 mesh=u.load_asset(DEST+'/'+name)
 mouth=None
 if gun=='AKM':
  path=DEST+'/M_AKM_MagazineMouth'
  mouth=u.load_asset(path) if E.does_asset_exist(path) else E.duplicate_asset(material.get_path_name(),path)
  # Newly made rim/interior samples a plain steel crop, not the source normal atlas.
  normal=L.create_material_expression(mouth,u.MaterialExpressionConstant3Vector);normal.constant=u.LinearColor(0,0,1,0);L.connect_material_property(normal,'',u.MaterialProperty.MP_NORMAL)
  ao=L.create_material_expression(mouth,u.MaterialExpressionConstant);ao.r=1.;L.connect_material_property(ao,'',u.MaterialProperty.MP_AMBIENT_OCCLUSION)
  L.recompile_material(mouth);save(mouth)
 slots=mesh.get_editor_property('static_materials')
 for i in range(len(slots)):
  slot=slots[i];slot.material_interface=mouth if 'Mouth' in str(slot.material_slot_name) else material
  # Unreal Array indexing returns a struct copy: assign that copy back.
  slots[i]=slot
 mesh.set_editor_property('static_materials',slots);save(mesh)
 actual=[{'slot':str(s.material_slot_name),'material':s.material_interface.get_path_name() if s.material_interface else None} for s in mesh.get_editor_property('static_materials')]
 if any(not s['material'] or 'WorldGridMaterial' in s['material'] for s in actual):raise RuntimeError('Material assignment did not persist '+name)
 report[gun]={'mesh':mesh.get_path_name(),'source':str(file),'host':hostpath,'actual_slots':actual,'saved':True}
 (O/'install_receipt.json').write_text(json.dumps(report,indent=2))
u.log('MAGAZINE_MOUTH_FINISH_INSTALLED '+json.dumps(report))
