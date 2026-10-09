"""Scoped catalog publication, after the loader's real assets have been saved."""
import json,shutil
from pathlib import Path
O=Path(__file__).parent;P=O.parents[1]
if not json.loads((O/'import_receipt.json').read_text(encoding='utf-8'))['completed']:
    raise RuntimeError('Import and save assets before publishing this option')
path=P/'Content/ColdSteelData/gunsmith.json';backup=O/'Before/gunsmith.json'
backup.parent.mkdir(parents=True,exist_ok=True)
if not backup.exists():shutil.copy2(path,backup)
data=json.loads(path.read_text(encoding='utf-8-sig'))
weapon=next(w for w in data['weapons'] if w['id']=='ue_super90')
if 'reload_device' not in weapon['allowed']:weapon['allowed'].append('reload_device')
weapon['options']['reload_device']=[
    {'id':'false','name':'逐发装填','description':'保持枪身侧倾，逐发补入管仓；未受打断时持续补满。','effects':[],'stats':{}},
    {'id':'super90_tube_loader','name':'管式快速装填器','description':'通过装填口导向件，将装填管内的弹药连续推入管仓。右手持枪，左手完成推送与回握。','effects':[
        {'text':'成组补弹；普通换弹耗时按完整装填器动作计算','benefit':1},
        {'text':'打断时完成当前入仓弹药，随后撤回装填器','benefit':0},
        {'text':'空仓装填后释放枪机；未入仓的弹药不扣除','benefit':0}], 'stats':{}}]
path.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
(O/'catalog_receipt.json').write_text(json.dumps({'published':True,'weapon':'ue_super90','slot':'reload_device','option':'super90_tube_loader','runtime_tested':False},indent=2),encoding='utf-8')
print('SUPER90_SPEEDLOADER_CATALOG_PUBLISHED')
