"""Import the new fitted scope revision; preserve the loaded V11 package."""
from pathlib import Path
import json,hashlib,unreal as u
P=Path('D:/FPS3D/FPSGAME/SourceAssets/PeakwatchADSJoint20261110')
ROOT=P.parents[1]
if Path(u.Paths.project_dir()).resolve()!=ROOT.resolve():raise RuntimeError('Wrong project')
ed=u.get_editor_subsystem(u.UnrealEditorSubsystem)
if ed and ed.get_game_world() is not None:raise RuntimeError('Preserving active PIE; import after play ends')
dest='/Game/Weapons/WoodSteelLongbow20261026/Scope3to6V12'
name='SM_Highland_Peakwatch3to6';pkg=dest+'/'+name
old='/Game/Weapons/WoodSteelLongbow20261026/Scope3to6V11/'+name
E,A=u.EditorAssetLibrary,u.AssetToolsHelpers.get_asset_tools()
if E.does_asset_exist(pkg):raise RuntimeError('New revision already exists; do not replay import')
original=u.load_asset(old)
if not isinstance(original,u.StaticMesh):raise RuntimeError('Current mesh unavailable')
materials={str(s.material_slot_name):s.material_interface for s in original.get_editor_property('static_materials')}
source=P/'Export'/(name+'.fbx')
flag='Interchange.FeatureFlags.Import.FBX';prior=u.SystemLibrary.get_console_variable_int_value(flag)
u.SystemLibrary.execute_console_command(None,flag+' 0')
try:
    opt=u.FbxImportUI();opt.automated_import_should_detect_type=False
    opt.mesh_type_to_import=u.FBXImportType.FBXIT_STATIC_MESH
    opt.import_mesh=True;opt.import_animations=False;opt.import_materials=False;opt.import_textures=False
    data=opt.static_mesh_import_data;data.combine_meshes=True;data.auto_generate_collision=False
    data.build_nanite=original.get_editor_property('nanite_settings').enabled
    data.generate_lightmap_u_vs=False;data.normal_import_method=u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS_AND_TANGENTS
    task=u.AssetImportTask();task.filename=str(source);task.destination_path=dest;task.destination_name=name
    task.automated=True;task.replace_existing=False;task.save=False;task.options=opt
    A.import_asset_tasks([task])
    mesh=u.load_asset(pkg)
    if not task.imported_object_paths or not isinstance(mesh,u.StaticMesh):raise RuntimeError('Scope mesh import failed')
    slots=list(mesh.get_editor_property('static_materials'))
    for index,slot in enumerate(slots):
        key=str(slot.material_slot_name)
        if key not in materials:raise RuntimeError('Unrecognized material slot: '+key)
        slot.set_editor_property('material_interface',materials[key]);slots[index]=slot
    mesh.set_editor_property('static_materials',slots)
    E.set_metadata_tag(mesh,'PeakwatchRevision','ContinuousJointV12_20261110')
    if not E.save_loaded_asset(mesh,False):raise RuntimeError('Scope mesh save failed')
finally:u.SystemLibrary.execute_console_command(None,flag+' '+str(prior))
(P/'import-receipt.json').write_text(json.dumps(dict(saved=mesh.get_path_name(),
    source_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),
    materials={str(s.material_slot_name):s.material_interface.get_path_name() for s in slots},
    runtime_tested=False),indent=2),encoding='utf-8')
print('PEAKWATCH_JOINT_SAVED '+mesh.get_path_name(),flush=True)
