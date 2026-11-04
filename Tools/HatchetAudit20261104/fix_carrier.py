from pathlib import Path
import runpy,shutil
P=Path(__file__).resolve().parent;ROOT=P.parents[1]
asset=ROOT/'Content/Weapons/TacticalHatchet20261101/ModulesV1/SM_TacticalHatchet_Head_Factory_RuneCarrier.uasset'
backup=P/'Before/SM_TacticalHatchet_Head_Factory_RuneCarrier.uasset'
backup.parent.mkdir(parents=True,exist_ok=True)
if not backup.exists():shutil.copy2(asset,backup)
runpy.run_path(str(ROOT/'SourceAssets/OneHandAxe20261101/CommonRunes20261104/resume_carrier.py'),run_name='__main__')
