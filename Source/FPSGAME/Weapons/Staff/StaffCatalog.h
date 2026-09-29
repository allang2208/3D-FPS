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
    inline bool IsStaff(const FColdSteelItem& I){return ColdSteelInventory::Text(I,TEXT("weaponType"))==TEXT("staff");}
}
