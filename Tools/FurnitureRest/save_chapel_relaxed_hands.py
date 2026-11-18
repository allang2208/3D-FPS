"""Save, publish, and capture the selected native hand revision in one headless batch."""
import os
from pathlib import Path
import runpy

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
OUT = ROOT / 'SourceAssets/ChapelFurniture20261116/HandsR2'
os.environ['CHAPEL_FURNITURE_STAGE'] = 'save'
os.environ['CHAPEL_FURNITURE_OUTPUT'] = str(OUT)
runpy.run_path(str(HERE / 'chapel_pew_assets.py'))
runpy.run_path(str(HERE / 'publish_chapel_hand_revision.py'))
os.environ['CHAPEL_PREVIEW_ROOT'] = str(OUT / 'Preview')
runpy.run_path(str(HERE / 'read_chapel_pew_preview.py'))
print('CHAPEL_RELAXED_HANDS_SAVED_PUBLISHED_CAPTURED', flush=True)
