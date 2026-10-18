"""ST6 refinement production entry; original sources stay available for rebuilding."""
from pathlib import Path
O=Path(__file__).parent;TASK=O.parent/'ST6Refine20261018'
for name in ('finish_assets.py',):
    file=TASK/name
    exec(compile(file.read_text(encoding='utf-8'),str(file),'exec'),{'__file__':str(file),'__name__':'__main__'})
