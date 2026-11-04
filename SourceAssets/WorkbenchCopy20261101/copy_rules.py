"""Workbench copy only. No gameplay, compatibility or asset fields are changed.

Author/reimport entry: apply_catalog(filename, catalog), then serialize as usual.
The approved frost coefficients and echo timing are read from the option stats.
"""
import re
import json
from pathlib import Path


def number(value):
    return f'{value:g}'


def normalize(text):
    text = text.replace('耐力', '体力').replace('快速打击', '快速近战')
    text = text.replace('基础伤害', '基础物理伤害').replace('削韧 +', '韧性伤害+').replace('削韧 -', '韧性伤害-')
    text = re.sub(r'(提高|增加|降低|减少|缩短)\s*(\d+(?:\.\d+)?)%',
                  lambda m: ('+' if m[1] in ('提高', '增加') else '-') + m[2] + '%', text)
    text = re.sub(r'\s*([+−-])\s*(\d+(?:\.\d+)?)\s*%', r'\1\2%', text)
    return text


MELEE_DESCRIPTIONS = {
    'star_marrow': '魔晶双手剑限定。长款晶体双刃内嵌三枚星髓晶核，保留原有护手与握柄接口；兼容红魔晶与高能魔晶。',
    'resonance_rune': '银白环纹彼此相连，共鸣微光沿刻纹缓缓明灭。',
    'erosion_rune': '紫色裂纹状符印沿金属表面延伸，刻纹间泛出微光。',
    'spirit_burst_rune': '魔晶双手剑专属。冰蓝晶光在刃内聚拢，双重柔光波纹依次扩散。',
    'conduction_rune': '银白导魔回路沿金属表面相连，微光循刻纹流动。',
    'wild_rune': '高地双手剑专属。兽颚主印与破甲爪痕相连，赤红裂隙沿剑脊明灭。',
    'auspicious_cloud_rune': '唐刀与玄螭镇岳限定。卷云主印向刃尖收束，淡金云纹间流转玉青微光。',
    'mountain_rune': '唐刀与玄螭镇岳限定。三峰主印与层叠岩脉沿刃身展开，土黄刻纹间浮起琥珀微光。',
    'jingang_rune': '玄螭镇岳专属。金刚经行草鎏入剑脊，随生命状态显现三种光纹。',
    'bastion_guard': '宽厚护翼向两侧展开，外缘厚实，中央连接握柄。',
    'riposte_guard': '上挑护翼围住握柄前端，内缘形成承刃的弧面。',
    'light_guard': '收窄的护翼保留简洁轮廓，两端轻巧上扬。',
    'highland_cloven_guard': '高地双手剑专属。双角护翼向外分叉，根部与握柄牢固衔接。',
    'xuan_cloud_dragon': '唐刀专属。鎏金龙云浮雕嵌入暗铜底面，层叠边框沿护翼收束。',
    'phoenix_feather': '唐刀专属。层叠凤羽围住红石嵌饰，卷云镂空穿过双侧护翼。',
    'panchi_zhanyue': '玄螭镇岳专属。双螭环抱青玉，宽展铜翼间贯通卷云纹孔。',
    'shock_wrap': '防滑织带层叠包覆握区，搭接边平整收束。',
    'swift_grip': '轻巧握柄收窄外轮廓，保留双手贴合的握区。',
    'long_twohand': '加长握柄拉开双手握持间距，尾端与配重连续衔接。',
    'iron_spine_power_grip': '贴平钢脊支撑三段皮革握区，金属边缘收进缠革下方。',
    'lockweave_guard_grip': '交错锁纹织带紧密贴合握区，两端以窄环收口。',
    'pommel_hardened': '加厚硬化钢质剑首，以宽阔棱面收束柄尾。',
    'pommel_runic': '苍蓝符文嵌入金属剑首，微光环绕柄尾流转。',
    'pommel_mana_orb': '魔晶双手剑与符文长剑限定。银色支架包覆蓝色魔力晶球。',
    'ballast_hardened': '厚重陨铁锤首收束柄尾，击打端保留宽阔棱面。',
    'highland_thorn_crown': '高地双手剑专属。银钢尖刺与编结纹包覆球体，两侧嵌有蓝宝石。',
    'ballast_rune': '魔晶双手剑与符文长剑限定。银色护架环抱凝碧晶核，星点在晶体内流转。',
    'ballast_magic_orb': '流线金属护架环绕柄尾，镂空窗口贯通配重。',
    'yanling_breaker': '唐刀专属。八面锥形柄尾配鎏金甲框，龙云浮雕与锻钢水波纹交错。',
    'tiger_mountain': '唐刀专属。虎首环抱穹顶红石，鬃纹向后收束，云环连接柄尾。',
    'chixiao': '斩马刀专属。暗红嵌线沿宽腹长刃延伸，刀根饰有金色云纹。',
    'starfall_nexus_guard': '符文长剑专属。冷银护翼承托修长星晶，细金星轨汇入中央晶核。',
}

MELEE_SPECIAL = {
    'star_marrow': [
        '晶能蓄积｜每次实际攻击出手获得1层晶能，上限3层；挥空也计层。普攻、重击、突刺、快速近战、武技和攻击魔法均可积蓄。',
        '晶髓过载｜出手前已有3层时，消耗3层，使本次攻击的附加魔法伤害×2，再获得新一轮1层。群攻、多段及本次后续伤害共用强化；不重复计层。',
        '法术导晶｜攻击魔法携带本剑的魔晶附伤；过载只翻倍附加魔法伤害，法术自身基础伤害不翻倍。',
        '晶能保留｜晶能不随时间衰减。切换武器、卸下星髓长锋或死亡时清除；满层攻击挥空同样消耗强化。'],
    'resonance_rune': ['冷却结算｜持握本武器时，使用技能按当前冷却缩减计算；不会直接扣减已经开始的剩余冷却。'],
    'auspicious_cloud_rune': ['击杀恢复｜装备本武器期间，你每击杀一个目标，恢复最大体力的15%；双持时两把武器分别结算。'],
    'riposte_guard': ['反击激励｜成功弹反后，攻击速度+20%、攻击体力消耗-20%，持续6秒；再次弹反刷新持续时间。'],
    'highland_cloven_guard': [
        '弹反重击｜成功弹反后4秒内，下一次普攻直接释放免蓄力重击；该击物理伤害+25%、韧性伤害+40%。',
        '消耗规则｜按重击消耗体力，出手即消耗强化，挥空也消耗；最多保留一次，再次弹反刷新。突刺与技能不消耗强化。'],
    'xuan_cloud_dragon': [
        '玄龙｜成功弹反后获得6秒龙威，触发冷却6秒。下一次刀刃命中伤害+50%，额外造成200基础韧性伤害。',
        '消耗规则｜最多保留一次，首次命中即消耗，挥空不消耗。快速近战、裂空斩和持续伤害不触发；超时、换武器或卸下护手时清除。'],
    'phoenix_feather': [
        '凤舞｜闪避中实际躲过敌方攻击后，获得6秒凤舞，攻击速度+50%，触发冷却10秒；空闪避不触发。',
        '回复规则｜凤舞期间前3次刀刃攻击命中，各恢复最大生命的2%；每次出手最多回复一次。快速近战、裂空斩与持续伤害不触发；切换武器或卸下护手清除凤舞，冷却不重置。'],
    'ballast_hardened': ['范围攻击｜快速近战可命中原判定范围内的多个目标，每个目标每次出手结算一次；判定距离与宽度不变。'],
    'highland_thorn_crown': ['出血｜快速近战命中有25%概率施加1层出血。'],
    'ballast_rune': ['魔法易伤｜快速近战命中后，目标受到的魔法伤害+15%，持续15秒；重复命中刷新，不叠加。'],
    'yanling_breaker': ['物理易伤｜快速近战命中后，目标受到的物理伤害+20%，持续15秒；重复命中刷新，不叠加。'],
    'tiger_mountain': ['虎啸｜快速近战命中后，目标受到的韧性伤害+25%，冲击、利器、钝器的韧性抵抗归零，持续6秒；重复命中刷新，不叠加。'],
    'beiwei_rune': ['武技剑气｜释放武技时，金色剑气沿刀刃轨迹展开并渐隐。',
                   '生效范围｜伤害与范围加成仅作用于武技，普通攻击与普通连段不受影响。'],
    'twin_star_guard': ['双曜增列｜G键魔法飞剑+2把，在原有队列左右最外侧各增加1把。',
                        '飞剑强化｜G键飞剑的基础伤害倍率提升至1.5×。'],
    'starfall_nexus_guard': ['天枢聚剑｜G键只召唤1把大型飞剑，覆盖锻造增加的飞剑数量；召唤与发射操作不变。',
                            '星陨爆破｜飞剑伤害倍率为8×，命中后产生半径3米的魔法爆炸，每个目标只结算一次伤害。'],
}

BOW_DESCRIPTIONS = {
    'steady_twist_string': '炭灰双股纤维紧密绞合，灰麻细线沿弦身交错。',
    'softcore_hold_string': '柔芯外包深棕与暗橄榄纤维，编织表面带有柔和蜡光。',
    'lined_rest': '窄皮垫贴合箭台托面，接触边缘圆润收束。',
    'no_sight': '移除瞄圈、准星及底座，保留原有弓身。',
    'highland_peakwatch_3_6x': '高地长弓专属。圆形镜片配银钢薄框，旧黄铜滚花环环绕镜缘。',
}

GUN_DESCRIPTIONS = {
    'pistol_grip_granular': '密集细颗粒覆盖握把接触面，保留原有握持轮廓。',
    'pistol_grip_diamond': '柔性橡胶覆以浅菱形格纹，边缘贴合握把。',
    'pistol_grip_quickdot': '低凸细点覆盖握面，表面纹路细密平整。',
    'titanium_brake': '钛金嵌边围住侧向排气孔，金属切面层次分明。',
    'multi_caliber_suppressor': '长筒外壳配开放式管口，尾端接环贴合枪管。',
    'stable_antislip_reargrip': '实心握把带指槽与橡胶防滑面。',
    'm1911_lightweight_fast': '轻量化扳机组件，保留原有扳机轮廓。',
    'pit_viper_lightweight_fast': '轻量化扳机组件，保留原有镂空扳机轮廓。',
    'legendary_full_auto_trigger': '半自动手枪专用射击模式改造，沿用原厂扳机外观。',
    'g18_controlled_trigger': '调校后的扳机组件，沿用原厂扳机外形。',
    'dw715_lightweight_fast': '轻量化扳机组件，保留原厂双动扳机外形。',
    'rsh12_lightweight_fast': '轻量化双动扳机机构，沿用原厂扳机轮廓。',
    'dw715_speedloader': '六孔速装器环绕中央释放旋钮，与弹仓孔位对应。',
    'rsh12_speedloader_5': '五孔装填器配中央释放结构，与五发弹巢对应。',
    'dw715_handgun_scope_2x': '固定2×长出瞳手枪镜，细十字与粗边分划配独立镜座。',
    'dw715_rubber_grip': '细颗粒橡胶与侧面防滑纹理贴合原厂握持轮廓。',
    'dw715_target_wood_grip': '纵向木纹与侧面菱形格纹交错，下沿连接加大底托。',
    'dw715_compact_grip': '轻量复合握把收紧外露后跟，保留安装颈部与主要握持轮廓。',
    'dw715_muzzle_brake': '短型金属制退器贴合枪口，双侧开口贯通壳体。',
    'dw715_compact_compensator': '短型金属补偿器贴合原厂枪口，边角圆润。',
    'dw715_target_muzzle_weight': '短型配重套包覆枪口，下部加厚，上方避让原厂准星。',
    'thermal_scope': '电子热成像瞄具，封闭镜筒内置热感应显示屏。',
    'laser': '紧凑激光发射器固定于枪身导轨，投出红色光束。',
    'blessed_laser': '金色光束间流动细丝，发射器贴合枪身导轨。',
    'flashlight': '导轨式手电筒配金属外壳与前置透镜。',
    'pkm_bipod': '成对金属支腿连接枪身下方夹座，可与前握把同时安装。',
    'lmg201_no_bipod': '移除原厂脚架及支架，保留枪身原有轮廓。',
    'large_drum': '圆鼓式储弹主体通过供弹颈连接弹匣井。',
}

GUN_SPECIAL = {
    'lpvo_1_6x': ['变倍瞄准｜瞄准时使用鼠标滚轮调节1–6×倍率，每格0.5×。'],
    'kv_scope_4x': ['变倍瞄准｜瞄准时使用鼠标滚轮切换1×、2×、4×三档倍率。'],
    'thermal_scope': ['电子变倍｜默认1.5×，瞄准时使用鼠标滚轮切换1.5×、3×、8×。',
                      '热成像｜显示怪物、隐身怪物与真实火源的热轮廓；实体墙壁仍会遮挡。'],
    'legendary_full_auto_trigger': ['射击模式｜主手按V、副手按H切换半自动与全自动；全自动时按住对应开火键持续射击。',
                                    '独立改造｜双持时只改变安装该扳机的武器。'],
    'laser': ['激光指示｜射程80米；腰射沿发射器方向，开镜时汇聚准星，遇遮挡截断。'],
    'blessed_laser': ['激光指示｜射程80米；腰射沿发射器方向，开镜时汇聚准星，遇遮挡截断。'],
    'flashlight': ['照明｜持枪时提供前向照明，遮挡物会投下阴影；收起武器或卸下手电时关闭。'],
    'dw715_speedloader': ['快速装填｜普通与空仓换弹均先退出弹仓内全部弹药，再由速装器装填；按背包余弹最多装入6发。',
                           '余弹损失｜未击发的弹仓余弹直接丢弃，不返还背包。'],
    'rsh12_speedloader_5': ['快速装填｜普通与空仓换弹均先退出弹巢内全部弹药，再由装填器装入；按背包余弹最多装入5发。',
                            '余弹损失｜未击发的弹巢余弹直接丢弃，不返还背包。'],
    'lmg201_no_bipod': ['无法架设｜卸下后不能架设武器；恢复原厂脚架后重新获得架设能力。'],
    'sniper_heavy_suppressor': ['消音｜降低枪声与枪口火光。',
                               '隐蔽击杀｜首发命中直接击杀目标时，不会引起其他怪物警觉；未击杀目标仍会发出警报。'],
    'm24_carbon_light_bolt': ['拉栓调校｜拉栓速度+30%，同步缩短射击间隔；换弹和装备动作保持原有节奏。'],
}

TOOL_DESCRIPTIONS = {
    'cushion_wrap': '握把缓冲调校。', 'quick_hands': '握位与挥击节奏调校。',
    'firm_hands': '握持稳定调校。', 'long_haft': '柄杆施力与触及距离调校。',
    'ash_haft': '轻量柄杆调校。', 'ironbound_haft': '柄杆承力调校。',
    'wedge_kit': '作业头部紧固调校。', 'whetstone_kit': '刃口保养与采集调校。',
    'lucky_charm': '采集与战斗幸运调校。', 'felling_head': '面向伐木的宽刃头调校。',
    'hardened_head': '斧刃硬度与承力调校。', 'splitting_head': '斧头劈裂能力调校。',
    'ore_head': '面向采矿的镐尖调校。', 'crushing_head': '镐头冲击能力调校。',
    'flanged_head': '镐头碎裂能力调校。',
}


def options(catalog):
    """Yield real options, including libraries and per-weapon firearm entries."""
    for column in catalog.get('columns', []):
        for option in column.get('options', []):
            yield column['key'], option, ''
    for option in catalog.get('options', []) if isinstance(catalog.get('options'), list) else []:
        yield '', option, ''
    for weapon in catalog.get('weapons', []):
        for slot, entries in weapon.get('options', {}).items():
            for option in entries:
                yield slot, option, weapon['id']
        for option in weapon.get('pistol_grip_surface', {}).get('exclusive_options', []):
            yield 'reargrip', option, weapon['id']
    for slot, entries in catalog.get('common_options', {}).items():
        for option in entries:
            yield slot, option, ''
    for option in catalog.get('pistol_grip_surface_options', []):
        yield 'reargrip', option, ''


def apply_catalog(filename, catalog, items=None):
    for slot, option, weapon in options(catalog):
        oid = option['id']
        stats = option.get('stats', {})
        option.setdefault('special_effects', [])
        if filename == 'melee-gunsmith.json':
            if oid in MELEE_DESCRIPTIONS: option['description'] = MELEE_DESCRIPTIONS[oid]
            if oid in MELEE_SPECIAL: option['special_effects'] = list(MELEE_SPECIAL[oid])
            if oid == 'frost_crystal':
                option['name'] = '魔晶'
                option['description'] = '符文长剑专属。冰蓝晶面保留魔晶纹理，剑身与剑根连成一体。'
            if oid in ('red_magic_crystal', 'high_energy_magic_crystal'):
                health = oid == 'red_magic_crystal'
                ratio = stats['hit_health_return_ratio' if health else 'hit_mana_return_ratio']
                resource = '生命值' if health else '魔法值'
                option['special_effects'] = [
                    f'{"生命汲取" if health else "魔能回流"}｜使用本武器攻击命中怪物时，按本次实际造成伤害的{number(ratio*100)}%恢复{resource}。',
                    f'多目标结算｜每个命中目标分别计算并累加恢复量；物理与魔法伤害均计入，溢出目标剩余生命的伤害不计入，恢复不超过自身{resource}上限。']
            if oid in ('frost_crystal', 'erosion_rune'):
                label = '魔晶侵蚀' if oid == 'frost_crystal' else '侵蚀附伤'
                effect = (f'{label}｜本武器近战攻击附加智力×{number(stats["rune_intelligence"]*100)}%'
                          f'＋精神×{number(stats["rune_wisdom"]*100)}%的魔法伤害；随本次攻击倍率结算，并受目标魔法防御影响。')
                option['special_effects'] = [effect]
                if oid == 'frost_crystal':
                    option['special_effects'].append('符文兼容｜仅限符文长剑，不占用符文栏，可与符文效果叠加。')
                option['effects'] = [{'text': effect.replace('｜', '：'), 'benefit': 1}]
            if oid == 'spirit_burst_rune':
                donor = (items or {})['ue_frost_crystal_sword']
                mult = stats['innate_erosion_mult']
                option['special_effects'] = [
                    f'精神迸发｜魔晶双手剑自带的侵蚀附伤×{number(mult)}：由智力×{number(donor["innate_erosion_intelligence"]*100)}%'
                    f'＋精神×{number(donor["innate_erosion_wisdom"]*100)}%，提升为智力×{number(donor["innate_erosion_intelligence"]*mult*100)}%'
                    f'＋精神×{number(donor["innate_erosion_wisdom"]*mult*100)}%的魔法伤害。',
                    '生效范围｜仅强化魔晶双手剑自带的侵蚀，不使其他来源的附加魔法伤害翻倍。']
                option['effects'] = [{'text': option['special_effects'][0].replace('｜', '：'), 'benefit': 1}]
            if oid == 'time_sand_gold':
                option['special_effects'] = [
                    f'时砂回响｜剑刃命中后延迟{number(stats["time_sand_echo_delay"])}秒，追加本次实际伤害的{number(stats["time_sand_echo_ratio"]*100)}%；保留原命中的物理与魔法伤害比例，不重复判定暴击。',
                    '回响共鸣｜有效回响使魔法及G飞剑剩余冷却各减少0.5秒，装备金色符文时为1秒；同一次挥击的回响只结算一次减冷却。',
                    '触发范围｜仅剑刃命中触发，配重锤、剑气与飞剑不触发。回响不会生成新的回响，也不触发其他命中附效。']
            if oid in ('chixiao','zhufeng'):
                for e in option.get('effects', []):e['text'] = e['text'].replace('物理攻击力', '物理伤害').replace('攻击范围', '攻击距离')
        elif filename == 'bow-gunsmith.json':
            if oid in BOW_DESCRIPTIONS:option['description'] = BOW_DESCRIPTIONS[oid]
            if oid == 'no_sight':option['special_effects'] = ['瞄准方式｜瞄准时沿箭杆方向观察，不提供光学放大。']
        elif filename == 'tool-gunsmith.json':
            if oid in TOOL_DESCRIPTIONS:
                option['description'] = TOOL_DESCRIPTIONS[oid]
                option['appearance'] = '沿用原装部件外形。'
        elif filename == 'staff-gunsmith.json':
            specialty = option.get('effects', {}).get('staffSpecialty')
            if specialty:
                title = {'ice':'冰系', 'fire':'火系', 'electric':'电系', 'light':'光系'}[specialty]
                lines = [line for line in option['special_effects'] if not line.startswith('杖头专精｜')]
                option['special_effects'] = [f'杖头专精｜赋予{title}专精，可激活匹配的杖冠。'] + lines
            if oid == 'sandalwood_grip':
                option['special_effects'] = ['余韵加速｜施法后获得1层移动加速，每层移动速度+10%，最多10层；每次增加5秒持续时间，到期后全部层数消失。']
            if oid == 'purification_vine':
                option['special_effects'] = ['净化加速｜光系法术治疗友方时，赋予目标2层移动加速，每层移动速度+10%，最多10层；每次增加10秒持续时间，到期后全部层数消失。']
        elif filename == 'runebound-warhammer-gunsmith.json':
            if oid == 'star_tide_core':
                option['special_effects'] = ['星潮续醒｜符文苏醒期间，每次对敌人造成有效攻击伤害，持续时间增加0.5秒，无上限；群攻命中的不同目标及连续有效命中分别延长。']
        elif filename == 'thunder-god-hammer-gunsmith.json':
            for old in ['；将蓄满重击化为可召回的旋转飞锤', '；单手举锤蓄力，指向地面召下疾雷',
                        '，环状雷印将积蓄的电荷向周围释放', '，在重击释放后寻找附近的敌人']:
                option['description'] = option['description'].replace(old, '')
        elif filename == 'gunsmith.json':
            # Keep model-specific mounting descriptions where they contain no numeric paraphrases.
            desc = option.get('description', '')
            if oid in GUN_DESCRIPTIONS and not (weapon == 'ue_m24' and oid in ('stable_antislip_reargrip',)):
                if oid != 'large_drum' or '装填耗时更长' in desc:desc = GUN_DESCRIPTIONS[oid]
            for fragment in ['，保持原枪开镜速度', '降低后坐力、提升枪械稳定性，不影响开镜耗时。',
                             '缩短开镜耗时，降低后坐力并提升枪械稳定性，但增加腰射随机散布。',
                             '开镜耗时增加、后坐力降低，但增加腰射随机散布。',
                             '，降低后坐力并提升枪械稳定性', '，减轻后坐、提高枪械稳定性',
                             '，使用专用支撑及换弹回握动作', '，配套独立抓握动作',
                             '，使用适配后的左手包握动作', '，使用对应抓握动作', '，独立校准瞄线']:
                desc = desc.replace(fragment, '')
            if oid in ('true', 'tactical_suppressor', 'rsh12_heavy_suppressor'):
                if oid == 'true':desc = '筒式消音器通过尾部接座连接枪口。'
                else:desc = re.sub(r'，(?:降低|抑制)枪声[与和]枪口火光。', '。', desc)
            if oid == 'lpvo_1_6x':
                desc = re.sub(r'[；。]瞄准时滚轮调节[^；。]+[；。]?', '；', desc).rstrip('；')+'。'
            if oid == 'kv_scope_4x':desc = desc.split('；瞄准时')[0]+'。'
            if oid == 'rsh12_tactical_square_sight':desc = desc.replace('固定低倍瞄准', '固定1.5×瞄准')
            option['description'] = desc.replace('。。','。')
            if oid in GUN_SPECIAL:option['special_effects'] = list(GUN_SPECIAL[oid])
            if oid in ('true','tactical_suppressor','multi_caliber_suppressor','rsh12_heavy_suppressor','ash12_tactical_suppressor'):
                option['special_effects'] = ['消音｜降低枪声与枪口火光。']
            if oid == 'super90_tube_loader':
                option['special_effects'] = ['成组装填｜推送到位后一次补满弹仓；备弹不足时装入剩余弹药，未入仓的弹药不扣除。',
                    '操作衔接｜按住开火或瞄准时，完成整次装填后接续操作。空仓完成后'+('回握护木并泵动上膛。' if weapon == 'ue_m870' else '释放枪机。')]
            if oid == 'false' and slot == 'bipod' and weapon == 'ue_lmg201':
                option['description'] = '双侧金属支腿安装于枪身下方，可折叠收起。'
                option['special_effects'] = ['架设｜找到合适支撑面后可架设：后坐力-66%、枪械稳定性+66%、散布-45%；架设时限制移动和瞄准转角，解除后恢复。']
            if oid == 'tactical_vertical_foregrip':
                option['effects'] = [{'text': f'开镜耗时{stats["ads_percent"]*100:+g}%', 'benefit': 1}]
        # Preserve numeric effects objects (staff gameplay data); only edit legacy text lists.
        if isinstance(option.get('effects'), list):
            for effect in option['effects']:
                if 'text' in effect:effect['text'] = normalize(effect['text'])
            if oid == 'knife_pommel_steel':
                option['effects'][0]['text'] = f'快速近战伤害倍率+{number(stats["quick_combat_damage_add"])}'
        option['description'] = normalize(option.get('description', ''))
        if 'appearance' in option:option['appearance'] = normalize(option['appearance'])
        option['special_effects'] = [normalize(line) for line in option['special_effects']]
    column_descriptions = {
        'melee-gunsmith.json': {
            'blade_1':'保留原装刃形、剑脊与刃口结构。', 'blade_2':'保留原装纹样，不附加改造符文。',
            'guard':'保留原装护手及其连接结构。', 'grip':'保留原装握柄与双手握持位置。',
            'pommel':'保留原装柄尾配重。'},
        'bow-gunsmith.json': {'grip':'中心缠带包覆弓根，形成手掌接触面。', 'string':'弓弦连接上下弓梢，中央为拉弦握点。'},
        'runebound-warhammer-gunsmith.json': {'head_mount':'原装符文锤座连接双侧锤头与长柄。', 'grip':'双手握持区覆以原装包覆，两端连接金属收口。'},
        'staff-gunsmith.json': {'head_crystal':'保留原装晶体杖头。', 'crown':'不加装杖冠。', 'shaft_rune':'不添加杖身符文。',
                              'grip_lining':'保留原装握柄。', 'tail_charm':'不加装尾坠。', 'mana_line':'保留原装导魔结构。'},
        'tool-gunsmith.json': {'grip':'保留原装握把与防滑面。', 'shaft':'保留原装柄杆、长度与材质。',
                             'fitting':'不加装改件，保留原装固定结构。', 'head':'保留原装作业头部。'},
    }
    for col in catalog.get('columns', []):
        replacement = column_descriptions.get(filename, {}).get(col['key'])
        if replacement:col['description'] = replacement
    if filename == 'bow-gunsmith.json':
        for weapon in catalog.get('weapons', []):
            for slot, entries in weapon.get('part_overrides', {}).items():
                factory = entries.get('false', {})
                if slot == 'grip' and 'description' in factory:factory['description'] = '旧革缠带沿掌心接触位置紧密包覆弓根。'
                if slot == 'arrow_rest' and 'description' in factory:factory['description'] = '侧置金属箭台贴合弓身，托住箭杆。'
    return catalog


CATALOG_FILES = {
    'gunsmith.json', 'melee-gunsmith.json', 'bow-gunsmith.json', 'staff-gunsmith.json',
    'tool-gunsmith.json', 'kukri-gunsmith.json', 'warhammer-gunsmith.json',
    'runebound-warhammer-gunsmith.json', 'thunder-god-hammer-gunsmith.json',
    'common-hammer-heads.json', 'common-hammer-seats.json', 'common-hammer-grips.json',
    'common-hammer-pommels.json', 'shared-knife-blade-options.json', 'shared-knife-component-options.json',
}


def apply_for_target(path, catalog):
    """Publication hook: unrelated receipts, assets and module recipes are untouched."""
    target = Path(path)
    name = target.name
    # Preserve authored snapshots/backups and receipts, even when they reuse a catalog filename.
    if len(target.parts)>1 and '/content/coldsteeldata/' not in ('/'+target.as_posix().lower()):return catalog
    if name not in CATALOG_FILES or not isinstance(catalog, dict):return catalog
    items = None
    if name == 'melee-gunsmith.json':
        root = Path(__file__).resolve().parents[2]
        items = json.loads((root/'Content/ColdSteelData/items.json').read_text(encoding='utf-8-sig'))
    return apply_catalog(name, catalog, items)
