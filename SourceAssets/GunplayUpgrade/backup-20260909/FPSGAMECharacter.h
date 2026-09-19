#pragma once

#include "CoreMinimal.h"
#include "GameFramework/Character.h"
#include "FPSGAMECharacter.generated.h"

class UCameraComponent;
class USkeletalMeshComponent;
class UAnimSequence;
class USoundBase;

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

public:
    AFPSGAMECharacter();
    virtual void Tick(float DeltaSeconds) override;
    virtual void SetupPlayerInputComponent(UInputComponent* PlayerInputComponent) override;

    UFUNCTION(BlueprintPure, Category = "FPS Movement") bool IsSprinting() const { return bIsSprinting; }
    UFUNCTION(BlueprintPure, Category = "FPS Movement") bool IsSliding() const { return bIsSliding; }
    UFUNCTION(BlueprintPure, Category = "AKM") bool IsAiming() const { return bIsAiming; }
    UFUNCTION(BlueprintPure, Category = "AKM") bool IsReloading() const { return WeaponState == EAKMWeaponState::Reloading || WeaponState == EAKMWeaponState::ReloadingEmpty; }
    UFUNCTION(BlueprintPure, Category = "AKM") int32 GetMagazineAmmo() const { return MagazineAmmo; }
    UFUNCTION(BlueprintPure, Category = "AKM") int32 GetReserveAmmo() const { return ReserveAmmo; }
    UFUNCTION(BlueprintPure, Category = "AKM") EAKMWeaponState GetWeaponState() const { return WeaponState; }

protected:
    virtual void BeginPlay() override;

    UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Camera") TObjectPtr<UCameraComponent> FirstPersonCamera;
    UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "AKM") TObjectPtr<USkeletalMeshComponent> AKMViewmodel;

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
    UPROPERTY(EditDefaultsOnly, Category = "AKM|Viewmodel") FVector ADSViewmodelLocation = FVector(11.8734f, -0.0085f, 1.6058f);
    UPROPERTY(EditDefaultsOnly, Category = "AKM|Viewmodel") FVector ViewmodelScale = FVector(1.0f);
    UPROPERTY(EditDefaultsOnly, Category = "AKM|Viewmodel") FRotator ViewmodelRotation = FRotator(0.0f, 90.0f, 0.0f);
    UPROPERTY(EditDefaultsOnly, Category = "AKM|Viewmodel") FRotator ADSViewmodelRotation = FRotator(-0.0865f, 90.0f, 0.0f);
    UPROPERTY(EditDefaultsOnly, Category = "AKM|Viewmodel") float WeaponADSSmooth = 9.985774f;
    UPROPERTY(EditDefaultsOnly, Category = "AKM|Viewmodel") float CameraADSSmooth = 9.0f;

    UPROPERTY(EditDefaultsOnly, Category = "AKM|Combat") float FireInterval = 0.12f;
    UPROPERTY(EditDefaultsOnly, Category = "AKM|Combat") float DamagePerShot = 30.0f;
    UPROPERTY(EditDefaultsOnly, Category = "AKM|Combat") float TraceDistance = 100000.0f;
    UPROPERTY(EditDefaultsOnly, Category = "AKM|Combat") float ReloadDuration = 2.7f;
    UPROPERTY(EditDefaultsOnly, Category = "AKM|Combat") float EmptyReloadDuration = 3.466667f;
    UPROPERTY(EditDefaultsOnly, Category = "AKM|Combat") int32 MagazineCapacity = 30;

private:
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
    void UpdateViewmodel(float DeltaSeconds);
    void FireShot();
    void StartEquipCharge();
    void FinishWeaponAction();
    void FinishReload();
    void ApplyShotFeedback();
    FVector ComputeShotDirection() const;
    void RunWeaponAudit(float DeltaSeconds);
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
    UPROPERTY(Transient) TObjectPtr<USoundBase> FireSound;
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
    int32 NextMechanicalCue = 0;
    TArray<float> MechanicalCueTimes;
    TArray<TObjectPtr<USoundBase>> MechanicalCueSounds;
    bool bPendingEmptyReload = false;

    float WeaponADSFactor = 0.0f;
    float CameraADSFactor = 0.0f;
    float WeaponBobTime = 0.0f;
    FVector WeaponBobPosition = FVector::ZeroVector;
    FVector WeaponBobRotation = FVector::ZeroVector;
    FVector WeaponSwayPosition = FVector::ZeroVector;
    FVector WeaponSwayRotation = FVector::ZeroVector;
    float SprintPoseFactor = 0.0f;

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
};
