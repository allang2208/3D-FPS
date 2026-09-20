"""Add the independent tactical grip to each rifle's existing underbarrel list."""
import json,re
from pathlib import Path
root=Path(__file__).resolve().parents[1]
path=root.parents[1]/'Content/ColdSteelData/gunsmith.json'
text=path.read_text(encoding='utf-8')
option={'id':'tactical_vertical_foregrip','name':'战术垂直握把',
        'description':'收颈式聚合物前握把，带侧面凹区与横向防滑纹，金属夹座适配护木下导轨。',
        'effects':[{'text':'缩短开镜耗时','benefit':1}],
        'stats':{'ads_percent':-.25}}
catalog=json.loads(text)
targets=[w['id'] for w in catalog['weapons'] if any(o['id']=='vertical_foregrip' for o in w['options'].get('underbarrel',[]))]
if 'tactical_vertical_foregrip' in text:raise RuntimeError('Already installed; do not duplicate the option')
backup=root/'Integration/Before/gunsmith.json';backup.parent.mkdir(parents=True,exist_ok=True);backup.write_text(text,encoding='utf-8')
def insert(match):
 indent=match.group(1)
 block=json.dumps(option,ensure_ascii=False,indent=2)
 return '\n'.join(indent+line for line in block.splitlines())+',\n'+match.group(0)
text=re.sub(r'(?m)^( +)\{\n\s+"id": "vertical_foregrip",',insert,text)
path.write_text(text,encoding='utf-8')
(root/'Integration/catalog_receipt.json').write_text(json.dumps({'weapon_ids':targets,'option':option,'only_requested_stat':True,'game_tested':False},ensure_ascii=False,indent=2),encoding='utf-8')
print('CATALOG_INSTALLED '+','.join(targets))
