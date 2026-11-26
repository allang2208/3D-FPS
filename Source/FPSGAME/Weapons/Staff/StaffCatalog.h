#pragma once
#include "CoreMinimal.h"
#include "Dom/JsonObject.h"
#include "../../UI/ColdSteelInventoryTypes.h"

namespace ColdSteelStaff
{
    using FParts=TMap<FString,FString>;
    FPSGAME_API TSharedPtr<FJsonObject> Catalog();
    FPSGAME_API FParts Installed(const FColdSteelItem& Item);
    FPSGAME_API FColdSteelItem Resolve(const FColdSteelItem& Item,const FParts* Draft=nullptr);
    FPSGAME_API void ApplyEquipmentDefinition(FJsonObject& Data,const FJsonObject& Definition);
    using ColdSteelInventory::IsStaff;
    inline const FString& CanonicalDefinition(const FString& Id)
    {
        static const FString Apprentice=TEXT("ue_apprentice_staff");
        return Id==TEXT("apprentice_staff")||Id==TEXT("weapon20")?Apprentice:Id;
    }
}
