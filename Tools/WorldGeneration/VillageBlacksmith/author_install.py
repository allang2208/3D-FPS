"""Production import/save entry point; does not run gameplay or render previews."""
import os,runpy,sys
from pathlib import Path
root=Path(__file__).resolve().parents[3]
folder=Path(__file__).parent
sys.path.insert(0,str(folder))
runpy.run_path(str(folder/'import_furniture.py'))
runpy.run_path(str(folder/'resize_road_writers.py'))
receipt=root/'SourceAssets/TemperateHillsVillage/Blacksmith20261117'
receipt.mkdir(parents=True,exist_ok=True)
os.environ['VILLAGE_RECEIPT_DIRECTORY']='Blacksmith20261117'
os.environ.pop('VILLAGE_REUSE_ROAD_MATERIAL',None)
runpy.run_path(str(root/'Tools/WorldGeneration/AbandonedVillage/author_village.py'),run_name='__main__')
