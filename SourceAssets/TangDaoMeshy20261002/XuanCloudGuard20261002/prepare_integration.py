"""Derive the standard one-part import and preserve future base reimports."""
from pathlib import Path
import shutil
P=Path(__file__).resolve().parent;BASE=P.parent
s=(BASE/'YanlingPommel20261002/import_assets.py').read_text(encoding='utf-8')
s=s.replace('yanling_breaker','xuan_cloud_dragon')
for old,new in [('pommel','guard'),('Pommel','Guard'),('POMMEL','GUARD'),('Yanling','XuanCloud'),('YANLING','XUAN_CLOUD'),('yanling','xuancloud')]:s=s.replace(old,new)
(P/'import_assets.py').write_text(s,encoding='utf-8')
for path in [BASE/'install_catalog.py',BASE/'SurfaceV2/import_surface.py']:
    text=path.read_text(encoding='utf-8')
    old="'YanlingPommel20261002/catalog_extension.py', 'CloudRune20261002/catalog_extension.py'"
    new="'YanlingPommel20261002/catalog_extension.py', 'XuanCloudGuard20261002/catalog_extension.py',\n                 'CloudRune20261002/catalog_extension.py'"
    if old in text:
        backup=P/'Before'/path.name
        if not backup.exists():shutil.copy2(path,backup)
        path.write_text(text.replace(old,new),encoding='utf-8')
ui=BASE.parents[1]/'Source/FPSGAME/UI/M4GunsmithLayout.cpp'
backup=P/'Before'/ui.name
if not backup.exists():shutil.copy2(ui,backup)
print('XUAN_CLOUD_GUARD_IMPORT_PREPARED',flush=True)
