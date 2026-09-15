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
    FVector GatherWrist{33,-24,-26}, ReleaseWrist{54,-22,-19}, WithdrawWrist{23,-35,-37};
    FVector WindupWrist{29,-28,-28}, ReleaseShoulder{10.8,-19,-19}, ReleaseElbowPole{14,-43,-42};
    FVector GatherDepart{-4,-7,-5}, GatherApproach{-8,-3,-2};
    FVector WindupDepart{-3,-6,-3}, WindupApproach{-4,-2,-2}, RecoveryDepart{-9,-5,-3};
    FVector GatherForward{.94,.22,.20}, GatherNormal{-.20,0,.98};
    FVector ReleaseForward{1,.02,-.04}, ReleaseMidNormal{0,-1,0}, ReleaseNormal{0,0,-1};
    FVector OrbOffset{12,0,18};
    TMap<FName,FFireballDigitPose> Digits;
    void Load();
    FQuat PalmFrame(float ReleaseAlpha) const;
};
