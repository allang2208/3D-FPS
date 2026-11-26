"""Promote complete cuff sources into the existing outfit revision."""
import json,shutil,hashlib
from pathlib import Path
from datetime import datetime
P=Path('D:/FPS3D/FPSGAME');R=P/'SourceAssets/ModernTacticalSet20261113/CombatShirtR3';C=R/'CuffRepairR1'
def read(p):return json.loads(Path(p).read_text(encoding='utf-8-sig'))
def write(p,d):Path(p).write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
expected={r['rig'] for r in read(R/'fp-authored.json')['rows']};fp={}
for file in C.glob('fp-batch-*.json'):
    for row in read(file)['rows']:
        if row['rig'] in fp:raise RuntimeError('Duplicate native cuff '+row['rig'])
        fp[row['rig']]=row
if set(fp)!=expected:raise RuntimeError('Native cuffs still pending: '+str(expected-set(fp)))
for rig,row in fp.items():
    if read(row['file']).get('cloth_production',{}).get('glove_tailoring')!='measured-native-strap-v1':raise RuntimeError('Glove tailoring pending: '+rig)
world=read(C/'authored-world.json')['rows']
if len(world)!=36:raise RuntimeError('Expected 36 upper-body variants')
anchors={}
for name in ['FP_'+rig for rig in expected]+['Shirt_Jason','Shirt_Kaitlin']:
    evidence=read(C/'Review'/(name+'-anchors.json'))
    if evidence['max_anchor_drift_cm']>.001 or evidence['rest_shape_key']:raise RuntimeError('Native cuff anchor failed '+name)
    anchors[name]=evidence
rows=world+list(fp.values());files={Path(row['file']) for row in rows}
gloves=read(C/'gloves-authored.json')
if not gloves['completed'] or len(gloves['rows'])!=26:raise RuntimeError('Native glove wrist fits incomplete')
files.update(Path(row['file']) for row in gloves['rows'])
for rig in ['Jason','Kaitlin']:
    for stem in ['shirt_cloth','shirt_detail','neck_skin']:files.add(C/'Authored'/f'{stem}_{rig}.json')
for name in ['outfit_display_Jason.json','pickup.json']:files.add(C/'Authored'/name)
art=read(C/'artwork.json')
backups=C/'Before/Authored';backups.mkdir(parents=True,exist_ok=True);promoted=[]
for file in sorted(files):
    target=R/'Authored'/file.name
    if target.exists() and not (backups/file.name).exists():shutil.copy2(target,backups/file.name)
    if file.resolve()!=target.resolve():shutil.copy2(file,target)
    promoted.append(dict(file=str(target),sha256=hashlib.sha256(target.read_bytes()).hexdigest()))
for row in fp.values():row['file']=str(R/'Authored'/Path(row['file']).name)
for row in gloves['rows']:row['file']=str(R/'Authored'/Path(row['file']).name)
write(C/'gloves-authored.json',gloves)
for folder in ['Models','Exports','Icons']:
    for file in (C/folder).iterdir():
        if not file.is_file() or file.suffix=='.blend1':continue
        target=R/folder/file.name;backup=C/'Before'/folder/file.name;backup.parent.mkdir(parents=True,exist_ok=True)
        if target.exists() and not backup.exists():shutil.copy2(target,backup)
        shutil.copy2(file,target)
def relocate(value):
    if isinstance(value,str):return value.replace(str(C),str(R)).replace(C.as_posix(),R.as_posix())
    if isinstance(value,list):return [relocate(v) for v in value]
    if isinstance(value,dict):return {k:relocate(v) for k,v in value.items()}
    return value
write(R/'artwork.json',relocate(art))
write(R/'fp-authored.json',dict(completed=True,rows=list(fp.values()),cuff_revision='CuffRepairR1'))
write(C/'promoted.json',dict(completed=True,time=datetime.now().astimezone().isoformat(),sources=promoted,native_profiles=len(fp),upper_variants=len(world),anchors=anchors,gameplay_tested=False))
print('CUFF_SOURCES_PROMOTED',len(promoted),flush=True)
