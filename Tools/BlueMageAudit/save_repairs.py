"""Save the three corrected families in one mutex-owned UE authoring process."""
import runpy,sys,gc
from pathlib import Path
import unreal as u
P=Path('D:/FPS3D/FPSGAME')
for family in ('BlueMagePants','BlueMageBoots','BlueMageHat'):
    sys.modules.pop('common',None)
    runpy.run_path(str(P/'Tools'/family/'save_assets.py'),run_name='__main__')
    gc.collect();u.SystemLibrary.collect_garbage()
print('MAGE_SET_REPAIRS_SAVED',flush=True)
