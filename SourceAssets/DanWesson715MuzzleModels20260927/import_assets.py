"""Import the new render assets with authored LODs, using existing DW715 materials.

Does not touch the gun mesh, catalogs, saved equipment or existing brake asset.
"""
import json
from pathlib import Path
import unreal as u

OUT = Path(__file__).parent
DEST = '/Game/Weapons/DanWesson715/MuzzleModels20260927'
auth = json.loads((OUT / 'authoring.json').read_text(encoding='utf-8'))
icons = json.loads((OUT / 'icons.json').read_text(encoding='utf-8'))
# Historical manifests may still list the rejected target weight. Its accepted
# replacement is exclusively installed by MuzzleWeightFitV2_20260927/install.py.
auth['parts'] = {k: v for k, v in auth['parts'].items() if k == 'dw715_compact_compensator'}
icons = {k: v for k, v in icons.items() if k == 'dw715_compact_compensator'}
A = u.AssetToolsHelpers.get_asset_tools()
E = u.EditorAssetLibrary
targets = {p['mesh'] for p in auth['parts'].values()}
targets |= {DEST + '/Icons/T_' + key for key in icons}
dirty = {p.get_path_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()}
if dirty & targets:
    raise RuntimeError('Target has unsaved editor changes: ' + str(sorted(dirty & targets)))

receipt = {'status': 'importing', 'saved': [], 'meshes': {}, 'icons': {},
           'gameplay_published': False, 'game_tested': False, 'native_change_required': False,
           'material_policy': 'Reuse current original brake bindings without editing materials'}


def record():
    (OUT / 'import_receipt.json').write_text(json.dumps(receipt, indent=2), encoding='utf-8')


def save(asset):
    if not u.EditorLoadingAndSavingUtils.save_packages([asset.get_outermost()], False):
        raise RuntimeError('Cannot save ' + asset.get_path_name())
    receipt['saved'].append(asset.get_path_name())
    record()


brake = u.load_asset('/Game/Weapons/DanWesson715/GripBrake20260927/Meshes/SM_dw715_muzzle_brake')
if not brake:
    raise RuntimeError('Existing DW715 material donor is missing')
bindings = {str(s.material_slot_name): s.material_interface for s in brake.static_materials}
flag = 'Interchange.FeatureFlags.Import.FBX'
old = u.SystemLibrary.get_console_variable_int_value(flag)
u.SystemLibrary.execute_console_command(None, flag + ' 0')
try:
    for key, part in auth['parts'].items():
        path = part['mesh']
        name = path.rsplit('/', 1)[1]
        existing = u.load_asset(path) if E.does_asset_exist(path) else None
        if existing and E.get_metadata_tag(existing, 'AuthorBatch') != OUT.name:
            raise RuntimeError('Destination already belongs to another asset: ' + path)
        options = u.FbxImportUI()
        options.automated_import_should_detect_type = False
        options.mesh_type_to_import = u.FBXImportType.FBXIT_STATIC_MESH
        options.import_mesh = True
        options.import_materials = False
        options.import_textures = False
        options.import_animations = False
        options.override_full_name = True
        options.set_editor_property('reset_to_fbx_on_material_conflict', True)
        data = options.static_mesh_import_data
        data.combine_meshes = False
        data.import_mesh_lods = True
        data.auto_generate_collision = False
        data.generate_lightmap_u_vs = False
        data.normal_import_method = u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS
        task = u.AssetImportTask()
        task.filename = part['fbx']
        task.destination_path = DEST + '/Meshes'
        task.destination_name = name
        task.options = options
        task.factory = u.FbxFactory()
        task.automated = True
        task.replace_existing = True
        task.replace_existing_settings = True
        task.save = False
        A.import_asset_tasks([task])
        mesh = u.load_asset(path)
        if not mesh:
            raise RuntimeError('Import did not create mesh: ' + path)
        slots = list(mesh.static_materials)
        for i, slot in enumerate(slots):
            label = str(slot.material_slot_name)
            if label not in bindings or not bindings[label]:
                raise RuntimeError('Material binding is missing: ' + label)
            slot.material_interface = bindings[label]
            slots[i] = slot
        mesh.set_editor_property('static_materials', slots)
        E.set_metadata_tag(mesh, 'AuthorBatch', OUT.name)
        E.set_metadata_tag(mesh, 'Source', part['source'])
        E.set_metadata_tag(mesh, 'MountReference', 'DW715 WPN_SOCKET_Muzzle; +X forward, +Z up; existing fitted-parts frame')
        E.set_metadata_tag(mesh, 'PublicationState', 'Model asset only; gameplay not published')
        save(mesh)
        receipt['meshes'][key] = {'asset': mesh.get_path_name(), 'lods': mesh.get_num_lods(),
            'material_bindings': {str(s.material_slot_name): s.material_interface.get_path_name() for s in slots}}
        record()
finally:
    u.SystemLibrary.execute_console_command(None, flag + ' ' + str(old))

for key, icon in icons.items():
    path = DEST + '/Icons/T_' + key
    task = u.AssetImportTask()
    task.filename = icon['file']
    task.destination_path = DEST + '/Icons'
    task.destination_name = 'T_' + key
    task.automated = True
    task.replace_existing = True
    task.save = False
    A.import_asset_tasks([task])
    texture = u.load_asset(path)
    if not texture:
        raise RuntimeError('Import did not create icon: ' + path)
    texture.srgb = True
    texture.compression_settings = u.TextureCompressionSettings.TC_EDITOR_ICON
    texture.lod_group = u.TextureGroup.TEXTUREGROUP_UI
    texture.mip_gen_settings = u.TextureMipGenSettings.TMGS_NO_MIPMAPS
    E.set_metadata_tag(texture, 'AuthorBatch', OUT.name)
    save(texture)
    receipt['icons'][key] = texture.get_path_name()
    record()
receipt['status'] = 'imported_and_saved'
record()
print('DW715_MUZZLE_MODELS_IMPORTED_AND_SAVED ' + str(len(receipt['saved'])), flush=True)
