"""Current Chixiao gameplay contract, shared by appearance and animation reimports."""
MECHANISM = '重击改为快速二连斩：先下斩，再从落刀处向右上方挑斩。两刀均造成完整重击伤害，属于武技。出手体力消耗翻倍，蓄力期间每秒体力消耗不变。'
TRAIL = '重击双斩时，红色剑气沿刀刃实际挥过的轨迹展开并渐隐；同时安装背嵬符文时，重击使用红色剑气，其他武技保留金色剑气。'

def extend_option(option):
    option['tier'] = 'legendary'
    option.setdefault('stats', {})['attack_speed_mult'] = 1.15
    option['stats']['physical_damage_mult'] = 1.1
    option['effects'] = [{'text': '攻击速度 +15%', 'benefit': 1}, {'text': '物理攻击力 +10%', 'benefit': 1}]
    option['special_effects'] = ['赤霄双斩｜' + MECHANISM, '赤霄剑气｜' + TRAIL]
    return option
