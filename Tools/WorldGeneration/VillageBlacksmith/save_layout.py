"""Save the authored village after a layout-only adjustment; reuse imported materials."""
import os,runpy
from pathlib import Path
root=Path(__file__).resolve().parents[3]
os.environ['VILLAGE_REUSE_ROAD_MATERIAL']='1'
os.environ['VILLAGE_RECEIPT_DIRECTORY']='Blacksmith20261117'
runpy.run_path(str(root/'Tools/WorldGeneration/AbandonedVillage/author_village.py'),run_name='__main__')
