#pragma once
#include "CoreMinimal.h"

struct FPotionDigitPose
{
    FVector Spread=FVector::ZeroVector;
    FVector Flex=FVector(45,100,145);
};
struct FPotionMotionKey
{
    float Time=0;
    FVector Grip=FVector::ZeroVector;
    FQuat Rotation=FQuat::Identity;
};

/** Authoring coordinates: camera X forward / Y right / Z up, distances in cm. */
struct FPotionUseMotion
{
    float Grab=.26f, Uncap=.64f, DrinkStart=1.08f, DrinkEnd=1.52f, Contact=1.46f;
    float Release=1.76f, Recover=1.8f, Duration=2.10f;
    FVector Shoulder{-3,-19,-19}, Pole{3,-39,-39};
    // Y points down the bottle: a negative Y anchor lowers the palm while
    // preserving the bottle path and the rim's drinking contact.
    FVector GripInPalm{5.3,-2.,5.1};
    float GripHeight=13.2f;
    TArray<FPotionMotionKey> Keys;
    TMap<FName,FPotionDigitPose> Digits;
    void Load(bool bMana);
    static float Ease(float X) { X=FMath::Clamp(X,0.f,1.f);return X*X*X*(X*(X*6.f-15.f)+10.f); }
    FTransform GripAt(float Age) const;
    FTransform BottleAt(float Age) const;
    FTransform PalmAt(float Age) const;
    float Layer(float Age) const;
    float FingerClosure(float Age) const;
};
