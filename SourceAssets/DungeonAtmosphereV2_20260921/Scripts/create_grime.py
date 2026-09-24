"""Keep historical room rebuilds on the current sparse wall-seepage material."""
import unreal as u
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[3]/'Tools/AssetPipeline'))
from dungeon_wall_stains import install_material
path='/Game/Dungeons/AtmosphereV2/Materials/M_LocalDampStreak'
m=u.load_asset(path)
if not m:
    m=u.AssetToolsHelpers.get_asset_tools().create_asset('M_LocalDampStreak',path.rsplit('/',1)[0],u.Material,u.MaterialFactoryNew())
if not m:raise RuntimeError('Cannot create wall stain material')
if not install_material(path):raise RuntimeError('Wall stain material was not installed')
print('V2_SPARSE_WALL_STREAK_MATERIAL_SAVED')
