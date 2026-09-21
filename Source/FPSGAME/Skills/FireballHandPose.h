#pragma once
#include "CoreMinimal.h"

// Semantic palm coordinates keep this pose independent of FBX bone axes.
struct FFireballDigitPose
{
    FVector Spread=FVector::ZeroVector, GatherFlex=FVector(6,11,14), ReleaseFlex=FVector(2,4,6);
};
struct FFireballHandPose
{
    FVector Shoulder{-3.2,-19,-19}, ElbowPole{0,-43,-42};
    FVector GatherWrist{33,-24,-26}, ReleaseWrist{44,-20,-17};
    FVector WindupWrist{29,-28,-28}, ReleaseShoulder{6,-19,-19}, ReleaseElbowPole{18,-25,-52};
    FVector GatherDepart{-4,-7,-5}, GatherApproach{-8,-3,-2};
    FVector WindupDepart{-3,-6,-3}, WindupApproach{-4,-2,-2};
    FVector RecoveryDepart{-8,-2,-3}, RecoveryApproach{-4,-5,-3};
    FVector GatherForward{.94,.22,.20}, GatherNormal{-.20,0,.98};
    FVector ReleaseForward{.25,.04,.967}, ReleaseMidNormal{0,-1,0}, ReleaseNormal{.968,0,-.25};
    FVector OrbOffset{12,0,18};
    TMap<FName,FFireballDigitPose> Digits;
    void Load();
    FQuat PalmFrame(float ReleaseAlpha) const;
};
