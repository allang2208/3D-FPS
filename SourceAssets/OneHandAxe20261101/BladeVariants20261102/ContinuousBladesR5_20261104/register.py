"""Publish only the saved R5 heads and the three imagegen shared icons."""
import copy,json,shutil
from pathlib import Path
P=Path(__file__).resolve().parent
DATA=P.parents[3]/'Content/ColdSteelData'
saved=json.loads((P/'import_receipt.json').read_text('utf-8'))
if not saved['complete'] or len(saved['parts'])!=2 or len(saved['icons'])!=3:raise RuntimeError('R5 asset save is incomplete')
appearance={
    'axe_heavy_cleaver':'宽腹厚背向刃口连续收薄，凸弧磨刃与主体自然衔接，柄颈圆顺过渡；原厂深灰石洗钢配同源浅银刃口。',
    'axe_folded_arc':'弧形斧身向锋缘连续收薄，细弧磨刃与柄颈平顺连接；原厂深灰钢保留低对比细密钢纹，搭配同源浅银刃口。'}
def read(name):return json.loads((DATA/name).read_text('utf-8-sig'))
def write(name,value):
    path=DATA/name;backup=P/'Before'/name
    if not backup.exists():shutil.copy2(path,backup)
    temporary=path.with_name(path.name+'.r5.tmp')
    temporary.write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    temporary.replace(path)
catalog=read('tactical-hatchet-modules.json')
for entry in saved['parts']:
    spec=copy.deepcopy(catalog['slots']['blade_1'][entry['id']])
    spec.update({key:entry[key] for key in ('mesh','location_cm','material_slot_names','trace_base_cm','trace_tip_cm')})
    spec['materials']={name:entry['material'] for name in entry['material_slot_names']}
    spec['appearance']=appearance[entry['id']]
    catalog['slots']['blade_1'][entry['id']]=spec
write('tactical-hatchet-modules.json',catalog)
library=read('shared-axe-blade-options.json')
for option in library['options']:
    if option['id'] in appearance:option['description']=option['appearance']=appearance[option['id']]
write('shared-axe-blade-options.json',library)
jobs=json.loads((P/'icon_deployments.json').read_text('utf-8'))
iconroot=DATA/'AttachmentIcons20260913'
for job in jobs:
    targets=[iconroot/(job['key']+'.png')]
    for folder in ['FramedFirearms','FramedBows']:
        extra=iconroot/folder/(job['key']+'.png')
        if extra.exists():targets.append(extra)
    for target in targets:
        backup=P/'Before/PublishedIcons'/target.relative_to(iconroot);backup.parent.mkdir(parents=True,exist_ok=True)
        if target.exists() and not backup.exists():shutil.copy2(target,backup)
        shutil.copy2(job['source'],target)
    job['deployed_pngs']=[str(path) for path in targets]
(P/'icon_deployments.json').write_text(json.dumps(jobs,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
delivery={'complete':True,'ids':list(appearance),'model_revision':'continuous_forged_r5_20261104',
    'material_revision':'factory_finish_20261104','source_saved':True,'geometry_modified':True,
    'ue_saved_asset_count':len(saved['assets']),'shared_icons_deployed':[job['key'] for job in jobs],
    'icon_method':'imagegen edit from approved muzzle_brake_framed_v2 master plus actual model input',
    'stats_modified':False,'runtime_tested':False,'model_acceptance':'pending user review'}
(P/'delivery.json').write_text(json.dumps(delivery,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print('CONTINUOUS_R5_REGISTERED heads=2 icons=3',flush=True)
