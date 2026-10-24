"""Reuse V8 manufactured frames at the new first-row facade placements."""
from pathlib import Path
import runpy
R=Path(__file__).resolve().parent
source=(R.parent/'RefinementV8/author.py').read_text(encoding='utf8')
source=source.replace('from design import *','globals().update(runpy.run_path(str(R/"design.py")))')
source=source.replace('SM_AP8_MountedFrames','SM_AP10_MountedFrames')
source=source.replace('for ob,world in [(frame,True),(screen,False)]:','for ob,world in [(frame,True)]:')
source=source.replace('AP8_GEOMETRY_AUTHORED','AP10_GEOMETRY_AUTHORED')
exec(compile(source,str(R/'author.py'),'exec'),dict(__file__=str(R/'author.py'),R=R,runpy=runpy))
