#pragma once
#include "CoreMinimal.h"

/** A confirmed local inventory gain. Presentation never grants the item. */
struct FColdSteelAcquisitionNotice
{
    FString Key;
    FString Name;
    int64 Count = 0;
    FLinearColor Color = FLinearColor::White;
};
