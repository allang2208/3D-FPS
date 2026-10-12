"""Save the revised shoulder fit through the existing editor's exclusive bridge."""
import runpy
import shutil
from pathlib import Path
repair=Path('D:/FPS3D/FPSGAME/SourceAssets/BackpackStraps20261012/backpack_repaired.json')
if repair.exists():
    # The complete harness supersedes the old shoulder-only fit. Keep the
    # production entry point from restoring its arm/leg-bound loose strips.
    runpy.run_path('D:/FPS3D/FPSGAME/Tools/PlayerBody/save_backpack_straps20261012.py',run_name='__main__')
else:
    backup=Path('D:/FPS3D/FPSGAME/trash/player-presentation-retired-20261012/SourceAssets/JasonEquipmentRepair20261003/ShoulderStraps/SK_Jason_Backpack_before.uasset')
    backup.parent.mkdir(parents=True,exist_ok=True)
    if not backup.exists():
        shutil.copy2('D:/FPS3D/FPSGAME/Content/Characters/ModularOutfit20260924/JasonPlayer20261003/EquipmentFit20261003/SK_Jason_Backpack.uasset',backup)
    runpy.run_path('D:/FPS3D/FPSGAME/Tools/PlayerBody/save_jason_equipment.py',
                  init_globals={'BACKPACK_ONLY':True,'STRAPS_ONLY':True})
