"""Save the two local anatomy refinements, then read back the saved candidate."""
from pathlib import Path
import runpy
HERE=Path(__file__).resolve().parent
OUT=Path('D:/FPS3D/FPSGAME/SourceAssets/JasonStrong20261117/R2_LongLegs/AnatomyReview')
before=OUT/'derived_before_refinement.json'
if not before.exists():
    before.write_bytes((OUT/'derived_saved_mesh.json').read_bytes())
runpy.run_path(str(HERE/'save_variant.py'),run_name='__main__')
runpy.run_path(str(HERE/'capture_anatomy_review.py'),run_name='__main__')
