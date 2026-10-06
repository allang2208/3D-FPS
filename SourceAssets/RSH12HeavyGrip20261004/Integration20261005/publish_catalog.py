"""RSH-exclusive grip body, independently combinable with surface patterns."""
import json
from pathlib import Path
O=Path(__file__).parent;P=O.parents[2]
def apply_weapon(weapon):
    if weapon.get('id')!='ue_rsh12':return
    if 'grip_body' not in weapon['allowed']:weapon['allowed'].append('grip_body')
    other_options=[o for o in weapon['options'].get('grip_body',[]) if o['id'] not in ('false','rsh12_heavy_grip')]
    weapon['options']['grip_body']=[
        dict(id='false',name='原厂握把',description='保留 RSH-12 原厂握把本体，可另选握把防滑纹。',effects=[],stats={}),
        dict(id='rsh12_heavy_grip',name='RSH 加重握把',description='RSH-12 专属。橡胶握持壳与金属配重底座，保留原握点，可搭配三种通用防滑纹。',
            effects=[dict(text='枪械稳定性提高15%',benefit=1),dict(text='后坐力降低10%',benefit=1),dict(text='开镜耗时增加5%',benefit=-1)],
            stats=dict(stability_mult=1.15,recoil_mult=.90,ads_percent=.05))]+other_options
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
    (O/'catalog_receipt.json').write_text(json.dumps(dict(weapon='ue_rsh12',slot='grip_body',options=weapon['options']['grip_body'],dual_wield='All heavy rear grip effects apply; only unsupported front grips lose benefits',runtime_tested=False),ensure_ascii=False,indent=2),encoding='utf8')
    print('RSH_HEAVY_GRIP_CATALOG_SAVED')
