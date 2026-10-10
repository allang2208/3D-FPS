"""Import/save V24 with the existing staged cloth and continuous-corpse pipeline."""
from pathlib import Path
import sys
sys.path.insert(0,'D:/FPS3D/FPSGAME/Tools/BoundCongregate')
from materials_garment_v24 import build
BC_GARMENT_REVISION='GarmentDrapeV24'
BC_GARMENT_VERSION='V24'
BC_GARMENT_PRESERVED='exposed anatomy and complete source body, tentacle rig, FlurryV22, other animations and current Blueprint gameplay tuning; covered body faces omitted only in this outfit'
BC_GARMENT_SOURCE='/Game/Monsters/BoundCongregate/GarmentDrapeV23/SK_BoundCongregate_GarmentDrapeV23'
BC_GARMENT_MATERIAL_AUTHOR=build
BC_GARMENT_COLLISION_REVISION='V24 garment-interior bodies, shared local skin carriers and contact backstops'
BC_GARMENT_MATERIAL_REVISION='V24 Witch Fabric09 weave, metric UV calibration, G/B wear and dirt; preserved Alpha drive'
script=Path('D:/FPS3D/FPSGAME/Tools/BoundCongregate/import_garment_drape_v18.py')
exec(compile(script.read_text(encoding='utf8'),str(script),'exec'),globals())
