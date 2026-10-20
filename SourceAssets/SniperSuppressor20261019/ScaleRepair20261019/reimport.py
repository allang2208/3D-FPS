"""Restore the cosmetic mesh's metre-to-centimetre import; keep materials/socket."""
from pathlib import Path
import unreal as u,json,hashlib,shutil
O=Path(__file__).resolve().parent;P=Path(u.Paths.project_dir()).resolve()
path='/Game/Weapons/SniperSuppressor20261019/SM_SniperHeavySuppressor'
file=P/'Content/Weapons/SniperSuppressor20261019/SM_SniperHeavySuppressor.uasset'
asset=u.load_asset(path);before=asset.get_bounds();oldhash=hashlib.sha256(file.read_bytes()).hexdigest()
if path in {p.get_path_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()}:
    raise RuntimeError('Preserve unsaved suppressor')
backup=Path('D:/FPS3D/FPSGAME_Backups/SniperSuppressorScale20261019');backup.mkdir(parents=True,exist_ok=True)
dest=backup/(oldhash+'.uasset')
if not dest.exists():shutil.copy2(file,dest)
materials={str(m.material_slot_name):m.material_interface for m in asset.static_materials}
flag='Interchange.FeatureFlags.Import.FBX';previous=u.SystemLibrary.get_console_variable_int_value(flag)
u.SystemLibrary.execute_console_command(None,flag+' 0')
try:
    task=u.AssetImportTask();task.filename=str(O.parent/'Exports/SM_SniperHeavySuppressor.fbx')
    task.destination_path=path.rsplit('/',1)[0];task.destination_name=path.rsplit('/',1)[1]
    task.automated=True;task.replace_existing=True;task.replace_existing_settings=True;task.save=False;task.factory=u.FbxFactory()
    options=u.FbxImportUI();options.import_mesh=True;options.import_as_skeletal=False
    options.automated_import_should_detect_type=False;options.import_animations=False
    options.import_materials=False;options.import_textures=False;options.mesh_type_to_import=u.FBXImportType.FBXIT_STATIC_MESH
    data=options.static_mesh_import_data;data.combine_meshes=True;data.auto_generate_collision=False;data.generate_lightmap_u_vs=False
    data.import_uniform_scale=1.;data.convert_scene_unit=False
    data.normal_import_method=u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS_AND_TANGENTS
    task.options=options;u.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
    if not task.imported_object_paths:raise RuntimeError('FBX task did not import an object')
    asset=u.load_asset(path);slots=list(asset.static_materials)
    for i,s in enumerate(slots):
        name=str(s.material_slot_name);label=name.removeprefix('SniperSuppressor_')
        material=materials.get(name)
        if not material:
            material=u.load_asset('/Game/Weapons/SniperSuppressor20261019/'+
                ('M_SniperSuppressor_Recess' if label=='Recess' else 'MI_SniperSuppressor_'+label))
        if not material:raise RuntimeError('Missing existing surface material '+name)
        s.material_interface=material;slots[i]=s
    asset.set_editor_property('static_materials',slots)
    for name,x in [('MountFace',0.),('Muzzle',31.7),('AimGuide',41.7)]:
        socket=asset.find_socket(name)
        if not socket:socket=u.new_object(u.StaticMeshSocket,outer=asset);socket.socket_name=name;asset.add_socket(socket)
        socket.relative_location=u.Vector(x,0,0)
    # Finish asynchronous render-data building before reading cached bounds.
    if not u.EditorAssetLibrary.save_loaded_asset(asset,False):raise RuntimeError('Suppressor save failed')
    after=asset.get_bounds();minimum=after.origin-after.box_extent;maximum=after.origin+after.box_extent
    if abs(minimum.x)>.02 or abs(maximum.x-31.7)>.02 or abs(after.box_extent.y-2.66)>.02:
        raise RuntimeError('Unexpected repaired cosmetic mesh bounds: '+str(after))
    if not u.EditorAssetLibrary.save_loaded_asset(asset,False):raise RuntimeError('Suppressor save failed')
    xyz=lambda v:[v.x,v.y,v.z]
    (O/'receipt.json').write_text(json.dumps({'complete':True,'old_sha256':oldhash,'sha256':hashlib.sha256(file.read_bytes()).hexdigest(),
        'before_origin':xyz(before.origin),'before_extent':xyz(before.box_extent),'after_min':xyz(minimum),'after_max':xyz(maximum),
        'materials_preserved':True,'socket_tip_cm':31.7,'runtime_rendered':False},indent=2))
    print('SNIPER_SUPPRESSOR_SCALE_REPAIRED',flush=True)
finally:u.SystemLibrary.execute_console_command(None,flag+' '+str(previous))
