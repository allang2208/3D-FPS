#pragma once
#include "../UI/ColdSteelInventoryTypes.h"
#include "../UI/ColdSteelItemReadCache.h"
#include "../Combat/WeaponDamageTypes.h"
#include "Dom/JsonObject.h"

namespace ConicalHammerSeat
{
    inline constexpr const TCHAR* Part=TEXT("conical_seat");
    inline void PrepareQuickDamage(FWeaponDamageParts& Panel)
    {
        // The thrust substitutes the physical panel into the quick-melee formula.
        // Preserve its physical base/additional split without redistributing that
        // scalar into the host hammer's unrelated magical damage channels.
        Panel.BaseMagic=Panel.AddedMagic=0.;
    }
    inline bool Installed(const FColdSteelItem* Item)
    {
        if(!Item||!ColdSteelInventory::IsTwoHandedBlunt(*Item))return false;
        const auto Data=ColdSteelItemData::Read(Item->Data);
        const TSharedPtr<FJsonObject>* Parts=nullptr;FString Id;
        return Data&&Data->TryGetObjectField(TEXT("gunsmith_parts"),Parts)
            &&(*Parts)->TryGetStringField(TEXT("head_mount"),Id)&&Id==Part;
    }
    inline FVector StrikeLocal(const FString& Definition)
    {
        // Authored cone tips in WPN_root space (native mesh units), before
        // the retained per-host bone mount converts to viewmodel centimetres.
        if(Definition==TEXT("ue_runebound_warhammer"))return FVector(-.0004452141,0.,1.078175);
        if(Definition==TEXT("ue_thunder_god_hammer"))return FVector(-.0004452141,0.,1.166325);
        return FVector(0.,0.,1.0962);
    }
}
