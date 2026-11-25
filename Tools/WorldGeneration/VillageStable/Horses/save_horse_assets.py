"""Build the horse assets on SM6 without loading the village scene."""
import json
import os
from pathlib import Path
import sys

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from Horses.import_horses import author

run=Path(os.environ['STABLE_RUN'])
(run/'horse-assets.json').write_text(json.dumps(author(),indent=2),encoding='utf-8')
