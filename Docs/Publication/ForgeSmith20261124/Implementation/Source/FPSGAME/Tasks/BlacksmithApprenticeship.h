#pragma once

#include "CoreMinimal.h"

struct FColdSteelProfile;
struct FColdSteelItem;
class UColdSteelStatusModel;

namespace BlacksmithApprenticeship
{
    // Preserve the saved v1–v3 values. Mining..ReturnOre encode 0..10 collected ore.
    enum class EStage : uint8 { NotStarted, Materials, Hammering, Finish, Complete, Smelting, OneIngot, TwoIngots, Mining, ReturnOre=18 };
    constexpr int32 RequiredOre = 10;
    bool IsMining(EStage Value);
    int32 OreCollected(EStage Value);
    bool InsertPickup(FColdSteelProfile& Profile,FColdSteelItem Item);
    constexpr int32 RequiredIngots = 3;
    int32 LessonStep(EStage Stage);
    int32 IngotsCollected(EStage Stage);
    void CollectIngots(FColdSteelProfile& Profile, int64 Count);
    inline constexpr TCHAR TargetRecipe[] = TEXT("forge_forged_steel_greatsword");

    inline constexpr TCHAR TaskId[] = TEXT("village.blacksmith.apprenticeship");
    bool Reset(FColdSteelProfile& Profile);
    EStage Stage(const FColdSteelProfile& Profile);
    bool NeedsSupplies(const FColdSteelProfile& Profile);
    void NormalizeImportedProfile(FColdSteelProfile& Profile);
    bool Accept(UColdSteelStatusModel* Model,const FString& HostSlot,FString& Message);
    // Called on the forge's pending profile, before its existing transaction commits.
    void WorkpieceUpdated(FColdSteelProfile& Profile);
    void WorkpieceRemoved(FColdSteelProfile& Profile,bool bClaimed);
}
