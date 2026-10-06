"""Copy common grip options into RSH only; retain all other catalog bytes."""
import copy,json
from pathlib import Path
O=Path(__file__).parent;P=O.parents[1]
def apply_weapon(weapon):
    if weapon.get('id')!='ue_rsh12':return
    catalog=json.loads((P/'Content/ColdSteelData/gunsmith.json').read_text(encoding='utf8'))
    donor=next(w for w in catalog['weapons'] if w['id']=='ue_m4a1')
    weapon['options']['underbarrel']=copy.deepcopy(donor['options']['underbarrel'])
    if 'underbarrel' not in weapon['allowed']:weapon['allowed'].append('underbarrel')
    for option in weapon['options']['underbarrel']:
        option['description']=option.get('description','').replace('M4 护木','RSH-12 下导轨').replace('M4 枪身','RSH-12 枪身')
        if option['id']=='false':option['description']='拆除下导轨前握把，恢复原双手持枪姿态。'
    text='前握把：单持获得完整效果；双持保留单手握姿，仅承受前握把减益。'
    traits=weapon.setdefault('traits',[])
    if not any(t.get('text','').startswith('前握把：') for t in traits):traits.append(dict(icon='neutral',text=text))

if __name__=='__main__':
    path=P/'Content/ColdSteelData/gunsmith.json';raw=path.read_bytes();text=raw.decode('utf8');decoder=json.JSONDecoder()
    pos=text.index('[',text.index('"weapons"'))+1
    while True:
        while text[pos].isspace() or text[pos]==',':pos+=1
        weapon,end=decoder.raw_decode(text,pos)
        if weapon['id']=='ue_rsh12':break
        pos=end
    backup=O/'Before/gunsmith.json';backup.parent.mkdir(exist_ok=True)
    if not backup.exists():backup.write_bytes(raw)
    apply_weapon(weapon)
    indent=''.join(c for c in text[:pos].rsplit('\n',1)[-1] if c in ' \t')
    replacement=json.dumps(weapon,ensure_ascii=False,indent=2).replace('\n','\n'+indent)
    if path.read_bytes()!=raw:raise RuntimeError('Catalog changed during publication')
    path.write_bytes((text[:pos]+replacement+text[end:]).encode('utf8'))
    (O/'catalog_receipt.json').write_text(json.dumps(dict(weapon='ue_rsh12',options=[v['id'] for v in weapon['options']['underbarrel']],runtime_tested=False),indent=2))
    print('RSH_FOREGRIP_CATALOG_SAVED')
