"""Shared hammer-head identity, appearance and direct modifier source."""
OPTIONS=[
    {'id':'heavy_forged','name':'重铸方锤','description':'宽厚的锻钢方头配阶梯式收肩，击打面保留大倒角。',
     'appearance':'宽方锤面 · 阶梯锤肩 · 成对锻钢头',
     'stats':{'physical_damage_mult':1.20,'attack_speed_mult':.90,'stamina_mult':1.15,'toughness_damage_mult':1.15}},
    {'id':'flanged_breaker','name':'破韧棱锤','description':'放射状棱翼沿锤体纵向展开，末端以收边棱面聚拢。',
     'appearance':'八道纵向棱翼 · 收边端面 · 成对棱锤',
     'stats':{'physical_damage_mult':.95,'attack_speed_mult':.95,'stamina_mult':1.10,'toughness_damage_mult':1.40}},
    {'id':'light_drum','name':'轻量鼓锤','description':'紧凑的鼓形锤头带环槽束腰，两端圆缘包住内凹击打面。',
     'appearance':'紧凑鼓形 · 环槽束腰 · 内凹端面',
     'stats':{'physical_damage_mult':.90,'attack_speed_mult':1.15,'stamina_mult':.88,'toughness_damage_mult':.85}}
]
FIELDS={'physical_damage_mult':('物理伤害',False),'attack_speed_mult':('攻击速度',False),
        'stamina_mult':('体力消耗',True),'toughness_damage_mult':('韧性伤害',False)}
for option in OPTIONS:
    option['effects']=[{'text':f'{FIELDS[key][0]} {(value-1)*100:+.0f}%',
                       'benefit':1 if ((value>1)!=FIELDS[key][1]) else -1} for key,value in option['stats'].items()]
    option['special_effects']=[]
