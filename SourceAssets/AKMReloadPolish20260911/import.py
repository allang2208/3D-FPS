import unreal as u,json
from pathlib import Path
O=Path(__file__).parent;P='/Game/Weapons/AKMIntegration/SovietFab/ReloadPolish';report={};L=u.EditorAssetLibrary
m=u.load_asset('/Game/Weapons/AKMIntegration/SovietFab/Attachments/SK_AKM_MannyNative')
for variant in ['base','prism','angled']:
 for file in sorted((O/variant).glob('*.fbx')):
  opt=u.FbxImportUI();opt.automated_import_should_detect_type=False;opt.mesh_type_to_import=u.FBXImportType.FBXIT_ANIMATION;opt.skeleton=m.skeleton;opt.import_mesh=False;opt.import_animations=True;opt.import_materials=False;opt.import_textures=False;opt.anim_sequence_import_data.set_editor_property('use_default_sample_rate',False);opt.anim_sequence_import_data.set_editor_property('custom_sample_rate',120)
  t=u.AssetImportTask();t.filename=str(file);t.destination_path=P+'/'+variant;t.destination_name=file.stem;t.options=opt;t.automated=True;t.replace_existing=True;t.save=True;u.AssetToolsHelpers.get_asset_tools().import_asset_tasks([t]);a=u.load_asset(t.destination_path+'/'+file.stem);assert a
  a.set_editor_property('bone_compression_settings',u.load_asset('/Game/Weapons/M4InfimaRigV4/BC_M4Viewmodel'));assert L.save_loaded_asset(a,False)
  report[file.stem]=a.get_play_length()
assert len(report)==12
(O/'import.json').write_text(json.dumps(report,indent=2));u.log('AKM_POLISH_IMPORT_PASS')
