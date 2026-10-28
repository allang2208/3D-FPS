"""Merge only the owned legendary option and material mappings into the current catalogs."""
import json,shutil
from pathlib import Path
P=Path(__file__).resolve().parent;ROOT=P.parents[2]
r=json.loads((P/'import-receipt.json').read_text('utf-8'))
if not r['complete']:raise RuntimeError('Save UE assets before publishing')
appearance='冰蓝鸟首与层叠羽纹沿刀面展开，细密刻线和镂空纹路交织成霜光。'
option={'id':'frost_raven_rune','name':'霜鸦符文','tier':'legendary','description':appearance,'appearance':appearance,
    'stats':{'critical_chance_add':20},'effects':[{'text':'暴击率+20%','benefit':1}],
    'special_effects':[
        '蓄能｜本刀成功出手命中敌人累计8次后进入霜狱，持续16s；同次出手命中多个目标仅计1次。',
        '霜狱｜本刀直接攻击和武技韧性伤害+35%；每次出手对每个命中的敌人叠加4层寒冷，同次双刀命中同一目标不重复叠加。',
        '寒冷｜每层移动速度−5%，本符文刷新4s持续时间；已有更长剩余时间不缩短。达到20层触发冻结并消耗10层；本符文触发的冻结持续4s。冻结期间不再叠加寒冷。',
        '双持｜两把都安装霜鸦时共用蓄能与状态，效果不叠加；只安装一枚时，仅对应刀提供激活加成。',
        '周期｜触发霜狱的当次出手只负责蓄能；状态期间不续时、不蓄能。切换武器或死亡清空蓄能和状态，目标已有寒冷自行计时。']}
def merge(path,edit):
    before=path.read_bytes();data=json.loads(before.decode('utf-8-sig'));edit(data)
    backup=P/'Before'/path.relative_to(ROOT);backup.parent.mkdir(parents=True,exist_ok=True)
    if not backup.exists():backup.write_bytes(before)
    if path.read_bytes()!=before:raise RuntimeError('Concurrent catalog edit: '+str(path))
    path.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def catalog(data):
    choices=next(c for c in data['columns'] if c['key']=='blade_2').setdefault('options',[])
    index=next((i for i,o in enumerate(choices) if o['id']==option['id']),None)
    if index is None:choices.append(option)
    else:choices[index]=option
def modules(data):data['slots']['blade_2'][option['id']]={'appearance':appearance,'surface_materials':r['surface_materials']}
for folder in ('Content/ColdSteelData','SourceAssets/KukriComponentVariants20261026'):
    merge(ROOT/folder/'kukri-gunsmith.json',catalog);merge(ROOT/folder/'kukri-modules.json',modules)
name='ue_kukri_blade_2_frost_raven_rune.png'
shutil.copy2(P/'Icons'/name,ROOT/'Content/ColdSteelData/AttachmentIcons20260913'/name)
(P/'published-option.json').write_text(json.dumps(option,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print('Published frost_raven_rune, six blade surfaces and standard icon')
