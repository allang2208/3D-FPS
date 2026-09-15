#pragma once
#include "CoreMinimal.h"
#include "InputCoreTypes.h"
#include "ColdSteelQuickBarTypes.generated.h"

USTRUCT()
struct FColdSteelQuickBinding
{
    GENERATED_BODY()
    UPROPERTY() FName Skill;
    UPROPERTY() FString ItemId;
    UPROPERTY() FString ItemDefinition;
    bool IsEmpty() const { return Skill.IsNone() && ItemDefinition.IsEmpty(); }
    bool operator==(const FColdSteelQuickBinding& Other) const
    { return Skill==Other.Skill && ItemId==Other.ItemId && ItemDefinition==Other.ItemDefinition; }
};

struct FColdSteelProfile;
namespace ColdSteelQuickBar
{
    constexpr int32 Count=7, ItemOffset=3;
    bool Migrate(FColdSteelProfile& Profile);
    void MirrorLegacy(FColdSteelProfile& Profile);
    bool Validate(const FColdSteelProfile& Profile,FString& Reason);
    const TCHAR* KeyLabel(int32 Index);
    int32 KeyIndex(const FKey& Key);
}
