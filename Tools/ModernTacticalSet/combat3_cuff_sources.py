"""Produce repaired shirt author files and the standard inventory icon."""
from pathlib import Path
T=Path(__file__).parent;C=Path('D:/FPS3D/FPSGAME/SourceAssets/ModernTacticalSet20261113/CombatShirtR3/CuffRepairR1')
for name in ['Models','Exports','Icons']:(C/name).mkdir(exist_ok=True)
code=(T/'combat3_sources.py').read_text(encoding='utf-8').replace("R=S/'CombatShirtR3'", "R=S/'CombatShirtR3/CuffRepairR1'").replace("R/'Textures'", "R.parent/'Textures'").replace("R/'Bakes'", "R.parent/'Bakes'")
exec(compile(code,str(T/'combat3_sources.py'),'exec'),{'__name__':'__main__','__file__':str(T/'combat3_sources.py')})
