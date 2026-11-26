"""Append completed native viewmodels to the already authored world garments."""
import json
from pathlib import Path
P=Path('D:/FPS3D/FPSGAME');S=P/'SourceAssets/ModernTacticalSet20261113';R=S/'CombatShirtR3';DEST='/Game/Characters/ModularOutfit20260924/ModernTacticalSet20261113/CombatShirtR3'
read=lambda p:json.loads(p.read_text(encoding='utf-8-sig'))
fp=read(R/'fp-authored.json');world=read(R/'authored-world.json');plan=read(S/'CombatShirtR1/plan.json')
if not fp.get('completed'):raise RuntimeError('Native first-person garment production is incomplete')
rows=world['rows']
for entry in fp['rows']:
    source=next(row['source'] for row in plan['rows'] if row['rig']==entry['rig']);rows.append(dict(source=source,rig=entry['rig'],file=entry['file'],asset=DEST+'/Wear/'+entry['rig']+'/SK_TS01_Combat_'+entry['rig']))
(R/'authored.json').write_text(json.dumps(dict(completed=True,rows=rows),indent=2),encoding='utf-8');print('R3_NATIVE_GARMENT_MANIFEST',len(rows))
