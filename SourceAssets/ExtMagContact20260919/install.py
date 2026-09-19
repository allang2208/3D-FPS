import unreal as u,json,shutil
from pathlib import Path
O=Path(__file__).parent;P=O.parents[1];DEST='/Game/Weapons/ExtMagContact20260919'
A=u.AssetToolsHelpers.get_asset_tools();E=u.EditorAssetLibrary
u.SystemLibrary.execute_console_command(None,'Interchange.FeatureFlags.Import.FBX 0')
hosts={'M4':u.load_asset('/Game/Weapons/M4HK416Replica/SK_M4_FoldingSights_HK416'),'AKM':u.load_asset('/Game/Weapons/AKMIntegration/SovietFab/RearGrip20260913/SK_AKM_MannyNative')}
report={};manifest=json.loads((O/'animation_authoring.json').read_text())
for name,entry in manifest.items():
 gun='M4' if name.startswith('A_M4_') else 'AKM';host=hosts[gun]
 t=u.AssetImportTask();t.filename=str(O/'FBX'/(name+'.fbx'));t.destination_path=DEST;t.destination_name=name;t.automated=True;t.replace_existing=True;t.save=False
 opts=u.FbxImportUI();opts.automated_import_should_detect_type=False;opts.mesh_type_to_import=u.FBXImportType.FBXIT_ANIMATION;opts.skeleton=host.skeleton;opts.import_mesh=False;opts.import_animations=True;opts.import_materials=False;opts.import_textures=False
 opts.anim_sequence_import_data.set_editor_property('use_default_sample_rate',False);opts.anim_sequence_import_data.set_editor_property('custom_sample_rate',entry['rate']);t.options=opts;t.factory=u.FbxFactory();A.import_asset_tasks([t])
 if not t.imported_object_paths:raise RuntimeError('Animation import failed '+name)
 anim=u.load_asset(DEST+'/'+name)
 if anim.get_editor_property('skeleton')!=host.skeleton:raise RuntimeError('Wrong skeleton '+name)
 compression=u.load_asset('/Game/Weapons/M4InfimaRigV4/BC_M4Viewmodel')
 if compression:anim.set_editor_property('bone_compression_settings',compression)
 if not E.save_loaded_asset(anim,False):raise RuntimeError('Save failed '+name)
 report[name]={'path':anim.get_path_name(),'skeleton':host.skeleton.get_path_name(),'saved':True}
name='SM_ExtMag_AKM40_Closed';t=u.AssetImportTask();t.filename=str(O/'FBX'/(name+'.fbx'));t.destination_path=DEST;t.destination_name=name;t.automated=True;t.replace_existing=True;t.save=False
opts=u.FbxImportUI();opts.automated_import_should_detect_type=False;opts.mesh_type_to_import=u.FBXImportType.FBXIT_STATIC_MESH;opts.import_materials=False;opts.import_textures=False;opts.import_animations=False
opts.static_mesh_import_data.combine_meshes=True;opts.static_mesh_import_data.convert_scene_unit=False;opts.static_mesh_import_data.normal_import_method=u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS_AND_TANGENTS;opts.static_mesh_import_data.generate_lightmap_u_vs=False
t.options=opts;t.factory=u.FbxFactory();A.import_asset_tasks([t]);mesh=u.load_asset(DEST+'/'+name)
material=next(s.material_interface for s in hosts['AKM'].get_editor_property('materials') if str(s.material_slot_name)=='M_AKM_Soviet_Magazine')
slots=mesh.get_editor_property('static_materials')
for i in range(len(slots)):
 slot=slots[i];slot.material_interface=material;slots[i]=slot
mesh.set_editor_property('static_materials',slots)
if not E.save_loaded_asset(mesh,False):raise RuntimeError('AKM mesh save failed')
report[name]={'path':mesh.get_path_name(),'saved':True,'material':material.get_path_name()}
icon=O/'Icons/ue_akm_magazine_ext_mag.png'
if icon.exists():
 target=P/'Content/ColdSteelData/AttachmentIcons20260913'/icon.name;(O/'Before').mkdir(exist_ok=True)
 if not (O/'Before'/icon.name).exists():shutil.copy2(target,O/'Before'/icon.name)
 shutil.copy2(icon,target)
(O/'install_receipt.json').write_text(json.dumps(report,indent=2));u.log('EXTCONTACT_INSTALLED '+json.dumps(report))
