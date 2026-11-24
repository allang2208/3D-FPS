#pragma once
#include "../GunsmithSystem.h"
#include "../WeaponDamagePanel.h"
class UColdSteelStatusModel;
namespace ColdSteelBow
{
inline constexpr float MinimumFireDrawFraction = .5f;
inline constexpr float PerfectReleaseWindow = .20f;
// 命中节拍不再加成伤害：下一次拉弓速度 +25%，与其它拉弓速度加成同一乘区。
inline constexpr float PerfectNextDrawSpeedBonus = .25f;
inline float DrawSpeedScale(bool bPendingBonus)
{
    return bPendingBonus ? 1.f/(1.f+PerfectNextDrawSpeedBonus) : 1.f;
}
inline bool IsPerfectRelease(float Elapsed,float FullDrawSeconds,float WindowSeconds=PerfectReleaseWindow)
{
    return FMath::IsFinite(Elapsed) && Elapsed >= FullDrawSeconds
        && Elapsed <= FullDrawSeconds + WindowSeconds;
}
// Below half draw no arrow can launch. Half draw deals 50%, full draw 150%.
float DrawDamageMultiplier(float DrawFraction);
// Equipment speed divides the nocking clock; 50% faster means time / 1.5.
double NockSpeedMultiplier(const UColdSteelStatusModel* Profile);
double ChargeStaminaPerSecond(const FColdSteelItem& Item,const UColdSteelStatusModel* Profile);
double ArrowRainStaminaPerSecond(const UColdSteelStatusModel& Profile);
const FGunsmithOption* AuroraRiser(const UColdSteelStatusModel* Profile, const FColdSteelItem* Bow);
const FGunsmithOption* EclipseRiser(const UColdSteelStatusModel* Profile, const FColdSteelItem* Bow, const FGunsmithParts* PreviewParts=nullptr);
struct FStats
{
    // Full-draw panel; the shot snapshot remains the uncharged weapon baseline.
    FWeaponDamageParts Damage;
    double Draw=1.4,Nock=.68,ChargeStamina=0,Speed=100,Stamina=3,Sway=.9,Spread=.04375,ADS=.24;
    double DrawSpeedBonus=0;
    double RhythmWindow=PerfectReleaseWindow;
    double Range=280,CriticalDamageBonus=0;
};
FStats Evaluate(const FColdSteelItem& Item,const UColdSteelStatusModel* Profile,const FGunsmithParts* Override=nullptr);
}
