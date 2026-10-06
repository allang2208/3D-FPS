"""Publish only this RSH exclusive option, retaining the current ASH numeric baseline."""
import copy,json,re
from pathlib import Path
O=Path(__file__).resolve().parent;P=O.parents[1]
if not json.loads((O/'import_receipt.json').read_text(encoding='utf8')).get('complete'):
    raise RuntimeError('Model import not complete')
icon=json.loads((O/'icon_receipt.json').read_text(encoding='utf8'))
path=P/'Content/ColdSteelData/gunsmith.json';before=path.read_text(encoding='utf-8-sig')
catalog=json.loads(before)
donor=next(w for w in catalog['weapons'] if w['id']=='ue_ash12')
option=copy.deepcopy(next(o for o in donor['options']['muzzle'] if o['id']=='ash12_tactical_suppressor'))
option.update(id='rsh12_heavy_suppressor',name='RSH 大口径消音器',
    description='RSH-12 专属短粗型消音器，带纵向凹槽与斜纹钛色套环，贴合下置枪管，抑制枪声和枪口火光。')
cube=O.parent/'RSH12CubeSuppressor20261004'
if (cube/'catalog_receipt.json').exists():
    import importlib.util
    spec=importlib.util.spec_from_file_location('rsh12_cube_catalog',cube/'publish_catalog.py')
    cube_module=importlib.util.module_from_spec(spec);spec.loader.exec_module(cube_module)
    option['description']=cube_module.DESCRIPTION
decoder=json.JSONDecoder();position=before.index('[',before.index('"weapons"'))+1
while True:
    while before[position].isspace() or before[position]==',':position+=1
    weapon,end=decoder.raw_decode(before,position)
    if weapon['id']=='ue_rsh12':break
    position=end
weapon['options']['muzzle']=[o for o in weapon['options']['muzzle'] if o['id']!=option['id']]+[option]
indent=re.search(r'[^\S\n]*$',before[:position]).group()
replacement=json.dumps(weapon,ensure_ascii=False,indent=2).replace('\n','\n'+indent)
if path.read_text(encoding='utf-8-sig')!=before:raise RuntimeError('Catalog changed while preparing RSH entry')
backup=O/'Before/gunsmith.json';backup.parent.mkdir(exist_ok=True)
if not backup.exists():backup.write_text(before,encoding='utf8')
path.write_text(before[:position]+replacement+before[end:],encoding='utf8')
(O/'catalog_receipt.json').write_text(json.dumps(dict(weapon='ue_rsh12',option=option,baseline='ue_ash12/ash12_tactical_suppressor',icon=icon['texture'],runtime_tested=False),ensure_ascii=False,indent=2),encoding='utf8')
print('RSH_HEAVY_SUPPRESSOR_CATALOG_SAVED')
