"""Register the five tier crates as building-panel prefabs in the 其他 (unclassified) tab.

    python Tools/AssetPipeline/ue_python_exec.py --script SourceAssets/WarehouseCrateTiers20260924/register_crate_prefabs.py

Runs INSIDE the live editor (remote execution): the interactive editor holds the palette
package, so an external commandlet write would silently fail (Docs/Building/voxel-build-workflow.md §6).
Drawer rule (VoxelBuildWidget.cpp): the 其他 tab lists only components whose palette
``Material`` field is empty; the furnace precedent is set_furnace_drawer.py.
``Surface`` is deliberately left empty: Configure() would SetMaterial(0,Surface) and
flatten the multi-material crates; the icon studio copies per-slot materials itself.
Footprint rounds UP to the 20 cm lattice (mesh slightly smaller than cells is allowed
for decorative pieces); PivotOffsetCm sinks the vertical rounding margin so the crate
sits on the cell floor. The components array is a copy: mutate entries, write the whole
array back, save, then re-load from disk to verify.
"""
import json, math
from pathlib import Path
import unreal as u

try:
    HERE = Path(__file__).parent
except NameError:  # remote MODE_EXEC_FILE may not define __file__
    HERE = Path('D:/FPS3D/FPSGAME/SourceAssets/WarehouseCrateTiers20260924')
PALETTE = '/Game/Building/Voxels/Rounded/DA_VoxelBuildPalette'
MESH_ROOT = '/Game/Props/WarehouseCrateTiers20260924'
EXPECTED = {
    'warehouse_crate_wood':      ('SM_WarehouseCrate_T1_Wood', '木箱', (164.0, 132.5, 111.1)),
    'warehouse_crate_stonewood': ('SM_WarehouseCrate_T2_StoneWood', '石饰木箱', (164.0, 132.5, 111.3)),
    'warehouse_crate_iron':      ('SM_WarehouseCrate_T3_Iron', '铁箱', (164.0, 132.5, 111.3)),
    'warehouse_crate_irongold':  ('SM_WarehouseCrate_T4_IronGold', '金纹铁箱', (164.0, 132.5, 111.3)),
    'warehouse_crate_silvergem': ('SM_WarehouseCrate_T5_SilverGem', '宝石银箱', (164.0, 132.5, 116.9)),
}
editor = u.get_editor_subsystem(u.UnrealEditorSubsystem)
# This runs INSIDE the live editor over remote execution, so a loaded game world here is
# the user's running PIE (a transient copy). Editing + saving the palette data asset is the
# documented path (workflow §6); the running PIE simply won't pick it up until restart.
pie_active = bool(editor and editor.get_game_world())

palette = u.load_asset(PALETTE)
if palette is None:
    raise RuntimeError('Active building palette missing: ' + PALETTE)

components = list(palette.get_editor_property('components'))
existing = {str(e.get_editor_property('id')): i for i, e in enumerate(components)}
receipt = {'palette': PALETTE, 'entries_before': len(components), 'pie_active': pie_active,
           'registered': {}, 'updated': [], 'skipped': []}

for pid, (mesh_name, display, expected_size) in EXPECTED.items():
    mesh = u.load_asset(MESH_ROOT + '/' + mesh_name)
    if mesh is None:
        raise RuntimeError('Crate mesh missing: ' + mesh_name)
    box = mesh.get_bounds()
    size = [2 * box.box_extent.x, 2 * box.box_extent.y, 2 * box.box_extent.z]
    # Silent-rescale guard: the palette footprint is a save contract.
    for measured, want in zip(size, expected_size):
        if abs(measured - want) > 0.5:
            raise RuntimeError('%s wrong scale: %s expected %s' % (pid, size, expected_size))
    cells = [max(1, math.ceil((v - 0.01) / 20.0)) for v in size]
    offset_z = -(cells[2] * 20.0 - size[2]) / 2.0
    entry = u.VoxelBuildPrefab()
    entry.set_editor_property('id', pid)
    entry.set_editor_property('display_name', u.Text(display))
    entry.set_editor_property('mesh', mesh)
    entry.set_editor_property('footprint', u.IntVector(cells[0], cells[1], cells[2]))
    entry.set_editor_property('mount', u.VoxelPrefabMount.FREE)
    entry.set_editor_property('pivot_offset_cm', u.Vector(0.0, 0.0, offset_z))
    # Material stays empty -> 其他 tab; Surface stays empty -> mesh keeps its own slots.
    if pid in existing:
        components[existing[pid]] = entry
        receipt['updated'].append(pid)
    else:
        components.append(entry)
    receipt['registered'][pid] = {'mesh': mesh_name, 'display': display, 'footprint': cells,
                                  'size_cm': [round(v, 2) for v in size], 'pivot_z': round(offset_z, 3)}

palette.modify()
palette.set_editor_property('components', components)
uasset = Path('D:/FPS3D/FPSGAME/Content/Building/Voxels/Rounded/DA_VoxelBuildPalette.uasset')
mtime_before = uasset.stat().st_mtime if uasset.exists() else 0
if not u.EditorLoadingAndSavingUtils.save_packages([u.load_package(PALETTE)], False):
    raise RuntimeError('Palette save failed')
mtime_after = uasset.stat().st_mtime if uasset.exists() else 0
if mtime_after <= mtime_before:
    raise RuntimeError('Palette .uasset on disk did not change (mtime %s -> %s)' % (mtime_before, mtime_after))

# Verify from the reloaded asset, not the in-memory copy.
check = u.load_asset(PALETTE)
found = {str(e.get_editor_property('id')): e for e in check.get_editor_property('components')}
for pid in EXPECTED:
    entry = found.get(pid)
    if entry is None:
        raise RuntimeError('Entry lost after save: ' + pid)
    material = entry.get_editor_property('material')
    if not (hasattr(material, 'is_none') and material.is_none()):
        raise RuntimeError('Saved Material is not empty (would leave 其他 tab): %s %r' % (pid, material))
    fp = entry.get_editor_property('footprint')
    want = receipt['registered'][pid]['footprint']
    if [fp.x, fp.y, fp.z] != want:
        raise RuntimeError('Footprint mismatch for %s: %s vs %s' % (pid, [fp.x, fp.y, fp.z], want))
    mesh_ref = entry.get_editor_property('mesh')
    if mesh_ref is None or 'WarehouseCrateTiers20260924' not in mesh_ref.get_path_name():
        raise RuntimeError('Mesh reference wrong after save: ' + pid)
receipt['entries_after'] = len(found)
receipt['total_components'] = len(check.get_editor_property('components'))
receipt['uasset_mtime'] = [round(mtime_before, 3), round(mtime_after, 3)]
receipt['runtime_tested'] = False
(HERE / 'register_receipt.json').write_text(json.dumps(receipt, ensure_ascii=False, indent=2), encoding='utf-8')
print('CRATE_PREFABS_REGISTERED ' + json.dumps(receipt, ensure_ascii=False), flush=True)
