#include "BowStats.h"
#include "../../Combat/CombatItemFormula.h"
#include "Dom/JsonObject.h"
#include "BowCadenceComponent.h"
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

double ColdSteelBow::NockSpeedMultiplier(const UColdSteelStatusModel* Profile)
{
    return FMath::Max(.05,1.+(Profile?Profile->EquipmentBonus(TEXT("bowNockSpeed")):0.));
}

double ColdSteelBow::ChargeStaminaPerSecond(const FColdSteelItem& Item,const UColdSteelStatusModel* Profile)
{
    if(!Profile)return 0.;
    const auto* G=Profile->GetGameInstance()->GetSubsystem<UGunsmithSystem>();
    return Profile->HeavyChargeStaminaPerSecond()*(G?G->Calculate(Item.Definition,G->Installed(Item)).Bow.ChargeStamina:1.);
}

const FGunsmithOption* ColdSteelBow::EclipseRiser(const UColdSteelStatusModel* Profile, const FColdSteelItem* Bow, const FGunsmithParts* PreviewParts)
{
    if (!Profile || !Bow || Bow->Definition != TEXT("bow_frontier_compound")) return nullptr;
    const auto* Gunsmith = Profile->GetGameInstance()->GetSubsystem<UGunsmithSystem>();
    if (!Gunsmith) return nullptr;
    const FString Riser = PreviewParts ? PreviewParts->FindRef(TEXT("riser")) : Gunsmith->Installed(*Bow).FindRef(TEXT("riser"));
    return Riser == TEXT("frontier_eclipse") ? Gunsmith->Option(Bow->Definition, TEXT("riser"), Riser) : nullptr;
}

const FGunsmithOption* ColdSteelBow::AuroraRiser(const UColdSteelStatusModel* Profile, const FColdSteelItem* Bow)
{
    if (!Profile || !Bow || Bow->Definition != TEXT("bow_frontier_compound")) return nullptr;
    const auto Data = CombatItemFormula::ReadOnly(*Bow);
    const TSharedPtr<FJsonObject>* Parts = nullptr;
    FString Riser;
    if (!Data || !Data->TryGetObjectField(TEXT("gunsmith_parts"), Parts)
        || !(*Parts)->TryGetStringField(TEXT("riser"), Riser) || Riser != TEXT("frontier_aurora")) return nullptr;
    const auto* Gunsmith = Profile->GetGameInstance()->GetSubsystem<UGunsmithSystem>();
    return Gunsmith ? Gunsmith->Option(Bow->Definition, TEXT("riser"), Riser) : nullptr;
}

double ColdSteelBow::ArrowRainStaminaPerSecond(const UColdSteelStatusModel& Profile)
{
    const auto* Bow=Profile.ActiveBow();
    return Bow?ChargeStaminaPerSecond(*Bow,&Profile):Profile.HeavyChargeStaminaPerSecond();
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
    S.RhythmWindow=PerfectReleaseWindow*FMath::Max(0.,1.+M.RhythmWindowBonus);
    S.Range=N(TEXT("range_cm"),28000)*M.Range/100.;
    S.CriticalDamageBonus=N(TEXT("critDamageBonus"),0)+M.CriticalDamageBonus;
    S.Nock=FMath::Max(.12,N(TEXT("nock_seconds"),.68))*M.Nock/NockSpeedMultiplier(Profile);
    S.ChargeStamina=(Profile?Profile->HeavyChargeStaminaPerSecond():0.)*M.ChargeStamina;
    S.Speed=N(TEXT("full_speed_cm"),10000)*M.Speed/100;S.Stamina=N(TEXT("stamina_cost"),3)*M.Stamina*(Profile?Profile->ActionStaminaMultiplier():1.f);
    S.Sway=N(TEXT("sway_amplitude_cm"),.9)*M.Sway;S.Spread=FMath::Max(0.,N(TEXT("bow_hip_spread"),.04375))*M.Spread;
    if(const auto* Cadence=UBowCadenceComponent::ForItem(Profile,I))S.Spread*=Cadence->SpreadMultiplier();
    S.ADS=FMath::Max(.01,N(TEXT("bow_ads_in_seconds"),.24))*M.ADS;return S;
}
