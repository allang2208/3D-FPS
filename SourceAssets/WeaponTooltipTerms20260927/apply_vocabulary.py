"""Replace equivalent UI labels with shared constants, retaining all numeric formulas."""
from pathlib import Path
P=Path(__file__).resolve().parents[2];U=P/'Source/FPSGAME/UI'
files=['ColdSteelItemTooltipData.cpp','ColdSteelItemTooltipSummary.cpp','ColdSteelItemTooltipFormula.cpp',
       'M4BowGunsmith.cpp','M4ToolGunsmith.cpp','M4MeleeGunsmith.cpp','M4GunsmithOverview.cpp',
       'M4GunsmithSelectedDetails.cpp','ColdSteelEnhancementWidget.cpp']
groups={
 'CombatParameters':['近战参数','弓箭参数','长杖参数','枪械参数'],
 'TotalDamage':['武器总伤害','自卫总伤害','满拉武器伤害','普通攻击总伤害','近身物理伤害','当前伤害'],
 'BasePhysical':['基础物理伤害'],'AddedPhysical':['附加物理伤害'],'AddedMagic':['附加魔法伤害'],
 'BaseDamageModifier':['自卫伤害','基础伤害'],
 'AttackInterval':['攻击间隔','挥砍间隔'],'AttackSpeed':['攻击速度','挥砍速度'],'AttackSpeedMultiplier':['挥砍速度倍率'],
 'StaminaCost':['体力消耗','耐力消耗','满拉体力消耗','攻击耐力消耗（含重击）'],
 'BlockStaminaCost':['防御受击耐力消耗'],'AttackDistance':['最大攻击距离'],
 'ADS':['进入 ADS 耗时','开镜耗时'],'ProjectileSpeed':['满拉箭速','子弹速度','弹速'],
 'Capacity':['弹容量','弹匣容量'],'Ammo':['箭种','弹药'],'AmmoEffect':['箭种效果','弹种效果'],
 'AmmoAdjustedDamage':['装填后射击伤害'],'DrawTime':['拉满耗时'],'NockTime':['搭箭耗时'],
 'HoldTime':['满弓保持时间'],'Sway':['瞄准晃动强度'],'HipSpreadAngle':['静止腰射半角'],
 'HipSpreadMultiplier':['腰射散布系数','腰射散布倍率'],'EffectiveRange':['有效射程'],'FlightLimit':['最大飞行距离'],
 'Reload':['普通换弹'],'EmptyReload':['空仓换弹'],'CriticalBonus':['暴击伤害加成']}
for name in files:
    path=U/name;old=path.read_text(encoding='utf8');s=old
    for key,labels in groups.items():
        for label in labels:s=s.replace('TEXT("'+label+'")','ColdSteelWeaponText::'+key)
    if s!=old:
        s='#include "ColdSteelWeaponText.h"\n'+s
        path.write_text(s,encoding='utf8',newline='\n')
        print(name)
bow=P/'Content/ColdSteelData/bows.json';s=bow.read_text(encoding='utf8');s=s.replace('"name": "暗纹猎弓"','"name": "猎手长弓"');bow.write_text(s,encoding='utf8',newline='\n')
tool=P/'Content/ColdSteelData/tool-gunsmith.json';s=tool.read_text(encoding='utf8')
s=s.replace('"text": "自卫伤害','"text": "基础伤害').replace('挥砍速度','攻击速度')
s=s.replace('有效伐木命中达标后获得木材；采集次数不随自卫伤害变化','按伐木伤害扣减树木生命值，归零后获得木材；改造会影响伐木伤害和采集效率')
s=s.replace('有效采矿命中达标后获得石材与矿石；采集次数不随自卫伤害变化','达到所需有效命中后获得石材与矿石；武器总伤害不改变采矿次数')
tool.write_text(s,encoding='utf8',newline='\n')
