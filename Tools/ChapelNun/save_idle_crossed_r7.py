"""Save the corrected, nun-only crossed-hands animation revision."""
from pathlib import Path
P=Path('D:/FPS3D/FPSGAME')
source=(P/'Tools/ChapelNun/save_idle_contact_r2.py').read_text(encoding='utf-8')
source=source.replace('IdleHandsFrontR2','IdleCrossedR7').replace('A_Nun_Idle_HandsFront_R2','A_Nun_Idle_Crossed_R7')
source=source.replace('Nun clasped hands and quiet breathing','Nun low crossed hands and quiet breathing').replace('HandsFrontR2','CrossedR7')
exec(compile(source,str(P/'Tools/ChapelNun/save_idle_contact_r2.py'),'exec'))
