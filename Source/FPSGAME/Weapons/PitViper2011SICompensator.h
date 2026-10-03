#pragma once
#include "CoreMinimal.h"

class USkeletalMeshComponent;

namespace PitViper2011SICompensator
{
    inline constexpr const TCHAR* Part = TEXT("pit_viper_si_compensator");
    inline constexpr const TCHAR* MeshPath = TEXT("/Game/Weapons/PitViper2011/SICompensator20261003/SM_PitViper2011_SICompensator");
    inline constexpr float MountOffsetCM = -1.72186285f;
    void ShowFactory(USkeletalMeshComponent* Host, bool bVisible);
}
