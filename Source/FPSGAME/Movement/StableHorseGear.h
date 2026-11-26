#pragma once

#include "HorseRosterTypes.h"

namespace StableHorseGear
{
    inline constexpr int32 Count=4;
    inline constexpr const TCHAR* Definitions[]={TEXT("stable_horseshoes"),TEXT("stable_saddle"),TEXT("stable_barding"),TEXT("stable_saddlebags")};
    inline constexpr const TCHAR* Labels[]={TEXT("马蹄"),TEXT("马鞍"),TEXT("护甲"),TEXT("行囊")};
    inline int32 SlotOf(const FString& Definition)
    {
        for(int32 I=0;I<Count;++I)if(Definition==Definitions[I])return I;
        return INDEX_NONE;
    }
    inline const FColdSteelItem* At(const FStableMountRecord& Horse,int32 Slot)
    {
        return Horse.Equipment.FindByPredicate([Slot](const auto& Item){return SlotOf(Item.Definition)==Slot;});
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
