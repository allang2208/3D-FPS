"""Preserve this guard on subsequent TangDao base/material imports."""
from pathlib import Path
import shutil
P=Path(__file__).resolve().parent;S=P.parent
for path in [S/'install_catalog.py',S/'SurfaceV2/import_surface.py']:
    text=path.read_text(encoding='utf-8');entry="'PhoenixFeatherGuard20261002/catalog_extension.py'"
    if entry not in text:
        backup=P/'Before'/path.name
        if not backup.exists():shutil.copy2(path,backup)
        text=text.replace("'XuanCloudGuard20261002/catalog_extension.py',","'XuanCloudGuard20261002/catalog_extension.py',\n                 "+entry+",")
        path.write_text(text,encoding='utf-8')
ui=S.parents[1]/'Source/FPSGAME/UI/M4GunsmithLayout.cpp';backup=P/'Before'/ui.name
if not backup.exists():shutil.copy2(ui,backup)
print('PHOENIX_GUARD_REIMPORT_HOOKS_PREPARED',flush=True)
