#pragma once
#include "CoreMinimal.h"

class USkeletalMeshComponent;
class USkeletalMesh;

struct FSwordGripFit
{
    FVector Offset[2]={FVector::ZeroVector,FVector::ZeroVector};
    FQuat Rotation[2]={FQuat::Identity,FQuat::Identity};
    TMap<FName,FQuat> Digits;
    bool IsEmpty() const {return Offset[0].IsNearlyZero()&&Offset[1].IsNearlyZero()&&Rotation[0].IsIdentity()&&Rotation[1].IsIdentity()&&Digits.IsEmpty();}
};

// Per-equipped-hilt fitting, evaluated before entry/recovery/casting blends.
// The source grip supplies contact weights, so a released or blade-bracing
// support hand keeps its authored trajectory rather than being pinned down.
struct FSwordGripClearance
{
    bool Configure(const FSwordGripFit& InFit);
    void CaptureIdle(USkeletalMeshComponent& Mesh);
    void Apply(USkeletalMeshComponent& Mesh);
private:
    FSwordGripFit Fit;
    TWeakObjectPtr<USkeletalMesh> ReferenceMesh;
    int32 Weapon=INDEX_NONE;
    int32 Upper[2]={INDEX_NONE,INDEX_NONE},Lower[2]={INDEX_NONE,INDEX_NONE},Hand[2]={INDEX_NONE,INDEX_NONE};
    int32 Twist[2][2]={{INDEX_NONE,INDEX_NONE},{INDEX_NONE,INDEX_NONE}};
    FTransform Grip[2];
    TArray<int32> Parents,Arm;
    TArray<FTransform> Source;
    TArray<FQuat> DigitDelta,IdleLocal;
};
