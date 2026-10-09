"""Import the saved gun shading; keep slots, bones, skin and animations intact."""
import unreal as u,json,hashlib,shutil,sys
from pathlib import Path
O=Path(__file__).parent;P=O.parents[1];S=O.parent/'BenelliM4Super9020261006';R='/Game/Weapons/Super90/Cransh20261006'
sys.path.insert(0,str(O));from material_surface import apply_receiver_surface
E=u.EditorAssetLibrary;A=u.AssetToolsHelpers.get_asset_tools();receipt={'saved':[],'runtime_tested':False}
B=O/'Before';B.mkdir(exist_ok=True)
def save(asset):
    if not u.EditorLoadingAndSavingUtils.save_packages([asset.get_outermost()],False):raise RuntimeError('Save failed: '+asset.get_path_name())
    receipt['saved'].append(asset.get_path_name());(O/'import_receipt.json').write_text(json.dumps(receipt,indent=2))
mesh=u.load_asset(R+'/SK_Super90_V7');material=u.load_asset(R+'/Materials/M_S90_TTI_Benelli_M4')
for asset in (mesh,material):
    path=P/'Content'/(asset.get_path_name().split('.')[0].removeprefix('/Game/')+'.uasset')
    if path.exists() and not (B/path.name).exists():shutil.copy2(path,B/path.name)
slots=list(mesh.materials);old={str(m.material_slot_name).removeprefix('Manny_S90_'):m for m in slots}
flag='Interchange.FeatureFlags.Import.FBX';previous=u.SystemLibrary.get_console_variable_int_value(flag)
u.SystemLibrary.execute_console_command(None,flag+' 0')
try:
    options=u.FbxImportUI();options.automated_import_should_detect_type=False;options.mesh_type_to_import=u.FBXImportType.FBXIT_SKELETAL_MESH
    options.import_as_skeletal=True;options.import_mesh=True;options.import_animations=False;options.import_materials=False;options.import_textures=False
    options.create_physics_asset=False;options.skeleton=mesh.skeleton
    data=options.skeletal_mesh_import_data;data.set_editor_property('update_skeleton_reference_pose',False)
    data.normal_import_method=u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS_AND_TANGENTS
    file=S/'Exports/SK_Super90_V7.fbx';task=u.AssetImportTask();task.filename=str(file);task.destination_path=R;task.destination_name='SK_Super90_V7'
    task.automated=True;task.replace_existing=True;task.replace_existing_settings=True;task.save=False;task.options=options;task.factory=u.FbxFactory()
    A.import_asset_tasks([task])
    if not task.imported_object_paths:raise RuntimeError('No saved mesh import returned')
    mesh=u.load_asset(R+'/SK_Super90_V7');new=list(mesh.materials)
    for i,m in enumerate(new):
        key=str(m.material_slot_name).removeprefix('Manny_S90_');previous_slot=old[key]
        m.material_slot_name=previous_slot.material_slot_name;m.material_interface=previous_slot.material_interface;new[i]=m
    mesh.set_editor_property('materials',new);mesh.set_editor_property('physics_asset',None)
    editor=u.get_editor_subsystem(u.SkeletalMeshEditorSubsystem);settings=editor.get_lod_build_settings(mesh,0)
    settings.use_full_precision_u_vs=True;settings.use_high_precision_tangent_basis=True
    settings.recompute_normals=False;settings.recompute_tangents=False;editor.set_lod_build_settings(mesh,0,settings)
    E.set_metadata_tag(mesh,'Super90SourceSHA256',hashlib.sha256(file.read_bytes()).hexdigest())
    E.set_metadata_tag(mesh,'Super90SurfaceRepair','20261007: curve normals, exported tangents, full precision UV0 and TBN')
    save(mesh)
finally:u.SystemLibrary.execute_console_command(None,flag+' '+str(previous))
apply_receiver_surface(material);save(material)
receipt['completed']=True;(O/'import_receipt.json').write_text(json.dumps(receipt,indent=2))
print('SUPER90_SURFACE_SAVED',len(receipt['saved']),flush=True)
