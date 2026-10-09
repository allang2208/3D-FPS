"""Publish only this loader's duration and description after real asset saves."""
import json,shutil
from pathlib import Path
O=Path(__file__).parent;P=O.parents[1]
receipt=json.loads((O/'import_receipt.json').read_text(encoding='utf-8'))
if not receipt.get('completed') or receipt.get('revision')!='OpenPalmFlowR6-20261008':
    raise RuntimeError('Save R6 animations, props and grip profiles before publishing timing')
path=P/'Content/ColdSteelData/gunsmith.json'
data=json.loads(path.read_text(encoding='utf-8-sig'))
weapon=next(w for w in data['weapons'] if w['id']=='ue_super90')
option=next(v for v in weapon['options']['reload_device'] if v['id']=='super90_tube_loader')
option['description']='通过装填口导向件成组补弹。左手推送到位后张掌回握，装填管与推杆脱手下落。'
option.setdefault('stats',{})['reload_mult']=1.3/.85
option['stats']['empty_reload_mult']=1.3/.85
for effect in option.get('effects',[]):
    if '打断时完成当前入仓弹药' in effect.get('text',''):
        effect['text']='打断时完成当前入仓弹药，随后释放装填器并回握'
path.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
(O/'catalog_receipt.json').write_text(json.dumps({
    'published':True,'weapon':'ue_super90','option':'super90_tube_loader',
    'previous_default_rate':1.3,'default_rate':.85,'duration_multiplier':1.3/.85,
    'normal_full_duration':146/60/.85,'empty_full_duration':182/60/.85,
    'runtime_tested':False},indent=2),encoding='utf-8')
print('SUPER90_R6_TIMING_PUBLISHED')
