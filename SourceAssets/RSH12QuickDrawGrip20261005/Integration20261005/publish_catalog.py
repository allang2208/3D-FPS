"""Publish only the RSH quick-draw rear grip, preserving existing options."""
import json
from pathlib import Path
O=Path(__file__).parent;P=O.parents[2]

def apply_weapon(weapon):
    if weapon.get('id')!='ue_rsh12':return
    option=dict(id='rsh12_quickdraw_grip',name='RSH 轻型快拔握把',
        description='RSH-12 专属。轻薄框体、内收圆角短尾与防滑掌面，保留原握持接口，可搭配三种通用防滑纹。',
        effects=[dict(text='拔出速度提高100%',benefit=1),dict(text='开镜耗时降低20%',benefit=1),dict(text='后坐力增加5%',benefit=-1)],
        stats=dict(equip_speed_bonus=1.,ads_percent=-.20,recoil_mult=1.05))
    if 'grip_body' not in weapon['allowed']:weapon['allowed'].append('grip_body')
    options=weapon['options'].setdefault('grip_body',[])
    for i,current in enumerate(options):
        if current['id']==option['id']:options[i]=option;break
    else:options.append(option)

if __name__=='__main__':
    if not json.loads((O/'import_receipt.json').read_text())['complete']:raise RuntimeError('Save assets before publication')
    path=P/'Content/ColdSteelData/gunsmith.json';raw=path.read_bytes();text=raw.decode('utf8');decoder=json.JSONDecoder()
    pos=text.index('[',text.index('"weapons"'))+1
    while True:
        while text[pos].isspace() or text[pos]==',':pos+=1
        weapon,end=decoder.raw_decode(text,pos)
        if weapon['id']=='ue_rsh12':break
        pos=end
    apply_weapon(weapon);indent=''.join(c for c in text[:pos].rsplit('\n',1)[-1] if c in ' \t')
    replacement=json.dumps(weapon,ensure_ascii=False,indent=2).replace('\n','\n'+indent)
    backup=O/'Before/gunsmith.json';backup.parent.mkdir(exist_ok=True)
    if not backup.exists():backup.write_bytes(raw)
    if path.read_bytes()!=raw:raise RuntimeError('Concurrent catalog edit')
    path.write_bytes((text[:pos]+replacement+text[end:]).encode('utf8'))
    (O/'catalog_receipt.json').write_text(json.dumps(dict(weapon='ue_rsh12',slot='grip_body',options=weapon['options']['grip_body'],
        equip_speed_semantics='duration / (1 + equip_speed_bonus); 100% bonus = 2x rate',
        dual_wield='Each hand uses its own installed grip; rear-grip effects remain active',runtime_tested=False),ensure_ascii=False,indent=2),encoding='utf8')
    print('RSH_QUICKDRAW_GRIP_CATALOG_SAVED')
