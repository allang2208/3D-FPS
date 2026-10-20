"""Save the revised quick-melee as editable native weapon and V9 actions."""
from pathlib import Path
source=Path(__file__).parent.parent/'QuickMeleeWrist20261019/export_editable.py'
code=source.read_text().replace('SVCH_QuickMeleeWrist_','SVCH_QuickMeleeSVDReferenceR2_')
exec(compile(code,str(source),'exec'),globals())
