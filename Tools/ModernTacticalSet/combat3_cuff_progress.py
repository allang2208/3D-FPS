"""Read the current production receipts without launching an application."""
import json
from pathlib import Path
C=Path('D:/FPS3D/FPSGAME/SourceAssets/ModernTacticalSet20261113/CombatShirtR3/CuffRepairR1')
print('TAILORED',len(list((C/'Review').glob('*-tailored.json'))),flush=True)
for name in ['tailor-c','glove-world','glove-a','glove-b','glove-c','world-finish-final']:
    file=C/'Logs'/(name+'.log')
    print(name,file.read_text(encoding='utf-8',errors='replace')[-900:],flush=True)
