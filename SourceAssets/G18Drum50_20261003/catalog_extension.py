"""Publish the dedicated G18 drum after its assets have been saved."""
import json
from pathlib import Path
O=Path(__file__).parent;P=O.parents[1]
ID='g18_drum_50'
def add_option(weapon):
    delta=50-int(weapon['base']['mag_size'])
    row={'id':ID,'name':'G18大弹鼓','description':'G18专属单鼓改造。长供弹颈连接厚实圆鼓，三辐端盖、周向锁扣与后壳加强筋延续黑色聚合物和发黑钢材质。',
         'effects':[{'text':f'弹匣容量增加{delta}发','benefit':1},
                    {'text':'装填耗时更长','benefit':-1},
                    {'text':'开镜耗时增加15%','benefit':-1}],
         'stats':{'mag_delta':delta,'reload_mult':1.5,'ads_percent':.15}}
    rows=weapon['options']['magazine']
    for i,old in enumerate(rows):
        if old['id']==ID:rows[i]=row;break
    else:rows.append(row)

def publish():
    receipt=json.loads((O/'import_receipt.json').read_text(encoding='utf-8'))
    if not receipt.get('complete'):raise RuntimeError('Actual asset import must finish before catalog publication')
    path=P/'Content/ColdSteelData/gunsmith.json'
    with path.open(encoding='utf-8-sig',newline='') as f:text=f.read()
    data=json.loads(text);weapon=next(w for w in data['weapons'] if w['id']=='ue_g18');add_option(weapon)
    import re
    match=re.search(r'"id"\s*:\s*"ue_g18"',text);a=text.rfind('{',0,match.start());_,length=json.JSONDecoder().raw_decode(text[a:])
    patched=text[:a]+json.dumps(weapon,ensure_ascii=False,indent=2)+text[a+length:]
    with path.open(encoding='utf-8-sig',newline='') as f:
        if f.read()!=text:raise RuntimeError('Concurrent G18 catalog edit')
    with path.open('w',encoding='utf-8',newline='') as f:f.write(patched)
    (O/'catalog_receipt.json').write_text(json.dumps({'weapon':'ue_g18','slot':'magazine','option':ID,'capacity':50,'reload_mult':1.5,'empty_reload_inherits_normal':True,'ads_percent':.15,'runtime_tested':False},indent=2))
    print('G18_DRUM50_CATALOG_SAVED',flush=True)
if __name__=='__main__':publish()
