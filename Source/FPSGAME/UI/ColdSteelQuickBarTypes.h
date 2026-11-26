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
    // 2026-11-17: Q/E/X retired. Slots 0..ItemOffset-1 stay in the 13-slot save layout but are unused;
    // version 3 moves their old bindings to the first free number slot (1-0).
    constexpr int32 Count=13, ItemOffset=3, LegacyCount=7, Version=3;
    bool Migrate(FColdSteelProfile& Profile);
    void MirrorLegacy(FColdSteelProfile& Profile);
    bool Validate(const FColdSteelProfile& Profile,FString& Reason);
    const TCHAR* KeyLabel(int32 Index);
    FKey Key(int32 Index);
    int32 KeyIndex(const FKey& Key);
}
