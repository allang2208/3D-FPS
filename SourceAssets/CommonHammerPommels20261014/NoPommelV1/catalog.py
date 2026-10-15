"""Shared no-counterweight option; retained end closure is not a weighted pommel."""
MESH_DIR='/Game/Weapons/CommonHammerPommels20261014/NoPommelV1'
OPTION={
 'id':'no_pommel','name':'无配重',
 'description':'移除柄尾配重坠体，握柄末端仅保留贴合安装端的轻薄金属收口。',
 'appearance':'无配重坠体 · 轻薄平整收口',
 'stats':{'attack_speed_mult':1.05,'stamina_mult':.95,'heavy_charge_speed_bonus':.10,'heavy_release_stamina_mult':1.10},
 'effects':[
  {'text':'攻击速度 +5%','benefit':1},
  {'text':'体力消耗 -5%','benefit':1},
  {'text':'重击蓄力速度 +10%','benefit':1},
  {'text':'重击出手体力消耗 +10%','benefit':-1}
 ],
 'special_effects':[]
}
