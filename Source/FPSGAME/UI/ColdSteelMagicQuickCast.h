#pragma once
#include "CoreMinimal.h"

struct FColdSteelProfile;
namespace ColdSteelMagicQuickCast
{
    constexpr int32 Count=10;
    constexpr int32 Version=1;
    constexpr int32 StaffInput=-2;
    bool IsMagic(FName Skill);
    bool Migrate(FColdSteelProfile& Profile);
    bool Validate(const FColdSteelProfile& Profile,FString& Reason);
}
