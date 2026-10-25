"""Shared seats; laminated damper redesigned for charged heavies on 2026-10-25."""
OPTIONS=[
 {'id':'reinforced_block','name':'厚壁重铸座','description':'整体承力芯外配阶梯加厚盖板，以嵌入铆钉固定。',
  'appearance':'厚壁方芯 · 阶梯盖板 · 嵌入铆钉',
  'stats':{'physical_damage_mult':1.10,'attack_speed_mult':.95,'stamina_mult':1.10,'toughness_damage_mult':1.15}},
 {'id':'ribbed_light','name':'镂肋轻型座','description':'前后盖板开出三角减重窗，支撑肋连接连续的中央承力芯。',
  'appearance':'三角减重窗 · 交叉支撑肋 · 连续内芯',
  'stats':{'physical_damage_mult':.95,'attack_speed_mult':1.10,'stamina_mult':.90,'toughness_damage_mult':.90}},
 {'id':'laminated_damper','name':'叠片缓冲座','description':'多层钢板夹持薄层垫片，由四角拉杆收束固定。',
  'appearance':'叠片盖板 · 深色垫片 · 四角拉杆',
  'stats':{'heavy_charge_speed_bonus':.20,'heavy_release_stamina_mult':.75,'attack_speed_mult':.95,'toughness_damage_mult':.90}}
]
FIELDS={'physical_damage_mult':('物理伤害',False,1),'attack_speed_mult':('攻击速度',False,1),
        'stamina_mult':('体力消耗',True,1),'toughness_damage_mult':('韧性伤害',False,1),
        'heavy_charge_speed_bonus':('重击蓄力速度',False,0),'heavy_release_stamina_mult':('重击出手体力消耗',True,1)}
for option in OPTIONS:
    option['effects']=[{'text':f'{FIELDS[key][0]} {(value-FIELDS[key][2])*100:+.0f}%',
                       'benefit':1 if ((value>FIELDS[key][2])!=FIELDS[key][1]) else -1} for key,value in option['stats'].items()]
    option['special_effects']=[]
