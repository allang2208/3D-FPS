"""Retarget gun_workbench_table to the medieval mesh inside the LIVE editor
(the palette asset is locked by the running editor process)."""
import json
from pathlib import Path
import unreal as u

E = u.EditorAssetLibrary
PALETTE = '/Game/Building/Voxels/Rounded/DA_VoxelBuildPalette'
NEW_MESH = '/Game/Building/GunWorkbenchMedieval20260928/SM_GunWorkbench.SM_GunWorkbench'
ENTRY_ID = 'gun_workbench_table'
RECEIPT = Path('D:/FPS3D/FPSGAME/SourceAssets/GunWorkbenchMedieval20260928/Receipts/import.json')

if u.get_editor_subsystem(u.UnrealEditorSubsystem).get_game_world():
    raise RuntimeError('Stop PIE before updating the palette')

mesh = u.load_asset(NEW_MESH)
if not mesh:
    raise RuntimeError('New mesh missing on disk: ' + NEW_MESH)
palette = u.load_asset(PALETTE)
if not palette:
    raise RuntimeError('Palette missing')

components = list(palette.get_editor_property('components'))
updated = False
previous = None
for index, current in enumerate(components):
    if str(current.get_editor_property('id')) == ENTRY_ID:
        previous = current.get_editor_property('mesh').get_path_name()
        current.set_editor_property('mesh', mesh)
        components[index] = current
        updated = True
        break
if not updated:
    raise RuntimeError('Palette entry missing: ' + ENTRY_ID)
palette.modify()
palette.set_editor_property('components', components)
if not E.save_loaded_asset(palette, False):
    raise RuntimeError('Palette save failed (live editor)')

# refresh the hand-off receipt with the authoritative palette state
if RECEIPT.exists():
    receipt = json.loads(RECEIPT.read_text(encoding='utf-8'))
    receipt['previous_mesh'] = previous
    receipt['palette_live_saved'] = True
    RECEIPT.write_text(json.dumps(receipt, ensure_ascii=False, indent=2),
                       encoding='utf-8')
print('LIVE_PALETTE_UPDATED previous=%s new=%s' % (previous, NEW_MESH))
