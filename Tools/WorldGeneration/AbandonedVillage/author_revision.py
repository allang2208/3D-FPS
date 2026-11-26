"""Save demo-style walls and camera eye-adaptation rooms after the native build."""
from pathlib import Path
import os
import runpy

os.environ['VILLAGE_REUSE_ROAD_MATERIAL']='1'
os.environ['VILLAGE_RECEIPT_DIRECTORY']='DemoRevision20261114'
runpy.run_path(str(Path(__file__).with_name('author_village.py')),run_name='__main__')
