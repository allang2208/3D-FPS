#pragma once
#include "CoreMinimal.h"

class USkeletalMesh;
class USkeletalMeshComponent;

// Cosmetic hinged flap. Belt envelopes are kinematic contacts; they do not
// create Chaos bodies or exert forces on the weapon, hands or ammunition.
struct FPKMExitCoverDynamics
{
    void Apply(USkeletalMeshComponent& Mesh, TArray<FTransform>& Pose,
        int32 Tab, int32 NewTab, const TArray<int32>& Clips,
        bool OldBeltVisible, bool NewBeltVisible, bool Active);
private:
    TWeakObjectPtr<USkeletalMesh> SourceMesh;
    int32 BoneCount=0, Bone=INDEX_NONE, Parent=INDEX_NONE;
    FTransform BindLocal=FTransform::Identity;
    double LastTime=-1.;
    FVector LastPosition=FVector::ZeroVector, LastVelocity=FVector::ZeroVector;
    FVector Acceleration=FVector::ZeroVector;
    float Angle=0.f, Speed=0.f;
};
