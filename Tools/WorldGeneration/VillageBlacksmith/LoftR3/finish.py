"""Complete dependent production stages in one existing-editor batch; never start PIE or render."""
import importlib,runpy,sys,json,os
from pathlib import Path
ROOT=Path(__file__).resolve().parents[4]
HERE=Path(__file__).resolve().parent
OUT=ROOT/'SourceAssets/HillsVillageBlacksmith20261117/LoftR3'
runpy.run_path(str(HERE/'install_assets.py'),run_name='__main__')
author=HERE.parent/'author_shop.py'
source=author.read_text(encoding='utf-8')
source=source.replace("KIT='/Game/WorldGeneration/TemperateHills/VillageBlacksmith/Meshes/SM_Village'","KIT='/Game/WorldGeneration/TemperateHills/VillageBlacksmith/ArtPassR2/Meshes/SM_Village'")
author.write_text(source,encoding='utf-8')
sys.path.insert(0,str(HERE.parent))
if 'author_shop' in sys.modules:importlib.reload(sys.modules['author_shop'])
runpy.run_path(str(HERE.parent/'WindowR7/finish.py'),run_name='__main__')
headless=os.environ.get('BLACKSMITH_LOFT_HEADLESS')=='1'
if not headless:runpy.run_path(str(HERE/'compile_existing_editor.py'),run_name='__main__')
(OUT/'finished.json').write_text(json.dumps(dict(assets_saved=True,map_saved=True,compile_requested=not headless,background_build=headless,gameplay_tested=False,engine_preview_rendered=False),indent=2),encoding='utf-8')
