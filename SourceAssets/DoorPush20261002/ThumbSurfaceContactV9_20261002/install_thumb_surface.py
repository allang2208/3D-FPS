"""Save the M16-only thumb surface without changing geometry, weights or poses.

Executed by the root's serialized background commandlet. Existing texture
inputs, canonical coordinate wiring and instance parameters are retained.
"""
import hashlib
import json
import shutil
from pathlib import Path

import unreal as u

HERE = Path(__file__).resolve().parent
PROJECT = Path(u.Paths.project_dir()).resolve()
SOURCE = '/Game/Characters/ModularOutfit20260924/BarePalmV7/Materials'
DEST = '/Game/Characters/ModularOutfit20260924/ThumbSurfaceContactV9_20261002/M16'
NATIVE = '/Game/Weapons/M16A2/Gameplay20260919/SK_M16_Manny.SK_M16_Manny'
E = u.EditorAssetLibrary
L = u.MaterialEditingLibrary
A = u.AssetToolsHelpers.get_asset_tools()
RECEIPT = HERE / 'installed.json'


def load(path):
    asset = u.load_asset(path)
    if asset is None:
        raise RuntimeError('Missing production input: ' + path)
    return asset


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def package(path):
    return PROJECT / 'Content' / (path.split('.')[0].removeprefix('/Game/') + '.uasset')


def write_receipt(receipt):
    temp = RECEIPT.with_suffix('.next.json')
    temp.write_text(json.dumps(receipt, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    temp.replace(RECEIPT)


def save(asset):
    if not (u.EditorLoadingAndSavingUtils.save_packages([asset.get_outer()], False)
            or E.save_loaded_asset(asset, False)):
        raise RuntimeError('Cannot save authored asset: ' + asset.get_path_name())


def copy_package(path):
    original = package(path)
    backup = HERE / 'BeforeAssets' / original.relative_to(PROJECT / 'Content')
    backup.parent.mkdir(parents=True, exist_ok=True)
    for suffix in ('.uasset', '.uexp', '.ubulk', '.uptnl'):
        src, dst = original.with_suffix(suffix), backup.with_suffix(suffix)
        if src.exists() and not dst.exists():
            shutil.copy2(src, dst)
    return str(backup)


def duplicate(asset, name):
    path = DEST + '/' + name
    result = u.load_asset(path)
    if result is None:
        result = A.duplicate_asset(name, DEST, asset)
    if result is None:
        raise RuntimeError('Cannot author material derivative: ' + path)
    return result


def material_family(base_name, instance_name, name, code, receipt):
    original_base = load(SOURCE + '/' + base_name)
    original_instance = load(SOURCE + '/' + instance_name)
    base = duplicate(original_base, 'M_M16Thumb' + name)
    custom = L.get_material_property_input_node(base, u.MaterialProperty.MP_NORMAL)
    if not isinstance(custom, u.MaterialExpressionCustom):
        raise RuntimeError('Preserve different material graph: ' + base.get_path_name())
    # Keep the source's existing inputs/additional outputs and canonical UV pins.
    before_code = custom.get_editor_property('code')
    custom.set_editor_property('code', code)
    errors = L.recompile_material(base)
    if errors:
        raise RuntimeError('Material authoring failed: ' + str(errors))
    save(base)
    instance = duplicate(original_instance, 'MI_M16Thumb' + name)
    L.set_material_instance_parent(instance, base)
    L.update_material_instance(instance)
    save(instance)
    receipt['materials'][name] = {
        'source_material': original_base.get_path_name(),
        'source_instance': original_instance.get_path_name(),
        'source_custom_code_sha256': hashlib.sha256(before_code.encode('utf-8')).hexdigest(),
        'material': base.get_path_name(), 'instance': instance.get_path_name(),
        'material_saved': True, 'instance_saved': True,
        'texture_inputs_and_uv_connections': 'inherited from existing canonical-coordinate material',
        'instance_parameters': 'inherited without texture/scalar/vector overrides',
    }
    write_receipt(receipt)
    return original_instance.get_path_name(), instance


def main():
    if u.get_editor_subsystem(u.UnrealEditorSubsystem).get_game_world():
        raise RuntimeError('Preserve loaded gameplay assets; stop PIE before asset authoring')
    config = json.loads((PROJECT / 'Content/ColdSteelData/modular_outfits.json').read_text(encoding='utf-8-sig'))
    profile = config['profiles'][NATIVE]
    paths = [NATIVE, profile['base'], profile['native_bare_skin']]
    for item in config['items'].values():
        path = item.get('skin_meshes', {}).get('M16')
        if path:
            paths.append(path)
    paths = list(dict.fromkeys(paths))
    dirty = {p.get_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()}
    for path in paths:
        if path.split('.')[0] in dirty:
            raise RuntimeError('Preserve unsaved production mesh: ' + path)
    code = (HERE / 'Surface/skin_surface_thumb_v9.hlsl').read_text(encoding='utf-8')
    receipt = json.loads(RECEIPT.read_text(encoding='utf-8')) if RECEIPT.exists() else {
        'schema': 'm16_thumb_surface_contact_v9_asset_save_v1',
        'materials': {}, 'meshes': {}, 'runtime_tested': False, 'rendered': False,
        'geometry_changed': False, 'skin_weights_changed': False, 'poses_changed': False,
    }
    receipt.update(shader_sha256=hashlib.sha256(code.encode('utf-8')).hexdigest(),
                   status='saving', selected_m16_meshes=paths)
    write_receipt(receipt)
    replacements = dict([
        material_family('M_BareNative_Default', 'MI_BareNative_Default', 'Native', code, receipt),
        material_family('M_BareFamily_Hands', 'MI_BareFamily_Hands', 'Hands', code, receipt),
    ])
    targets = {a.get_path_name(): a for a in replacements.values()}
    for path in paths:
        mesh = load(path)
        slots = [s.copy() for s in mesh.get_editor_property('materials')]
        edited, existing = [], []
        for index, slot in enumerate(slots):
            current = slot.material_interface
            old = current.get_path_name() if current else None
            if old in targets:
                existing.append(index)
            if old not in replacements:
                continue
            replacement = replacements[old]
            slot.set_editor_property('material_interface', replacement)
            edited.append({'index': index, 'slot_name': str(slot.material_slot_name),
                           'before': old, 'after': replacement.get_path_name()})
        if edited:
            backup = copy_package(path)
            mesh.modify()
            mesh.set_editor_property('materials', slots)
            E.set_metadata_tag(mesh, 'M16LeftThumbSurface', '20261002 V9; localized canonical thumb appearance')
            save(mesh)
            receipt['meshes'][path] = {'saved': True, 'slots': edited,
                                      'disk_backup': backup, 'after_sha256': digest(package(path))}
        elif not existing:
            raise RuntimeError('Preserve mesh with differing skin material assignment: ' + path)
        write_receipt(receipt)
        u.log('M16_THUMB_SURFACE_SAVED ' + path)
    receipt['status'] = 'assets_saved'
    receipt['saved_mesh_count'] = len(receipt['meshes'])
    receipt['saved_material_count'] = len(receipt['materials']) * 2
    write_receipt(receipt)
    u.log('M16_THUMB_SURFACE_ASSET_SAVE_COMPLETED ' + str(len(receipt['meshes'])))


main()
