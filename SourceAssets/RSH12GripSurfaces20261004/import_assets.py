"""Import only the RSH-fitted mesh; reuse the three shared surface materials."""
import json
from pathlib import Path
import unreal as u
O=Path(__file__).resolve().parent;P=O.parents[1]
auth=json.loads((O/'authoring.json').read_text(encoding='utf8'))
E=u.EditorAssetLibrary;A=u.AssetToolsHelpers.get_asset_tools()
if '-run=pythonscript' not in u.SystemLibrary.get_command_line().lower():
    editor=u.get_editor_subsystem(u.UnrealEditorSubsystem)
    if editor and editor.get_game_world():raise RuntimeError('PIE blocks RSH grip import')
if Path(u.Paths.project_dir()).resolve()!=P.resolve():raise RuntimeError('Wrong project')
if any(p.get_name()==auth['mesh'] for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()):
    raise RuntimeError('RSH grip target has unsaved changes')
materials={key:u.load_asset(path) for key,path in auth['materials'].items()}
if not all(materials.values()):raise RuntimeError('Shared pistol grip materials must exist')
flag='Interchange.FeatureFlags.Import.FBX';old=u.SystemLibrary.get_console_variable_int_value(flag)
u.SystemLibrary.execute_console_command(None,flag+' 0')
try:
    opt=u.FbxImportUI();opt.automated_import_should_detect_type=False;opt.mesh_type_to_import=u.FBXImportType.FBXIT_STATIC_MESH
    opt.import_mesh=True;opt.import_as_skeletal=False;opt.import_materials=False;opt.import_textures=False;opt.import_animations=False
    opt.override_full_name=True
    settings=opt.static_mesh_import_data;settings.combine_meshes=True;settings.auto_generate_collision=False
    settings.generate_lightmap_u_vs=False;settings.normal_import_method=u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS
    task=u.AssetImportTask();task.filename=auth['fbx'];task.destination_path=auth['mesh'].rsplit('/',1)[0];task.destination_name=auth['name']
    task.automated=True;task.replace_existing=True;task.replace_existing_settings=True;task.save=False
    task.options=opt;task.factory=u.FbxFactory();A.import_asset_tasks([task]);mesh=u.load_asset(auth['mesh'])
    if not mesh:raise RuntimeError('RSH grip mesh import failed')
    slots=list(mesh.static_materials)
    for i,slot in enumerate(slots):slot.material_interface=materials['pistol_grip_granular'];slots[i]=slot
    mesh.set_editor_property('static_materials',slots)
    editor=u.get_editor_subsystem(u.StaticMeshEditorSubsystem)
    if editor:
        settings=editor.get_lod_build_settings(mesh,0);settings.use_full_precision_u_vs=True;editor.set_lod_build_settings(mesh,0,settings)
    E.set_metadata_tag(mesh,'SourceAttribution',auth['provenance'])
    E.set_metadata_tag(mesh,'GripSurfaceFrame',auth['frame'])
    E.set_metadata_tag(mesh,'GripSurfaceSource',auth['blend'])
    E.set_metadata_tag(mesh,'GripSurfaceBoundary','Actual 9_l outer lateral palm domains, native perimeter and holes inset, sealed feathered skin')
    if not E.save_loaded_asset(mesh,False):raise RuntimeError('RSH grip mesh save failed')
finally:u.SystemLibrary.execute_console_command(None,flag+' '+str(old))
(O/'import_receipt.json').write_text(json.dumps(dict(status='imported_and_saved',complete=True,
    saved=[mesh.get_path_name()],materials={k:m.get_path_name() for k,m in materials.items()},
    shared_materials_changed=False,native_mesh_changed=False,runtime_tested=False),indent=2),encoding='utf8')
print('RSH_GRIP_SURFACE_IMPORTED_AND_SAVED',mesh.get_path_name(),flush=True)
