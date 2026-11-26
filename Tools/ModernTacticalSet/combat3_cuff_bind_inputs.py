import json,math
from pathlib import Path
C=Path('D:/FPS3D/FPSGAME/SourceAssets/ModernTacticalSet20261113/CombatShirtR3/CuffRepairR1')
rows=json.loads((C/'captured.json').read_text(encoding='utf-8'))['rows']
for rig in ['M4','Super90','M16','Body']:
    g=json.loads(Path(next(r['file'] for r in rows if r['key']=='Glove_'+rig)).read_text(encoding='utf-8'));n=json.loads(Path(next(r['file'] for r in rows if r['key']=='Native_'+rig)).read_text(encoding='utf-8'));names=[name for name in n['bones'] if name.startswith(('upperarm','lowerarm','hand_')) and name in g['bones']]
    dp=max(math.dist(n['bones'][name]['position'],g['bones'][name]['position']) for name in names);da=max(math.dist(a,b) for name in names for a,b in zip(n['bones'][name]['axes'],g['bones'][name]['axes']))
    print(rig,dict(max_arm_bind_position_cm=dp,max_arm_bind_axis_difference=da,glove_hand=g['bones']['hand_l']['position'],native_hand=n['bones']['hand_l']['position']),flush=True)
