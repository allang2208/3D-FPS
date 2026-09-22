#pragma once

#include "CoreMinimal.h"
#include "FPSPlayerBodyTypes.generated.h"

class UPrimitiveComponent;

/** Helpers shared by the world-body implementation files. */
namespace FPSBodyEquipment
{
    /** Applies owner-visibility flags only where they differ, because each setter
     *  dirties the primitive's render state. Defined in FPSPlayerBodyEquipment.cpp. */
    void ApplyOwnerVisibilityFlags(UPrimitiveComponent* Mesh, bool bOnlyOwnerSee, bool bOwnerNoSee);
    void ApplyShadowFlags(UPrimitiveComponent* Mesh, bool bCastShadow);
}

UENUM(BlueprintType)
enum class EFPSBodyAction : uint8
{
    None, Equip, Reload, ReloadEmpty, Inspect, Strike, HeavyStrike, Thrust, Guard, Cast, Traverse, Dead,
    GunBash, Pommel, Charge, GuardHit, GuardBreak, Whirlwind, ToolRecover
};

UENUM(BlueprintType)
enum class EFPSBodyMotion : uint8 { Ground, Dodge, Slide, Vault, Mantle };

/** Each pistol retains its own action clock. Presentation never commits ammo. */
USTRUCT(BlueprintType)
struct FFPSBodyHandState
{
    GENERATED_BODY()
    UPROPERTY(BlueprintReadOnly) bool bReloading = false;
    UPROPERTY(BlueprintReadOnly) bool bEquipping = false;
    UPROPERTY(BlueprintReadOnly) float Progress = 0.f;
    UPROPERTY(BlueprintReadOnly) float LastShotAt = -100.f;
};

/** Presentation only. Ammo, hits and movement remain owned by their gameplay systems. */
USTRUCT(BlueprintType)
struct FFPSBodyState
{
    GENERATED_BODY()
    UPROPERTY(BlueprintReadOnly) FName Weapon;
    UPROPERTY(BlueprintReadOnly) FName Family = TEXT("Unarmed");
    UPROPERTY(BlueprintReadOnly) EFPSBodyAction Action = EFPSBodyAction::None;
    UPROPERTY(BlueprintReadOnly) float ActionStartedAt = 0.f;
    UPROPERTY(BlueprintReadOnly) float ActionDuration = 0.f;
    UPROPERTY(BlueprintReadOnly) float ContactFraction = .5f;
    UPROPERTY(BlueprintReadOnly) float LastShotAt = -100.f;
    UPROPERTY(BlueprintReadOnly) float AimPitch = 0.f;
    UPROPERTY(BlueprintReadOnly) bool bAiming = false;
    UPROPERTY(BlueprintReadOnly) bool bSprinting = false;
    UPROPERTY(BlueprintReadOnly) bool bCrouched = false;
    UPROPERTY(BlueprintReadOnly) bool bSliding = false;
    UPROPERTY(BlueprintReadOnly) bool bDual = false;
    UPROPERTY(BlueprintReadOnly) FName ActionVariant;
    // Source-normalized progress preserves hit pauses and nonuniform playback.
    UPROPERTY(BlueprintReadOnly) bool bHasActionProgress = false;
    UPROPERTY(BlueprintReadOnly) float ActionProgress = 0.f;
    UPROPERTY(BlueprintReadOnly) float ActionWeight = 1.f;
    UPROPERTY(BlueprintReadOnly) float ReleaseFraction = .8f;
    UPROPERTY(BlueprintReadOnly) FFPSBodyHandState RightHand;
    UPROPERTY(BlueprintReadOnly) FFPSBodyHandState LeftHand;
    UPROPERTY(BlueprintReadOnly) EFPSBodyMotion Motion = EFPSBodyMotion::Ground;
    UPROPERTY(BlueprintReadOnly) float MotionProgress = 0.f;
    UPROPERTY(BlueprintReadOnly) float MotionContact = .25f;
    UPROPERTY(BlueprintReadOnly) float MotionRelease = .75f;
    UPROPERTY(BlueprintReadOnly) float MotionHandContact = 0.f;
    // Mesh space: +Y forward, -X right. Surface contacts remain world positions.
    UPROPERTY(BlueprintReadOnly) FVector MotionDirection = FVector(0,1,0);
    UPROPERTY(BlueprintReadOnly) bool bHasHandholds = false;
    UPROPERTY(BlueprintReadOnly) FVector RightHandhold = FVector::ZeroVector;
    UPROPERTY(BlueprintReadOnly) FVector LeftHandhold = FVector::ZeroVector;
};

USTRUCT()
struct FFPSBodyAttachment
{
    GENERATED_BODY()
    UPROPERTY() TSoftObjectPtr<class UStaticMesh> Mesh;
    UPROPERTY() TArray<TSoftObjectPtr<class UMaterialInterface>> Materials;
    UPROPERTY() FName Socket;
    UPROPERTY() FTransform RelativeTransform;
};

/** Frozen weapon pose and parts; no first-person skeleton transforms are streamed. */
USTRUCT()
struct FFPSBodyWeapon
{
    GENERATED_BODY()
    UPROPERTY() TSoftObjectPtr<class USkeletalMesh> Mesh;
    UPROPERTY() TSoftObjectPtr<class UAnimSequence> HoldClip;
    UPROPERTY() TArray<TSoftObjectPtr<class UMaterialInterface>> Materials;
    UPROPERTY() TArray<int32> HiddenMaterials;
    UPROPERTY() TArray<FFPSBodyAttachment> Parts;
    UPROPERTY() FName GripBone = TEXT("hand_r");
    UPROPERTY() TSoftObjectPtr<class UStaticMesh> StaticMesh;
    UPROPERTY() FTransform StaticGrip = FTransform::Identity;
};

USTRUCT(BlueprintType)
struct FFPSBodyOutfitSlot
{
    GENERATED_BODY()
    UPROPERTY(BlueprintReadOnly) int32 Slot = INDEX_NONE;
    UPROPERTY(BlueprintReadOnly) FName Definition;
};

/** UHT requires a reflected struct between nested container properties. */
USTRUCT()
struct FFPSBodyOriginalMaterials
{
    GENERATED_BODY()
    UPROPERTY() TObjectPtr<class USkeletalMesh> MeshAsset;
    UPROPERTY() TArray<TObjectPtr<class UMaterialInterface>> Materials;
};
