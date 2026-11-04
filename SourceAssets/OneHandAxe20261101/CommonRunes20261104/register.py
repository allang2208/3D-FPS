"""Register a surface-only slot from the existing shared one-handed rune library."""
from pathlib import Path
import json,shutil
P=Path(__file__).resolve().parent;DATA=P.parents[2]/'Content/ColdSteelData'
receipt=json.loads((P/'import_receipt.json').read_text('utf-8'))
if not receipt['complete']:raise RuntimeError('Rune assets have not finished saving')
shared=json.loads((DATA/'shared-knife-component-options.json').read_text('utf-8'))
runes=next(c['options'] for c in shared['columns'] if c['key']=='blade_2')
def read(name):return json.loads((DATA/name).read_text('utf-8-sig'))
def write(name,data):
    path=DATA/name;backup=P/'Before'/name
    if not backup.exists():shutil.copy2(path,backup)
    temp=path.with_name(path.name+'.hatchet-runes.tmp')
    temp.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8');temp.replace(path)
catalog=read('tactical-hatchet-modules.json')
catalog['slots']['blade_1']['factory'].update(receipt['factory_carrier'])
for head in receipt['heads']:catalog['slots']['blade_1'][head['id']]['rune_surface_revision']='isometric-head-uv0-v1'
slot=catalog['slots'].setdefault('blade_2',{})
slot['factory']={'appearance':'保留原有斧面钢材，不添加额外符文。'}
for rune in runes:
    appearance=rune.get('appearance',rune['description']).replace('刀面','斧面')
    slot[rune['id']]={'appearance':appearance,'surface_materials':receipt['rune_surfaces'][rune['id']]}
# Surface-only slot: it must never become an extra physical module.
write('tactical-hatchet-modules.json',catalog)
gunsmith=read('tactical-hatchet-gunsmith.json')
column=next((c for c in gunsmith['columns'] if c['key']=='blade_2'),None)
if column is None:
    column={'key':'blade_2','options':[]}
    position=next(i for i,c in enumerate(gunsmith['columns']) if c['key']=='blade_1')+1
    gunsmith['columns'].insert(position,column)
column.update(name='斧面符文',default='无附加符文',description='保留斧头主体钢材，不添加额外符文。',
    options_library='shared-knife-component-options.json',options_column='blade_2')
write('tactical-hatchet-gunsmith.json',gunsmith)
delivery={'complete':True,'slot':'blade_2','label':'斧面符文','rune_ids':[r['id'] for r in runes],
    'head_ids':[h['id'] for h in receipt['heads']],'saved_asset_count':len(receipt['saved_assets']),
    'shared_stats_and_icons_reused':True,'native_code_changed':False,'runtime_tested':False,'editor_ui_started':False,
    'projection':'isometric local centimetres; per-head UV0; same orientation from either side',
    'scope':'head body only; factory head unique material slot excludes grip and pommel'}
(P/'delivery.json').write_text(json.dumps(delivery,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print('HATCHET_COMMON_RUNES_REGISTERED heads=5 runes=3')
