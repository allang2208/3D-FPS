#pragma once

#include "HorseRosterTypes.h"

struct FStableTackBonuses
{
    float MaxHealthAdd = 0.f;
    float MaxStaminaAdd = 0.f;
    float SpeedBonus = 0.f;
    float JumpBonus = 0.f;
    float TurnBonus = 0.f;
    float StaminaCostReduction = 0.f;
    float StaminaRecoveryBonus = 0.f;
    float HealRateBonus = 0.f;
    float MountedDamageReduction = 0.f;
    float PotionHealBonus = 0.f;
    int32 RetreatCooldownReductionSeconds = 0;
    int32 EquippedCount = 0;
    bool bFullSet = false;
};

namespace StableHorseGear
{
    inline constexpr int32 Count=4;
    inline constexpr const TCHAR* Definitions[]={TEXT("stable_horseshoes"),TEXT("stable_saddle"),TEXT("stable_barding"),TEXT("stable_saddlebags")};
    inline constexpr const TCHAR* Labels[]={TEXT("马蹄"),TEXT("马鞍"),TEXT("护甲"),TEXT("行囊")};
    inline constexpr const TCHAR* SetId=TEXT("east_gate_cavalry");
    inline constexpr const TCHAR* SetName=TEXT("东门骑兵马具");
    inline constexpr int32 BaseRetreatCooldownSeconds=60;

    inline int32 SlotOf(const FString& Definition)
    {
        for(int32 I=0;I<Count;++I)if(Definition==Definitions[I])return I;
        return INDEX_NONE;
    }
    inline const TCHAR* WorldMesh(const FString& Definition)
    {
        static constexpr const TCHAR* Meshes[]={
            TEXT("/Game/WorldGeneration/TemperateHills/VillageStable/HorseTackR52/SM_Tack_Horseshoes.SM_Tack_Horseshoes"),
            TEXT("/Game/WorldGeneration/TemperateHills/VillageStable/HorseTackR52/SM_Tack_Saddle.SM_Tack_Saddle"),
            TEXT("/Game/WorldGeneration/TemperateHills/VillageStable/HorseTackR52/SM_Tack_Barding.SM_Tack_Barding"),
            TEXT("/Game/WorldGeneration/TemperateHills/VillageStable/HorseTackR52/SM_Tack_Saddlebags.SM_Tack_Saddlebags"),
        };
        const int32 Slot=SlotOf(Definition);
        return Slot!=INDEX_NONE?Meshes[Slot]:TEXT("");
    }
    inline const FColdSteelItem* At(const FStableMountRecord& Horse,int32 Slot)
    {
        return Horse.Equipment.FindByPredicate([Slot](const auto& Item){return SlotOf(Item.Definition)==Slot;});
    }
    inline uint8 TackMask(const FStableMountRecord& Horse)
    {
        return Horse.EquippedTackBitmask();
    }
    inline FStableTackBonuses BonusesFromMask(uint8 Mask)
    {
        FStableTackBonuses B;
        if(Mask&(1u<<0))
        {
            ++B.EquippedCount;
            B.SpeedBonus+=.12f;
            B.JumpBonus+=.10f;
            B.StaminaCostReduction+=.15f;
        }
        if(Mask&(1u<<1))
        {
            ++B.EquippedCount;
            B.MaxStaminaAdd+=60.f;
            B.TurnBonus+=.18f;
            B.StaminaRecoveryBonus+=.20f;
        }
        if(Mask&(1u<<2))
        {
            ++B.EquippedCount;
            B.MaxHealthAdd+=150.f;
            B.MountedDamageReduction+=.18f;
            B.HealRateBonus+=.30f;
        }
        if(Mask&(1u<<3))
        {
            ++B.EquippedCount;
            B.MaxStaminaAdd+=40.f;
            B.HealRateBonus+=.50f;
            B.PotionHealBonus+=.35f;
            B.RetreatCooldownReductionSeconds+=15;
        }
        if(B.EquippedCount==Count)
        {
            B.bFullSet=true;
            B.SpeedBonus+=.05f;
            B.MountedDamageReduction+=.05f;
            B.StaminaCostReduction+=.10f;
        }
        return B;
    }
    inline FStableTackBonuses Bonuses(const FStableMountRecord& Horse)
    {
        return BonusesFromMask(TackMask(Horse));
    }
    inline const TCHAR* ShortSlotEffect(int32 Slot)
    {
        switch(Slot)
        {
        case 0: return TEXT("疾驰+12% · 跃高+10% · 耗耐-15%");
        case 1: return TEXT("耐力+60 · 转向+18% · 回耐+20%");
        case 2: return TEXT("生命+150 · 骑乘减伤18% · 回血+30%");
        case 3: return TEXT("耐力+40 · 回血+50% · 药效+35% · 冷却-15s");
        default: return TEXT("");
        }
    }
    // Gear moves together with the backpack transaction. Roster-only messages
    // may arrive on a different channel before or after the matching item delta.
    inline void CopyEquipment(FStableMountRoster& To,const FStableMountRoster& InventoryVersion)
    {
        TMap<FGuid,const FStableMountRecord*> Equipped;
        for(const auto& Entry:InventoryVersion.Horses)
            if(!Entry.Equipment.IsEmpty())Equipped.Add(Entry.HorseId,&Entry);
        for(auto& Entry:To.Horses)
        {
            if(const auto* From=Equipped.Find(Entry.HorseId))Entry.Equipment=(*From)->Equipment;
            else Entry.Equipment.Reset();
        }
    }
}
