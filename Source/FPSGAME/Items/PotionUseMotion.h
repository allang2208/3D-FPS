#pragma once
#include "CoreMinimal.h"

struct FPotionDigitPose
{
    FVector Spread=FVector::ZeroVector;
    FVector Flex=FVector(45,100,145);
    // Keep the native roll carried by the parent while aiming the digit.
    bool bPreserveNativeRoll=false;
    // Optional rotations relative to each native local joint. Authored for the
    // loaded binding; the two-hand lamb uses the fixed Traversal hand family.
    FQuat LocalRotations[3]={FQuat::Identity,FQuat::Identity,FQuat::Identity};
    bool bHasLocalRotations=false;
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
    // Optional original-mesh frame for foods whose handle is not on upright Z.
    FVector ObjectGrip=FVector::ZeroVector;
    FVector BiteInObject=FVector::ZeroVector;
    FQuat ObjectRotation=FQuat::Identity;
    // Per-food palm bases keep the object path independent of wrist orientation.
    FQuat PalmRotation=FQuat::Identity,RightPalmRotation=FQuat::Identity;
    bool bHasObjectGrip=false;
    bool bTwoHanded=false;
    FVector RightObjectGrip=FVector::ZeroVector,RightGripInPalm{6.95,0,3.3};
    FVector ObjectGripPoint() const { return bHasObjectGrip?ObjectGrip:FVector(0,0,GripHeight); }
    bool bOpensContainer=true;
    TArray<FPotionMotionKey> Keys;
    TMap<FName,FPotionDigitPose> Digits;
    TMap<FName,FPotionDigitPose> RightDigits;
    // Asymmetric two-hand foods may need a separately authored support thumb.
    FPotionDigitPose RightThumb;
    bool bHasRightThumb=false;
    void Load(bool bMana,const TCHAR* Definition=nullptr);
    static float Ease(float X) { X=FMath::Clamp(X,0.f,1.f);return X*X*X*(X*(X*6.f-15.f)+10.f); }
    FTransform GripAt(float Age) const;
    FTransform BottleAt(float Age) const;
    FTransform PalmAt(float Age) const;
    FQuat PalmBasis(bool bRight=false) const;
    float Layer(float Age) const;
    float FingerClosure(float Age) const;
};
