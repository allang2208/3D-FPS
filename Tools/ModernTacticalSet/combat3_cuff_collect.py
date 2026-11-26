"""Collect the independent current-glove wrist production batches."""
import json
from pathlib import Path
R=Path('D:/FPS3D/FPSGAME/SourceAssets/ModernTacticalSet20261113/CombatShirtR3');C=R/'CuffRepairR1'
def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
rows={}
for name in ['world','a','b','c']:
    batch=read(C/('gloves-batch-'+name+'.json'))
    if not batch['completed']:raise RuntimeError('Wrist glove batch in progress '+name)
    for row in batch['rows']:
        if row['rig'] in rows:raise RuntimeError('Duplicate glove native profile '+row['rig'])
        rows[row['rig']]=row
expected={row['rig'] for row in read(R/'fp-authored.json')['rows']}|{'Jason','Kaitlin'}
if set(rows)!=expected:raise RuntimeError('Missing glove native profiles '+str(expected-set(rows)))
for rig in ['Body','Super90']:
    if read(Path(rows[rig]['file'])).get('native_cuff_fit',{}).get('method')!='current_native_skin_v2':raise RuntimeError('Native glove cuff fit pending: '+rig)
(C/'gloves-authored.json').write_text(json.dumps(dict(completed=True,rows=list(rows.values())),indent=2)+'\n',encoding='utf-8');print('NATIVE_GLOVE_BATCHES_COLLECTED',len(rows),flush=True)
