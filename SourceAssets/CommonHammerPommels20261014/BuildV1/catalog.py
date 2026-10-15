"""Common hammer pommels with the user's final 2026-10-14 balance table."""
MESH_DIR = '/Game/Weapons/CommonHammerPommels20261014/BuildV1'
OPTIONS = [
    {'id': 'octagonal_impact', 'name': '八棱镇击配重',
     'description': '实心八棱钢坠上肩收窄、下腹厚实，磨亮棱线与圆钝底端环绕嵌入式锁盖。',
     'appearance': '八棱锻钢 · 宽倒角 · 齐平锁盖',
     'stats': {'physical_damage_mult': 1.05, 'attack_speed_mult': .95, 'stamina_mult': 1.05, 'toughness_damage_mult': 1.10},
     'effects': [], 'special_effects': []},
    {'id': 'caged_agility', 'name': '镂笼灵巧配重',
     'description': '六根弧形钢肋连接安装圈与底盘，纵向窗口贯通笼体，内壁保留暗色锻钢。',
     'appearance': '六肋镂笼 · 贯通窗口 · 内凹紧固件',
     'stats': {'physical_damage_mult': .95, 'attack_speed_mult': 1.10, 'stamina_mult': .90}, 'effects': [], 'special_effects': []},
    {'id': 'twin_disc_balance', 'name': '双盘平衡配重',
     'description': '两枚厚圆盘通过短芯固定连接，环形凹槽分隔上下盘，宽倒角包住同心车纹。',
     'appearance': '双盘配重 · 刚性短芯 · 同心车纹',
     'stats': {'stamina_mult': .80, 'toughness_damage_mult': .90, 'martial_cooldown_mult': .80}, 'effects': [], 'special_effects': []}
]

FIELDS = {'physical_damage_mult': ('物理伤害', False), 'attack_speed_mult': ('攻击速度', False),
          'stamina_mult': ('体力消耗', True), 'toughness_damage_mult': ('韧性伤害', False),
          'martial_cooldown_mult': ('武技冷却时间', True)}
for option in OPTIONS:
    for key, value in option['stats'].items():
        label, lower_is_better = FIELDS[key]
        delta = value - 1
        option['effects'].append({'text': f'{label} {delta*100:+.0f}%',
                                  'benefit': 1 if ((delta > 0) != lower_is_better) else -1})
