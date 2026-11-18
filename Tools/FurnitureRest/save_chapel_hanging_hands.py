"""Save the hanging-hand revision, publish owned clip fields, capture its preview."""
import os
from pathlib import Path
import runpy

HERE = Path(__file__).resolve().parent
OUT = HERE.parents[1] / 'SourceAssets/ChapelFurniture20261116/HangingHandsR3'
os.environ['CHAPEL_FURNITURE_OUTPUT'] = str(OUT)
os.environ['CHAPEL_FURNITURE_STAGE'] = 'save'
runpy.run_path(str(HERE/'chapel_pew_assets.py'))
runpy.run_path(str(HERE/'publish_chapel_hand_revision.py'))
os.environ['CHAPEL_PREVIEW_ROOT'] = str(OUT/'Preview')
runpy.run_path(str(HERE/'read_chapel_pew_preview.py'))
print('CHAPEL_HANGING_SAVED_PUBLISHED_CAPTURED', flush=True)
