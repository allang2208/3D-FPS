#pragma once
#include "CoreMinimal.h"

// Small presentation-only rigid proxy. The high-detail pouch is never simulated
// or CPU-skinned; its two sewn ends drive the fitted strap's existing WPO field.
struct FFPSHangingInfluence
{
    int32 Bone=INDEX_NONE;
    FVector Local=FVector::ZeroVector;
    float Weight=0.f;
};
struct FFPSHangingTether
{
    FVector Point=FVector::ZeroVector,PreviousAnchor=FVector::ZeroVector;
    float Length=0.f;
    TArray<FFPSHangingInfluence> Support;
};
struct FFPSHangingHull
{
    int32 Bone=INDEX_NONE;
    int32 SidePlanes=0;
    TArray<FPlane> Planes;
    FTransform PreviousFrame;
};
struct FFPSHangingPack
{
    bool Enabled=false,Initialized=false;
    FVector Position=FVector::ZeroVector,Velocity=FVector::ZeroVector,AngularVelocity=FVector::ZeroVector;
    FQuat Rotation=FQuat::Identity;
    FTransform PreviousCarrier;
    TArray<FFPSHangingTether> Tethers;
    TArray<FFPSHangingHull> Hulls;
    TArray<FVector> Probes;
    float InverseInertia=1.f/180.f,LinearDamping=3.2f,AngularDamping=8.f;
    float ContactRadius=.2f,MaxTravel=6.f,MaxAngle=28.f;
};
