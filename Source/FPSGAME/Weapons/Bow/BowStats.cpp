#include "BowStats.h"
#include "../WeaponStatEvaluation.h"
#include "../../UI/ColdSteelStatusModel.h"
#include "Engine/GameInstance.h"

float ColdSteelBow::DrawDamageMultiplier(float DrawFraction)
{
    if (DrawFraction < MinimumFireDrawFraction) return 0.f;
    const float Alpha = (FMath::Clamp(DrawFraction, MinimumFireDrawFraction, 1.f)
        - MinimumFireDrawFraction) / (1.f - MinimumFireDrawFraction);
    return FMath::Lerp(.5f, 1.5f, Alpha);
}

ColdSteelBow::FStats ColdSteelBow::Evaluate(const FColdSteelItem& Item,const UColdSteelStatusModel* Profile,const FGunsmithParts* Override)
{
    const auto* G=Profile?Profile->GetGameInstance()->GetSubsystem<UGunsmithSystem>():nullptr;
    const auto I=G?G->ResolveBowVisual(Item,Override):Item;
    const auto M=G?G->Calculate(I.Definition,G->Installed(I)).Bow:FGunsmithStats::FBowModifiers();
    auto N=[&](const TCHAR* Key,double Default){return ColdSteelInventory::Number(I,Key,Default);};
    FStats S;S.Damage=ColdSteelWeaponStats::DamageParts(I,Profile,N(TEXT("full_damage"),69)).Scaled(DrawDamageMultiplier(1.f));
    S.Draw=FMath::Max(.3,ColdSteelWeaponStats::Interval(&I,Profile,N(TEXT("draw_seconds"),1.4)));
    S.DrawSpeedBonus=ColdSteelWeaponStats::BowDrawSpeedBonus(&I,Profile);
    S.Nock=FMath::Max(.12,N(TEXT("nock_seconds"),.68))*M.Nock;S.Hold=FMath::Max(0.,N(TEXT("hold_seconds"),2.2))*M.Hold;
    S.Speed=N(TEXT("full_speed_cm"),9800)*M.Speed/100;S.Stamina=N(TEXT("stamina_cost"),3)*M.Stamina;
    S.Sway=N(TEXT("sway_amplitude_cm"),.9)*M.Sway;S.Spread=FMath::Max(0.,N(TEXT("bow_hip_spread"),.035))*M.Spread;
    S.ADS=FMath::Max(.01,N(TEXT("bow_ads_in_seconds"),.24))*M.ADS;return S;
}
