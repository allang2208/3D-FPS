"""Merge blade options, including the approved author-library stats, after asset save."""
import copy,json,shutil
from pathlib import Path
P=Path(__file__).resolve().parent
DATA=P.parents[1]/'Content/ColdSteelData'
variants=json.loads((P/'variants.json').read_text(encoding='utf-8'))['variants']
receipt=json.loads((P/'import_receipt.json').read_text(encoding='utf-8'))
if not receipt['complete']:raise RuntimeError('Complete asset import before publishing options')
descriptions={
 'swift_blade':'窄弧刀身配连续浅槽，石墨灰刀面衔接银色刃口。',
 'heavy_back_blade':'宽腹刀身与厚实脊面，深灰锻面衔接宽银色刃口。',
 'folded_balanced_blade':'平顺弧腹配银灰百炼流纹，保留素面刃口。'}
library_name='shared-knife-blade-options.json'
authored={o['id']:o for o in json.loads((P/library_name).read_text(encoding='utf-8-sig'))['options']}
library={'version':1,'family':'knife_blade','options':[]}
for v in variants:
    library['options'].append({'id':v['id'],'name':v['name'],'description':descriptions[v['id']],
        'appearance':descriptions[v['id']],'effects':copy.deepcopy(authored[v['id']].get('effects',[])),
        'stats':copy.deepcopy(authored[v['id']].get('stats',{}))})
library_path=DATA/library_name
if library_path.exists():
    existing=json.loads(library_path.read_text(encoding='utf-8-sig'))
    owned={v['id'] for v in variants}
    existing['options']=[o for o in existing.get('options',[]) if o.get('id') not in owned]+library['options']
    library=existing

# Fresh read/field merge preserves current options, runes and other concurrent work.
menu_path=DATA/'kukri-gunsmith.json'
menu=json.loads(menu_path.read_text(encoding='utf-8-sig'))
column=next(c for c in menu['columns'] if c['key']=='blade_1')
if column.get('options_library') not in (None,library_name):
    owned={v['id'] for v in variants}
    column['options']=[o for o in column.get('options',[]) if o.get('id') not in owned]+library['options']
else:
    column['options_library']=library_name

assembly_path=DATA/'kukri-modules.json'
assembly=json.loads(assembly_path.read_text(encoding='utf-8-sig'))
factory=assembly['slots']['blade_1']['factory']
for v in variants:
    previous=assembly['slots']['blade_1'].get(v['id'],{})
    spec=copy.deepcopy(factory)
    spec['mesh']=v['mesh'];spec['appearance']=descriptions[v['id']]
    # Assembly only owns trace/placement; gameplay modifiers belong to the shared option library.
    spec.pop('materials',None)
    spec.pop('material_slot_names',None)
    for field in ('materials','material_slot_names'):
        if field in previous:spec[field]=previous[field]
    assembly['slots']['blade_1'][v['id']]=spec

before=P/'Before';before.mkdir(exist_ok=True)
for name,value in [(library_name,library),('kukri-gunsmith.json',menu),('kukri-modules.json',assembly)]:
    target=DATA/name
    if target.exists() and not (before/name).exists():shutil.copy2(target,before/name)
    text=json.dumps(value,ensure_ascii=False,indent=2)+'\n'
    (P/name).write_text(text,encoding='utf-8');target.write_text(text,encoding='utf-8')
jobs=[]
for v in variants:
    dest=DATA/'AttachmentIcons20260913'/(v['icon_key']+'.png')
    shutil.copy2(v['icon'],dest)
    jobs.append({'id':v['id'],'key':v['icon_key'],'source':v['icon'],'runtime_png':str(dest)})
(P/'publication_receipt.json').write_text(json.dumps({'complete':True,'options_library':library_name,
    'weapon':'ue_kukri','slot':'blade_1','ids':[v['id'] for v in variants],'stats_authored':True,
    'icons':jobs,'runtime_tested':False},ensure_ascii=False,indent=2),encoding='utf-8')
print('KUKRI_VARIANTS_PUBLISHED: '+', '.join(v['name'] for v in variants))
