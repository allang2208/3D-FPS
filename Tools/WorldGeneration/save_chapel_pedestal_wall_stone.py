"""Save the user's low-wall-stone revision, retaining the prior pedestal packages."""
import os,runpy,shutil
from pathlib import Path
ROOT=Path('D:/FPS3D/FPSGAME')
OUT=ROOT/'SourceAssets/ChapelShrineForecourt20261116/WallStoneR3'
OUT.mkdir(parents=True,exist_ok=True);(OUT/'Before').mkdir(exist_ok=True)
for name in ('SM_ChapelShrineRockPedestal','M_ChapelShrinePedestalStone'):
    source=ROOT/'Content/WorldGeneration/HillsNightRaid'/(name+'.uasset')
    target=OUT/'Before'/(name+'.uasset')
    if not target.exists():shutil.copy2(source,target)
os.environ['CHAPEL_SHRINE_OUTPUT']=str(OUT)
os.environ['CHAPEL_SHRINE_SOURCE_ROOT']=str(ROOT)
runpy.run_path(str(ROOT/'Tools/WorldGeneration/author_chapel_shrine_pedestal.py'))
print('CHAPEL_WALL_STONE_SAVED',flush=True)
