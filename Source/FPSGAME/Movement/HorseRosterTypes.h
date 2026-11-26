#pragma once
#include "CoreMinimal.h"
#include "StableHorseTraits.h"
#include "StableHorseAffixes.h"
#include "../UI/ColdSteelItemInstance.h"
#include "HorseRosterTypes.generated.h"

USTRUCT()
struct FStableMountRecord
{
    GENERATED_BODY()
    UPROPERTY() FGuid HorseId;
    UPROPERTY() FGuid SourceResident; // Set on binding a placed horse; older personal records start unbound.
    UPROPERTY() int64 RecallAfterUtc=0; // UTC ticks survive travel, logout and server restarts.
    UPROPERTY() uint8 Stall=0; // Display provenance only.

    UPROPERTY() TArray<FColdSteelItem> Equipment;
    UPROPERTY() float Health=300.f;
    UPROPERTY() float Stamina=300.f;
    UPROPERTY() bool bExhausted=false;
    UPROPERTY() float MaxHealth=300.f;
    UPROPERTY() float MaxStamina=300.f;
    // Missing tagged properties in existing saves retain the legacy birth projection.
    UPROPERTY() uint8 BirthVersion=0;
    UPROPERTY() int32 Level=1;
    UPROPERTY() int64 Experience=0;
    FStableHorseTraits Traits() const { return FStableHorseTraits::FromId(HorseId,BirthVersion,Level); }
    FStableHorseAffixBonuses AffixBonuses() const { return StableHorseAffixes::Bonuses(HorseId); }
    int32 BagRows() const { return StableHorseAffixes::BagRowsForHorse(HorseId); }
    FString BagContainerKey() const { return StableHorseAffixes::BagContainerKey(HorseId); }
    int32 BirthPrice() const
    {
        const auto Base=FStableHorseTraits::FromId(HorseId,BirthVersion);
        const auto Affix=StableHorseAffixes::Bonuses(HorseId);
        if(BirthVersion)return FMath::Max(400,Base.MarketPrice(FStableHorseTraits::EffectiveGrowth(HorseId))+Affix.PriceDelta);
        // The old price is only shown on a lot already bought before the update.
        return FMath::Max(400,1000+30*FMath::RoundToInt(Base.Strength+Base.Agility+Base.Intelligence+
            Base.Constitution+Base.Spirit+Base.Luck-36.f)+Affix.PriceDelta);
    }
    static int64 ExperienceNeeded(int32 L) { return (20ll+20ll*L+12ll*L*L)*8; }
    bool GainExperience(int64 Amount)
    {
        if(Amount<=0 || Level>=FStableHorseTraits::MaxLevel)return false;
        Experience+=FMath::Min(Amount,MAX_int64-Experience);
        const int32 Previous=Level;
        while(Level<FStableHorseTraits::MaxLevel && Experience>=ExperienceNeeded(Level))
        {
            Experience-=ExperienceNeeded(Level);
            ++Level;
        }
        if(Level==FStableHorseTraits::MaxLevel)Experience=0;
        if(Level!=Previous)ApplyBirthLimits();
        return true;
    }
    FString DisplayName() const
    {
        return FStableHorseTraits::Name(HorseId,BirthVersion);
    }
    uint8 EquippedTackBitmask() const
    {
        uint8 Mask=0;
        for(const auto& Item:Equipment)
        {
            if(Item.Definition==TEXT("stable_horseshoes"))Mask|=1u<<0;
            else if(Item.Definition==TEXT("stable_saddle"))Mask|=1u<<1;
            else if(Item.Definition==TEXT("stable_barding"))Mask|=1u<<2;
            else if(Item.Definition==TEXT("stable_saddlebags"))Mask|=1u<<3;
        }
        return Mask;
    }
    bool ApplyBirthLimits()
    {
        const auto Rated=Traits();
        const auto Affix=StableHorseAffixes::Bonuses(HorseId);
        const uint8 Mask=EquippedTackBitmask();
        const float TargetMaxHealth=Rated.HealthLimit()*Affix.HealthMultiplier+((Mask&(1u<<2))?150.f:0.f);
        const float TargetMaxStamina=Rated.StaminaLimit()*Affix.StaminaMultiplier+((Mask&(1u<<1))?60.f:0.f)+((Mask&(1u<<3))?40.f:0.f);
        if(FMath::IsNearlyEqual(MaxHealth,TargetMaxHealth) && FMath::IsNearlyEqual(MaxStamina,TargetMaxStamina))return false;
        const float PrevHealth=Health;
        Health=TargetMaxHealth*FMath::Clamp(Health/FMath::Max(1.f,MaxHealth),0.f,1.f);
        if(PrevHealth>0.f && Health<1.f)Health=1.f;
        Stamina=TargetMaxStamina*FMath::Clamp(Stamina/FMath::Max(1.f,MaxStamina),0.f,1.f);
        MaxHealth=TargetMaxHealth;MaxStamina=TargetMaxStamina;
        return true;
    }
    bool Cooling(int64 Now) const {return RecallAfterUtc>Now;}
    static FGuid LegacyId(FGuid Owner,uint8 OldStall)
    {return FGuid::NewDeterministicGuid(FString::Printf(TEXT("StableR22/%s/%u"),*Owner.ToString(),OldStall));}
};

USTRUCT()
struct FStableMountRoster
{
    GENERATED_BODY()
    UPROPERTY() TArray<FStableMountRecord> Horses;
    UPROPERTY() FGuid Deployed;
    UPROPERTY() uint8 Selected=0; // Read once when upgrading R22 profiles.
    bool Upgrade(FGuid Owner)
    {
        bool Changed=false;
        for(auto& Horse:Horses)
        {
            if(!Horse.HorseId.IsValid())
            {
                Horse.HorseId=FStableMountRecord::LegacyId(Owner,Horse.Stall);
                if(Selected==Horse.Stall)Deployed=Horse.HorseId;
                Changed=true;
            }
            Changed|=Horse.ApplyBirthLimits();
        }
        if(Selected){Selected=0;Changed=true;}
        return Changed;
    }
    UPROPERTY() int64 Revision=0;
    void ClearVolatileCondition()
    {
        for(auto& Horse:Horses){Horse.Health=0.f;Horse.Stamina=0.f;Horse.bExhausted=false;}
    }
    const FStableMountRecord* Find(FGuid Id) const
    { return Horses.FindByPredicate([Id](const auto& Horse){return Horse.HorseId==Id;}); }
    FStableMountRecord* Find(FGuid Id)
    { return Horses.FindByPredicate([Id](const auto& Horse){return Horse.HorseId==Id;}); }
};
