"""Copy generated media from tool-returned local paths into this production folder."""
import json,shutil
from pathlib import Path
P=Path(__file__).resolve().parent
jobs=json.loads((P/'imagegen-receipt.json').read_text(encoding='utf-8'))
for job in jobs:
    if job.get('generated_file'):
        target=P/'Generated'/(job['id']+'.png')
        if not target.exists():shutil.copy2(job['generated_file'],target)
print('KUKRI_GENERATED_MASTERS_RETAINED '+str(sum(bool(j.get('generated_file')) for j in jobs)))
