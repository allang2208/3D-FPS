#pragma once

#include "CoreMinimal.h"

// Presentation cells are separate from the persistent equipment slot IDs.
namespace ColdSteelEquipmentLayout
{
inline constexpr int32 Columns = 3;
inline constexpr int32 CellCount = 17;
inline constexpr int32 Rows = (CellCount + Columns - 1) / Columns;

inline int32 CellForSlot(int32 Slot)
{
    return Slot == 13 ? 16 : Slot == 15 ? 13 : Slot;
}

inline int32 SlotForCell(int32 Cell)
{
    if (Cell == 13) return 15;
    if (Cell == 16) return 13;
    return Cell >= 0 && Cell < 15 ? Cell : INDEX_NONE;
}

inline int32 StepSlot(int32 Slot, int32 DX, int32 DY)
{
    const int32 Cell = CellForSlot(Slot);
    int32 X = Cell % Columns + DX;
    int32 Y = Cell / Columns + DY;
    while (X >= 0 && X < Columns && Y >= 0 && Y < Rows)
    {
        const int32 Next = SlotForCell(Y * Columns + X);
        if (Next != INDEX_NONE) return Next;
        X += DX;
        Y += DY;
    }
    return Slot;
}
}
