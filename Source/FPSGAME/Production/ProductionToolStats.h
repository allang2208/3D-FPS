#pragma once
#include "CoreMinimal.h"
#include "../UI/ColdSteelInventoryTypes.h"
#include "../Combat/WeaponDamageTypes.h"
#include "../Weapons/GunsmithSystem.h"

struct FProductionResource;
class UColdSteelStatusModel;

/**
 * 采集工具（伐木斧、矿镐）改造后的实值快照。
 *
 * 采集链路（所需命中、产出、采集距离与宽容半径）和自卫链路（伤害面板、挥砍节奏、
 * 体力、暴击与削韧）都读这一份结果，UI 与实战不各自换算——与剑类的
 * `ColdSteelMelee::Evaluate` 同一分工。未登记进工具目录的物品（铁铲）返回出厂值。
 */
struct FProductionToolStats
{
    FToolModifiers Modifiers;
    /** 自卫伤害面板：工具基础公式 × 改造倍率，再走附魔／加工／附加伤害后处理。 */
    FWeaponDamageParts Damage;
    /** 作者节奏 ÷ 挥砍速度倍率；组件按 RateScale 在作者时间与真实时间之间换算。 */
    double SwingSeconds=1.1, ContactSeconds=.48, RateScale=1;
    double StaminaCost=10;
    double HarvestReachCM=320, HarvestRadiusCM=0, CombatReachCM=180, CombatRadiusCM=0;
    double HarvestYield=1, BonusHarvestChance=0, ToughnessDamage=1, CriticalChanceAdd=0;
    int32 HarvestHitsAdd=0;
    /** 该工具是否登记进改造目录（铁铲没有目录条目，永远 false）。 */
    bool bModifiable=false;
};

namespace ColdSteelTool
{
    bool Supports(const FColdSteelItem& Item);
    FProductionToolStats Evaluate(const FColdSteelItem& Item,const UColdSteelStatusModel* Profile,const FGunsmithParts* Preview=nullptr);
    /** 当前手持工具的实值；没有工具时返回出厂默认。 */
    FProductionToolStats EvaluateActive(const UColdSteelStatusModel* Profile,const FGunsmithParts* Preview=nullptr);
    /** 所需有效命中 = 出厂值 + 改造加值，最少 1 次。 */
    int32 HitsNeeded(const FProductionResource& Target,const FProductionToolStats& Stats);
    /** 同上，出厂值由调用方给出（表土 1 次，树与岩块 `FProductionResource::RequiredHits`）。 */
    int32 HitsNeeded(int32 Factory,const FProductionToolStats& Stats);
    /** 采集产出 = 出厂数量 × 产出倍率，四舍五入，最少 1。 */
    int64 Yield(int64 Factory,const FProductionToolStats& Stats);
}
