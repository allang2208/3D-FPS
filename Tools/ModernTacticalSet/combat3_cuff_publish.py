"""Record the actually saved cuff repair, retaining existing game identities."""
import json,hashlib
from pathlib import Path
from datetime import datetime
P=Path('D:/FPS3D/FPSGAME');R=P/'SourceAssets/ModernTacticalSet20261113/CombatShirtR3';C=R/'CuffRepairR1'
def read(p):return json.loads(Path(p).read_text(encoding='utf-8-sig'))
saved=read(R/'saved.json');manifest=read(R/'authored.json');evidence={v['asset'].split('.')[0]:v for file in (C/'Review/Saved').glob('*.json') if (v:=read(file))};cuffs=[]
for row in manifest['rows']:
    sha=hashlib.sha256(Path(row['file']).read_bytes()).hexdigest()
    if saved['wear'].get(row['asset'],{}).get('sha256')!=sha:raise RuntimeError('Unsaved source '+row['asset'])
    if row.get('kind') or row.get('owner'):continue
    d=read(row['file'])
    if d.get('cloth_production',{}).get('glove_tailoring')!='measured-native-strap-v1':raise RuntimeError('Untailored cuff '+row['asset'])
    check=evidence.get(row['asset'])
    if not check or check.get('source_sha256')!=sha:raise RuntimeError('Saved render cuff not read '+row['asset'])
    cuffs.append(check)
if not read(R/'artwork-saved.json')['completed']:raise RuntimeError('Artwork not saved')
gloves=read(C/'gloves-authored.json')
if not read(C/'gloves-published.json')['completed']:raise RuntimeError('Wrist gloves not published')
for row in gloves['rows']:
    sha=hashlib.sha256(Path(row['file']).read_bytes()).hexdigest();check=evidence.get(row['asset'])
    if saved['wear'].get(row['asset'],{}).get('sha256')!=sha or not check or check.get('source_sha256')!=sha:raise RuntimeError('Saved wrist glove not read '+row['rig'])
    cuffs.append(check)
record=dict(completed=True,time=datetime.now().astimezone().isoformat(),native_profiles=24,body_variants=2,garment_assets=len(manifest['rows']),saved_cuff_meshes=len(cuffs),saved_lods=sum(len(row['lods']) for row in cuffs),root_cause='Blender rest shape keys moved pinned wrist targets; glove wrist tabs also intersected old sleeve opening',repair='Fixed wrist targets; no finger weights in cuff; measured glove-tab clearance; paired cloth facing; preserved native bind and solved sleeve folds',m4_native_contact=read(C/'Review/M4-native-glove-contact.json'),gameplay_tested=False,network_tested=False,inventory_regrant=False)
record['glove_wrist_assets']=len(gloves['rows'])
(C/'published.json').write_text(json.dumps(record,ensure_ascii=False,indent=2)+'\n',encoding='utf-8');(C/'pending.json').write_text(json.dumps(dict(state='completed',receipt=str(C/'published.json')),indent=2),encoding='utf-8');print('NATIVE_CUFF_REPAIR_SAVED',len(cuffs),flush=True)
