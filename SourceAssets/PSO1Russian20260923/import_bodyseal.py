"""Replace AKM and A762 PSO meshes with the sealed full export. Materials and sockets stay."""
import json
import unreal as u
from pathlib import Path

O = Path(r'D:\FPS3D\FPSGAME\SourceAssets\PSO1Russian20260923')
P = '/Game/Weapons/PSO1Russian20260923'
GLASS = '/Game/Weapons/SVDDragunov20260922/Complete20260923/Materials/M_SVD_OpticalGlass'
spec = json.loads((O / 'authoring.json').read_text(encoding='utf-8'))
E = u.EditorAssetLibrary
A = u.AssetToolsHelpers.get_asset_tools()
if u.get_editor_subsystem(u.UnrealEditorSubsystem).get_game_world():
    raise RuntimeError('Preserve the play session')

receipt = {'hosts': {}, 'saved': True}
for host in ('A762', 'AKM'):
    info = spec['hosts'][host]
    mesh_name = info['mesh']
    dest = P + '/' + host
    asset = dest + '/' + mesh_name
    fbx = O / 'Exports' / ('SM_PSO1_%s_BodySealFull.fbx' % host)
    if not fbx.exists():
        raise RuntimeError('Missing ' + str(fbx))
    if E.does_asset_exist(asset) and not E.delete_asset(asset):
        raise RuntimeError('Could not delete ' + asset)
    opts = u.FbxImportUI()
    opts.automated_import_should_detect_type = False
    opts.mesh_type_to_import = u.FBXImportType.FBXIT_STATIC_MESH
    opts.import_materials = False
    opts.import_textures = False
    opts.import_animations = False
    data = opts.static_mesh_import_data
    data.combine_meshes = True
    data.auto_generate_collision = False
    data.generate_lightmap_u_vs = False
    data.normal_import_method = u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS_AND_TANGENTS
    data.vertex_color_import_option = u.VertexColorImportOption.REPLACE
    task = u.AssetImportTask()
    task.filename = str(fbx)
    task.destination_path = dest
    task.destination_name = mesh_name
    task.options = opts
    task.factory = u.FbxFactory()
    task.automated = True
    task.replace_existing = False
    task.save = False
    A.import_asset_tasks([task])
    mesh = u.load_asset(asset)
    if not mesh:
        raise RuntimeError('Import failed ' + host)
    shell = u.load_asset(P + '/Materials/M_PSO1_%s_Shell' % host)
    adapter = u.load_asset(P + '/Materials/M_PSO1_%s_Adapter' % host)
    glass = u.load_asset(GLASS)
    if not shell or not adapter or not glass:
        raise RuntimeError('Missing materials ' + host)
    slots = list(mesh.static_materials)
    for i, slot in enumerate(slots):
        name = str(slot.material_slot_name)
        if 'Shell' in name or name.startswith('PSO_Scope'):
            slot.material_interface = shell
        elif 'Adapter' in name or 'Pad' in name or 'Bridge' in name or 'Dovetail' in name or 'Bolt' in name or 'Recoil' in name:
            slot.material_interface = adapter
        elif 'Glass' in name or 'Lens' in name:
            slot.material_interface = glass
        else:
            raise RuntimeError('Unmapped slot ' + host + ' ' + name)
        slots[i] = slot
    mesh.set_editor_property('static_materials', slots)
    for name, location in info['sockets_cm'].items():
        socket = mesh.find_socket(name)
        if not socket:
            socket = u.new_object(u.StaticMeshSocket, outer=mesh)
            socket.set_editor_property('socket_name', name)
            mesh.add_socket(socket)
        socket.relative_location = u.Vector(*location)
        socket.relative_rotation = u.Rotator(0, 0, 0)
    extent = mesh.get_bounds().box_extent * 2
    size = list(extent.to_tuple())
    if not (20 < size[0] < 45 and 4 < size[1] < 16 and 8 < size[2] < 22):
        raise RuntimeError('Unexpected size ' + host + ' ' + str(size))
    E.set_metadata_tag(mesh, 'PSO1_Host', host)
    E.set_metadata_tag(mesh, 'PSO1_BodySeal', 'cylinder patches on PSO_ScopeBody; side mount kept')
    if not E.save_loaded_asset(mesh, False):
        raise RuntimeError('Save failed ' + mesh.get_path_name())
    receipt['hosts'][host] = {
        'asset': mesh.get_path_name(),
        'size_cm': size,
        'slots': {str(s.material_slot_name): s.material_interface.get_path_name() for s in mesh.static_materials},
        'aim_center_cm': list(mesh.find_socket('AimCenter').relative_location.to_tuple()),
    }
    print('PSO_BODYSEAL_IMPORTED', host, size, flush=True)
(O / 'inspect_akm_a762' / 'bodyseal_import_receipt.json').write_text(json.dumps(receipt, indent=2), encoding='utf-8')
print('PSO_BODYSEAL_IMPORT_COMPLETE', flush=True)
