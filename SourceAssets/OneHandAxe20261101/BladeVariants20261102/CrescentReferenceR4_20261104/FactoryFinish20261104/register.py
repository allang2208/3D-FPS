"""Publish the material description and matching shared icon after texture save."""
from pathlib import Path
import json,shutil
P=Path(__file__).resolve().parent;R4=P.parent;DATA=P.parents[4]/'Content/ColdSteelData'
saved=json.loads((P/'import_receipt.json').read_text('utf-8'))
if not saved['complete']:raise RuntimeError('Texture import has not completed')
appearance='宽月牙弧形刃面与短后钩；主体沿用原厂深灰石洗钢质感，刃口采用同源浅银磨刃，双凹刃根与柄颈连续衔接。'
for name in ['tactical-hatchet-modules.json','shared-axe-blade-options.json']:
    path=DATA/name;backup=P/'Before'/name
    if not backup.exists():shutil.copy2(path,backup)
    data=json.loads(path.read_text('utf-8-sig'))
    if name.startswith('tactical'):data['slots']['blade_1']['axe_swift_crescent']['appearance']=appearance
    else:
        for option in data['options']:
            if option['id']=='axe_swift_crescent':option['description']=option['appearance']=appearance
    path.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
jobs=json.loads((R4/'icon_deployments.json').read_text('utf-8'))
for job in jobs:
    paths=[DATA/'AttachmentIcons20260913'/(job['key']+'.png')]
    for folder in ['FramedFirearms','FramedBows']:
        extra=DATA/'AttachmentIcons20260913'/folder/(job['key']+'.png')
        if extra.exists():paths.append(extra)
    for path in paths:
        backup=P/'Before/PublishedIcons'/path.relative_to(DATA/'AttachmentIcons20260913');backup.parent.mkdir(parents=True,exist_ok=True)
        if path.exists() and not backup.exists():shutil.copy2(path,backup)
        shutil.copy2(job['source'],path)
    job['material_revision']='factory_finish_20261104';job['deployed_pngs']=[str(path) for path in paths]
(R4/'icon_deployments.json').write_text(json.dumps(jobs,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
(P/'delivery.json').write_text(json.dumps({'complete':True,'id':'axe_swift_crescent','material_revision':'factory_finish_20261104',
    'source_saved':True,'textures_saved_in_ue':len(saved['assets']),'shared_icon_deployed':True,
    'geometry_modified':False,'uv_modified':False,'stats_modified':False,'runtime_tested':False},indent=2)+'\n',encoding='utf-8')
print('CRESCENT_FACTORY_FINISH_REGISTERED',flush=True)
