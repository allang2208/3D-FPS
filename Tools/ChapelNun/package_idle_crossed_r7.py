"""Editable crossed-hands animation source with the current robe and body."""
from pathlib import Path
P=Path('D:/FPS3D/FPSGAME')
source=(P/'Tools/ChapelNun/package_idle_contact_r2.py').read_text(encoding='utf-8')
source=source.replace('IdleHandsFrontR2','IdleCrossedR7').replace('Nun_Idle_HandsFront_Rig','Nun_Idle_Crossed_Rig')
source=source.replace('IdleBackReviewR2/InputsAfter','IdleRelaxedR3/Review/InputsAfter')
source=source.replace('Nun_HandsFront_QuietBreathing_12s','Nun_Crossed_QuietBreathing_12s')
source=source.replace('A_Nun_Idle_HandsFront_R2','A_Nun_Idle_Crossed_R7').replace('Nun_HandsFront_Idle_R2.blend','Nun_Crossed_Idle_R7.blend')
exec(compile(source,str(P/'Tools/ChapelNun/package_idle_contact_r2.py'),'exec'))
