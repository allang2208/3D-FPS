"""Final runtime-path check for the battle axe. Read-only."""
import os
import unreal as u

mesh = u.EditorAssetLibrary.load_asset('/Game/Items/ProductionTools/BattleAxe20260919/SM_BattleAxe')
if mesh:
    bounds = mesh.get_bounds()
    print('TOOL_MESH_OK height_cm', round(bounds.box_extent.z * 2, 1),
          'width_cm', round(bounds.box_extent.x * 2, 1))
else:
    print('TOOL_MESH_MISSING')

icon_dir = u.Paths.project_content_dir() + 'ColdSteelData/ProductionTools/'
for name in ['axe.png', 'pickaxe.png', 'shovel.png']:
    print('ICON', name, os.path.exists(icon_dir + name), os.path.getsize(icon_dir + name))
print('FINAL_CHECK_DONE')