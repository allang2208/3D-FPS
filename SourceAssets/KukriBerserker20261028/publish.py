"""Merge the completed legendary rune into the current Kukri catalog."""
import json
import shutil
from pathlib import Path

P=Path(__file__).resolve().parent
ROOT=P.parents[1]
receipt=json.loads((P/'import-receipt.json').read_text('utf-8'))
if not receipt.get('complete'):
    raise RuntimeError('Complete and save the UE assets before publishing the option.')

appearance='血红狼首与獠牙纹样沿刀面自然展开，细长血痕连接下缘，纹路带有微弱呼吸红光。'
option={
    'id':'berserker_rune',
    'name':'狂战士符文',
    'tier':'legendary',
    'description':appearance,
    'appearance':appearance,
    'effects':[{'text':'物理伤害+10%','benefit':1}],
    'stats':{'physical_damage_mult':1.10},
    'special_effects':[
        '蓄能｜本刀成功出手命中敌人累计12次后进入狂战士状态，持续20s；同次出手命中多个敌人仅计1次。',
        '狂战士｜本刀攻击和武技不消耗体力，攻击速度+25%、攻击伤害+25%；直接攻击按实际造成伤害的10%恢复生命，移动速度+15%。',
        '双持｜两把刀都安装本符文时共用蓄能槽与状态，效果不叠加；只安装一枚时，仅对应刀享受攻击强化与免体力消耗。',
        '周期｜状态期间不续时、不再次蓄能；切换武器立即退出狂战士并清空蓄能，切回后重新累计；死亡同样清空。'
    ]
}

def write(path,value):
    backup=P/'Before'/path.relative_to(ROOT)
    if path.exists() and not backup.exists():
        backup.parent.mkdir(parents=True,exist_ok=True)
        shutil.copy2(path,backup)
    path.write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')

for directory in ('Content/ColdSteelData','SourceAssets/KukriComponentVariants20261026'):
    path=ROOT/directory/'kukri-gunsmith.json'
    catalog=json.loads(path.read_text('utf-8-sig'))
    column=next(c for c in catalog['columns'] if c['key']=='blade_2')
    choices=column.setdefault('options',[])
    index=next((i for i,value in enumerate(choices) if value.get('id')==option['id']),None)
    if index is None:choices.append(option)
    else:choices[index]=option
    write(path,catalog)
    path=ROOT/directory/'kukri-modules.json'
    modules=json.loads(path.read_text('utf-8-sig'))
    modules['slots']['blade_2'][option['id']]={
        'appearance':appearance,
        'surface_materials':receipt['surface_materials']
    }
    write(path,modules)

name='ue_kukri_blade_2_berserker_rune.png'
shutil.copy2(P/'Icons'/name,ROOT/'Content/ColdSteelData/AttachmentIcons20260913'/name)
(P/'published-option.json').write_text(json.dumps(option,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print('Published berserker_rune catalog, six blade material mappings, and standard icon.')
