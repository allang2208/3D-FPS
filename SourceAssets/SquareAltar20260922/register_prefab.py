"""Append one marble prefab; retain every existing entry and its live fields."""
import json
import math
from pathlib import Path
import unreal as u

HERE=Path(__file__).parent
ROOT='/Game/Props/SquareAltar20260922'
PALETTE='/Game/Building/Voxels/Rounded/DA_VoxelBuildPalette'
mesh=u.load_asset(ROOT+'/SM_SquareAltar')
palette=u.load_asset(PALETTE)
if not mesh or not palette:raise RuntimeError('Altar mesh or active building palette missing')
b=mesh.get_bounds();size=[2*b.box_extent.x,2*b.box_extent.y,2*b.box_extent.z]
cells=[max(1,math.ceil((v-.01)/20)) for v in size]
entry=u.VoxelBuildPrefab()
entry.set_editor_property('id','square_altar')
entry.set_editor_property('display_name',u.Text('白金方形祭坛'))
entry.set_editor_property('mesh',mesh)
entry.set_editor_property('footprint',u.IntVector(*cells))
entry.set_editor_property('material','marble')
# No surface override: the original four material slots remain visible.
# ComputeTransform centres the mesh in its occupied volume. Subtract the
# vertical rounding margin so the actual stone bottom sits on the ground.
entry.set_editor_property('pivot_offset_cm',u.Vector(0,0,-(cells[2]*20-size[2])/2))
components=list(palette.get_editor_property('components'))
if any(str(e.get_editor_property('id'))=='square_altar' for e in components):
    raise RuntimeError('square_altar already registered; preserve current entry')
palette.modify();components.append(entry);palette.set_editor_property('components',components)
if not u.EditorLoadingAndSavingUtils.save_packages([u.load_package(PALETTE)],False):raise RuntimeError('Palette save failed')
receipt={'palette':PALETTE,'id':'square_altar','name':'白金方形祭坛','menu':'大理石 / 其他构造',
    'mesh':mesh.get_path_name(),'mesh_dimensions_cm':size,'footprint':cells,
    'placement_offset_z_cm':-(cells[2]*20-size[2])/2,'saved':True,'runtime_tested':False}
(HERE/'integration_receipt.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2),encoding='utf-8')
print('SQUARE_ALTAR_PREFAB_SAVED '+json.dumps(receipt,ensure_ascii=False))
