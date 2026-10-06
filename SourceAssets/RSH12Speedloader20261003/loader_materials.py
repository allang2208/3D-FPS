"""Production WS1 surfaces for the carrier and five retention collars."""
from pathlib import Path
import runpy

def create(root,save):
    helper=Path(__file__).resolve().parents[1]/'RSH12MaterialFinish20261005/finish_materials.py'
    return runpy.run_path(str(helper))['make_loader_materials'](save)
