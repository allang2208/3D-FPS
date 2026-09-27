"""Finish our interrupted first station import; only that known package is task-owned dirty."""
from pathlib import Path
import runpy
ns=runpy.run_path(str(Path(__file__).parent/'install.py'),run_name='anvil_resume')
ns['run']({'/Game/Props/CastingStation20260926/SM_CastingStation'})
