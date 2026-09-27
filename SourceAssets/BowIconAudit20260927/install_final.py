"""Preserve the first deployment receipt and apply the rest-material refinement."""
import hashlib,json,shutil
from pathlib import Path
P=Path(__file__).resolve().parent
receipt=json.loads((P/'icon-install-receipt.json').read_text(encoding='utf8'))
changed=[]
for row in receipt['pngs']:
    target=Path(row['png']);source=P/'Icons'/(row['name']+'.png')
    digest=hashlib.sha256(source.read_bytes()).hexdigest()
    if digest==row['sha256']:continue
    if hashlib.sha256(target.read_bytes()).hexdigest()!=row['sha256']:raise RuntimeError('Concurrent change '+str(target))
    changed.append(row['name']);shutil.copy2(source,target);row['sha256']=digest
receipt['refinement']='Restore current UE carved-wood PBR on the two arrow rests before grayscale conversion'
receipt['refined_pngs']=changed
(P/'icon-install-final-receipt.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2),encoding='utf8')
print('BOW_ICON_FINAL_DEPLOYMENT',len(receipt['pngs']),'rest refinements',len(changed))
