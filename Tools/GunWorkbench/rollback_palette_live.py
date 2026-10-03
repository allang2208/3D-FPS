"""Rollback: retarget gun_workbench_table back to the pre-medieval mesh inside
the LIVE editor (user rejected the medieval restyle on 2026-09-28)."""
import json
from pathlib import Path
import unreal as u

E = u.EditorAssetLibrary
PALETTE = '/Game/Building/Voxels/Rounded/DA_VoxelBuildPalette'
RESTORE_MESH = ('/Game/Building/GunWorkbenchLibraryTools20260928/'
                'SM_GunWorkbench.SM_GunWorkbench')
ENTRY_ID = 'gun_workbench_table'
RECEIPT = Path('D:/FPS3D/FPSGAME/SourceAssets/GunWorkbenchMedieval20260928/Receipts/import.json')

if u.get_editor_subsystem(u.UnrealEditorSubsystem).get_game_world():
    raise RuntimeError('Stop PIE before rolling back the palette')

mesh = u.load_asset(RESTORE_MESH)
if not mesh:
    raise RuntimeError('Restore mesh missing: ' + RESTORE_MESH)
palette = u.load_asset(PALETTE)
if not palette:
    raise RuntimeError('Palette missing')

components = list(palette.get_editor_property('components'))
rolled = False
previous = None
for index, current in enumerate(components):
    if str(current.get_editor_property('id')) == ENTRY_ID:
        previous = current.get_editor_property('mesh').get_path_name()
        current.set_editor_property('mesh', mesh)
        components[index] = current
        rolled = True
        break
if not rolled:
    raise RuntimeError('Palette entry missing: ' + ENTRY_ID)
palette.modify()
palette.set_editor_property('components', components)
if not E.save_loaded_asset(palette, False):
    raise RuntimeError('Palette save failed (live editor)')

if RECEIPT.exists():
    receipt = json.loads(RECEIPT.read_text(encoding='utf-8'))
    receipt['rejected'] = True
    receipt['rolled_back_to'] = RESTORE_MESH
    receipt['rollback_previous'] = previous
    RECEIPT.write_text(json.dumps(receipt, ensure_ascii=False, indent=2),
                       encoding='utf-8')
print('LIVE_PALETTE_ROLLED_BACK previous=%s restored=%s' % (previous, RESTORE_MESH))
