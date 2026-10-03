"""Keep the new private pommel option on base/surface reimports and exclusive cards."""
from pathlib import Path
import shutil
P=Path(__file__).resolve().parent;S=P.parent;ROOT=S.parents[1]
for path in [S/'install_catalog.py',S/'SurfaceV2/import_surface.py']:
    text=path.read_text(encoding='utf-8');entry="'TigerPommel20261002/catalog_extension.py'"
    if entry not in text:
        backup=P/'Before'/path.name
        if not backup.exists():shutil.copy2(path,backup)
        anchor="'CloudRune20261002/catalog_extension.py'"
        if anchor not in text:raise RuntimeError('TangDao extension list changed; preserved it')
        text=text.replace(anchor,entry+',\n                 '+anchor)
        path.write_text(text,encoding='utf-8')
ui=ROOT/'Source/FPSGAME/UI/M4GunsmithLayout.cpp'
text=ui.read_text(encoding='utf-8')
anchor='(SlotKey==TEXT("pommel") && Id==TEXT("yanling_breaker"))'
replacement='(SlotKey==TEXT("pommel") && (Id==TEXT("yanling_breaker")||Id==TEXT("tiger_mountain")))'
if replacement not in text:
    if anchor not in text:raise RuntimeError('TangDao exclusive-card clause changed; preserved it')
    backup=P/'Before/M4GunsmithLayout.cpp'
    if not backup.exists():shutil.copy2(ui,backup)
    ui.write_text(text.replace(anchor,replacement),encoding='utf-8')
print('TIGER_POMMEL_REIMPORT_AND_GOLD_CARD_SOURCE_SAVED',flush=True)
