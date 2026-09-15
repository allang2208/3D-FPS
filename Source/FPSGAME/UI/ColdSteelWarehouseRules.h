#pragma once
#include "ColdSteelInventoryTypes.h"
namespace ColdSteelWarehouse
{
    constexpr int32 Place = 4;
    constexpr int32 Columns = 18;
    constexpr int32 Rows = 12;
    constexpr int32 CellsPerPage = Columns * Rows;
    constexpr int32 MaxPages = 5000;
    FPSGAME_API bool Fits(const TArray<FColdSteelItem>& Items,const FColdSteelItem& Item,int32 Cell,int32 Capacity);
    FPSGAME_API bool MigrateLayout(FColdSteelProfile& Profile);
    FPSGAME_API bool Insert(TArray<FColdSteelItem>& Items,FColdSteelItem Item,int32 Capacity,int32 Preferred=-1);
    FPSGAME_API FColdSteelProposal Transfer(const TArray<FColdSteelItem>& Items,const FString& Id,int32 Destination,int32 Cell,int32 Capacity,int32 Page=0);
    FPSGAME_API int32 Category(const FColdSteelItem& Item);
}
