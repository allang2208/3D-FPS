"""Save the fitted SI body extension at the existing part path and keep its finish."""
import json,hashlib,re,shutil
from pathlib import Path
import unreal as u
O=Path(__file__).parent;P=O.parents[1];SI=O.parent/'PitViper2011SICompensator20261002'
D='/Game/Weapons/PitViper2011/SICompensator20261003';NAME='SM_PitViper2011_SICompensator';PATH=D+'/'+NAME
if Path(u.Paths.project_dir()).resolve()!=P.resolve():raise RuntimeError('Wrong production project')
dirty={p.get_path_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()}
if PATH in dirty:raise RuntimeError('Preserve unsaved SI mesh')
old=u.load_asset(PATH)
if not old:raise RuntimeError('Expected the existing integrated SI mesh')
canon=lambda name:re.sub(r'[._]\d{3}$','',str(name))
materials={canon(s.material_slot_name):s.material_interface for s in old.static_materials}
source=P/'Content/Weapons/PitViper2011/SICompensator20261003'/(NAME+'.uasset')
backup=O/'Before/Content/Weapons/PitViper2011/SICompensator20261003'/(NAME+'.uasset')
if source.exists() and not backup.exists():backup.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(source,backup)
auth=json.loads((SI/'authoring_receipt.json').read_text(encoding='utf8'))
flag='Interchange.FeatureFlags.Import.FBX';oldflag=u.SystemLibrary.get_console_variable_int_value(flag)
u.SystemLibrary.execute_console_command(None,flag+' 0')
try:
    opt=u.FbxImportUI();opt.automated_import_should_detect_type=False;opt.mesh_type_to_import=u.FBXImportType.FBXIT_STATIC_MESH
    opt.import_mesh=True;opt.import_materials=False;opt.import_textures=False;opt.import_animations=False;opt.override_full_name=True
    opt.static_mesh_import_data.combine_meshes=True;opt.static_mesh_import_data.auto_generate_collision=False
    opt.static_mesh_import_data.generate_lightmap_u_vs=False;opt.static_mesh_import_data.normal_import_method=u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS
    task=u.AssetImportTask();task.filename=auth['fbx'];task.destination_path=D;task.destination_name=NAME
    task.automated=True;task.replace_existing=True;task.replace_existing_settings=True;task.save=False;task.options=opt;task.factory=u.FbxFactory()
    u.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task]);mesh=u.load_asset(PATH)
    if not mesh:raise RuntimeError('SI mesh import failed')
    slots=list(mesh.static_materials)
    for i,s in enumerate(slots):
        s.material_interface=materials[canon(s.material_slot_name)];slots[i]=s
    mesh.set_editor_property('static_materials',slots)
    for label,point in auth['sockets_blender_m'].items():
        name=label.removeprefix('SOCKET_');socket=mesh.find_socket(name)
        if not socket:socket=u.new_object(u.StaticMeshSocket,outer=mesh);socket.set_editor_property('socket_name',name);mesh.add_socket(socket)
        socket.set_editor_property('relative_location',u.Vector(point[0]*100,-point[1]*100,point[2]*100))
    subsystem=u.get_editor_subsystem(u.StaticMeshEditorSubsystem)
    if subsystem:
        settings=subsystem.get_lod_build_settings(mesh,0);settings.use_full_precision_u_vs=True;subsystem.set_lod_build_settings(mesh,0,settings)
    u.EditorAssetLibrary.set_metadata_tag(mesh,'InterfaceRevision',auth['interface_revision'])
    u.EditorAssetLibrary.set_metadata_tag(mesh,'SourceAttribution',auth['provenance'])
    u.EditorAssetLibrary.set_metadata_tag(mesh,'SICompensatorSourceSHA256',hashlib.sha256(Path(auth['fbx']).read_bytes()).hexdigest())
    if not u.EditorLoadingAndSavingUtils.save_packages([mesh.get_outermost()],False):raise RuntimeError('SI mesh save failed')
finally:u.SystemLibrary.execute_console_command(None,flag+' '+str(oldflag))
receipt={'status':'imported_and_saved','mesh':mesh.get_path_name(),'fbx':auth['fbx'],
    'fbx_sha256':hashlib.sha256(Path(auth['fbx']).read_bytes()).hexdigest(),'interface':auth['interface_contract'],
    'materials':{str(s.material_slot_name):s.material_interface.get_path_name() for s in mesh.static_materials},
    'part':'pit_viper_si_compensator','runtime_mount_changed':False,'native_build_required':False,
    'native_skeletal_meshes_reimported':False,'game_tested':False,'acceptance_rendered':False}
(O/'import_receipt.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2),encoding='utf8')
record_path=SI/'integration_receipt.json';record=json.loads(record_path.read_text(encoding='utf8'))
record['interface_revision']=receipt;record_path.write_text(json.dumps(record,ensure_ascii=False,indent=2),encoding='utf8')
print('SI_VIPER_BODY_EXTENSION_MESH_IMPORTED_AND_SAVED',flush=True)
