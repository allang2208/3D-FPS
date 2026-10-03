"""Save the revised shoulder fit through the existing editor's exclusive bridge."""
import runpy
import shutil
from pathlib import Path
backup=Path('D:/FPS3D/FPSGAME/SourceAssets/JasonEquipmentRepair20261003/ShoulderStraps/SK_Jason_Backpack_before.uasset')
if not backup.exists():
    shutil.copy2('D:/FPS3D/FPSGAME/Content/Characters/ModularOutfit20260924/JasonPlayer20261003/EquipmentFit20261003/SK_Jason_Backpack.uasset',backup)
runpy.run_path('D:/FPS3D/FPSGAME/Tools/PlayerBody/save_jason_equipment.py',
              init_globals={'BACKPACK_ONLY':True,'STRAPS_ONLY':True})
