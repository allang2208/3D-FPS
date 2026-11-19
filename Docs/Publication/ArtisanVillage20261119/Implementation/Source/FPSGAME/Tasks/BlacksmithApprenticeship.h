#pragma once

#include "CoreMinimal.h"

struct FColdSteelProfile;
class UColdSteelStatusModel;

namespace BlacksmithApprenticeship
{
    enum class EStage : uint8 { NotStarted, Materials, Hammering, Finish, Complete };
    inline constexpr TCHAR TargetRecipe[] = TEXT("forge_tang_dao");

    EStage Stage(const FColdSteelProfile& Profile);
    bool NeedsSupplies(const FColdSteelProfile& Profile);
    void NormalizeImportedProfile(FColdSteelProfile& Profile);
    bool Accept(UColdSteelStatusModel* Model,const FString& HostSlot,FString& Message);
    // Called on the forge's pending profile, before its existing transaction commits.
    void WorkpieceUpdated(FColdSteelProfile& Profile);
    void WorkpieceRemoved(FColdSteelProfile& Profile,bool bClaimed);
}
