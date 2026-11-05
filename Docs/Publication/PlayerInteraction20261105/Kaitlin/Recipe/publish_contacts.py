"""Install new packages, then update only the 56 female weapon motion roles."""
import hashlib,json,runpy,shutil
from pathlib import Path
import tempfile
import os

P=Path(os.environ['FPSGAME_PROJECT']).resolve()
W=Path(__file__).resolve().parent
H=Path(tempfile.gettempdir())/'KaitlinWeaponContacts20261024/AuthorHost'
DEST=P/'SourceAssets/KaitlinWeaponContacts20261024/ContactFitV1'
read=lambda p:json.loads(p.read_text(encoding='utf-8-sig'))
digest=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
saved=read(W/'saved_assets.json')
report=read(W/'saved_contact_report.json')
plan=read(W/'selected.json')
if set(saved)!=set(plan) or set(report)!=set(saved):raise RuntimeError('Incomplete saved motion set')
config=P/'Content/ColdSteelData/player_body.json'
before=config.read_bytes();candidate=json.loads(before.decode('utf-8-sig'))
owned=[]
for key,row in saved.items():
    for role in row['roles']:
        if candidate['clips'][role]!=row['male']:raise RuntimeError('Male source role changed: '+role)
        if candidate['body_variants']['kaitlin']['clips'][role] not in (row['previous'],row['asset']):
            raise RuntimeError('Female role changed during authoring: '+role)
        owned.append(('body_variants','kaitlin','clips',role))
    for path in (row['male'],row['previous']):
        rel=Path(path.split('.')[0][6:]+'.uasset')
        if digest(P/'Content'/rel)!=digest(H/'Content'/rel):raise RuntimeError('Saved source changed during authoring: '+path)
installed=[]
for row in saved.values():
    rel=Path(row['asset'].split('.')[0][6:]+'.uasset')
    if not str(rel).replace('\\','/').startswith('Characters/KaitlinPlayer20261023/WeaponContacts20261024/Animations/'):
        raise RuntimeError('Unexpected destination')
    source=H/'Content'/rel;target=P/'Content'/rel
    target.parent.mkdir(parents=True,exist_ok=True)
    if target.exists():
        if digest(target)!=digest(source):raise RuntimeError('Destination already has a different revision: '+str(target))
    else:shutil.copy2(source,target)
    installed.append({'path':str(target),'sha256':digest(target),'bytes':target.stat().st_size})
    for role in row['roles']:candidate['body_variants']['kaitlin']['clips'][role]=row['asset']
commit=runpy.run_path(str(P/'Tools/PlayerBody/config_transaction.py'))['commit']
receipt=commit(config,before,candidate,owned_paths=owned,producer=str(__file__))
publication={'complete':True,'assets':len(installed),'roles':len(owned),'installed':installed,
             'configuration_receipt':receipt,'male_roles_modified':False,'runtime_tested':False,
             'preview_rendered':False,'native_code_changed':False,'cook_root':'/Game/Characters/KaitlinPlayer20261023'}
(W/'published.json').write_text(json.dumps(publication,indent=2,ensure_ascii=False),encoding='utf-8')
DEST.mkdir(parents=True,exist_ok=True)
for path in W.iterdir():
    if path.is_file() and path.suffix in ('.py','.json'):
        target=DEST/path.name
        if path.resolve()!=target.resolve():shutil.copy2(path,target)
for folder in ('Captured','Tracks','Authored'):
    (DEST/folder).mkdir(exist_ok=True)
    for path in (W/folder).iterdir():
        if path.is_file():shutil.copy2(path,DEST/folder/path.name)
print('FEMALE_WEAPON_CONTACTS_PUBLISHED',len(installed),'assets',len(owned),'roles')
