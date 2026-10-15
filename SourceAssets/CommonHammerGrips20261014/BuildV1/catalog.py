"""Shared grip appearance and user-selected modifiers (2026-10-14)."""
MESH_DIR='/Game/Weapons/CommonHammerGrips20261014/BuildV1/UV1'
OPTIONS=[
 {'id':'bias_speed_wrap','name':'斜纹速握包覆','description':'薄织带斜向缠绕，压平搭接边，以窄收口束紧两端。',
  'appearance':'灰褐织带 · 连续螺旋搭接 · 窄边收口',
  'stats':{'attack_speed_mult':1.15,'stamina_mult':.90,'toughness_damage_mult':.85},'special_effects':[]},
 {'id':'layered_cushion_wrap','name':'叠革缓震包覆','description':'深棕皮革包裹薄软垫，横向分节，缝线收在侧面凹槽。',
  'appearance':'棕色皮革 · 分节软垫 · 侧面缝线','stats':{'stamina_mult':.75},'special_effects':[]},
 {'id':'diamond_power_wrap','name':'菱编蓄力包覆','description':'宽皮条交叉编织，形成连续菱纹，暗色衬底连接两端收口。',
  'appearance':'黑褐编革 · 菱纹交叠 · 金属收口',
  'stats':{'attack_speed_mult':1.05,'stamina_mult':1.10,'heavy_charge_speed_bonus':.25},'special_effects':[]}
]
FIELDS={'attack_speed_mult':('攻击速度',False),'stamina_mult':('体力消耗',True),
        'toughness_damage_mult':('韧性伤害',False),'heavy_charge_speed_bonus':('重击蓄力速度',False)}
for option in OPTIONS:
    option['effects']=[]
    for key,value in option['stats'].items():
        delta=value if key=='heavy_charge_speed_bonus' else value-1
        label,lower=FIELDS[key]
        option['effects'].append({'text':f'{label} {delta*100:+.0f}%', 'benefit':1 if ((delta>0)!=lower) else -1})
