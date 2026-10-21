"""Restore only the missing, previously published local warhammer body roles.

The intact pre-helmet config agrees with the production asset receipts. Do not
replace the shared config with Git HEAD or a complete old working copy.
"""
import hashlib
import json
import re
import runpy
import subprocess
from pathlib import Path

ROOT=Path('D:/FPS3D/FPSGAME')
OUT=ROOT/'Saved/WarhammerThirdPersonRestore20261020'
BASE=ROOT/'SourceAssets/SteelArmet20261019/ReferenceMatchV5/player_body-before.json'
FAMILY=ROOT/'SourceAssets/WarhammerThirdPersonSevarog20261016'
CONFIG=ROOT/'Content/ColdSteelData/player_body.json'
OUT.mkdir(parents=True,exist_ok=True)
def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def digest(b):return hashlib.sha256(b).hexdigest()

baseline=read(BASE)
roles={k:v for k,v in baseline['clips'].items() if k.startswith('Warhammer.')}
receipts={};expected={}
for stage in ('AnatomicalGripV7','RefinementV8','SourceGripV16','NaturalComboV17','Slash3AlignmentV18'):
    path=FAMILY/stage/'assets-published.json';saved=read(path)
    if not saved.get('complete') or not saved.get('published'):raise RuntimeError('Incomplete receipt: '+str(path))
    for key,value in saved['clips'].items():
        expected[key]=value;receipts[key]=str(path.relative_to(ROOT))
if len(roles)!=39 or roles!=expected:raise RuntimeError('Backup does not match the saved V7/V8/V16/V17/V18 role set')

before_bytes=CONFIG.read_bytes();text=before_bytes.decode('utf-8-sig');before=json.loads(text)
missing={k:v for k,v in roles.items() if k not in before['clips']}
conflicts={k:before['clips'][k] for k,v in roles.items() if k in before['clips'] and before['clips'][k]!=v}
if conflicts:raise RuntimeError('Existing warhammer routes changed; preserve them: '+str(conflicts))
if not missing and (OUT/'receipt.json').exists():
    print('All 39 restored roles are already present; retaining the original restore receipt.')
    raise SystemExit(0)
packages={}
for value in sorted(set(roles.values())):
    path=ROOT/'Content'/(value.split('.')[0].removeprefix('/Game/')+'.uasset')
    if not path.is_file():raise RuntimeError('Missing saved animation package: '+str(path))
    packages[value]={'path':str(path.relative_to(ROOT)),'bytes':path.stat().st_size,'sha256':digest(path.read_bytes())}

# Preserve every byte outside clips and every existing entry inside it.
match=re.search(r'"clips"\s*:\s*\{',text)
if not match:raise RuntimeError('No clips object')
start=match.end()-1;_,length=json.JSONDecoder().raw_decode(text[start:]);close=start+length-1
body=text[start+1:close];end=start+1+len(body.rstrip())
newline='\r\n' if '\r\n' in text else '\n'
addition=','+newline+(','+newline).join('    '+json.dumps(k)+': '+json.dumps(v) for k,v in missing.items())
result=text[:end]+addition+text[end:] if missing else text
after=json.loads(result)
other_before={k:v for k,v in before['clips'].items() if not k.startswith('Warhammer.')}
other_after={k:v for k,v in after['clips'].items() if not k.startswith('Warhammer.')}
assert other_after==other_before
assert {k:v for k,v in after.items() if k!='clips'}=={k:v for k,v in before.items() if k!='clips'}
assert {k:v for k,v in after['clips'].items() if k.startswith('Warhammer.')}==roles
backup=OUT/'player_body-before.json'
if missing:
    if backup.exists():raise RuntimeError('Existing restore backup; do not overwrite')
    backup.write_bytes(before_bytes)
    if CONFIG.read_bytes()!=before_bytes:raise RuntimeError('Shared config changed during preparation; retry against new contents')
    runpy.run_path(str(ROOT/'Tools/PlayerBody/config_transaction.py'))['commit'](
        CONFIG,before_bytes,result,owned_paths=[('clips',key) for key in missing],producer=__file__)
readback=read(CONFIG)
assert all(readback['clips'][k]==v for k,v in roles.items())
report={
    'restored':True,'config':str(CONFIG.relative_to(ROOT)),'baseline':str(BASE.relative_to(ROOT)),
    'head':subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
    'baseline_sha256':digest(BASE.read_bytes()),'before_sha256':digest(before_bytes),'after_sha256':digest(CONFIG.read_bytes()),
    'clips_before':len(before['clips']),'clips_after':len(after['clips']),
    'restored_role_count':len(missing),'existing_non_warhammer_roles_preserved':len(other_before),
    'roles':roles,'receipt_by_role':receipts,'saved_packages':packages,
    'non_clip_configuration_unchanged':True,'runtime_cpp_changed':False,'animation_packages_modified':False,
    'git_commit_or_push_performed':False,'editor_launched':False,'game_tested':False,
    'scope_check':'39 restored routes equal the intact backup and five production receipts; all referenced packages exist; all non-warhammer configuration preserved',
}
(OUT/'receipt.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps({k:report[k] for k in ('restored','clips_before','clips_after','restored_role_count','existing_non_warhammer_roles_preserved','non_clip_configuration_unchanged')},ensure_ascii=False))
print('saved_animation_packages',len(packages))
