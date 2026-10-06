"""Publish only the RSH optic choices after the saved asset import completes."""
import copy,json,re,runpy
from pathlib import Path
O=Path(__file__).parent;P=O.parents[1]
receipt=json.loads((O/'import_receipt.json').read_text(encoding='utf8'))
if not receipt.get('complete'):raise RuntimeError('Optic assets have not finished saving')
path=P/'Content/ColdSteelData/gunsmith.json';before=path.read_text(encoding='utf-8-sig')
catalog=json.loads(before);donor=next(w for w in catalog['weapons'] if w['id']=='ue_m4a1')
keys=['holographic','panoramic_red_dot','prism_scope_2x','lpvo_1_6x','eoth_holographic']
decoder=json.JSONDecoder();pos=before.index('[',before.index('"weapons"'))+1
while True:
    while before[pos].isspace() or before[pos]==',':pos+=1
    value,end=decoder.raw_decode(before,pos)
    if value['id']=='ue_rsh12':break
    pos=end
options=copy.deepcopy([next(x for x in donor['options']['optic'] if x['id']==key) for key in keys])
for option in options:
    if option['id']=='holographic':option['description']='安装在 RSH-12 上导轨的全息瞄具，保留 1× 视野。'
value['options']['optic']=[o for o in value['options']['optic'] if o['id'] not in keys]+options
indent=re.search(r'[^\S\n]*$',before[:pos]).group()
replacement=json.dumps(value,ensure_ascii=False,indent=2).replace('\n','\n'+indent)
after=before[:pos]+replacement+before[end:]
if path.read_text(encoding='utf-8-sig')!=before:raise RuntimeError('Catalog changed during RSH publication')
backup=O/'BeforeCatalog/gunsmith.json';backup.parent.mkdir(exist_ok=True)
if not backup.exists():backup.write_text(before,encoding='utf8')
path.write_text(after,encoding='utf8')
(O/'catalog_receipt.json').write_text(json.dumps(dict(weapon='ue_rsh12',options=keys,shared_icons=True,runtime_tested=False),indent=2))
print('RSH_OPTIC_CATALOG_SAVED',','.join(keys))
compact=O.parent/'RSH12CompactOptics20261004'
if (compact/'import_receipt.json').exists() and json.loads((compact/'import_receipt.json').read_text(encoding='utf8')).get('complete'):
    runpy.run_path(str(compact/'publish_catalog.py'),run_name='__main__')
