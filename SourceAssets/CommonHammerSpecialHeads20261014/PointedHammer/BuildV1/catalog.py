"""Shared pointed-hammer appearance and direct modifiers; user balance revision V2."""
MESH_DIR = '/Game/Weapons/CommonHammerSpecialHeads20261014/PointedHammer/BuildV1'
OPTION = {
    'id': 'pointed_hammer', 'name': '双棱尖头锤',
    'description': '双侧尖头沿直轴对称展开，纵向棱脊与凹槽汇向尖端，短连接颈衔接中央锤座。',
    'appearance': '双侧直尖 · 纵向棱槽 · 锻钢收肩',
    'stats': {
        'physical_damage_mult': 1.30,
        'attack_speed_mult': 1.05,
        'stamina_mult': 1.15,
        'toughness_damage_mult': 0.75,
        'physical_armor_penetration': 0.15
    },
    'effects': [], 'special_effects': []
}
FIELDS = {
    'physical_damage_mult': ('物理伤害', False),
    'attack_speed_mult': ('攻击速度', False),
    'stamina_mult': ('体力消耗', True),
    'toughness_damage_mult': ('韧性伤害', False)
}
OPTION['effects'] = [
    {'text': f'{FIELDS[key][0]} {(value-1)*100:+.0f}%',
     'benefit': 1 if ((value > 1) != FIELDS[key][1]) else -1}
    for key, value in OPTION['stats'].items() if key in FIELDS
]
OPTION['effects'].append({
    'text': f"物理防御穿透 +{OPTION['stats']['physical_armor_penetration']*100:.0f}%",
    'benefit': 1
})
OPTIONS = [OPTION]
