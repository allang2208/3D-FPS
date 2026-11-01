import json,shutil
from pathlib import Path
from catalog import apply,ID
O=Path(__file__).resolve().parent;P=O.parents[1]
if not json.loads((O/'install_receipt.json').read_text())['complete']:raise RuntimeError('Bipod assets not saved')
path=P/'Content/ColdSteelData/gunsmith.json';before=path.read_bytes();data=json.loads(before)
apply(next(row for row in data['weapons'] if row['id']=='ue_m24'))
backup=O/'gunsmith-before.json'
if not backup.exists():backup.write_bytes(before)
if path.read_bytes()!=before:raise RuntimeError('Concurrent gunsmith change retained')
path.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
icons=P/'Content/ColdSteelData/AttachmentIcons20260913';framed=icons/'FramedFirearms'
for folder in (icons,framed):
    source=folder/'ue_pkm_lowpoly_bipod_pkm_bipod.png'
    if not source.exists():source=folder/'bipod_pkm_bipod.png'
    if source.exists():
        for name in ('bipod_'+ID,'ue_m24_bipod_'+ID):shutil.copy2(source,folder/(name+'.png'))
    category=folder/'category_bipod.png'
    if not category.exists():category=folder/'ue_pkm_lowpoly_category_bipod.png'
    if category.exists():shutil.copy2(category,folder/'ue_m24_category_bipod.png')
(O/'catalog_receipt.json').write_text(json.dumps({'complete':True,'part':ID,'default_installed':False,'icon_source':'PKM approved bipod icon','runtime_tested':False},indent=2))
print('M24_BIPOD_CATALOG_SAVED')
