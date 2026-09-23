#pragma once
#include "CoreMinimal.h"

class USkeletalMesh;
class USkeletalMeshComponent;

// Cosmetic one-axis hinge, evaluated after the authored weapon pose. Each
// viewmodel owns its spring state; gameplay and mechanical action clocks do not.
struct FPKMCarryHandleDynamics
{
    void Apply(USkeletalMeshComponent& Mesh, TArray<FTransform>& Pose);

private:
    TWeakObjectPtr<USkeletalMesh> SourceMesh;
    int32 BoneIndex = INDEX_NONE;
    int32 ParentIndex = INDEX_NONE;
    int32 BoneCount = 0;
    FTransform BindLocal = FTransform::Identity;
    double LastTime = -1.;
    FVector LastPosition = FVector::ZeroVector;
    FQuat LastRotation = FQuat::Identity;
    FVector LastVelocity = FVector::ZeroVector;
    FVector LastAngularVelocity = FVector::ZeroVector;
    FVector Acceleration = FVector::ZeroVector;
    FVector AngularAcceleration = FVector::ZeroVector;
    float Angle = 0.f;
    float AngularSpeed = 0.f;
};
