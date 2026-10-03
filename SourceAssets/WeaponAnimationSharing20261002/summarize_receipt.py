"""Record saved production counts; no game or animation tests."""
from pathlib import Path
import runpy

job = Path(__file__).parent
runpy.run_path(str(job.parent / 'WeaponAnimationSharing20261001/summarize_receipt.py'),
               init_globals={'ANIMATION_SHARING_JOB_ROOT': str(job)})
