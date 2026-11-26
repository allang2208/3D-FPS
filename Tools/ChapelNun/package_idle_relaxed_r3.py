"""Package the new editable animation source without rendering."""
from pathlib import Path
P=Path('D:/FPS3D/FPSGAME')
source=(P/'Tools/ChapelNun/package_idle_contact_r2.py').read_text(encoding='utf-8')
source=source.replace('IdleHandsFrontR2','IdleRelaxedR3').replace('Nun_Idle_HandsFront_Rig','Nun_Idle_Relaxed_Rig')
source=source.replace('Nun_HandsFront_QuietBreathing_12s','Nun_Relaxed_QuietBreathing_12s')
source=source.replace('A_Nun_Idle_HandsFront_R2','A_Nun_Idle_Relaxed_R3').replace('Nun_HandsFront_Idle_R2.blend','Nun_Relaxed_Idle_R3.blend')
exec(compile(source,str(P/'Tools/ChapelNun/package_idle_contact_r2.py'),'exec'))
