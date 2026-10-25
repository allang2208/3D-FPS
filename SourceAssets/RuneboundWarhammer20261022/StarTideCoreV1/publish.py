"""Publish the exclusive pommel and its existing data-driven save identity."""
import json,os,shutil
from pathlib import Path
P=Path(__file__).resolve().parent;ROOT=P.parents[2]
saved=json.loads((P/'import_receipt.json').read_text('utf-8'))
if not saved.get('complete'):raise RuntimeError('Save pommel assets first')
option={'id':'star_tide_core','name':'星潮之核','tier':'special','weapons':['ue_runebound_warhammer'],
    'description':'符文战锤专属。深蓝晶球由交错黑银弧架与符文环轨托持，蓝晶嵌窗依次明灭，双螺旋光流在球内循环。',
    'appearance':'深蓝晶球 · 交错弧架与蓝晶环轨 · 球内双螺旋光流','stats':{},'effects':[],
    'special_effects':['星潮续醒｜符文唤醒期间，每次命中目标使持续时间增加0.5秒，持续时间无上限。']}
spec={'mesh':saved['mesh'],'location_cm':[0.,0.,-8.5],'appearance':option['appearance'],
    'interface':'runebound_warhammer_modular_v1','exclusive_to':'ue_runebound_warhammer','model_revision':'StarTideCoreV1','materials':saved['materials']}
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
    backup=P/'Before'/relative;backup.parent.mkdir(parents=True,exist_ok=True)
    if not backup.exists():backup.write_bytes(before)
    if file.read_bytes()!=before:raise RuntimeError('Concurrent catalog write '+relative)
    tmp=file.with_suffix('.star-tide.tmp');tmp.write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    if file.read_bytes()!=before:raise RuntimeError('Concurrent catalog write before commit '+relative)
    os.replace(tmp,file);writes.append(relative)
icon='ue_runebound_warhammer_pommel_star_tide_core.png'
shutil.copy2(P/icon,ROOT/'Content/ColdSteelData/AttachmentIcons20260913'/icon)
(P/'published.json').write_text(json.dumps({'complete':True,'catalogs':writes,'icon':icon,'saved_assets':saved['assets'],
    'extension_per_hit_seconds':0.5,'duration_cap_seconds':None,'base_duration_seconds':20,'tested':False},ensure_ascii=False,indent=2),encoding='utf-8')
design_path=P.parent/'EverflowOrbConceptV1/design.json'
design=json.loads(design_path.read_text('utf-8'))
design.update(status='approved_design_modeled_and_integrated',model_authored=True,runtime_integrated=True,model_revision='StarTideCoreV1',user_runtime_acceptance=False)
design_path.write_text(json.dumps(design,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print('Star Tide Core exclusive special pommel published')
