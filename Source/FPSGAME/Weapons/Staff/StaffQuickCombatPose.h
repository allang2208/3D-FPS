#pragma once
#include "CoreMinimal.h"
class USkeletalMesh;
class USkeletalMeshComponent;

namespace StaffQuickCombatPose
{
    void CaptureEntry(USkeletalMeshComponent& Arms,uint32 Serial);
    void Apply(USkeletalMeshComponent& Arms,const TArray<FTransform>& Reference,
        TArray<FTransform>& LocalPose,float Age,uint32 Serial);
}
