"""Save the new nun-only relaxed animation revision."""
from pathlib import Path
P=Path('D:/FPS3D/FPSGAME')
source=(P/'Tools/ChapelNun/save_idle_contact_r2.py').read_text(encoding='utf-8')
source=source.replace('IdleHandsFrontR2','IdleRelaxedR3').replace('A_Nun_Idle_HandsFront_R2','A_Nun_Idle_Relaxed_R3')
source=source.replace('Nun clasped hands and quiet breathing','Nun relaxed arms and quiet breathing').replace('HandsFrontR2','RelaxedR3')
exec(compile(source,str(P/'Tools/ChapelNun/save_idle_contact_r2.py'),'exec'))
