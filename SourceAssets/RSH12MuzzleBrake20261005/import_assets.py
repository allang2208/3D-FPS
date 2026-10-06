"""Import and save the approved RSH muzzle brake. LOD1 is finalized in the offline stage."""
import json
import shutil
from pathlib import Path
import unreal as u

O = Path(__file__).resolve().parent
D = '/Game/Weapons/RSH12/MuzzleBrake20261005'
E = u.EditorAssetLibrary
L = u.MaterialEditingLibrary
A = u.AssetToolsHelpers.get_asset_tools()
auth = json.loads((O / 'authoring.json').read_text(encoding='utf8'))
inputs = json.loads((O / 'integration_inputs.json').read_text(encoding='utf8'))
receipt = dict(saved=[], materials={}, complete=False, lod1_saved=False, runtime_tested=False)
headless = '-run=pythonscript' in u.SystemLibrary.get_command_line().lower()
if not headless:
    editor = u.get_editor_subsystem(u.UnrealEditorSubsystem)
    if editor and editor.get_game_world():
        raise RuntimeError('PIE blocks RSH muzzle brake import; no assets changed')
dirty = {p.get_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()}
if any(p.startswith(D) or p == '/Game/Weapons/RSH12/Materials/DA_RSH12_WetMaterials' for p in dirty):
    raise RuntimeError('RSH muzzle brake packages have unsaved changes')

def record():
    (O / 'import_receipt.json').write_text(json.dumps(receipt, indent=2), encoding='utf8')

def load(path):
    asset = u.load_asset(path)
    if not asset:
        raise RuntimeError('Missing required input ' + path)
    return asset

def save(asset):
    if not E.save_loaded_asset(asset, False):
        raise RuntimeError('Cannot save ' + asset.get_path_name())
    if asset.get_path_name() not in receipt['saved']:
        receipt['saved'].append(asset.get_path_name())
    record()

def texture(relative, kind):
    filename = O / relative
    task = u.AssetImportTask()
    task.filename = str(filename)
    task.destination_path = D + '/Textures'
    task.destination_name = filename.stem
    task.automated = True
    task.replace_existing = True
    task.save = False
    A.import_asset_tasks([task])
    tex = load(task.destination_path + '/' + filename.stem)
    tex.srgb = kind == 'color'
    tex.compression_settings = {'color': u.TextureCompressionSettings.TC_BC7,
        'rough': u.TextureCompressionSettings.TC_GRAYSCALE,
        'mask': u.TextureCompressionSettings.TC_MASKS,
        'normal': u.TextureCompressionSettings.TC_NORMALMAP}[kind]
    tex.lod_group = u.TextureGroup.TEXTUREGROUP_WEAPON
    if kind == 'normal':
        tex.set_editor_property('flip_green_channel', False)
    save(tex)
    return tex

parent = load('/Game/Weapons/RSH12/Optics20261004/Materials/MI_RSH12_RailSteel')
materials = {}
for part, spec in inputs['textures'].items():
    maps = {'SourceBaseColor': texture(spec['base_color'], 'color'),
        'SourceRoughness': texture(spec['roughness_texture'], 'rough'),
        'SurfaceNormal': texture(spec['normal_dx'], 'normal'),
        'SurfaceMask': texture(spec['surface_mask'], 'mask')}
    name = 'MI_RSH12_Brake_' + part
    path = D + '/Materials/' + name
    mat = load(path) if E.does_asset_exist(path) else A.create_asset(
        name, D + '/Materials', u.MaterialInstanceConstant, u.MaterialInstanceConstantFactoryNew())
    mat.set_editor_property('parent', parent)
    values = dict(SourceColorWeight=1., Roughness=.5, SourceRoughnessWeight=1., SourceRoughnessPivot=.5,
        Metallic=1., MaskUVChannel=0., GrainRoughness=0., MottleRoughness=0., MottleColor=0., Stipple=0.,
        EdgeWear=0., EdgeHighlight=0., CavityDarken=0., CavityRoughness=0., HandlingPolish=0.,
        ScratchAmount=0., AOStrength=1., WeaponWetness=0., BeadScale=60.)
    for key, value in values.items():
        L.set_material_instance_scalar_parameter_value(mat, key, value)
    for key, tex in maps.items():
        L.set_material_instance_texture_parameter_value(mat, key, tex)
    L.update_material_instance(mat)
    E.set_metadata_tag(mat, 'RSHBrakeFinish', 'Approved authored cube PBR; shared WS wet layer; UV0; normal already DirectX')
    save(mat)
    materials[part] = mat
    receipt['materials'][part] = dict(path=mat.get_path_name(), parent=parent.get_path_name(),
        textures={k: t.get_path_name() for k, t in maps.items()})

name = 'M_RSH12_Brake_Recess'
path = D + '/Materials/' + name
if E.does_asset_exist(path):
    recess = load(path)
else:
    recess = A.create_asset(name, D + '/Materials', u.Material, u.MaterialFactoryNew())
    color = L.create_material_expression(recess, u.MaterialExpressionConstant3Vector)
    color.constant = u.LinearColor(.006, .0065, .007, 1.)
    rough = L.create_material_expression(recess, u.MaterialExpressionConstant)
    rough.r = .85
    metal = L.create_material_expression(recess, u.MaterialExpressionConstant)
    metal.r = 0.
    for node, prop in ((color, u.MaterialProperty.MP_BASE_COLOR),
        (rough, u.MaterialProperty.MP_ROUGHNESS), (metal, u.MaterialProperty.MP_METALLIC)):
        if not L.connect_material_property(node, '', prop):
            raise RuntimeError('Recess material connection failed')
    for key in ('used_with_skeletal_mesh', 'used_with_morph_targets', 'used_with_clothing'):
        recess.set_editor_property(key, False)
    errors = L.recompile_material(recess)
    if errors:
        raise RuntimeError('Recess material compilation failed ' + str(errors))
metal = L.get_material_property_input_node(recess, u.MaterialProperty.MP_METALLIC)
if isinstance(metal, u.MaterialExpressionConstant):
    metal.r = 0.
    errors = L.recompile_material(recess)
    if errors:
        raise RuntimeError('Recess material compilation failed ' + str(errors))
save(recess)
materials['Recess'] = recess

flag = 'Interchange.FeatureFlags.Import.FBX'
previous = u.SystemLibrary.get_console_variable_int_value(flag)
u.SystemLibrary.execute_console_command(None, flag + ' 0')
try:
    task = u.AssetImportTask()
    task.filename = auth['fbx']
    task.destination_path = D
    task.destination_name = auth['model']
    task.automated = True
    task.replace_existing = True
    task.replace_existing_settings = True
    task.save = False
    task.factory = u.FbxFactory()
    options = u.FbxImportUI()
    options.automated_import_should_detect_type = False
    options.mesh_type_to_import = u.FBXImportType.FBXIT_STATIC_MESH
    options.import_as_skeletal = False
    options.import_mesh = True
    options.import_materials = False
    options.import_textures = False
    options.import_animations = False
    data = options.static_mesh_import_data
    data.combine_meshes = True
    data.auto_generate_collision = False
    data.generate_lightmap_u_vs = False
    data.normal_import_method = u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS_AND_TANGENTS
    data.vertex_color_import_option = u.VertexColorImportOption.REPLACE
    task.options = options
    A.import_asset_tasks([task])
    mesh = load(D + '/' + auth['model'])
    if headless:
        mesh_editor = u.get_editor_subsystem(u.StaticMeshEditorSubsystem) or u.new_object(u.StaticMeshEditorSubsystem)
        if mesh_editor.import_lod(mesh, 1, auth['lod1_fbx']) != 1:
            raise RuntimeError('Authored brake LOD1 import failed')
        if not mesh_editor.set_lod_screen_sizes(mesh, [1., .12]):
            raise RuntimeError('Brake LOD screen-size assignment failed')
        receipt['lod1_saved'] = True
    slots = list(mesh.static_materials)
    for i, slot in enumerate(slots):
        part = str(slot.material_slot_name).removeprefix('RSH12Brake_')
        slot.material_interface = materials[part]
        slots[i] = slot
    mesh.set_editor_property('static_materials', slots)
    tip = inputs['muzzle_tip_cm']
    for name, position in {'MountFace': (0., 0., 0.), 'Muzzle': tip, 'AimGuide': (tip[0] + 10, tip[1], tip[2])}.items():
        socket = mesh.find_socket(name)
        if not socket:
            socket = u.new_object(u.StaticMeshSocket, outer=mesh)
            socket.set_editor_property('socket_name', name)
            mesh.add_socket(socket)
        socket.set_editor_property('relative_location', u.Vector(*position))
    E.set_metadata_tag(mesh, 'ExclusiveWeapon', 'ue_rsh12')
    E.set_metadata_tag(mesh, 'SourceAttribution', auth['provenance'])
    E.set_metadata_tag(mesh, 'GunsmithOption', 'rsh12_large_caliber_brake')
    E.set_metadata_tag(mesh, 'MountContract', 'Approved compact brake; existing native WPN_root frame; .01 unit conversion; original shroud contour contact')
    save(mesh)
    receipt['mesh'] = mesh.get_path_name()
    receipt['slots'] = {str(s.material_slot_name): s.material_interface.get_path_name() for s in mesh.static_materials}
    receipt['muzzle_tip_cm'] = tip
finally:
    u.SystemLibrary.execute_console_command(None, flag + ' ' + str(previous))
# The RSH static surface parent has a private graph: register these instances explicitly.
wet_path='/Game/Weapons/RSH12/Materials/DA_RSH12_WetMaterials'
table=load(wet_path)
source=O.parents[1]/'Content/Weapons/RSH12/Materials/DA_RSH12_WetMaterials.uasset'
backup=O/'Before/DA_RSH12_WetMaterials.uasset'
backup.parent.mkdir(parents=True,exist_ok=True)
if not backup.exists():shutil.copy2(source,backup)
mapping=dict(table.get_editor_property('wet_materials'))
for key in ('Shell','Trim'):
    mat=materials[key];mapping[mat.get_path_name()]=mat
table.set_editor_property('wet_materials',mapping);save(table)
receipt['complete'] = True
record()
print('RSH_BRAKE_ASSETS_SAVED', mesh.get_path_name(), 'LOD1', receipt['lod1_saved'], flush=True)
