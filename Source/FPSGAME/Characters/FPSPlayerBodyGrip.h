#pragma once
#include "CoreMinimal.h"
#include "ReferenceSkeleton.h"

// Equipment-time mapping. No mesh vertices or UObject access in the animation thread.
struct FFPSBodyGripRig
{
    struct FDigit { int32 Source[3],Target[3]; };
    TArray<FDigit> Digits;
    TArray<FTransform> SourceBind,TargetBind,TargetLocal;
    TArray<int32> Parents,Descendants;
    TArray<bool> HalfJoint,IsFinger;
    int32 SourceHand=INDEX_NONE,TargetHand=INDEX_NONE;
    FTransform Mount=FTransform::Identity;
    void Initialize(const FReferenceSkeleton& Source,const FReferenceSkeleton& Target,FName From,FName To);
    bool IsValid() const {return SourceHand!=INDEX_NONE&&TargetHand!=INDEX_NONE&&!Digits.IsEmpty();}
    void Transfer(const TArray<FTransform>& SourcePose,TArray<FTransform>& TargetPose) const;
};
