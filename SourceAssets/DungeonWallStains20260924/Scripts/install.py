"""Background asset production; no level edits or game/visual tests."""
import json,sys
from pathlib import Path
import unreal as u
ROOT=Path(__file__).resolve().parents[1]
PROJECT=ROOT.parents[1]
if Path(u.Paths.project_dir()).resolve()!=PROJECT.resolve():raise RuntimeError('Wrong project')
sys.path.insert(0,str(PROJECT/'Tools/AssetPipeline'))
import dungeon_wall_stains as stains
saved=[]
for path in stains.PATHS:
    stains.install_material(path);saved.append(path)
receipt=ROOT/'Receipts/install.json';receipt.parent.mkdir(parents=True,exist_ok=True)
receipt.write_text(json.dumps({'status':'materials_saved','materials':saved,
    'mask':stains.BASE+'/Textures/T_WallStreakMasks','game_tested':False},indent=2),encoding='utf-8')
print('WALL_STREAK_INSTALL_COMPLETE',flush=True)
