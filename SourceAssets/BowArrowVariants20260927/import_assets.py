"""Import/save this task's new arrow meshes and materials only. No play or QA."""
import json
from pathlib import Path
import unreal as u

P = Path(__file__).resolve().parent
DEST = '/Game/Weapons/DarkBow20260925/ArrowVariants20260927'
ORIGINAL = '/Game/Weapons/DarkBow20260925/ArmsV2/SM_Bow_WoodArrow'
E = u.EditorAssetLibrary
A = u.AssetToolsHelpers.get_asset_tools()
L = u.MaterialEditingLibrary
receipt_path = P / 'import_receipt.json'
receipt = json.loads(receipt_path.read_text(encoding='utf-8')) if receipt_path.exists() else dict(saved={}, runtime_tested=False)
pending = receipt.setdefault('pending', {})
# The first attempt authored this new material but PIE rejected its save.
# Its ownership is recorded in Saved/BowArrowVariants20260927/import-mcp-01.json.
if not receipt['saved'] and not pending:
    pending['M_ArrowSteelForged'] = DEST + '/Materials/M_ArrowSteelForged'
if u.get_editor_subsystem(u.UnrealEditorSubsystem).get_game_world():
    raise RuntimeError('Stop the current play session before saving arrow assets; editor may remain open.')
dirty = [p.get_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()
         if p.get_name().startswith(DEST + '/') and p.get_name() not in pending.values()]
if dirty:
    raise RuntimeError('Preserving unsaved arrow edits: ' + str(dirty))

def save(asset):
    asset.modify()
    if not E.save_loaded_asset(asset, False):
        raise RuntimeError('Asset save failed: ' + asset.get_path_name())
    receipt['saved'][asset.get_name()] = asset.get_path_name()
    pending.pop(asset.get_name(), None)
    receipt_path.write_text(json.dumps(receipt, ensure_ascii=False, indent=2), encoding='utf-8')

def owned_or_new(name, folder, cls, factory):
    asset = u.load_asset(folder + '/' + name)
    if asset and name not in receipt['saved'] and name not in pending:
        raise RuntimeError('Preserving pre-existing unowned asset ' + asset.get_path_name())
    asset = asset or A.create_asset(name, folder, cls, factory)
    pending[name] = folder + '/' + name
    receipt_path.write_text(json.dumps(receipt, indent=2), encoding='utf-8')
    return asset

original = u.load_asset(ORIGINAL)
if not original:
    raise RuntimeError('Missing accepted wooden arrow')
source_materials = {str(s.material_slot_name): s.material_interface for s in original.static_materials}
ash = u.load_asset('/Game/Weapons/DarkBow20260925/ArmsV2/Materials/MI_BowWood_Arrow')
materials = {}
for label, (color, metallic, roughness) in json.loads((P/'materials.json').read_text()).items():
    name = 'M_' + label
    if name in receipt['saved']:
        materials[label] = u.load_asset(receipt['saved'][name])
        continue
    if name in pending and E.does_asset_exist(pending[name]):
        mat = u.load_asset(pending[name])
        save(mat)
        materials[label] = mat
        continue
    mat = owned_or_new(name, DEST + '/Materials', u.Material, u.MaterialFactoryNew())
    rgb = L.create_material_expression(mat, u.MaterialExpressionConstant3Vector)
    rgb.constant = u.LinearColor(*color, 1)
    L.connect_material_property(rgb, '', u.MaterialProperty.MP_BASE_COLOR)
    for value, prop in ((metallic,u.MaterialProperty.MP_METALLIC),(roughness,u.MaterialProperty.MP_ROUGHNESS)):
        node = L.create_material_expression(mat, u.MaterialExpressionConstant)
        node.r = value
        L.connect_material_property(node, '', prop)
    L.recompile_material(mat)
    save(mat)
    materials[label] = mat

u.SystemLibrary.execute_console_command(None, 'Interchange.FeatureFlags.Import.FBX 0')
for variant in ('ArmorPiercing', 'Poison', 'Serrated'):
    name = 'SM_Arrow_' + variant
    if name in receipt['saved'] and E.does_asset_exist(DEST+'/'+name):
        continue
    if E.does_asset_exist(DEST+'/'+name):
        raise RuntimeError('Preserving pre-existing unowned arrow mesh '+name)
    options = u.FbxImportUI()
    options.automated_import_should_detect_type = False
    options.mesh_type_to_import = u.FBXImportType.FBXIT_STATIC_MESH
    options.import_mesh = True
    options.import_materials = False
    options.import_textures = False
    options.import_animations = False
    options.static_mesh_import_data.combine_meshes = True
    options.static_mesh_import_data.auto_generate_collision = False
    options.static_mesh_import_data.normal_import_method = u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS
    task = u.AssetImportTask()
    task.filename = str(P/'Export'/(name+'.fbx'))
    task.destination_path = DEST
    task.destination_name = name
    task.automated = True
    task.replace_existing = False
    task.options = options
    task.save = False
    A.import_asset_tasks([task])
    mesh = u.load_asset(DEST+'/'+name)
    if not mesh:
        raise RuntimeError('Arrow import failed: '+name)
    for index, slot in enumerate(mesh.static_materials):
        label = str(slot.material_slot_name)
        material = materials.get(label) or source_materials.get(label)
        if label.startswith('ArrowWood') and ash:
            material = ash
        if not material:
            raise RuntimeError('Missing authored material binding: '+label)
        mesh.set_material(index, material)
    save(mesh)
receipt['icons'] = [f'Icons/ArrowVariants20260927/{name}.png' for name in
                    ('arrow_wood','arrow_broadhead','arrow_poison','arrow_serrated')]
receipt['icon_delivery'] = 'PNG files read directly by existing AmmoIcon runtime cache'
receipt['native_build'] = 'deferred by user'
receipt_path.write_text(json.dumps(receipt, ensure_ascii=False, indent=2), encoding='utf-8')
print('BOW_ARROW_VARIANTS_SAVED', len(receipt['saved']))
