#pragma once
#include "FireballCastMotion.h"

struct FPowerFistDigitPose
{
    FVector Flex=FVector::ZeroVector,Spread=FVector::ZeroVector;
    float CloseDelay=0.f;
};

// Same camera-space source parameters as LeftHandPowerFist20260923. Applied
// only to the left arm, so each weapon keeps its live right-hand animation.
struct FLeftHandPowerFistMotion
{
    float Duration=1.f,LiftStart=.045f,ClenchStart=.125f,ClenchEnd=.225f,SettleEnd=.30f,RecoverStart=.52f;
    FVector Wrist{34,-24,-12},Shoulder{-2,-20.5,-20},ElbowPole{9,-36,-37};
    FVector Anticipation{-1.2,-.6,-1.5},LiftDepart{-2,-7,-1},LiftApproach{-3,-2,-8};
    FVector RecoveryDepart{-3,-2,-3},RecoveryApproach{-3,-5,-3};
    FVector PalmForward{.5853,.22,.7804},PalmNormal{-.8,0,.6},BrakeOffset{-.85,-.12,.7};
    TMap<FName,FPowerFistDigitPose> Digits;

    FLeftHandPowerFistMotion();
    void Load();
    float RecoveryDuration() const {return FMath::Max(.01f,Duration-RecoverStart);}
    FFireballArmMotion Sample(const FFireballArmMotion& Entry,const FQuat& Correction,float Age) const;
    FFireballArmMotion Recover(const FFireballArmMotion& From,const FFireballArmMotion& Current,float Fraction) const;
    // X: relax the entering grip; Y: close into the source fist.
    FVector2D FingerWeights(FName Digit,float Age,float RecoveryFraction) const;
    float ArmSupportWeight(float Age,float RecoveryFraction) const;
};
