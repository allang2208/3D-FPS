"""Assemble the repaired upper-body variants without rebuilding trousers."""
import sys
from pathlib import Path
T=Path(__file__).parent
code=(T/'combat3_assemble.py').read_text(encoding='utf-8').replace("R=S/'CombatShirtR3'", "R=S/'CombatShirtR3/CuffRepairR1'")
sys.argv.append('--upper-only')
exec(compile(code,str(T/'combat3_assemble.py'),'exec'),{'__name__':'__main__','__file__':str(T/'combat3_assemble.py')})
