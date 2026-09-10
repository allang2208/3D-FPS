#pragma once

#include "CoreMinimal.h"
#include "GameFramework/Character.h"
#include "Weapons/WeaponHandling.h"
#include "FPSGAMECharacter.generated.h"

class UCameraComponent;
class USkeletalMeshComponent;
class UAnimSequence;
class USoundBase;
class UAudioComponent;
class UFPSWeaponFXComponent;
class UFPSGunplayAnimInstance;

UENUM(BlueprintType)
enum class EAKMWeaponState : uint8
{
    Equipping,
    Idle,
    Reloading,
    ReloadingEmpty,
    Inspecting
};

UCLASS()
class FPSGAME_API AFPSGAMECharacter : public ACharacter
{
    GENERATED_BODY()
    friend class AColdSteelPickup;

    friend class UColdSteelWeaponIcons;

public:
    UPROPERTY(EditDefaultsOnly, Category = "Weapon|Model") bool bUseM4Infima = true;
    AFPSGAMECharacter();
    void ApplyColdSteelProfile(class UColdSteelStatusModel* Profile);
    bool HasInventoryWeapon() const { return bInventoryWeaponReady; }
    void SuspendWeaponForMenu(){FireReleased();AimReleased();}
    void SetGunsmithOptic(bool bHolographic);
    void SetGunsmithDrum(bool bDrum);
    void SetGunsmithMuzzle(const FString& Variant);
    FVector GetEffectiveMuzzleLocation() const;
    FVector GetEffectiveMuzzleForward() const;
    bool IsMuzzleSuppressed() const {return MuzzleVariant==TEXT("true");}
    void SetGunsmithInspection(bool bInspect);
    void UpdateGunsmithCapture(class USceneCaptureComponent2D* Capture, bool bAim);
    bool HasGunsmithDrum() const {return bDrumVisual;}
    bool ValidateDrumAttachment() const;
    float GetReloadSeconds(bool bEmpty) const {return bEmpty?EmptyReloadDuration:ReloadDuration;}
    float GetADSSeconds() const {return ADSInDuration;}
    void SetGunsmithAimPreview(bool bAim){if(bAim)AimPressed();else AimReleased();}
    bool HasHolographicOptic() const {return bHolographicOptic;}
    bool ValidateGunsmithSight(float& PixelError) const;
    bool ValidateHolographicShot() const;
    bool MeasureHolographicOrientation(float& ScreenRollDegrees,float& RailErrorDegrees) const;
    bool ValidateFoldingSights(bool bFolded) const;
    virtual void Tick(float DeltaSeconds) override;
    virtual void SetupPlayerInputComponent(UInputComponent* PlayerInputComponent) override;

    UFUNCTION(BlueprintPure, Category = "FPS Movement") bool IsSprinting() const { return bIsSprinting; }
    UFUNCTION(BlueprintPure, Category = "FPS Movement") bool IsSliding() const { return bIsSliding; }
    UFUNCTION(BlueprintPure, Category = "AKM") bool IsAiming() const { return bIsAiming; }
    UFUNCTION(BlueprintPure, Category = "AKM") bool IsReloading() const { return WeaponState == EAKMWeaponState::Reloading || WeaponState == EAKMWeaponState::ReloadingEmpty; }
    UFUNCTION(BlueprintPure, Category = "AKM") int32 GetMagazineAmmo() const { return MagazineAmmo; }
    int32 GetMagazineCapacity() const { return MagazineCapacity; }
    UFUNCTION(BlueprintPure, Category = "AKM") int32 GetReserveAmmo() const { return ReserveAmmo; }
    UFUNCTION(BlueprintPure, Category = "AKM") bool HasInfiniteReserveAmmo() const;
    UFUNCTION(BlueprintPure, Category = "AKM") EAKMWeaponState GetWeaponState() const { return WeaponState; }

protected:
    UPROPERTY(Transient) TObjectPtr<class UStaticMeshComponent> MuzzleAttachment;
    UPROPERTY(VisibleAnywhere) TObjectPtr<class UFPSBallisticsComponent> Ballistics;
    UPROPERTY(Transient) TObjectPtr<USoundBase> SuppressedFireSound;
    FString MuzzleVariant;
    FVector MuzzleLocalTip=FVector::ZeroVector;
    FVector MuzzleLocalAxis=FVector::ForwardVector;
    float ProjectileSpeedCM=9000.f;
    void RunMuzzleMigrationAudit();
    FWeaponHandling WeaponHandling;
    void RunWeaponHandlingAudit();
    virtual void BeginPlay() override;
    virtual void EndPlay(const EEndPlayReason::Type Reason) override;
    void InitializeWeaponVisuals();
    FString ActiveInventoryWeapon;
    bool bInventoryWeaponReady = true;

    UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Camera") TObjectPtr<UCameraComponent> FirstPersonCamera;
    UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "AKM") TObjectPtr<USkeletalMeshComponent> AKMViewmodel;
    UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "AKM") TObjectPtr<UFPSWeaponFXComponent> WeaponFX;

    // UE-space cm. All presentation tuning is local to this pawn (single-player).
    UPROPERTY(EditDefaultsOnly, Category = "AKM|Handling", meta = (ClampMin = "0.05")) float ADSInDuration = 0.24f;
    UPROPERTY(EditDefaultsOnly, Category = "AKM|Handling", meta = (ClampMin = "0.05")) float ADSOutDuration = 0.18f;
    UPROPERTY(EditDefaultsOnly, Category = "AKM|Handling") float SprintToFireDuration = 0.18f;
    UPROPERTY(EditDefaultsOnly, Category = "AKM|Handling") float ADSWalkSpeed = 300.0f;
    UPROPERTY(EditDefaultsOnly, Category = "AKM|Handling") float ADSMouseSensitivity = 1.0f;
    UPROPERTY(EditDefaultsOnly, Category = "AKM|Handling", meta = (ClampMin = "0.0", ClampMax = "1.0")) float CameraMotionScale = 0.45f;
    UPROPERTY(EditDefaultsOnly, Category = "AKM|Handling") float ADSRearEyeDistance = 42.0f;
    // Derived from the equipped catalog entry; editing the old CDO scalar must
    // not silently make runtime recoil disagree with the gunsmith overview.
    UPROPERTY(VisibleInstanceOnly, BlueprintReadOnly, Category = "Weapon|Handling") float BallisticRecoilScale = FWeaponHandling::ReferenceBallisticScale;
    UPROPERTY(EditDefaultsOnly, Category = "AKM|Handling") float VisualRecoilScale = 0.65f;

    UPROPERTY(EditDefaultsOnly, Category = "FPS Movement|Speed") float WalkSpeed = 450.0f;
    UPROPERTY(EditDefaultsOnly, Category = "FPS Movement|Speed") float SprintSpeed = 700.0f;
    UPROPERTY(EditDefaultsOnly, Category = "FPS Movement|Speed") float CrouchSpeed = 250.0f;
    UPROPERTY(EditDefaultsOnly, Category = "FPS Movement|Slide") float SlideMinimumSpeed = 600.0f;
    UPROPERTY(EditDefaultsOnly, Category = "FPS Movement|Slide") float SlideSpeedMultiplier = 2.0f;
    UPROPERTY(EditDefaultsOnly, Category = "FPS Movement|Slide") float SlideFriction = 1.5f;
    UPROPERTY(EditDefaultsOnly, Category = "FPS Movement|Slide") float SlideMaximumTime = 2.0f;
    UPROPERTY(EditDefaultsOnly, Category = "FPS Movement|Slide") float SlideBoostCooldown = 2.0f;
    UPROPERTY(EditDefaultsOnly, Category = "FPS Movement|Slide") float SlideJumpLockTime = 0.24f;
    UPROPERTY(EditDefaultsOnly, Category = "FPS Movement|Slide") float JumpInputBufferTime = 0.16f;
    UPROPERTY(EditDefaultsOnly, Category = "FPS Movement|Camera") float StandingCameraHeight = 74.0f;
    UPROPERTY(EditDefaultsOnly, Category = "FPS Movement|Camera") float SlidingCameraHeight = 42.0f;
    UPROPERTY(EditDefaultsOnly, Category = "FPS Movement|Camera") float BaseVerticalFieldOfView = 75.0f;
    UPROPERTY(EditDefaultsOnly, Category = "FPS Movement|Camera") float ADSVerticalFieldOfView = 55.0f;
    UPROPERTY(EditDefaultsOnly, Category = "FPS Movement|Camera") float SprintFieldOfView = 112.0f;
    UPROPERTY(EditDefaultsOnly, Category = "FPS Movement|Stance") float StandingCapsuleHalfHeight = 96.0f;

    // Runtime-probed Godot calibration. The +19 cm Y offset compensates the merged FBX pivot.
    UPROPERTY(EditDefaultsOnly, Category = "AKM|Viewmodel") FVector HipViewmodelLocation = FVector(10.0f, 31.0f, -3.0f);
    // M4 framing matched to the Godot Infima rifle's projected hip sights at 75 degrees vertical FOV.
    UPROPERTY(EditDefaultsOnly, Category = "M4|Viewmodel") FVector M4HipViewmodelLocation = FVector(0.0f, 7.0f, -7.0f);
    // Leave room for both hands and the magazine during equip/reload.
    UPROPERTY(EditDefaultsOnly, Category = "M4|Viewmodel") FVector M4ActionViewmodelLocation = FVector(10.0f, 0.0f, -5.0f);
    float M4ActionFramingAlpha = 0.0f;
    // Camera-space raised ready pose; transform the complete rig to retain both grips.
    UPROPERTY(EditDefaultsOnly, Category = "M4|Sprint") FVector M4SprintOffset = FVector(6.0f, 3.0f, -9.0f);
    UPROPERTY(EditDefaultsOnly, Category = "M4|Sprint") FRotator M4SprintRotation = FRotator(35.0f, -12.0f, -8.0f);
    UPROPERTY(EditDefaultsOnly, Category = "M4|Sprint", meta = (ClampMin = "0.0", ClampMax = "4.0")) float M4SprintSwayCM = 1.8f;
    float M4SprintPhase = 0.0f;
    UPROPERTY(EditDefaultsOnly, Category = "AKM|Viewmodel") FVector ADSViewmodelLocation = FVector(11.8734f, -0.0085f, 1.6058f);
    UPROPERTY(EditDefaultsOnly, Category = "AKM|Viewmodel") FVector ViewmodelScale = FVector(1.0f);
    UPROPERTY(EditDefaultsOnly, Category = "AKM|Viewmodel") FRotator ViewmodelRotation = FRotator(0.0f, 90.0f, 0.0f);
    UPROPERTY(EditDefaultsOnly, Category = "AKM|Viewmodel") FRotator ADSViewmodelRotation = FRotator(-0.0865f, 90.0f, 0.0f);

    UPROPERTY(EditDefaultsOnly, Category = "AKM|Combat") float FireInterval = 0.12f;
    UPROPERTY(EditDefaultsOnly, Category = "AKM|Combat") float DamagePerShot = 30.0f;
    UPROPERTY(EditDefaultsOnly, Category = "AKM|Combat") float TraceDistance = 100000.0f;
    UPROPERTY(EditDefaultsOnly, Category = "AKM|Combat") float ReloadDuration = 2.7f;
    UPROPERTY(EditDefaultsOnly, Category = "AKM|Combat") float EmptyReloadDuration = 3.466667f;
    UPROPERTY(EditDefaultsOnly, Category = "AKM|Combat") int32 MagazineCapacity = 30;

private:
    void RunInfiniteAmmoAudit();
    void RunDrumGripAudit();
    int32 DrumGripAuditStage = 0;
    int32 DrumGripAuditFailures = 0;
    int32 DrumGripAuditReserve = 0;
    int32 DrumGripAuditCapture = 0;
    float DrumGripAuditLastCapture = -1.f;
    float DrumGripAuditRightDepthMin = 0.f;
    float DrumGripAuditRightDepthMax = 0.f;
    int32 InfiniteAmmoAuditStage = 0;
    int32 InfiniteAmmoAuditReserve = 0;
    UPROPERTY(Transient) TObjectPtr<class UStaticMeshComponent> HolographicOptic;
    FTransform HolographicMount;
    bool bHolographicOptic=false;
    UPROPERTY(Transient) TObjectPtr<class UStaticMeshComponent> LargeDrum;
    FTransform DrumMount;
    bool bDrumVisual=false;
    void UpdateDrumDropVisual();
    bool bDrumReleasedDuringReload=false;
    bool bDrumMagazineHidden=false;
    int32 DrumDropCount=0;
    TWeakObjectPtr<AActor> LastDroppedDrum;
    FVector LastDrumDropStart=FVector::ZeroVector;
    bool bGunsmithInspection=false;
    bool bDrumInstalled=false;
    UPROPERTY(Transient) TObjectPtr<class UAnimSequence> DrumReloadAnimation;
    UPROPERTY(Transient) TMap<TObjectPtr<class UAnimSequence>, TObjectPtr<class UAnimSequence>> DrumSupportAnimations;
    UPROPERTY(Transient) TObjectPtr<class UAnimSequence> DrumReloadEmptyAnimation;
    UPROPERTY(Transient) TArray<TObjectPtr<class UStaticMeshComponent>> FoldingSightHeads;
    TArray<FTransform> FoldingSightMounts;
    float SightFoldAlpha=0.f;
    void InitializeFoldingSights();
    void UpdateFoldingSights(float DeltaSeconds);
    FVector HolographicAimPoint() const;
    bool bUsingM4Infima = false;
    void MoveForward(float Value);
    void MoveRight(float Value);
    void Turn(float Value);
    void LookUp(float Value);
    void SprintPressed();
    void SprintReleased();
    void SlidePressed();
    void JumpPressed();
    void JumpReleased();
    void FirePressed();
    void FireReleased();
    void AimPressed();
    void AimReleased();
    void ReloadPressed();
    void InspectPressed();
    void RefreshMovementState();
    void StartSlide();
    void StopSlide(bool bTryToStand);
    void TryBufferedJump();
    void UpdateSlide(float DeltaSeconds);
    void UpdateWeaponState(float DeltaSeconds);
    void UpdateWeaponFeedback(float DeltaSeconds);
    void UpdateCamera(float DeltaSeconds);
    void SetAimingState(bool bNewAiming);
    void UpdateADSProgress();
    void UpdateViewmodel(float DeltaSeconds);
    void UpdateActionPose(float DeltaSeconds);
    void UpdateADSPose();
    void ExitSprintForWeapon(double ExitTime = -1.0);
    void StartSprintToFireLock(double StartTime);
    void ServiceHeldFire();
    void EmitMechanicalCue(int32 CueIndex);
    void PlayMechanicalSound(USoundBase* Sound, float Volume);
    void StopMechanicalAudio();
    float ReloadSourceTime(float RuntimeTime) const;
    float ReloadRuntimeTime(float SourceTime) const;
    float LookSensitivityScale() const;
    void FireShot();
    void StartEquipCharge();
    void RunEquipFramingAcceptance(float DeltaSeconds);
    void FinishWeaponAction();
    void FinishReload();
    void ApplyShotFeedback();
    FVector ComputeShotDirection() const;
    void RunWeaponAudit(float DeltaSeconds);
    void RunGunplayAcceptance(float DeltaSeconds);
    void PlayWeaponAnimation(UAnimSequence* Animation, bool bLoop, float PlayRate = 1.0f, float StartPosition = 0.0f);
    void ResumeWeaponPose();
    void PlaySound2D(USoundBase* Sound, float VolumeMultiplier) const;
    UAnimSequence* LoadAKMAnimation(const TCHAR* AssetName);
    USoundBase* LoadAKMSound(const TCHAR* AssetName);
    bool CanStand() const;
    bool IsWeaponBusy() const;
    float HorizontalSpeed() const;
    float VerticalToHorizontalFOV(float VerticalFOV) const;
    static void AdvanceSpring(FVector& Position, FVector& Velocity, float Stiffness, float Damping, float DeltaSeconds);
    static void AdvanceSpring(float& Position, float& Velocity, float Stiffness, float Damping, float DeltaSeconds);

    UPROPERTY(Transient) FVector2D MoveInput = FVector2D::ZeroVector;
    UPROPERTY(Transient) FVector2D LookInput = FVector2D::ZeroVector;
    FVector CameraRestLocation = FVector::ZeroVector;
    float CameraBobPhase = 0.0f;
    float SlideAge = 0.0f;
    float SlideTimeRemaining = 0.0f;
    float SlideBoostCooldownRemaining = 0.0f;
    float JumpBufferRemaining = 0.0f;
    float SavedGroundFriction = 0.0f;
    float SavedBrakingDeceleration = 0.0f;

    UPROPERTY(Transient) bool bSprintHeld = false;
    UPROPERTY(Transient) bool bIsSprinting = false;
    UPROPERTY(Transient) bool bIsSliding = false;
    UPROPERTY(Transient) bool bIsAiming = false;
    UPROPERTY(Transient) bool bFireHeld = false;
    bool bAimHeld = false;
    UPROPERTY(Transient) int32 MagazineAmmo = 30;
    UPROPERTY(Transient) int32 ReserveAmmo = 90;
    UPROPERTY(Transient) EAKMWeaponState WeaponState = EAKMWeaponState::Equipping;

    UPROPERTY(Transient) TObjectPtr<UAnimSequence> IdleAnimation;
    UPROPERTY(Transient) TObjectPtr<UAnimSequence> AimAnimation;
    UPROPERTY(Transient) TObjectPtr<UAnimSequence> FireAnimation;
    UPROPERTY(Transient) TObjectPtr<UAnimSequence> AimFireAnimation;
    UPROPERTY(Transient) TObjectPtr<UAnimSequence> ReloadAnimation;
    UPROPERTY(Transient) TObjectPtr<UAnimSequence> ReloadEmptyAnimation;
    UPROPERTY(Transient) TObjectPtr<UAnimSequence> InspectAnimation;
    UPROPERTY(Transient) TObjectPtr<UAnimSequence> EquipAnimation;
    UPROPERTY(Transient) TObjectPtr<UFPSGunplayAnimInstance> GunplayAnimation;
    UPROPERTY(Transient) TObjectPtr<UAnimSequence> ActiveActionAnimation;
    UPROPERTY(Transient) TObjectPtr<USoundBase> FireSound;
    UPROPERTY(VisibleAnywhere, Category = "M4|Audio") TObjectPtr<UAudioComponent> M4FireVoice;
    UPROPERTY(Transient) TMap<FName, TObjectPtr<UAudioComponent>> MechanicalVoices;
    UPROPERTY(Transient) TObjectPtr<USoundBase> BoltReleaseSound;
    UPROPERTY(Transient) TObjectPtr<USoundBase> EquipSound;
    UPROPERTY(Transient) TObjectPtr<USoundBase> MagOutSound;
    UPROPERTY(Transient) TObjectPtr<USoundBase> MagInsertSound;
    UPROPERTY(Transient) TObjectPtr<USoundBase> MagSeatSound;
    UPROPERTY(Transient) TObjectPtr<USoundBase> ChargePullSound;
    UPROPERTY(Transient) TObjectPtr<USoundBase> ChargeReleaseSound;
    UPROPERTY(Transient) TObjectPtr<USoundBase> DryClickSound;
    UPROPERTY(Transient) TObjectPtr<USoundBase> CriticalHitSound;

    float WeaponStateElapsed = 0.0f;
    float WeaponStateDuration = 0.0f;
    double WeaponActionStartedAt = 0.0;
    int32 NextMechanicalCue = 0;
    TArray<float> MechanicalCueTimes;
    TArray<TObjectPtr<USoundBase>> MechanicalCueSounds;
    bool bPendingEmptyReload = false;

    float WeaponADSFactor = 0.0f;
    float ADSProgress = 0.0f;
    float ADSStartProgress = 0.0f;
    double ADSStartedAt = 0.0;
    float SprintToFireLeft = 0.0f;
    double SprintStartedAt = 0.0;
    double SprintFireUnlockTime = 0.0;
    double NextAllowedShotTime = 0.0;
    double LastShotWorldTime = -1.0;
    double TriggerFirstShotWorldTime = -1.0;
    static constexpr int32 MaxFireCatchUpShots = 4;
    bool bUsingReplacement = false;
    bool bSightCalibrated = false;
    FVector CalibratedADSLocation = FVector::ZeroVector;
    FQuat CalibratedADSRotation = FQuat::Identity;
    float ActionElapsed = 0.0f;
    float ActionDuration = 0.0f;
    float ActionStartPosition = 0.0f;
    float ActionPlayRate = 1.0f;
    float ActionBlendIn = 0.035f;
    float LandingOffset = 0.0f;
    float LandingVelocity = 0.0f;
    float PreviousVerticalVelocity = 0.0f;
    bool bWasGrounded = true;
    float NearWallAlpha = 0.0f;
    float CameraADSFactor = 0.0f;
    float WeaponBobTime = 0.0f;
    FVector WeaponBobPosition = FVector::ZeroVector;
    FVector WeaponBobRotation = FVector::ZeroVector;
    FVector WeaponSwayPosition = FVector::ZeroVector;
    FVector WeaponSwayRotation = FVector::ZeroVector;
    float SprintPoseFactor = 0.0f;
    float SprintCameraFactor = 0.0f;

    FVector GunKickPosition = FVector::ZeroVector;
    FVector GunKickPositionVelocity = FVector::ZeroVector;
    FVector GunKickRotation = FVector::ZeroVector;
    FVector GunKickRotationVelocity = FVector::ZeroVector;
    FVector GunJitterPosition = FVector::ZeroVector;
    FVector GunJitterPositionVelocity = FVector::ZeroVector;
    FVector GunJitterRotation = FVector::ZeroVector;
    FVector GunJitterRotationVelocity = FVector::ZeroVector;
    float GunFlip = 0.0f;
    float GunFlipVelocity = 0.0f;

    float CameraKickPitch = 0.0f;
    float CameraKickPitchVelocity = 0.0f;
    float CameraKickYaw = 0.0f;
    float CameraKickYawVelocity = 0.0f;
    FVector CameraJitterPosition = FVector::ZeroVector;
    FVector CameraJitterPositionVelocity = FVector::ZeroVector;
    FVector CameraJitterRotation = FVector::ZeroVector;
    FVector CameraJitterRotationVelocity = FVector::ZeroVector;
    float FireTrauma = 0.0f;
    float FOVPunch = 0.0f;
    float FeedbackTime = 0.0f;
    int32 RecoilPatternIndex = 0;
    float TimeSinceLastShot = 100.0f;
    float PatternRecoveryAccumulator = 0.0f;
    float CurrentSpread = 0.0f;
    float SpreadRecoveryLeft = 0.0f;
    float MoveSpread = 0.0f;
    float AirSpread = 0.0f;

    FTimerHandle FireTimerHandle;
    FTimerHandle WeaponPoseTimerHandle;
    bool bRunWeaponAudit = false;
    float WeaponAuditTime = 0.0f;
    int32 WeaponAuditStage = 0;
    bool bRunGunplayAcceptance = false;
    int32 GunplayAuditStage = 0;
    float GunplayAuditElapsed = 0.0f;
    double GunplayAuditWallStarted = 0.0;
    double GunplayAuditWorldStarted = 0.0;
    float GunplayAuditMaxDelta = 0.0f;
    int32 GunplayAuditTicks = 0;
    int32 GunplayAuditFailures = 0;
    int32 ShotsFired = 0;
    bool bLastShotMuzzleBlocked = false;
    int32 AuditSavedShots = 0;
    int32 AuditSavedAmmo = 0;
    float AuditSavedActionTime = 0.0f;
    double AuditSprintFireDeadline = 0.0;
    TWeakObjectPtr<AActor> GunplayAuditWall;
    FString GunplayAuditDirectory;
    TMap<FName, FVector> AuditRigidBoneOffsets;
    float AuditMaxRigidBoneDriftCM = 0.0f;
    int32 AuditRigidPoseSamples = 0;
    int32 AuditNormalMechanicalCues = 0;
    int32 AuditEmptyMechanicalCues = 0;
    int32 AuditBoltReleaseCues = 0;
    float AuditMaxMechanicalLateness = 0.0f;
    float AuditMaxEmptyBoltTravelCM = 0.0f;
};
