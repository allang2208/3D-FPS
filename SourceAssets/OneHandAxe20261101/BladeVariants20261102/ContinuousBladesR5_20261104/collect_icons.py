"""Copy original imagegen outputs unchanged and record the shared icon inputs."""
from pathlib import Path
import json,shutil
P=Path(__file__).resolve().parent
jobs=json.loads((P/'icon_jobs.json').read_text('utf-8'))
names=['exec-edcdf8e6-762e-4471-b78e-0c87e5b80361.png','exec-a6cf57e6-ec5c-408e-9d90-6ad3fd74892d.png','exec-0bf844ee-1574-4550-be6c-988f3c9d59cb.png']
generated=Path('C:/Users/allan/.codex/generated_images/01a195a9-36a2-73c3-b35d-e1ea19859acf')
for job,name in zip(jobs,names):
    original=generated/name
    Path(job['source']).parent.mkdir(parents=True,exist_ok=True)
    shutil.copy2(original,job['source'])
    job['generated_original']=str(original)
    job['icon_revision']='approved_master_imagegen_r5_20261104'
(P/'icon_deployments.json').write_text(json.dumps(jobs,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print('IMAGEGEN_ICONS_COLLECTED count='+str(len(jobs)))
