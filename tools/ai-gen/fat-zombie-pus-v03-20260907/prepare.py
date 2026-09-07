from pathlib import Path
import shutil
p=Path(__file__).resolve().parent
shutil.copy2(p.parent/'deathcow-backfall-v02-20260907/fat-zombie-backfall-v02.glb',p/'model.glb')
