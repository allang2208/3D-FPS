"""Requested publication checks against the isolated staged tree; no engine/tests."""
import json
import os
from pathlib import Path, PurePosixPath
import posixpath
import re
import subprocess

P=Path(__file__).resolve().parents[2]
O=P/'Saved/WeaponAccessoriesPublication20261006'
ENV=dict(os.environ,GIT_INDEX_FILE=str(O/'publication.index'))
def git(*args):
    return subprocess.check_output(['git',*args],cwd=P,env=ENV)
manifest=json.loads((P/'SourceAssets/WeaponAccessoriesPublication20261006/published-files.json').read_text(encoding='utf-8'))
base=manifest['base']
subprocess.run(['git','diff','--cached','--check',base],cwd=P,env=ENV,check=True)
paths=git('diff','--cached','--name-only',base).decode().splitlines()
expected={r['path'] for r in manifest['files']}|{'SourceAssets/WeaponAccessoriesPublication20261006/published-files.json'}
assert set(paths)==expected, 'Unexpected staged paths'
tracked=set(git('ls-files').decode().splitlines())
errors=[];sizes=[];relative_includes=0
secrets=[r'-----BEGIN (?:RSA |OPENSSH |EC )?PRIVATE KEY-----',r'gh[pousr]_[A-Za-z0-9]{30,}',
         r'github_pat_[A-Za-z0-9_]{40,}',r'AKIA[A-Z0-9]{16}',r'sk-(?:proj-)?[A-Za-z0-9_-]{32,}',
         r'(?i)(?:api[_-]?key|client_secret|access_token|password)\s*[=:]\s*["\'][A-Za-z0-9_./+=-]{24,}["\']']
for path in paths:
    data=git('show',':'+path);text=data.decode('utf-8-sig')
    sizes.append((len(data),path))
    if len(data)>2*1024*1024 or b'\x00' in data:errors.append((path,'large or binary payload'))
    if PurePosixPath(path).suffix not in ('.cpp','.h','.json','.py','.ps1','.md','.hlsl','.ini') and path!='.gitignore':
        errors.append((path,'unexpected file type'))
    for pattern in secrets:
        if re.search(pattern,text):errors.append((path,'possible credential; content withheld'))
    if re.search(r'^(?:<<<<<<< |=======\s*$|>>>>>>> )',text,re.M):errors.append((path,'conflict marker'))
    if path.endswith(('.h','.cpp')):
        for include in re.findall(r'^#include "([^"]+)"',text,re.M):
            if include.startswith('../'):
                relative_includes+=1
                target=posixpath.normpath(posixpath.join(posixpath.dirname(path),include))
                if target not in tracked:errors.append((path,'unpublished local include '+target))
    if path.startswith('Source/FPSGAME/'):
        patch=git('diff','--cached','--unified=0',base,'--',path).decode()
        additions='\n'.join(s[1:] for s in patch.splitlines() if s.startswith('+') and not s.startswith('+++'))
        if any(s in additions for s in ('Super90','BoundCongregate','ue_xuanchi_zhenyue','ResolveWorldWeaponPart')):
            errors.append((path,'unrelated feature in staged additions'))

catalog=json.loads(git('show',':Content/ColdSteelData/gunsmith.json'))
original=json.loads(git('show',base+':Content/ColdSteelData/gunsmith.json'))
weapons=[]
for weapon in catalog['weapons']:
    options=weapon['options'].get('stock',[])
    installed=[v for v in options if v['id']=='legendary_adjustable_tactical_stock']
    if installed:
        weapons.append(weapon['id'])
        assert len(installed)==1 and installed[0]['stats']==dict(recoil_mult=.65,stability_mult=1.3,ads_percent=-.1,hip_spread_mult=1.15)
        weapon['options']['stock']=[v for v in options if v['id']!='legendary_adjustable_tactical_stock']
assert len(weapons)==9
common=catalog.pop('common_options')
assert common['tactical'][0]['id']=='blessed_laser'
assert common['tactical'][0]['stats']==dict(hip_spread_mult=.2,ads_percent=-.3,recoil_mult=1.15,stability_mult=.85)
if 'common_options' in original:catalog['common_options']=original['common_options']
assert catalog==original, 'Unrelated catalog changes'
assert not any(path.startswith(('Content/Weapons/','trash/','Binaries/')) for path in paths)
report=dict(base=base,files=len(paths),bytes=sum(n for n,p in sizes),largest=sorted(sizes,reverse=True)[:5],
            relative_includes=relative_includes,stock_weapons=weapons,errors=errors,
            engine_started=False,game_tests_run=False,license_scope='source recipes and small authored parameters; binaries retained locally')
(O/'review.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(report,ensure_ascii=False))
if errors:raise SystemExit(1)
