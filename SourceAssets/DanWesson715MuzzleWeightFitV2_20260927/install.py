"""Reimport only the target weight and its icon through the current UE asset context."""
import json
import shutil
from pathlib import Path
import unreal as u

OUT = Path(__file__).parent
ROOT = OUT.parents[1]
DEST = '/Game/Weapons/DanWesson715/MuzzleModels20260927'
KEY = 'dw715_target_muzzle_weight'
MESH = DEST+'/Meshes/SM_'+KEY
ICON = DEST+'/Icons/T_'+KEY
MAT = DEST+'/Materials/M_DW715_TargetWeightSteel_V2'
WET = '/Game/Weapons/DanWesson715/GripBrake20260927/DA_DW715_GripBrakeWetMaterials'
A = u.AssetToolsHelpers.get_asset_tools()
E = u.EditorAssetLibrary
L = u.MaterialEditingLibrary
auth = json.loads((OUT/'authoring.json').read_text(encoding='utf-8'))
icons = json.loads((OUT/'icons.json').read_text(encoding='utf-8'))
dirty = {p.get_path_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()}
if dirty & {MESH, ICON, MAT, WET}:
    raise RuntimeError('Unsaved target asset changes: '+str(sorted(dirty & {MESH, ICON, MAT, WET})))
existing = u.load_asset(MESH)
if not existing:
    raise RuntimeError('Installed target mesh is missing')
if E.get_metadata_tag(existing, 'AuthorBatch') not in ('DanWesson715MuzzleModels20260927', OUT.name):
    raise RuntimeError('Target mesh belongs to an unexpected author batch')
bindings = {str(s.material_slot_name): s.material_interface for s in existing.static_materials}
report = {'revision': 'V2', 'status': 'installing', 'saved': [], 'game_tested': False,
          'native_changes': False, 'gameplay_stats_changed': False,
          'preserved_fx_tip_cm': [1.17, 0, 0], 'backups': []}


def record():
    (OUT/'install_receipt.json').write_text(json.dumps(report, indent=2), encoding='utf-8')


def save(asset):
    if not u.EditorLoadingAndSavingUtils.save_packages([asset.get_outermost()], False):
        raise RuntimeError('Save failed: '+asset.get_path_name())
    report['saved'].append(asset.get_path_name())
    record()


# Retain the pre-revision saved files outside cooked Content. Never delete packages.
backup = OUT/'Before'
backup.mkdir(exist_ok=True)
for package in (MESH, ICON, WET):
    filename = ROOT/'Content'/(package.removeprefix('/Game/')+'.uasset')
    target = backup/filename.name
    if filename.exists() and not target.exists():
        shutil.copy2(filename, target)
        report['backups'].append(str(target))

if E.does_asset_exist(MAT):
    material = u.load_asset(MAT)
    if E.get_metadata_tag(material, 'AuthorBatch') != OUT.name:
        raise RuntimeError('Finish destination is already in use')
else:
    material = E.duplicate_asset(bindings['DW715_Steel'].get_path_name(), MAT)
if not material:
    raise RuntimeError('Cannot make the target-specific finish')
roughness = L.get_material_property_input_node(material, u.MaterialProperty.MP_ROUGHNESS)
if not isinstance(roughness, u.MaterialExpressionCustom):
    raise RuntimeError('Existing finish uses an unexpected roughness graph')
roughness.set_editor_property('code',
    'float r=ORM.g*.20; return lerp(lerp(r,max(.024,r*.70),Data.a),.032,Data.b*.8);')
E.set_metadata_tag(material, 'AuthorBatch', OUT.name)
E.set_metadata_tag(material, 'Source', 'Target-weight-only polish; existing DW715 steel PBR maps and rain graph')
L.recompile_material(material)
save(material)

flag = 'Interchange.FeatureFlags.Import.FBX'
old = u.SystemLibrary.get_console_variable_int_value(flag)
u.SystemLibrary.execute_console_command(None, flag+' 0')
try:
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
    task.filename = auth['parts'][KEY]['fbx']
    task.destination_path = DEST+'/Meshes'
    task.destination_name = 'SM_'+KEY
    task.options = options
    task.factory = u.FbxFactory()
    task.automated = True
    task.replace_existing = True
    task.replace_existing_settings = True
    task.save = False
    A.import_asset_tasks([task])
    asset = u.load_asset(MESH)
    if not asset:
        raise RuntimeError('Mesh import did not return its asset')
    bindings['DW715_Steel'] = material
    slots = list(asset.static_materials)
    for i, slot in enumerate(slots):
        slot.material_interface = bindings[str(slot.material_slot_name)]
        slots[i] = slot
    asset.set_editor_property('static_materials', slots)
    E.set_metadata_tag(asset, 'AuthorBatch', OUT.name)
    E.set_metadata_tag(asset, 'Source', auth['parts'][KEY]['source'])
    E.set_metadata_tag(asset, 'PublicationState', 'Installed V2 target weight; user testing pending')
    E.set_metadata_tag(asset, 'MountReference', 'Unchanged DW715 WPN_SOCKET_Muzzle frame; +X; exit 1.17 cm')
    save(asset)
    report['mesh'] = {'path': asset.get_path_name(), 'lods': asset.get_num_lods(),
        'materials': {str(s.material_slot_name): s.material_interface.get_path_name() for s in asset.static_materials}}
    record()
finally:
    u.SystemLibrary.execute_console_command(None, flag+' '+str(old))

library = u.load_asset(WET)
mapping = dict(library.get_editor_property('wet_materials'))
mapping[material.get_path_name()] = material
library.set_editor_property('wet_materials', mapping)
save(library)

task = u.AssetImportTask()
task.filename = icons[KEY]['file']
task.destination_path = DEST+'/Icons'
task.destination_name = 'T_'+KEY
task.automated = True
task.replace_existing = True
task.save = False
A.import_asset_tasks([task])
texture = u.load_asset(ICON)
if not texture:
    raise RuntimeError('Icon import did not return its asset')
texture.srgb = True
texture.compression_settings = u.TextureCompressionSettings.TC_EDITOR_ICON
texture.lod_group = u.TextureGroup.TEXTUREGROUP_UI
texture.mip_gen_settings = u.TextureMipGenSettings.TMGS_NO_MIPMAPS
E.set_metadata_tag(texture, 'AuthorBatch', OUT.name)
save(texture)

png = Path(icons[KEY]['file'])
published = ROOT/'Content/ColdSteelData/AttachmentIcons20260913'/png.name
if published.exists() and not (backup/png.name).exists():
    shutil.copy2(published, backup/png.name)
shutil.copy2(png, published)
report['icon_png'] = str(published)
report['status'] = 'imported_and_saved'
record()
print('DW715_TARGET_WEIGHT_V2_SAVED '+json.dumps(report['saved']), flush=True)
