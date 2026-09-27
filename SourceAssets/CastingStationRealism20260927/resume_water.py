from pathlib import Path
import runpy
ns=runpy.run_path(str(Path(__file__).parent/'install.py'),run_name='casting_realism_resume')
ns['run']({'/Game/Props/CastingStation20260926/RealismV5/M_QuenchWater'})
