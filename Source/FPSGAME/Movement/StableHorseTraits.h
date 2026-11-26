#pragma once
#include "CoreMinimal.h"

// Each birth roll has its own stream; version zero retains the original names and base traits.
struct FStableHorseTraits
{
    float Strength=10, Agility=10, Intelligence=10, Constitution=10, Spirit=10, Luck=10;
    static constexpr int32 NameCount=50;
    static constexpr uint8 IndependentRolls=1;
    static constexpr int32 MaxLevel=50;
    static int32 NameIndex(const FGuid& Id,uint8 BirthVersion);
    static const TCHAR* Name(const FGuid& Id,uint8 BirthVersion);
    static FStableHorseTraits FromId(const FGuid& Id,uint8 BirthVersion,int32 Level=1);
    static FStableHorseTraits Growth(const FGuid& Id);
    static FStableHorseTraits EffectiveGrowth(const FGuid& Id);
    int32 MarketPrice(const FStableHorseTraits& PerLevel) const;
    float HealthLimit() const { return 300.f+12.f*(Constitution-10); }
    float StaminaLimit() const { return 300.f+8.f*(Constitution-10)+4.f*(Spirit-10); }
    float JumpRise() const { return 220.f+5.f*(Strength-10); }
    float SpeedScale() const { return 1.f+.025f*(Agility-10); }
    float TurnScale() const { return 1.f+.035f*(Intelligence-10); }
    float RecoveryScale() const { return 1.f+.05f*(Spirit-10); }
    float HealingScale() const { return 1.f+.06f*(Luck-10); }
    float CanterSpeed() const { return 1160.f*SpeedScale(); }
    FString RatingsText() const;
    FString PerformanceText() const;
};
