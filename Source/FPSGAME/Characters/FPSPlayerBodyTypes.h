#pragma once

#include "CoreMinimal.h"
#include "Engine/NetSerialization.h"
#include "UObject/SoftObjectPath.h"
#include "FPSBodyMotionSample.h"
#include "FPSPlayerBodyTypes.generated.h"

class UPrimitiveComponent;

USTRUCT(BlueprintType)
struct FFPSBodyAppearance
{
    GENERATED_BODY()
    UPROPERTY(EditAnywhere,BlueprintReadWrite) FName HeadId;
    UPROPERTY(EditAnywhere,BlueprintReadWrite) FName HairId;
    bool operator==(const FFPSBodyAppearance& Other) const {return HeadId==Other.HeadId&&HairId==Other.HairId;}
};

/** Helpers shared by the world-body implementation files. */
namespace FPSBodyEquipment
{
    /** Applies owner-visibility flags only where they differ, because each setter
     *  dirties the primitive's render state. Defined in FPSPlayerBodyEquipment.cpp. */
    void ApplyOwnerVisibilityFlags(UPrimitiveComponent* Mesh, bool bOnlyOwnerSee, bool bOwnerNoSee);
    void ApplyShadowFlags(UPrimitiveComponent* Mesh, bool bCastShadow);
    /** Static world mesh bound to an equipment definition by
     *  ColdSteelData/player_body.json outfits[].world_static_mesh. Invalid when the
     *  definition has no rigid attachment; the icon studio shares this source so the
     *  inventory picture is the mesh actually worn. */
    FSoftObjectPath StaticOutfitMesh(const FString& Definition);
}

UENUM(BlueprintType)
enum class EFPSBodyAction : uint8
{
    None, Equip, Reload, ReloadEmpty, Inspect, Strike, HeavyStrike, Thrust, Guard, Cast, Traverse, Dead,
    GunBash, Pommel, Charge, GuardHit, GuardBreak, Whirlwind, ToolRecover, Consume, DoorPush, StaffLight
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
    UPROPERTY() float ProgressRate = 0.f;
};

/** Final owner-traced laser endpoint; observers never choose a second aim ray. */
USTRUCT()
struct FFPSBodyLaserSample
{
    GENERATED_BODY()
    UPROPERTY() uint8 RigIndex=0;
    UPROPERTY() uint8 PartIndex=0;
    UPROPERTY() uint32 Schema=0;
    UPROPERTY() FVector_NetQuantize100 End=FVector::ZeroVector;
    UPROPERTY() FVector_NetQuantizeNormal Normal=FVector::UpVector;
    UPROPERTY() bool bDot=false;
};

/** Presentation only. Ammo, hits and movement remain owned by their gameplay systems. */
USTRUCT(BlueprintType)
struct FFPSBodyState
{
    GENERATED_BODY()
    UPROPERTY(BlueprintReadOnly) FName Weapon;
    // Runtime identity only: late snapshots from a different copy of the same
    // weapon, or from the previous offhand loadout, must not drive this rig.
    UPROPERTY() FString WeaponInstance;
    UPROPERTY() FString OffhandInstance;
    UPROPERTY(BlueprintReadOnly) FName Family = TEXT("Unarmed");
    UPROPERTY(BlueprintReadOnly) EFPSBodyAction Action = EFPSBodyAction::None;
    UPROPERTY(BlueprintReadOnly) float ActionStartedAt = 0.f;
    UPROPERTY(BlueprintReadOnly) float ActionDuration = 0.f;
    UPROPERTY(BlueprintReadOnly) float ContactFraction = .5f;
    UPROPERTY(BlueprintReadOnly) float LastShotAt = -100.f;
    UPROPERTY(BlueprintReadOnly) float AimPitch = 0.f;
    UPROPERTY(BlueprintReadOnly) float AimYaw = 0.f;
    UPROPERTY(BlueprintReadOnly) bool bAiming = false;
    UPROPERTY(BlueprintReadOnly) bool bSprinting = false;
    UPROPERTY(BlueprintReadOnly) bool bCrouched = false;
    UPROPERTY(BlueprintReadOnly) bool bSliding = false;
    UPROPERTY(BlueprintReadOnly) bool bDual = false;
    UPROPERTY(BlueprintReadOnly) bool bOffhandPistol = false;
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
    // Bounded interpolation between cosmetic snapshots; never used for gameplay.
    UPROPERTY() float PresentationSampledAt = 0.f;
    UPROPERTY() float ActionProgressRate = 0.f;
    UPROPERTY() float MotionSampledAt = 0.f;
    UPROPERTY() float MotionProgressRate = 0.f;
    // Cosmetic bow sampling; asset names are resolved only against server equipment.
    UPROPERTY() FName BowClip;
    UPROPERTY() float BowClipTime = 0.f;
    UPROPERTY() float BowClipRate = 0.f;
    UPROPERTY() float BowClipLength = 0.f;
    UPROPERTY() bool bBowClipLooping = false;
    UPROPERTY() FVector BowNock = FVector::ZeroVector;
    UPROPERTY() bool bBowArrow = false;
    UPROPERTY() bool bBowTakingArrow = false;
    UPROPERTY() float BowSeat = 1.f;
    UPROPERTY() float BowStringContact = 0.f;
    UPROPERTY() bool bBowCarryAxis = false;
    UPROPERTY() FFPSBodyMotionSample Contacts;
    UPROPERTY() TArray<FFPSBodyLaserSample> Lasers;
    UPROPERTY() float ActionEntryFraction=0.f;
    // Presentation only; a stopped swept lunge must not keep running in place.
    UPROPERTY() bool bUppercutLungeBlocked=false;
    // Signed gameplay turns; the world body reverses them on the same clock.
    UPROPERTY() float WhirlwindTurns=-2.f;
    // Azure Dragon claws (cosmetic, see URuneSwordComponent::SampleAzureDragonNet): flags, strike clip
    // length and entry (source seconds), heavy charge start (server clock).
    UPROPERTY() uint8 AzureFlags=0;
    UPROPERTY() float AzureSourceLength=0.f;
    UPROPERTY() float AzureEntryTime=0.f;
    UPROPERTY() float AzureChargeStartedAt=0.f;
};

USTRUCT()
struct FFPSBodyAttachment
{
    GENERATED_BODY()
    UPROPERTY() TSoftObjectPtr<class UStaticMesh> Mesh;
    UPROPERTY() TArray<TSoftObjectPtr<class UMaterialInterface>> Materials;
    UPROPERTY() FName Socket;
    UPROPERTY() FTransform RelativeTransform;
    UPROPERTY() TSoftObjectPtr<class USkeletalMesh> SkeletalMesh;
    UPROPERTY() FName Slot;
    UPROPERTY() FName TacticalKind;
    UPROPERTY() bool bAuthoredEmitterAxis=false;
    UPROPERTY() bool bVisible=true;
    // Reconstruct transient rune ink on every observer; parent materials alone
    // lose both the overlay and the installed rune's palette/mask selection.
    UPROPERTY() FString RuneDefinition;
    UPROPERTY() FString RuneId;
    UPROPERTY() FName RuneSlot;
    UPROPERTY() FVector RuneDimensions=FVector(12,10,63);
};

USTRUCT()
struct FFPSBodyBowSettings
{
    GENERATED_BODY()
    UPROPERTY() FVector UpperTip = FVector::ZeroVector;
    UPROPERTY() FVector LowerTip = FVector::ZeroVector;
    UPROPERTY() FVector Brace = FVector::ZeroVector;
    UPROPERTY() FVector ArrowRest = FVector::ZeroVector;
    UPROPERTY() float StringRadius = .09f;
    UPROPERTY() float ArrowRadius = .3f;
    UPROPERTY() float ArrowLength = 76.f;
    UPROPERTY() float FlexDistribution = 1.15f;
};

USTRUCT()
struct FFPSBodyBowClip
{
    GENERATED_BODY()
    UPROPERTY() FName Role;
    UPROPERTY() TSoftObjectPtr<class UAnimSequence> Sequence;
};

/** Server-owned equipment schema. Cosmetic contacts stream only hands and mechanical parts. */
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
    UPROPERTY() FName PoseFamily;
    UPROPERTY() uint8 AttachHand = 0;
    UPROPERTY() TSoftObjectPtr<class UWeaponGripProfile> GripProfile;
    UPROPERTY() int32 StaffVariant = 0;
    UPROPERTY() TArray<FFPSBodyBowClip> MotionClips;
    UPROPERTY() FFPSBodyBowSettings Bow;
    UPROPERTY() TArray<int32> MotionBones;
    UPROPERTY() uint32 MotionSchema=0;
    UPROPERTY() FVector StaffLightLocation=FVector::ZeroVector;
    UPROPERTY() TSoftObjectPtr<class USkeletalMesh> ReloadPropMesh;
    UPROPERTY() TArray<TSoftObjectPtr<class UMaterialInterface>> ReloadPropMaterials;
    UPROPERTY() FString GunInstance;
    UPROPERTY() FName GunDefinition;
    UPROPERTY() bool bGunPistol=false;
    UPROPERTY() bool bGunRevolver=false;
    UPROPERTY() bool bGunSuppressed=false;
    UPROPERTY() FTransform GunMuzzleInRoot=FTransform::Identity;
    UPROPERTY() TSoftObjectPtr<class USoundBase> GunFireSound;
    UPROPERTY() TSoftObjectPtr<class USoundBase> GunSuppressedSound;
    UPROPERTY() TArray<TSoftObjectPtr<class USoundBase>> GunSounds;
    UPROPERTY() TArray<TSoftObjectPtr<class UStaticMesh>> GunCartridges;
    UPROPERTY() int32 MuzzlePart=INDEX_NONE;
    UPROPERTY() FVector MuzzleTip=FVector::ZeroVector;
    UPROPERTY() FVector MuzzleAxis=FVector::ForwardVector;
    // Local adapters are never serialized as equipment or accepted from clients.
    TWeakObjectPtr<class USkeletalMeshComponent> Source;
    TWeakObjectPtr<class USkeletalMeshComponent> ReloadPropSource;
    TWeakObjectPtr<class UStaticMeshComponent> StaticSource;
    TArray<TWeakObjectPtr<class UStaticMeshComponent>> SourceParts;
    TArray<TWeakObjectPtr<class UTacticalDeviceComponent>> SourceTacticalDevices;
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
