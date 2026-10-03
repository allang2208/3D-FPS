"""Produce and save this batch with the shared offline animation producer."""
from pathlib import Path
import runpy

job = Path(__file__).parent
runpy.run_path(str(job.parent / 'WeaponAnimationSharing20261001/install_profiles.py'),
               init_globals={'ANIMATION_SHARING_JOB_ROOT': str(job),
                             'ANIMATION_SHARING_AUTHOR': 'WeaponAnimationSharing20261002'})
