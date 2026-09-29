import sys
from pathlib import Path
P=Path('D:/FPS3D/FPSGAME');sys.path.insert(0,str(P/'Tools/ModularOutfit'));from garment_ue import collect_motion
R=P/'SourceAssets/GarmentFoundation20260929'
for name in ['ue_chainmail_shirt','ue_field_sweater','ue_field_sweater_charcoal']:collect_motion(R/name/'candidate.json')
for profile in ['M16','ASH12']:collect_motion(R/'NativeProbe'/profile/'candidate.json')
