from pathlib import Path
import runpy
_parent=Path(__file__).resolve().parent.parent
_base=runpy.run_path(str(_parent/'design.py'))
SURFACES=_base['SURFACES'];SUB=_base['SUB'];SOURCE_MAP=_base['SOURCE_MAP'];MAP=_base['MAP']
R=Path(__file__).resolve().parent;PROJECT=R.parents[3]
BASE='/Game/Props/CyberpunkBedroomPilot20261024/RefinementV2'
OWNER='Cyberpunk.BedroomPilot.RefinementV2'
BRIEF=dict(_base['BRIEF'],geometry_checks_requested=True,revision='V2 support surfaces and component clearances')
