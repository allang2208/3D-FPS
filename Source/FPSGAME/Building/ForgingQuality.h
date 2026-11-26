#pragma once
#include "CoreMinimal.h"
struct FColdSteelItem;
struct FColdSteelForgeJob;

namespace ColdSteelForgeQuality
{
    constexpr int32 Version=2;
    constexpr int32 TargetCount=20;
    constexpr double MaxMaterialBonus=.10;
    constexpr double MaxHitBonus=.15;
    constexpr double BonusPerHit=MaxHitBonus/TargetCount;
    constexpr int32 SmithMinPercent=-25, SmithMaxPercent=5;
    double HitBonus(int32 Hits);
    double FromHits(int32 Hits,double MaterialBonus);
    double Multiplier(const FColdSteelForgeJob& Job);
    double Multiplier(const FColdSteelItem& Item);
    FString Label(int32 Hits);
    bool Apply(FColdSteelItem& Item,const FColdSteelForgeJob& Job);
    bool ApplyBlacksmithOffer(FColdSteelItem& Item,int32 QualityPercent);
    void PreserveAuthoritative(TArray<FColdSteelItem>& Incoming,const TArray<FColdSteelItem>& Authority);
}
