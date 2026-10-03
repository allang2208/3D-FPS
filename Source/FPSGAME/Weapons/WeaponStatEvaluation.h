#pragma once
#include "CoreMinimal.h"
#include "../UI/ColdSteelInventoryTypes.h"
#include "../Combat/WeaponDamageTypes.h"
class UColdSteelStatusModel;

/** Shared post-processing for runtime weapons and read-only item inspectors. */
namespace ColdSteelWeaponStats
{
    double Damage(const FColdSteelItem& Item,const UColdSteelStatusModel* Model,double WeaponBase);
    FWeaponDamageParts DamageParts(const FColdSteelItem& Item,const UColdSteelStatusModel* Model,double WeaponBase);
    /** 拉弓速度增量 = 改造 + 装备 + 当前弓的附魔，各项相加。 */
    double BowDrawSpeedBonus(const FColdSteelItem* Item,const UColdSteelStatusModel* Model);
    double Interval(const FColdSteelItem* Item,const UColdSteelStatusModel* Model,double WeaponBase);
    /** 换弹时间 = 基础 ÷（敏捷 × 快手 × 附魔 × 改造），各项速度独立相乘。 */
    double Reload(const FColdSteelItem* Item,const UColdSteelStatusModel* Model,double WeaponBase);
    /** 敏捷每点换弹速度 +0.3%；与快手、附魔各自相乘，不相加。 */
    inline constexpr double DexReloadSpeedPerPoint=0.003;
    FString AmmoName(const FString& Definition);
}
