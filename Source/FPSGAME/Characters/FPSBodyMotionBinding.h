#pragma once
#include "FPSPlayerBodyTypes.h"
#include "FPSPlayerBodyGrip.h"

struct FFPSBodyMotionBinding
{
    FFPSBodyWeapon Definition;
    TWeakObjectPtr<class UFPSBodyWeaponMeshComponent> Mesh;
    TWeakObjectPtr<class UStaticMeshComponent> Static;
    TArray<TWeakObjectPtr<class UStaticMeshComponent>> Parts;
    TArray<FTransform> FrozenPose;
    TArray<FTransform> FrozenParts;
    int32 NativeWeaponRoot=INDEX_NONE;
    // Sword carry keeps its ordinary idle/walk pose on an independent clip clock.
    FName LocomotionClip;
    float LocomotionTime=0.f;
    TArray<FTransform> LocomotionPose;
    FTransform Mount=FTransform::Identity;
    uint32 LastSections=0;
    bool bHasSections=false;
    FFPSBodyMotionRig Smoothed;
};
struct FFPSBodyMotionMap
{
    TWeakObjectPtr<class USkeletalMeshComponent> Source;
    TWeakObjectPtr<class USkeletalMesh> SourceAsset;
    FName Hand;
    int32 Side=0;
    FFPSBodyGripRig Rig;
};
