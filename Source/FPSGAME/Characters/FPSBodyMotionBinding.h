#pragma once
#include "FPSPlayerBodyTypes.h"
#include "FPSPlayerBodyGrip.h"
#include "FPSBodyRevolverReload.h"

struct FFPSBodyMotionBinding
{
    FFPSBodyWeapon Definition;
    TWeakObjectPtr<class UFPSBodyWeaponMeshComponent> Mesh;
    TWeakObjectPtr<class USkeletalMeshComponent> ReloadProp;
    TWeakObjectPtr<class UStaticMeshComponent> Static;
    TArray<TWeakObjectPtr<class UStaticMeshComponent>> Parts;
    TArray<FTransform> FrozenPose;
    TArray<FTransform> FrozenParts;
    int32 NativeWeaponRoot=INDEX_NONE;
    // Reused ordinary carry buffer; tactical FPS sprint never opens the rifle
    // support grip. Sword carry also keeps an independent clip clock here.
    FName LocomotionClip;
    float LocomotionTime=0.f;
    TArray<FTransform> LocomotionPose;
    FTransform Mount=FTransform::Identity;
    TOptional<FTransform> UppercutReverseMount;
    uint32 LastSections=0;
    uint32 IncomingFeedSections=0;
    bool bHasSections=false;
    FFPSBodyMotionRig Smoothed;
    // World-only dual-pistol reload. Factory geometry is retained by the body
    // component; attached magazines reuse their equipped mesh and materials.
    TWeakObjectPtr<class UStaticMesh> FactoryMagazine;
    int32 MagazineBone=INDEX_NONE,MagazinePart=INDEX_NONE;
    TArray<int32> MagazineBones;
    FVector MagazineExit=FVector::ZeroVector;
    FTransform MagazinePartPose=FTransform::Identity;
    float MagazineReloadStartedAt=-100.f;
    bool bMagazineDropArmed=false,bMagazineDropped=false;
    bool bMagazineOverride=false,bMagazineHidden=false;
    FFPSBodyRevolverReload Revolver;
};
struct FFPSBodyMotionMap
{
    TWeakObjectPtr<class USkeletalMeshComponent> Source;
    TWeakObjectPtr<class USkeletalMesh> SourceAsset;
    FName Hand;
    int32 Side=0;
    FFPSBodyGripRig Rig;
};
