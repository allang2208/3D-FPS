"""Legendary head exclusive to the existing steel warhammer."""
MESH_DIR='/Game/Weapons/SteelWarhammerLegendaryHeads20261014/MeteorCore/BuildV1'
OPTION={
 'id':'meteor_core','name':'陨星熔核',
 'description':'八棱陨铁锤面嵌有星纹浮雕，青铜符箍束住承力笼架，暗橙熔光从内部陨石裂隙间缓缓流转。',
 'appearance':'八棱星纹锤面 · 青铜符箍 · 熔岩裂隙',
 'stats':{
  'physical_damage_mult':1.40,
  'attack_speed_mult':0.85,
  'stamina_mult':1.25,
  'toughness_damage_mult':1.40,
  'shockwave_radius_mult':1.50
 },'effects':[],'special_effects':[]
}
FIELDS={
 'physical_damage_mult':('物理伤害',False),
 'attack_speed_mult':('攻击速度',False),
 'stamina_mult':('体力消耗',True),
 'toughness_damage_mult':('韧性伤害',False)
}
OPTION['effects']=[
 {'text':f'{FIELDS[key][0]} {(value-1)*100:+.0f}%',
  'benefit':1 if ((value>1)!=FIELDS[key][1]) else -1}
 for key,value in OPTION['stats'].items() if key in FIELDS
]
OPTION['special_effects']=[
 f"震荡扩散｜重击与冲刺攻击的冲击波范围增加{(OPTION['stats']['shockwave_radius_mult']-1)*100:.0f}%。"
]
MATERIALS={
 'M_SteelWarhammerSurface':'/Game/Weapons/SteelWarhammer20261014/Materials/M_SteelWarhammerSurface',
 'M_CommonHammerHeadSteel':'/Game/Weapons/CommonHammerHeads20261014/Materials/M_CommonHammerHeadSteel',
 'M_MeteorBronze':MESH_DIR+'/Materials/M_MeteorBronze',
 'M_MeteorRuneBand':MESH_DIR+'/Materials/M_MeteorRuneBand',
 'M_MeteorLavaCore':MESH_DIR+'/Materials/M_MeteorLavaCore'
}
