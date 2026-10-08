"""Reuse the established clothing/corpse importer with the new garment cut."""
from pathlib import Path
BC_GARMENT_REVISION='GarmentRebuildV19'
BC_GARMENT_VERSION='V19'
BC_GARMENT_SOURCE='/Game/Monsters/BoundCongregate/GarmentDrapeV18/SK_BoundCongregate_GarmentDrapeV18'
script=Path('D:/FPS3D/FPSGAME/Tools/BoundCongregate/import_garment_drape_v18.py')
exec(compile(script.read_text(encoding='utf8'),str(script),'exec'),globals())
