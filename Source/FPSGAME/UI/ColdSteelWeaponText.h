#pragma once
#include "CoreMinimal.h"

// Shared player-facing vocabulary for tooltip summaries, details and workbenches.
// Labels describe the statistic; attack/charge conditions belong in the scope text.
// Do not merge different measurements (flight limit vs full-damage range, angle vs multiplier).
namespace ColdSteelWeaponText
{
inline constexpr const TCHAR* CombatParameters=TEXT("战斗参数");
inline constexpr const TCHAR* TotalDamage=TEXT("武器总伤害");
inline constexpr const TCHAR* BasePhysical=TEXT("基础物理伤害");
inline constexpr const TCHAR* AddedPhysical=TEXT("附加物理伤害");
inline constexpr const TCHAR* AddedMagic=TEXT("附加魔法伤害");
inline constexpr const TCHAR* BaseDamageModifier=TEXT("基础伤害");
inline constexpr const TCHAR* ForgeQuality=TEXT("锻造品质");
inline constexpr const TCHAR* ForgeDamageModifier=TEXT("锻造伤害修正");
inline constexpr const TCHAR* AttackInterval=TEXT("攻击间隔");
inline constexpr const TCHAR* AttackSpeed=TEXT("攻击速度");
inline constexpr const TCHAR* AttackSpeedMultiplier=TEXT("攻击速度倍率");
inline constexpr const TCHAR* StaminaCost=TEXT("体力消耗");
inline constexpr const TCHAR* BlockStaminaCost=TEXT("格挡体力消耗");
inline constexpr const TCHAR* AttackDistance=TEXT("最大攻击距离");
inline constexpr const TCHAR* ADS=TEXT("开镜耗时");
inline constexpr const TCHAR* ProjectileSpeed=TEXT("弹速");
inline constexpr const TCHAR* Capacity=TEXT("弹匣容量");
inline constexpr const TCHAR* Ammo=TEXT("弹药");
inline constexpr const TCHAR* AmmoEffect=TEXT("弹种效果");
inline constexpr const TCHAR* AmmoAdjustedDamage=TEXT("弹药修正后伤害");
inline constexpr const TCHAR* DrawTime=TEXT("拉弓耗时");
inline constexpr const TCHAR* NockTime=TEXT("搭箭耗时");
inline constexpr const TCHAR* HoldTime=TEXT("满弓保持时间");
inline constexpr const TCHAR* Sway=TEXT("瞄准晃动强度");
inline constexpr const TCHAR* HipSpreadAngle=TEXT("腰射散布半角");
inline constexpr const TCHAR* HipSpreadMultiplier=TEXT("腰射散布倍率");
inline constexpr const TCHAR* EffectiveRange=TEXT("有效射程");
inline constexpr const TCHAR* FlightLimit=TEXT("最大飞行距离");
inline constexpr const TCHAR* Reload=TEXT("普通换弹");
inline constexpr const TCHAR* EmptyReload=TEXT("空仓换弹");
inline constexpr const TCHAR* CriticalBonus=TEXT("暴击伤害加成");
inline constexpr const TCHAR* DamageComposition=TEXT("伤害组成");
inline constexpr const TCHAR* BowScope=TEXT("按当前角色、强化和改造计算；弓以满弓单箭为准，武器总伤害已计满弓蓄力倍率，拉弓耗时、弹速和体力消耗也以满弓为准。未计弹种倍率、暴击和目标防御；腰射散布取站立静止值。");
}
