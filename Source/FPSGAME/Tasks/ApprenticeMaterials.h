#pragma once

#include "CoreMinimal.h"

class UColdSteelStatusModel;
struct FColdSteelCraftingInput;
struct FColdSteelProfile;

namespace ApprenticeMaterials
{
    // A workpiece already on the bench at reset stays collectible outside the new lesson.
    inline FString PriorWorkpieceKey(const FString& JobId) { return TEXT("village.lesson.prior-workpiece.") + JobId; }

    // The materials, lesson stage and one-time receipt share the inventory save.
    bool Grant(UColdSteelStatusModel& Model, FColdSteelProfile&& Next, const FString& GuestSlot,
        const FString& Receipt, const TArray<FColdSteelCraftingInput>& Inputs, FString& Message);
}
