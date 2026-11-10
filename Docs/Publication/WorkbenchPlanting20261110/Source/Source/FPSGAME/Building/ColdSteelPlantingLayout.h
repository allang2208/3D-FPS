#pragma once
#include "CoreMinimal.h"

// Four user-facing planting positions over the unchanged 4x4 save/network cells.
// Existing plants retain their original slot, footprint, transform and identity.
namespace ColdSteelPlantingLayout
{
    inline constexpr int32 Columns=2;
    inline constexpr int32 PlotCount=Columns*Columns;
    inline constexpr int32 StorageColumns=4;
    inline constexpr int32 StorageCount=StorageColumns*StorageColumns;
    inline constexpr int32 CellsPerPlot=4;
    inline bool IsPlot(int32 Plot) {return Plot>=0&&Plot<PlotCount;}
    inline int32 Anchor(int32 Plot) {return IsPlot(Plot)?(Plot/Columns)*8+(Plot%Columns)*2:INDEX_NONE;}
    inline int32 PlotForSlot(int32 Slot)
    {return Slot>=0&&Slot<StorageCount?(Slot/StorageColumns/2)*Columns+(Slot%StorageColumns/2):INDEX_NONE;}
    inline bool IsAnchor(int32 Slot) {return Slot>=0&&Slot==Anchor(PlotForSlot(Slot));}
    inline uint32 Mask(int32 Plot) {return IsPlot(Plot)?(0x33u<<Anchor(Plot)):0u;}
    inline void AppendCells(int32 Plot,TArray<int32>& Cells)
    {
        if(!IsPlot(Plot))return;
        const int32 Start=Anchor(Plot);
        for(int32 Offset:{0,1,StorageColumns,StorageColumns+1})Cells.Add(Start+Offset);
    }
}
