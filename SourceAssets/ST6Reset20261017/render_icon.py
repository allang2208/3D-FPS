"""ST6 refinement production entry; original sources stay available for rebuilding."""
from pathlib import Path
O=Path(__file__).parent;TASK=O.parent/'ST6Refine20261018'
for name in ('author_collar.py', 'render_icon.py'):
    file=TASK/name
    exec(compile(file.read_text(encoding='utf-8'),str(file),'exec'),{'__file__':str(file),'__name__':'__main__'})

import shutil
for name in ("ue_st6_sleeves.png","SM_ue_st6_sleeves.fbx"):
    shutil.copy2(TASK/name,O/name)
