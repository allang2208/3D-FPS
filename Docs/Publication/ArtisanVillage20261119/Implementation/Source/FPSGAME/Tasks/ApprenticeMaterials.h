#pragma once

#include "CoreMinimal.h"

class UColdSteelStatusModel;
struct FColdSteelCraftingInput;
struct FColdSteelProfile;

namespace ApprenticeMaterials
{
    // The materials, lesson stage and one-time receipt share the inventory save.
    bool Grant(UColdSteelStatusModel& Model, FColdSteelProfile&& Next, const FString& GuestSlot,
        const FString& Receipt, const TArray<FColdSteelCraftingInput>& Inputs, FString& Message);
}
