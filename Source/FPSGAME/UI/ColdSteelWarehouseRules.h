#pragma once
#include "ColdSteelInventoryTypes.h"
namespace ColdSteelWarehouse
{
    constexpr int32 Place = 4;
    FPSGAME_API bool Insert(TArray<FColdSteelItem>& Items,FColdSteelItem Item,int32 Capacity,int32 Preferred=-1);
    FPSGAME_API FColdSteelProposal Transfer(const TArray<FColdSteelItem>& Items,const FString& Id,int32 Destination,int32 Cell,int32 Capacity,int32 Page=0);
    FPSGAME_API int32 Category(const FColdSteelItem& Item);
}
