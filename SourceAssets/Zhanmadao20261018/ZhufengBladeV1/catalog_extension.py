"""Keep Zhufeng in the live modular catalog and all model reimport paths."""
import json
from pathlib import Path
P=Path(__file__).resolve().parent
def extend(catalog):
    file=P/'import_receipt.json'
    if not file.exists():return catalog
    receipt=json.loads(file.read_text(encoding='utf-8'))
    if not receipt.get('assets_saved'):return catalog
    ex=json.loads((P/'exports.json').read_text(encoding='utf-8'))
    part={k:ex[k] for k in ['trace_base_cm','trace_tip_cm','rune_dimensions_cm']}
    part.update(mesh=receipt['mesh'],materials=receipt['materials'],location_cm=[0,0,0],interface=catalog['interface'],
        appearance='青灰锻钢 · 银白开锋 · 旋流刀脊',rune_layout_revision='ZhufengContourV1',dash_attack='zhufeng_whirlwind')
    catalog['slots']['blade_1']['zhufeng']=part
    catalog['zhufeng_blade_revision']='ZhufengBladeV1'
    return catalog
def extend_option(entry):
    entry.update(id='zhufeng',name='逐风',tier='legendary',weapons=['ue_zhanmadao'],stats={'range_mult':1.2,'physical_damage_mult':1.1,'whirlwind_damage_add':0.5},
        description='青灰长刃配银白刃口，刀脊饰旋流锻纹。',
        effects=[{'text':'攻击范围 +20%','benefit':1},{'text':'物理攻击力 +10%','benefit':1}],
        special_effects=[
            '逐风旋斩｜冲刺攻击改为向前匀速推进的群体旋风，旋转结束或受阻时停止推进；每个目标仅命中一次。',
            '旋风强化｜旋风伤害倍率 +0.5，旋转时显现青色剑气；主动大旋风同样生效。',
            '施放条件｜需学会冲刺攻击。沿用大旋风等级、消耗并共用冷却；未学大旋风时按一级计算。'])
    return entry
