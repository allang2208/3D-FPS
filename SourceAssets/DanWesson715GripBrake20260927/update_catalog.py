"""Install only the three requested DW715 game options in the shared catalog."""
import json
from pathlib import Path

p=Path(__file__).parents[2]/'Content/ColdSteelData/gunsmith.json'
d=json.loads(p.read_text(encoding='utf-8-sig'))
w=next(x for x in d['weapons'] if x['id']=='ue_dan_wesson715')
for slot in ['reargrip','muzzle']:
    if slot not in w['allowed']:w['allowed'].append(slot)
def option(id,name,description,stats,effects):
    return dict(id=id,name=name,description=description,effects=[dict(text=t,benefit=b) for t,b in effects],stats=stats)
reargrips=[
 option('false','原厂握把','使用 715 原厂握把。',{},[]),
 option('dw715_rubber_grip','防滑橡胶握把','细颗粒橡胶与侧面防滑纹理，保留原厂握持轮廓，便于控制连续点射。',
        {'recoil_mult':.90,'stability_mult':1.10},[('后坐力降低10%',1),('枪械稳定性提高10%',1)]),
 option('dw715_target_wood_grip','加大型靶射木握把','纵向木纹、侧面菱形格纹与加大底托，偏重稳定瞄准；较大的握把增加开镜耗时。',
        {'stability_mult':1.35,'ads_percent':.10},[('枪械稳定性提高35%',1),('开镜耗时增加10%',-1)])]
# Preserve later grip additions when regenerating this earlier production batch.
known={x['id'] for x in reargrips}
w['options']['reargrip']=reargrips+[x for x in w['options'].get('reargrip',[]) if x['id'] not in known]
w['options']['muzzle']=[
 option('false','原厂枪口','保留原厂枪口。',{},[]),
 option('dw715_muzzle_brake','左轮专用制退器','适配 715 枪口轮廓的短型金属制退器，双侧开口结构；减轻后坐，但增加前端重量和开镜耗时。',
        {'recoil_mult':.80,'ads_percent':.05},[('后坐力降低20%',1),('开镜耗时增加5%',-1)])]
for trait in w['traits']:
    if '换弹逐发退壳再逐发装填' in trait['text']:
        trait['text']='逐发装填按缺弹数补弹；六发速装器换弹会丢弃弹巢内全部余弹'
    elif '瞄具、扳机、战术挂件与装填装置全部可改造' in trait['text']:
        trait['text']='瞄具、枪口、握把、扳机、战术挂件与装填装置均可改造'
p.write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print('DW715 catalog: two grips and one muzzle brake installed')
