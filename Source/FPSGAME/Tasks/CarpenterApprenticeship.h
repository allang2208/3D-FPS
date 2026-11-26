#pragma once

#include "CoreMinimal.h"

struct FColdSteelProfile;
class UColdSteelStatusModel;

namespace CarpenterApprenticeship
{
    enum class EStage : uint8 { NotStarted, Materials, Working, Finish, Complete };
    inline constexpr TCHAR TargetRecipe[] = TEXT("woodwork_staff");

    inline constexpr TCHAR TaskId[] = TEXT("village.carpenter.apprenticeship");
    bool Reset(FColdSteelProfile& Profile);
    EStage Stage(const FColdSteelProfile& Profile);
    bool NeedsSupplies(const FColdSteelProfile& Profile);
    void NormalizeImportedProfile(FColdSteelProfile& Profile);
    bool Accept(UColdSteelStatusModel* Model, const FString& HostSlot, FString& Message);

    // Called on the pending profile before the workstation commits the same workpiece.
    void WorkpieceUpdated(FColdSteelProfile& Profile);
    void WorkpieceRemoved(FColdSteelProfile& Profile,bool bClaimed);
}
