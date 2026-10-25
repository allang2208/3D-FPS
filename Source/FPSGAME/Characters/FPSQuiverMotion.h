#pragma once

#include "CoreMinimal.h"

class USkeletalMeshComponent;
class UStaticMeshComponent;
class UStaticMesh;
class UFPSPlayerBodyComponent;
class FJsonObject;

/** Cosmetic, damped hip suspension. Inventory and ammunition stay authoritative. */
struct FFPSQuiverMotion
{
    ~FFPSQuiverMotion();
    void Initialize(USkeletalMeshComponent* InBody, USkeletalMeshComponent* InBelt,
        const TSharedPtr<FJsonObject>& Settings, UStaticMesh* ArrowMesh, bool bOwnerBody);
    void Tick(float Delta);

private:
    void Push(const FTransform& Frame, const FQuat& Rotation, const FVector& Shift, bool bReset);
    void FollowVisibility();
    TWeakObjectPtr<USkeletalMeshComponent> Body, Belt;
    TWeakObjectPtr<UFPSPlayerBodyComponent> BodyState;
    TArray<TWeakObjectPtr<UStaticMeshComponent>> Arrows;
    TArray<FTransform> ArrowReferences;
    FTransform InverseBind;
    int32 Pelvis = INDEX_NONE;
    FVector Pivot = FVector::ZeroVector, Outward = FVector::RightVector;
    FVector BoundsMin = FVector::ZeroVector, BoundsMax = FVector::ZeroVector;
    FVector Angles = FVector::ZeroVector, AngularVelocity = FVector::ZeroVector;
    FVector LastAnchor = FVector::ZeroVector, FilteredVelocity = FVector::ZeroVector;
    FQuat LastFrame = FQuat::Identity;
    float Bounce = 0.f, BounceVelocity = 0.f;
    float Frequency = 1.7f, Damping = 1.f, MaxAngle = 2.f, MaxTravel = 2.f;
    bool bInitialized = false;
    float Previous[15] = {};
};
