#pragma once
#include "CoreMinimal.h"

struct FReferenceSkeleton;

namespace FPSUnarmedHandPose
{
// The first-person idle/walk/run bank shares this closed-hand shape.
// Return component-space fingers on the source bind arm for retargeting.
bool Build(const FReferenceSkeleton& Skeleton,FName Hand,TArray<FTransform>& Pose);
}
