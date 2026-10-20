"""Editable native rigs and corrected R3 quick-melee; shared V9 remains read-only."""
from pathlib import Path
source=Path(__file__).parent.parent/'QuickMeleeWrist20261019/export_editable.py'
code=source.read_text().replace('SVCH_QuickMeleeWrist_','SVCH_QuickMeleeHandR3_')
exec(compile(code,str(source),'exec'),globals())
