"""Shared seat appearance and user-selected direct modifiers (2026-10-14)."""
OPTIONS=[
 {'id':'reinforced_block','name':'厚壁重铸座','description':'整体承力芯外配阶梯加厚盖板，以嵌入铆钉固定。',
  'appearance':'厚壁方芯 · 阶梯盖板 · 嵌入铆钉',
  'stats':{'physical_damage_mult':1.10,'attack_speed_mult':.95,'stamina_mult':1.10,'toughness_damage_mult':1.15}},
 {'id':'ribbed_light','name':'镂肋轻型座','description':'前后盖板开出三角减重窗，支撑肋连接连续的中央承力芯。',
  'appearance':'三角减重窗 · 交叉支撑肋 · 连续内芯',
  'stats':{'physical_damage_mult':.95,'attack_speed_mult':1.10,'stamina_mult':.90,'toughness_damage_mult':.90}},
 {'id':'laminated_damper','name':'叠片缓冲座','description':'多层钢板夹持薄层垫片，由四角拉杆收束固定。',
  'appearance':'叠片盖板 · 深色垫片 · 四角拉杆',
  'stats':{'physical_damage_mult':1.05,'attack_speed_mult':1.05,'stamina_mult':.85,'toughness_damage_mult':.85}}
]
FIELDS={'physical_damage_mult':('物理伤害',False),'attack_speed_mult':('攻击速度',False),
        'stamina_mult':('体力消耗',True),'toughness_damage_mult':('韧性伤害',False)}
for option in OPTIONS:
    option['effects']=[{'text':f'{FIELDS[key][0]} {(value-1)*100:+.0f}%',
                       'benefit':1 if ((value>1)!=FIELDS[key][1]) else -1} for key,value in option['stats'].items()]
    option['special_effects']=[]
