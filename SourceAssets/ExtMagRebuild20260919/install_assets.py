"""Import into new revision packages; safe to author alongside the open editor.
The runtime attachment icons are PNG files, loaded by M4GunsmithLayout.
"""
import unreal as u,json,shutil
from pathlib import Path
O=Path(__file__).parent;P=O.parents[1];DEST='/Game/Weapons/ExtMagRebuild20260919/Release';ANIM=DEST
jobs={
 'M4':('SM_ExtMag_M440','/Game/Weapons/M4HK416Replica/SK_M4_FoldingSights_HK416','Magazine_Light_001','ue_m4a1'),
 'AKM':('SM_ExtMag_AKM40','/Game/Weapons/AKMIntegration/SovietFab/RearGrip20260913/SK_AKM_MannyNative','M_AKM_Soviet_Magazine','ue_akm'),
 'QBZ':('SM_ExtMag_QBZ40','/Game/Weapons/QBZ191/RearGrip20260913/SK_QBZ191_Manny','M_QBZ191_Wear_Magazine','ue_qbz191'),
}
E=u.EditorAssetLibrary;A=u.AssetToolsHelpers.get_asset_tools();report={};backup=O/'Before';backup.mkdir(exist_ok=True)
u.SystemLibrary.execute_console_command(None,'Interchange.FeatureFlags.Import.FBX 0')
def keep_file(path):
 if path.exists():
  target=backup/path.name
  if not target.exists():shutil.copy2(path,target)
for gun,(name,hostpath,slot,weapon) in jobs.items():
 host=u.load_asset(hostpath)
 if not host:raise RuntimeError('Missing host '+hostpath)
 material=next((s.material_interface for s in host.get_editor_property('materials') if str(s.material_slot_name)==slot),None)
 if not material:raise RuntimeError('Missing factory material '+slot)
 keep_file(P/'Content/Weapons/ExtMagUniversal20260917'/(name+'.uasset'))
 task=u.AssetImportTask();task.filename=str(O/'FBX'/(name+'.fbx'));task.destination_path=DEST;task.destination_name=name;task.automated=True;task.replace_existing=True;task.save=False
 opts=u.FbxImportUI();opts.automated_import_should_detect_type=False;opts.mesh_type_to_import=u.FBXImportType.FBXIT_STATIC_MESH;opts.import_materials=False;opts.import_textures=False;opts.import_animations=False
 opts.static_mesh_import_data.combine_meshes=True;opts.static_mesh_import_data.convert_scene_unit=False;opts.static_mesh_import_data.normal_import_method=u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS;opts.static_mesh_import_data.generate_lightmap_u_vs=False
 task.options=opts;task.factory=u.FbxFactory();A.import_asset_tasks([task])
 if not task.imported_object_paths:raise RuntimeError('No imported mesh '+name)
 mesh=u.load_asset(DEST+'/'+name)
 slots=mesh.get_editor_property('static_materials')
 for i in range(len(slots)):slots[i].material_interface=material
 mesh.set_editor_property('static_materials',slots)
 if not E.save_loaded_asset(mesh,False):raise RuntimeError('Save failed '+name)
 report[gun]={'mesh':mesh.get_path_name(),'material':material.get_path_name(),'saved':True}
 icon=O/'Icons'/(weapon+'_magazine_ext_mag.png')
 if icon.exists():
  live=P/'Content/ColdSteelData/AttachmentIcons20260913'/icon.name;keep_file(live);keep_file(live.with_suffix('.uasset'));shutil.copy2(icon,live)
  report[gun]['icon_png']=str(live)
host=u.load_asset(jobs['M4'][1])
for clip in ['reload','reload_empty']:
 name='A_M4_ExtMagGrip_'+clip;t=u.AssetImportTask();t.filename=str(O/'FBX'/('A_M4_ExtMag_'+clip+'.fbx'));t.destination_path=ANIM;t.destination_name=name;t.automated=True;t.replace_existing=True;t.save=False
 opts=u.FbxImportUI();opts.automated_import_should_detect_type=False;opts.mesh_type_to_import=u.FBXImportType.FBXIT_ANIMATION;opts.skeleton=host.skeleton;opts.import_mesh=False;opts.import_animations=True;opts.import_materials=False;opts.import_textures=False
 opts.anim_sequence_import_data.set_editor_property('use_default_sample_rate',False);opts.anim_sequence_import_data.set_editor_property('custom_sample_rate',480);t.options=opts;t.factory=u.FbxFactory();A.import_asset_tasks([t])
 if not t.imported_object_paths:raise RuntimeError('No imported animation '+name)
 anim=u.load_asset(ANIM+'/'+name);compression=u.load_asset('/Game/Weapons/M4InfimaRigV4/BC_M4Viewmodel')
 if anim.get_editor_property('skeleton')!=host.skeleton:raise RuntimeError('Animation importer did not use the host skeleton: '+name)
 if compression:anim.set_editor_property('bone_compression_settings',compression)
 if not E.save_loaded_asset(anim,False):raise RuntimeError('Animation save failed '+name)
 report[clip]={'path':anim.get_path_name(),'saved':True}
(O/'install_receipt.json').write_text(json.dumps(report,indent=2),encoding='utf-8');u.log('EXTMAG_REBUILD_INSTALLED '+json.dumps(report))
