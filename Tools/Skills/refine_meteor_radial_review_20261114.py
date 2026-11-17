"""Apply the reviewed radial recipe without overwriting the first author receipt."""
import importlib
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'Tools/Skills'))
import add_meteor_radial_impact_20261114 as author
importlib.reload(author)
author.OUT=ROOT/'SourceAssets/MeteorRadialReview20261114'
author.run()
