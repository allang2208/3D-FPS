"""Publish the exclusive pommel and its existing data-driven save identity."""
import json,os,shutil
from pathlib import Path
P=Path(__file__).resolve().parent;ROOT=P.parents[2]
saved=json.loads((P/'import_receipt.json').read_text('utf-8'))
if not saved.get('complete'):raise RuntimeError('Save pommel assets first')
option={'id':'empowered_mana_orb','name':'强化魔力球','tier':'special','weapons':['ue_runebound_warhammer'],
    'description':'符文战锤专属。外露紫晶球由黑银雕刻护爪托持，球内能量云、流光与微粒围绕魔力核心旋转。',
    'appearance':'外露紫晶球 · 雕刻黑银护爪 · 内部魔力旋流','stats':{},'effects':[],
    'special_effects':['延续苏醒｜符文苏醒持续时间增加10秒，由20秒延长至30秒。']}
spec={'mesh':saved['mesh'],'location_cm':[0.,0.,-8.5],'appearance':option['appearance'],
    'interface':'runebound_warhammer_modular_v1','exclusive_to':'ue_runebound_warhammer','model_revision':'ManaOrbPommelV2','materials':saved['materials']}
writes=[]
for relative,kind in [('Content/ColdSteelData/runebound-warhammer-modules.json','model'),
    ('SourceAssets/RuneboundWarhammer20261022/ModulesV1/catalog_base.json','model'),
    ('Content/ColdSteelData/runebound-warhammer-gunsmith.json','bench'),
    ('SourceAssets/RuneboundWarhammer20261022/ModulesV1/workbench.json','bench')]:
    file=ROOT/relative;before=file.read_bytes();value=json.loads(before.decode('utf-8-sig'))
    if kind=='model':value['slots']['pommel'][option['id']]=spec
    else:
        column=next(c for c in value['columns'] if c['key']=='pommel')
        column['options']=[o for o in column.get('options',[]) if o['id']!=option['id']]+[option]
        for trait in value.get('traits',[]):
            trait['text']=trait['text'].replace('蓄满后自动激活20秒','蓄满后自动激活，基础持续20秒，强化魔力球可延长10秒')
        for c in value['columns']:
            for o in c.get('options',[]):
                if o.get('id')=='destruction_mana_rune':o['special_effects']=[s.replace('持续20秒','基础持续20秒，可由强化魔力球延长') for s in o.get('special_effects',[])]
    backup=P/'Before'/relative;backup.parent.mkdir(parents=True,exist_ok=True)
    if not backup.exists():backup.write_bytes(before)
    if file.read_bytes()!=before:raise RuntimeError('Concurrent catalog write '+relative)
    tmp=file.with_suffix('.mana-orb.tmp');tmp.write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    if file.read_bytes()!=before:raise RuntimeError('Concurrent catalog write before commit '+relative)
    os.replace(tmp,file);writes.append(relative)
icon='ue_runebound_warhammer_pommel_empowered_mana_orb.png'
shutil.copy2(P/icon,ROOT/'Content/ColdSteelData/AttachmentIcons20260913'/icon)
(P/'published.json').write_text(json.dumps({'complete':True,'catalogs':writes,'icon':icon,'saved_assets':saved['assets'],
    'duration_seconds':30,'base_duration_seconds':20,'tested':False},ensure_ascii=False,indent=2),encoding='utf-8')
design_path=P.parent/'ManaOrbPommelConceptV2/design.json'
design=json.loads(design_path.read_text('utf-8'))
design.update(status='approved_design_modeled_and_integrated',model_authored=True,runtime_integrated=True,model_revision='ManaOrbPommelV2',user_runtime_acceptance=False)
design_path.write_text(json.dumps(design,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print('Exclusive purple mana-orb pommel published')
