#pragma once

#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "LumberMillTimberWagon.generated.h"

class USceneComponent;
class UBoxComponent;
class UStaticMeshComponent;
class USkeletalMeshComponent;
class UCharacterMovementComponent;
class ATemperateHillsWorld;
class UAnimSequence;
class USoundBase;
class USoundAttenuation;

UENUM()
enum class ELumberWagonPhase : uint8
{
    ParkedAtMill = 0,
    OutboundToVillage,
    ParkedAtTavern,
    ReturningToMill,
};

USTRUCT()
struct FLumberWagonNetState
{
    GENERATED_BODY()

    UPROPERTY() uint8 Phase = 0;
    UPROPERTY() bool bLoaded = false;
    UPROPERTY() bool bSupplyBlocked = false;
    UPROPERTY() bool bNightInvasion = false;
    UPROPERTY() uint16 RemainingRaiders = 0;
    UPROPERTY() float DistanceCm = 0.f;
    UPROPERTY() float SpeedCmPerSec = 0.f;
    UPROPERTY() double ServerWorldTime = 0.0;
};

/**
 * Articulated horse-drawn Timber Wagon travelling along the 352 m LumberMillSupplyRoute
 * between the restored Lumber Mill and the Village Central Plaza at 17:00 daily.
 *
 * Components follow exact build_lumber_wagon_r52.py (R56) datums:
 *   - Rear axle at X=-105, Z=52 (R=52 cm, Y=+-76 cm)
 *   - Front steerable kingpin at X=+105, Z=37.44 (R=37.44 cm, scale 0.72, Y=+-72 cm, cut-under sills Z>=78.5 cm)
 *   - Draft horse centered at FrontAxle X=+218, Z=-37.44 (hooves on ground, singletree +19 cm aft of walk tail)
 *   - Driver bench seat top at Chassis (+108, 0, 136 cm), footboard top Z=94 cm
 */
UCLASS()
class FPSGAME_API ALumberMillTimberWagon : public AActor
{
    GENERATED_BODY()

public:
    ALumberMillTimberWagon();

    virtual void BeginPlay() override;
    virtual void EndPlay(const EEndPlayReason::Type EndPlayReason) override;
    virtual void Tick(float DeltaSeconds) override;
    virtual void GetLifetimeReplicatedProps(TArray<FLifetimeProperty>& OutLifetimeProps) const override;

    // Server-side authoritative drive API (called by ULumberMillOperationsSubsystem).
    void SetAuthoritativeState(ELumberWagonPhase InPhase, bool bInLoaded, float InDistanceCm, float InSpeedCmPerSec);
    void SetSupplyBlockState(bool bInBlocked, bool bInNightInvasion, int32 InRemainingRaiders);
    void SetDriverWorker(AActor* InDriver);
    void RefreshDynamicReins();

    ELumberWagonPhase GetPhase() const { return static_cast<ELumberWagonPhase>(NetState.Phase); }
    bool IsLoaded() const { return NetState.bLoaded; }
    bool IsSupplyBlocked() const { return NetState.bSupplyBlocked; }
    bool IsNightInvasionBlocking() const { return NetState.bNightInvasion; }
    int32 GetBlockingRaiderCount() const { return int32(NetState.RemainingRaiders); }
    float GetCurrentDistanceCm() const { return VisualDistanceCm; }
    float GetRouteTotalCm() const { return RouteTotalCm; }
    bool IsInTransit() const;

    USceneComponent* GetDriverSeatAnchor() const { return DriverSeatAnchor; }
    void ApplyArtAssets(
        class UStaticMesh* ChassisSM,
        class UStaticMesh* FrontAxleSM,
        class UStaticMesh* WheelSM,
        class UStaticMesh* TimberLoadSM,
        class UStaticMesh* HarnessSM,
        class USkeletalMesh* HorseSK,
        class USkeletalMesh* HorseManeSK,
        UAnimSequence* HorseIdleAnim,
        UAnimSequence* HorseWalkAnim,
        const TArray<USoundBase*>& HoofSounds,
        USoundAttenuation* HoofAtten);

private:
    UPROPERTY(VisibleAnywhere) TObjectPtr<USceneComponent> WagonRoot;
    UPROPERTY(VisibleAnywhere) TObjectPtr<UStaticMeshComponent> ChassisMesh;
    UPROPERTY(VisibleAnywhere) TObjectPtr<UStaticMeshComponent> TimberLoadMesh;
    // R62 walkable & ridable collision primitives (stably named subobjects => base-relative MP sync on Host + Clients).
    UPROPERTY(VisibleAnywhere) TObjectPtr<UBoxComponent> BedWalkDeck;
    UPROPERTY(VisibleAnywhere) TObjectPtr<UBoxComponent> RearLowerStep;
    UPROPERTY(VisibleAnywhere) TObjectPtr<UBoxComponent> RearUpperStep;
    UPROPERTY(VisibleAnywhere) TObjectPtr<UBoxComponent> SideGuardL;
    UPROPERTY(VisibleAnywhere) TObjectPtr<UBoxComponent> SideGuardR;
    UPROPERTY(VisibleAnywhere) TObjectPtr<UBoxComponent> DriverSeatDeck;
    UPROPERTY(VisibleAnywhere) TObjectPtr<UBoxComponent> DriverFootboardDeck;
    UPROPERTY(VisibleAnywhere) TObjectPtr<UBoxComponent> FrontDashGuard;
    UPROPERTY(VisibleAnywhere) TObjectPtr<UBoxComponent> UndercarriageBox;
    UPROPERTY(VisibleAnywhere) TObjectPtr<UStaticMeshComponent> RearLeftWheel;
    UPROPERTY(VisibleAnywhere) TObjectPtr<UStaticMeshComponent> RearRightWheel;
    UPROPERTY(VisibleAnywhere) TObjectPtr<USceneComponent> FrontAxlePivot;
    UPROPERTY(VisibleAnywhere) TObjectPtr<UStaticMeshComponent> FrontAxleMesh;
    UPROPERTY(VisibleAnywhere) TObjectPtr<UStaticMeshComponent> FrontLeftWheel;
    UPROPERTY(VisibleAnywhere) TObjectPtr<UStaticMeshComponent> FrontRightWheel;
    UPROPERTY(VisibleAnywhere) TObjectPtr<USceneComponent> HorseRoot;
    UPROPERTY(VisibleAnywhere) TObjectPtr<USkeletalMeshComponent> HorseMesh;
    UPROPERTY(VisibleAnywhere) TObjectPtr<USkeletalMeshComponent> HorseManeMesh;
    UPROPERTY(VisibleAnywhere) TObjectPtr<UStaticMeshComponent> HarnessMesh;
    UPROPERTY(VisibleAnywhere) TObjectPtr<USceneComponent> DriverSeatAnchor;
    UPROPERTY(VisibleAnywhere) TObjectPtr<UStaticMeshComponent> ReinLeftRearMesh;
    UPROPERTY(VisibleAnywhere) TObjectPtr<UStaticMeshComponent> ReinLeftFrontMesh;
    UPROPERTY(VisibleAnywhere) TObjectPtr<UStaticMeshComponent> ReinRightRearMesh;
    UPROPERTY(VisibleAnywhere) TObjectPtr<UStaticMeshComponent> ReinRightFrontMesh;

    UPROPERTY(ReplicatedUsing=OnRep_NetState) FLumberWagonNetState NetState;
    UFUNCTION() void OnRep_NetState();

    UPROPERTY(Replicated) TWeakObjectPtr<AActor> DriverWorker;

    UPROPERTY(Transient) TObjectPtr<UAnimSequence> HorseIdleClip;
    UPROPERTY(Transient) TObjectPtr<UAnimSequence> HorseWalkClip;
    UPROPERTY(Transient) TArray<TObjectPtr<USoundBase>> HoofWalkSounds;
    UPROPERTY(Transient) TObjectPtr<USoundAttenuation> HoofAttenuation;

    TWeakObjectPtr<ATemperateHillsWorld> Hills;
    TArray<FVector2D> RoutePoints;
    TArray<double> RouteCumulativeCm;
    double RouteTotalCm = 0.0;
    bool bRouteBuilt = false;
    bool bAssetsBound = false;
    bool bHorseWalking = false;
    bool bHasInitialNetSync = false;
    bool bWalkDeckLoaded = false;
    bool bParkedPoseSettled = false;
    bool bLastAppliedReturning = false;

    float VisualDistanceCm = 0.f;
    float LastAppliedDistanceCm = -1.f;
    float WheelRollCm = 0.f;
    float CurrentSteerYawDeg = 0.f;
    float CurrentShaftPitchDeg = 0.f;
    float NextHoofSoundAt = 0.f;
    int32 HoofStepIndex = 0;
    bool bWagonRTVisible = true;
    double NextWagonRTCheckAt = -1.;
    TArray<TWeakObjectPtr<UCharacterMovementComponent>> TrackedRiderMovements;
    void UpdateRayTracingVisibility(bool bForce = false);

    void EnsureRouteAndTerrain();
    void UpdateWalkDeckForLoadState(bool bLoaded);
    void SyncRidingCharacterTickOrder();
    void ClearRidingCharacterTickOrder();
    void ApplyRoutePose(float DistanceCm, bool bFacingReturn, float DeltaSeconds);
    void UpdateHorseAnimation(bool bMoving, float SpeedCmPerSec);
    void UpdateDynamicReins();
    void TryPlayHoofSound(float SpeedCmPerSec);
    double SampleGroundZ(const FVector2D& XY) const;
};
