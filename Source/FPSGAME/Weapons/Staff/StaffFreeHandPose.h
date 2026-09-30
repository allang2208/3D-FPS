#pragma once
#include "CoreMinimal.h"
class USkeletalMesh;

namespace StaffFreeHandPose
{
    // Apply before local-to-component conversion. The native full left chain
    // preserves segment lengths while the wrist swings through the lower-left view.
    void Apply(USkeletalMesh* Mesh,const TArray<FTransform>& Reference,
        TArray<FTransform>& LocalPose,float StridePhase,float MoveWeight,float RunWeight,float MotionTime);
}
