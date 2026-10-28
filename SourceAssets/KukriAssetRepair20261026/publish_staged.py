"""Publish the repaired mesh packages after the project asset-use window is clear."""
import json,hashlib,shutil,os
from pathlib import Path
from datetime import datetime
P=Path(__file__).resolve().parent
receipt=json.loads((P/'repair-receipt.json').read_text(encoding='utf-8'))
if not receipt['complete']:raise RuntimeError('Staged repair is incomplete')
if receipt['published_to_game']:raise RuntimeError('Repair was already run in the game project')
packages={name.split('.')[0] for name in receipt['saved_assets']}
originals=json.loads((P/'staging-inputs.json').read_text(encoding='utf-8'))
inputs={r['source']:r for r in originals if r['package'] in packages}
jobs=[]
for original in inputs.values():
    target=Path(original['source']);staged=Path(original['staged'])
    if hashlib.sha256(target.read_bytes()).hexdigest()!=original['sha256']:
        raise RuntimeError('Game asset changed while repair was staged: '+str(target))
    if not staged.exists():raise RuntimeError('Staged output missing: '+str(staged))
    jobs.append((target,staged))
publication={'complete':False,'started':datetime.now().astimezone().isoformat(),'files':[],
             'runtime_tested':False,'numeric_changes':False}
for target,staged in jobs:
    backup=P/'Before'/target.name
    if not backup.exists():shutil.copy2(target,backup)
    temp=target.with_name(target.name+'.kukri-repair-'+str(os.getpid())+'.tmp')
    shutil.copy2(staged,temp);os.replace(temp,target)
    publication['files'].append({'target':str(target),'source':str(staged),
                                 'sha256':hashlib.sha256(staged.read_bytes()).hexdigest()})
    (P/'publication-receipt.json').write_text(json.dumps(publication,ensure_ascii=False,indent=2),encoding='utf-8')
publication['complete']=True
(P/'publication-receipt.json').write_text(json.dumps(publication,ensure_ascii=False,indent=2),encoding='utf-8')
print('KUKRI_REPAIRED_PACKAGES_PUBLISHED '+str(len(jobs)))
