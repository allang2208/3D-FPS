#pragma once

#include "CoreMinimal.h"
#include "GameFramework/Character.h"
#include "Weapons/WeaponHandling.h"
#include "Weapons/M4TacticalSprintComponent.h"
#include "Monsters/MonsterHitFeedback.h"
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
    Inspecting,
    QuickCombat
};

UCLASS()
class FPSGAME_API AFPSGAMECharacter : public ACharacter
{
    GENERATED_BODY()

    friend class UColdSteelWeaponIcons;
    friend class AColdSteelPickup;
    friend class UM4GunsmithWidget;
    friend class UFPSTraversalComponent;
    friend class UFPSStairAudit;
    friend class UTacticalDeviceComponent;
    friend class UPistolDualWieldComponent;

public:
    UPROPERTY(EditDefaultsOnly, Category = "Weapon|Model") bool bUseM4Infima = true;
    UPROPERTY(EditDefaultsOnly, Category = "Weapon|Model") bool bUseQBZ191 = false;
    UPROPERTY(EditDefaultsOnly, Category = "Weapon|Model") bool bUseASH12 = false;
    UPROPERTY(EditDefaultsOnly, Category = "Weapon|Model") bool bUseM1911 = false;
    UPROPERTY(EditDefaultsOnly, Category = "Weapon|Model") bool bUseDanWesson715 = false;
    bool IsPistolWeapon() const { return bUseM1911 || bUseDanWesson715; }
    UPROPERTY(VisibleAnywhere, Category="Weapon") TObjectPtr<class UPistolDualWieldComponent> DualPistols;
    UPROPERTY(VisibleAnywhere, Category="Skills") TObjectPtr<class UFPSQuickCombatComponent> QuickCombatPistol;
    bool IsDualWieldingPistols() const;
    /** 手枪版快速进战：单持松左手、右手持枪握把前砸；仲裁通过后转交动作组件。 */
bool TriggerPistolQuickCombat();
    /** 步枪版快速进战（M4 枪托砸击）：双手持枪的整枪动作；仲裁通过后转交同一动作组件。 */
    bool TriggerRifleStockMelee();
    bool IsWeaponFireHeld() const;
    void RunWeaponVolumeAudit();
    int32 GetRevolverCaseCount() const { return RevolverCaseCount; }
    AFPSGAMECharacter(const FObjectInitializer& ObjectInitializer = FObjectInitializer::Get());
    void ApplyColdSteelProfile(class UColdSteelStatusModel* Profile);
    bool HasInventoryWeapon() const { return bInventoryWeaponReady; }
    // Casting owns the left hand independently from movement and firearm hip fire.
    bool IsLeftHandBusyForCast() const;
    // The off-hand pistol of an akimbo pair holds the left hand until the loadout
    // changes, so left-hand spells refuse the request instead of queueing behind it.
    bool IsLeftHandHeldForCast() const;
    bool IsCastingWithLeftHand() const;
    bool IsCastBlockingLeftHandAction() const;
    // Single-weapon hip cone, or the real per-hand dual cone while both pistols
    // are out; the reticle and the shot direction must share this one value.
    float GetHipSpread() const;
    FVector2D GetCrosshairHalfExtent(FVector2D LocalSize) const;
    /** bFirearmHit selects the gun hit cue; melee and skills keep the shared one. */
    void NotifyConfirmedWeaponHit(AActor* Target, float AppliedDamage,const FWeaponDamageResult* DamageResult=nullptr,bool bFirearmHit=false);
    float GetHitMarkerOpacity() const;
    bool GetMonsterHitFeedback(FMonsterHitFeedback& Out) const;
private:
    double LastConfirmedWeaponHitTime = -1000.0;
    UPROPERTY(Transient) TObjectPtr<USoundBase> ConfirmedMonsterHitSound;
    FMonsterHitFeedback LastMonsterHit;
public:
    bool IsTraversing() const;
    UFUNCTION(BlueprintPure, Category="FPS Movement|Dodge") bool IsDodging() const;
    UFUNCTION(BlueprintCallable, Category="FPS Movement|Dodge") bool TryDodge();
    virtual float TakeDamage(float DamageAmount, const FDamageEvent& DamageEvent,
        AController* EventInstigator, AActor* DamageCauser) override;
    /** Menus swallow the key release, so a held trajectory preview is dropped here too. */
    void SuspendWeaponForMenu();
    void SetGunsmithOptic(bool bHolographic);
    void SetGunsmithOpticVariant(const FString& Variant);
    const FString& GetGunsmithOpticVariant() const { return OpticVariant; }
    float GetOpticMagnification() const { return OpticVariant==TEXT("lpvo_1_6x")?LPVOMagnification:(OpticVariant==TEXT("prism_scope_2x")?2.f:1.f); }
    float EffectiveADSVerticalFOV() const;
    bool AdjustOpticMagnification(float Delta);
    void SetLPVOMagnification(float Value);
    float GetScopePresentationAlpha() const;
    // Optic-layer firing presentation facts. Read-only: they never write
    // ControlRotation, the shot direction or the trace.
    float GetLastShotAgeSeconds() const;
    float GetLastShotSeed() const;
    void UpdateScopePresentation();
private:
    TArray<TWeakObjectPtr<class UPrimitiveComponent>> ScopeHiddenParts;
public:
    void SetGunsmithMagazineAttachment(const FString& Id);
    void SetGunsmithMuzzle(const FString& Variant);
    void SetGunsmithHandstop(const FString& Variant);
    void SetGunsmithStock(const FString& Variant);
    void SetGunsmithRearGrip(const FString& Variant);
    void SetGunsmithTactical(const FString& Variant);
    UPROPERTY(Transient) TObjectPtr<class UTacticalDeviceComponent> TacticalDevice;
    UPROPERTY(Transient) TObjectPtr<class UStaticMeshComponent> RearGripAttachment;
    bool HasSkeletonStock() const;
    bool ValidateStockAttachment() const;
    void RunStockAudit();
    UPROPERTY(Transient) TObjectPtr<class UStaticMeshComponent> StockAttachment;
    FTransform StockMount;
    bool bSkeletonStock=false;
    int32 StockAuditStage=0, StockAuditChecks=0, StockAuditFailures=0;
    float StockAuditNextTime=0.f;
    bool HasPrismHandstop() const;
    bool HasVerticalForegrip() const;
    bool HasCantedForegrip() const;
    bool HasAngledForegrip() const;
    FVector GetEffectiveMuzzleLocation() const;
    FVector GetEffectiveMuzzleForward() const;
    bool IsMuzzleSuppressed() const {return MuzzleVariant==TEXT("true")||MuzzleVariant==TEXT("tactical_suppressor");}
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
    /** Stable eye/control-aim frame for melee; excludes cosmetic camera feedback. */
    FTransform GetMeleeAimTransform() const;
    virtual void SetupPlayerInputComponent(UInputComponent* PlayerInputComponent) override;

    UFUNCTION(BlueprintPure, Category = "FPS Movement") bool IsSprinting() const { return bIsSprinting; }
    UFUNCTION(BlueprintPure, Category = "FPS Movement") bool IsSliding() const { return bIsSliding; }
    UFUNCTION(BlueprintPure, Category = "AKM") bool IsAiming() const { return bIsAiming; }
    UFUNCTION(BlueprintPure, Category = "AKM") bool IsReloading() const;
    UFUNCTION(BlueprintPure, Category = "AKM") int32 GetMagazineAmmo() const { return MagazineAmmo; }
    int32 GetMagazineCapacity() const { return MagazineCapacity; }
    UFUNCTION(BlueprintPure, Category = "AKM") int32 GetReserveAmmo() const { return ReserveAmmo; }
    UFUNCTION(BlueprintPure, Category = "AKM") bool HasInfiniteReserveAmmo() const;
    UFUNCTION(BlueprintPure, Category = "AKM") EAKMWeaponState GetWeaponState() const { return WeaponState; }

protected:
    UPROPERTY(VisibleAnywhere, Category="FPS Movement") TObjectPtr<class UFPSTraversalComponent> Traversal;
    UPROPERTY(VisibleAnywhere, Category="Weapon") TObjectPtr<class URuneSwordComponent> RuneSword;
    void SetAngledForegrip(bool bEnabled);
    void InitializeForegripAnimations();
    void InitializePrismGripAnimations();
    void InitializeCantedGripAnimations();
    void SetCantedForegrip(bool bEnabled);
    UPROPERTY(Transient) TObjectPtr<class UStaticMeshComponent> CantedForegrip;
    UPROPERTY(Transient) TMap<TObjectPtr<UAnimSequence>,TObjectPtr<UAnimSequence>> CantedGripAnimations;
    void InitializeVerticalGripAnimations();
    void SetVerticalForegrip(bool bEnabled);
    UPROPERTY(Transient) TObjectPtr<class UStaticMeshComponent> VerticalForegrip;
    UPROPERTY(Transient) TMap<TObjectPtr<UAnimSequence>,TObjectPtr<UAnimSequence>> VerticalGripAnimations;
    void RunForegripAudit();
    int32 ForegripAuditStage=0, ForegripAuditFailures=0, ForegripAuditCapture=0;
    float ForegripAuditNextTime=0.f, ForegripAuditLastCapture=-1.f;
    FVector ForegripAuditSeatedMagazine=FVector::ZeroVector;
    FVector ForegripAuditSeatedHand=FVector::ZeroVector;
    bool bForegripAuditSawPull=false,bForegripAuditSawDrop=false;
    UPROPERTY(Transient) TObjectPtr<class UStaticMeshComponent> AngledForegrip;
    UPROPERTY(Transient) TMap<TObjectPtr<UAnimSequence>,TObjectPtr<UAnimSequence>> ForegripAnimations;
    UPROPERTY(Transient) TMap<TObjectPtr<UAnimSequence>,TObjectPtr<UAnimSequence>> PrismGripAnimations;
    UPROPERTY(Transient) TObjectPtr<class UStaticMeshComponent> PrismHandstop;
    UPROPERTY(Transient) TObjectPtr<class UStaticMeshComponent> MuzzleAttachment;
    UPROPERTY(VisibleAnywhere) TObjectPtr<class UFPSBallisticsComponent> Ballistics;
    UPROPERTY(Transient) TObjectPtr<USoundBase> SuppressedFireSound;
    FString MuzzleVariant;
    FVector MuzzleLocalTip=FVector::ZeroVector;
    FVector MuzzleLocalAxis=FVector::ForwardVector;
    float ProjectileSpeedCM=9000.f;
    float EffectiveWeaponRangeCM=100000.f;
    float HipSpreadMultiplier=1.f;
    int32 ADSHorizontalRecoilIndex=0;
    void RunMuzzleMigrationAudit();
    FWeaponHandling WeaponHandling;
    void RunWeaponHandlingAudit();
    void RunM1911DevelopmentAudit();
    void RunBallisticPresentationAudit();
    virtual void BeginPlay() override;
    virtual void EndPlay(const EEndPlayReason::Type Reason) override;
    void InitializeWeaponVisuals();
    FString ActiveInventoryWeapon;
    FString ActiveInventoryWeaponDefinition;
    void ApplyWeaponAttachmentPresentation(const TMap<FString,FString>& Parts);
    TMap<FString,FString> AppliedWeaponVisualParts;
    bool bWeaponVisualPartsApplied = false;
    bool bInventoryWeaponReady = true;
    bool bReloadAfterCasting = false;
    void ServiceReloadAfterCasting();

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
    float PistolMoveSpeedMultiplier = 1.f;
    UPROPERTY(EditDefaultsOnly, Category="FPS Movement|Dodge", meta=(ClampMin="0.01", Units="s")) float DodgeDuration = .3f;
    UPROPERTY(EditDefaultsOnly, Category="FPS Movement|Dodge", meta=(ClampMin="1", Units="cm")) float DodgeDistance = 300.f;
    bool bDodgeMeleeRewarded=false, bDodgeRangedRewarded=false;
    UPROPERTY(EditDefaultsOnly, Category="FPS Movement|Dodge", meta=(ClampMin="0.01", Units="s")) float DodgeTapMaximumHold = .2f;
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
    UPROPERTY(EditDefaultsOnly, Category = "M4|Sprint") FVector M4SprintMidpointOffset = FVector(-1.5f, -0.5f, -1.0f);
    float M4SprintPhase = 0.0f;
    UPROPERTY(EditDefaultsOnly, Category = "Weapon|Locomotion", meta = (ClampMin = "0.0", ClampMax = "2.0")) float RifleLocomotionScale = 1.0f;
    void UpdateLocomotionPresentation(float DeltaSeconds);
    void ResetRifleLocomotion();
    FVector LocomotionLaggedVelocity = FVector::ZeroVector;
    FVector RifleInertiaOffset = FVector::ZeroVector;
    FVector RifleInertiaVelocity = FVector::ZeroVector;
    // Camera-space degrees: pitch, yaw, roll. Kept separate from mesh import axes.
    FVector RifleInertiaAngles = FVector::ZeroVector;
    FVector RifleInertiaAngularVelocity = FVector::ZeroVector;
    float GroundLocomotionWeight = 0.0f;
    float LocomotionSideAlpha = 0.0f;
    float RifleLocomotionWeight = 0.0f;
    bool bLocomotionInitialized = false;
    // Camera-space framing; sprint arm/weapon motion is authored in separate clips.
    UPROPERTY(EditDefaultsOnly, Category = "Pistol|Viewmodel") FVector PistolHipViewmodelLocation = FVector(-2.f, 3.f, -6.5f);
    UPROPERTY(EditDefaultsOnly, Category = "Pistol|Viewmodel") FVector RevolverHipViewmodelLocation = FVector(1.f, 3.2f, -7.f);
    UPROPERTY(EditDefaultsOnly, Category = "Pistol|Locomotion") FVector PistolWalkAmplitudeCM = FVector(.20f, .65f, .32f);
    UPROPERTY(EditDefaultsOnly, Category = "Pistol|Locomotion", meta = (ClampMin = "0.0", ClampMax = "1.0")) float PistolIdleBreathCM = .12f;
    UPROPERTY(Transient) TObjectPtr<UAnimSequence> PistolSprintAnimation;
    UPROPERTY(Transient) TObjectPtr<UAnimSequence> PistolSprintEmptyAnimation;
    FVector PistolLocomotionOffset = FVector::ZeroVector;
    FRotator PistolLocomotionRotation = FRotator::ZeroRotator;
    FVector PistolLaggedVelocity = FVector::ZeroVector;
    float PistolLocomotionAlpha = 0.0f;
    float PistolSprintPhase = 0.0f;
    void UpdatePistolLocomotion(float DeltaSeconds);
    void ResetPistolLocomotion();
    UPROPERTY(EditDefaultsOnly, Category = "AKM|Viewmodel") FVector ADSViewmodelLocation = FVector(11.8734f, -0.0085f, 1.6058f);
    UPROPERTY(EditDefaultsOnly, Category = "AKM|Viewmodel") FVector ViewmodelScale = FVector(1.0f);
    UPROPERTY(EditDefaultsOnly, Category = "AKM|Viewmodel") FRotator ViewmodelRotation = FRotator(0.0f, 90.0f, 0.0f);
    UPROPERTY(EditDefaultsOnly, Category = "AKM|Viewmodel") FRotator ADSViewmodelRotation = FRotator(-0.0865f, 90.0f, 0.0f);

    UPROPERTY(EditDefaultsOnly, Category = "AKM|Combat") float FireInterval = 0.12f;
    UPROPERTY(EditDefaultsOnly, Category = "AKM|Combat") float DamagePerShot = 30.0f;
    UPROPERTY(EditDefaultsOnly, Category = "AKM|Combat") float TraceDistance = 100000.0f;
    UPROPERTY(EditDefaultsOnly, Category = "AKM|Combat") float ReloadDuration = 2.1f;
    UPROPERTY(EditDefaultsOnly, Category = "AKM|Combat") float EmptyReloadDuration = 2.7f;
    UPROPERTY(EditDefaultsOnly, Category = "AKM|Combat") int32 MagazineCapacity = 30;

private:
    void RunInfiniteAmmoAudit();
    void RunDrumGripAudit();
    void RunAKMIntegrationAudit();
    void RunQBZ191IntegrationAudit();
    void RunASH12IntegrationAudit();
    int32 DrumGripAuditStage = 0;
    int32 DrumGripAuditFailures = 0;
    int32 DrumGripAuditReserve = 0;
    int32 DrumGripAuditCapture = 0;
    float DrumGripAuditLastCapture = -1.f;
    float DrumGripAuditRightDepthMin = 0.f;
    float DrumGripAuditRightDepthMax = 0.f;
    float DrumGripAuditFramingMaxError = 0.f;
    float DrumGripAuditReloadDuration = 0.f;
    int32 InfiniteAmmoAuditStage = 0;
    int32 InfiniteAmmoAuditReserve = 0;
    UPROPERTY(Transient) TObjectPtr<class UStaticMeshComponent> HolographicOptic;
    UPROPERTY(Transient) TObjectPtr<class UStaticMeshComponent> AKMOpticBridge;
    FTransform HolographicMount;
    bool bHolographicOptic=false;
    FString OpticVariant;
    float LPVOMagnification=1.f;
    UPROPERTY(Transient) TObjectPtr<class UStaticMeshComponent> LPVORing;
    UPROPERTY(Transient) TObjectPtr<class UStaticMeshComponent> LargeDrum;
    FTransform DrumMount;
    FString MagazineAttachmentId;
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
    TArray<FVector> FoldingSightAxes;
    TArray<float> FoldingSightAngles;
    float SightFoldAlpha=0.f;
    void InitializeFoldingSights();
    void UpdateFoldingSights(float DeltaSeconds);
    FVector HolographicAimPoint() const;
    FVector OpticLocalAimPoint() const;
    bool bUsingM4Infima = false;
    void MoveForward(float Value);
    void MoveRight(float Value);
    void Turn(float Value);
    void LookUp(float Value);
    void SprintPressed();
    void SprintReleased();
    float DodgePresentationWeight() const;
    void SlidePressed();
    void JumpPressed();
    void JumpReleased();
    void FirePressed();
    void FireInputReleased();
    void FireReleased();
    void AimPressed();
    void AimReleased();
    void ReloadPressed();
    void InspectPressed();
    void QuickCombatPressed();
    /** 当前 M4 的握把配置（冲刺与枪托砸击共用同一解析口径）。 */
    EM4SprintGrip ResolveRifleGripProfile() const;
    /** 按握把配置取枪托砸击 clip（六个配置各自一条作者源动画）。 */
    UAnimSequence* RifleQuickCombatClip(EM4SprintGrip Grip);
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
    FRotator GetViewmodelBaseRotation() const;
    void UpdateViewmodel(float DeltaSeconds);
    void UpdateActionPose(float DeltaSeconds);
    void UpdateADSPose();
    void ExitSprintForWeapon(double ExitTime = -1.0);
    void StartSprintToFireLock(double StartTime);
    void ServiceHeldFire();
    void EmitMechanicalCue(int32 CueIndex);
    void PlayMechanicalSound(USoundBase* Sound, float Volume, float StartTime = 0.f);
    void StopMechanicalAudio();
    float ReloadSourceTime(float RuntimeTime) const;
    float ReloadRuntimeTime(float SourceTime) const;
    float LookSensitivityScale() const;
    void FireShot();
    void StartEquipCharge();
    void InterruptPistolEquip();
    void SetM1911Optic(const FString& Variant);
    void SetDanWesson715Optic(const FString& Variant);
    void SetM1911Muzzle(const FString& Variant);
    void RunEquipFramingAcceptance(float DeltaSeconds);
    void FinishWeaponAction();
    void FinishReload();
    void ApplyShotFeedback();
    FVector ComputeShotDirection() const;
    void RunWeaponAudit(float DeltaSeconds);
    void RunGunplayAcceptance(float DeltaSeconds);
    void RunRifleSprintAcceptance(float DeltaSeconds);
    void PlayWeaponAnimation(UAnimSequence* Animation, bool bLoop, float PlayRate = 1.0f, float StartPosition = 0.0f);
    void ResumeWeaponPose();
    void PlaySound2D(USoundBase* Sound, float VolumeMultiplier) const;
    UAnimSequence* LoadAKMAnimation(const TCHAR* AssetName);
    // Pistol-only presentation on the common first-person rig and action clock.
    UPROPERTY(Transient) TObjectPtr<UAnimSequence> PistolIdleEmptyAnimation;
    UPROPERTY(Transient) TObjectPtr<UAnimSequence> PistolAimEmptyAnimation;
    UPROPERTY(Transient) TObjectPtr<UAnimSequence> PistolFireLastAnimation;
    UPROPERTY(Transient) TObjectPtr<UAnimSequence> PistolAimFireLastAnimation;
    bool bPistolShotPending = false;
    int32 RevolverCaseCount = 6;
    bool bRevolverSpeedloaderInstalled = false;
    bool bRevolverSingleReload = false;
    bool bRevolverCasesCleared = false;
    bool bRevolverReloadAfterFire = false;
    bool IsRevolverFireActionPlaying() const;
    void ServiceRevolverReloadAfterFire();
    int32 RevolverReloadStartLive = 0;
    int32 RevolverReloadCount = 0;
    int32 RevolverReloadCommitted = 0;
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
    double SprintPressedAt = -1.0;
    UPROPERTY(Transient) bool bIsSprinting = false;
    UPROPERTY(Transient) bool bIsSliding = false;
    UPROPERTY(Transient) bool bIsAiming = false;
    // Single-weapon input only. Common consumers query IsWeaponFireHeld().
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
    /** 快速进战（手枪握把砸击）单发动作；仅 Dan Wesson 715 有作者源 clip。 */
    UPROPERTY(Transient) TObjectPtr<UAnimSequence> QuickCombatAnimation;
    /** 快速进战（步枪枪托砸击）六条作者源 clip：Base/Drum/Angled/Vertical/Canted/Prism。 */
    UPROPERTY(Transient) TArray<TObjectPtr<UAnimSequence>> RifleQuickCombatClips;
    UPROPERTY(Transient) TObjectPtr<UAnimSequence> EquipAnimation;
    UPROPERTY(Transient) TObjectPtr<UFPSGunplayAnimInstance> GunplayAnimation;
    UPROPERTY(Transient) TObjectPtr<UAnimSequence> ActiveActionAnimation;
    UPROPERTY(Transient) TObjectPtr<USoundBase> FireSound;
    UPROPERTY(Transient) TArray<TObjectPtr<USoundBase>> RevolverSpeedloaderSounds;
    UPROPERTY(Transient) TArray<TObjectPtr<USoundBase>> RifleFireVariants;
    UPROPERTY(Transient) TArray<TObjectPtr<USoundBase>> RifleSuppressedVariants;
    UPROPERTY(Transient) TObjectPtr<class USoundConcurrency> RifleFireConcurrency;
    int32 LastRifleFireVariant = INDEX_NONE;
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
    // Seconds since the last shot for the fire clip compensation layer, negative
    // when idle. Weapons whose own fire animation carries no gun motion read
    // their recoil from FPSVisualRecoil::FProfile::ClipPosition/Rotation.
    float ClipRecoilSeconds = -1.0f;
    void AdvanceVisualWeaponRecoil(double Now);
    // Dual wield keeps one recoil spring set per hand. UPistolDualWieldComponent
    // owns the per-hand control-rotation pattern, so these only add the
    // presentation layers the single-weapon path gets from ApplyShotFeedback().
    struct FDualWieldRecoil
    {
        FVector Position = FVector::ZeroVector, PositionVelocity = FVector::ZeroVector;
        FVector Rotation = FVector::ZeroVector, RotationVelocity = FVector::ZeroVector;
        FVector JitterPosition = FVector::ZeroVector, JitterPositionVelocity = FVector::ZeroVector;
        FVector JitterRotation = FVector::ZeroVector, JitterRotationVelocity = FVector::ZeroVector;
        float Flip = 0.0f, FlipVelocity = 0.0f;
        double UpdatedAt = -1.0, RecoverAt = -10.0;
    };
    FDualWieldRecoil DualRecoil[2];
    void ApplyDualWieldShotFeedback(int32 HandIndex, bool bRevolver, const FWeaponHandling& Handling,
        int32 ShotIndex, float Interval, float RecoilLoad);
    void AdvanceDualWieldHandRecoil(int32 HandIndex, bool bRevolver, const FWeaponHandling& Handling, float DeltaSeconds);
    void GetDualWieldHandRecoil(int32 HandIndex, FVector& OutOffset, FVector& OutAngles) const;
    double VisualRecoilUpdatedAt = -1.0;
    double LastVisualShotAt = -10.0;
    double VisualRecoverAt = -10.0;
    int32 VisualBurstIndex = 0;

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
    float MoveSpread = 0.0f;
    float AirSpread = 0.0f;

    FTimerHandle FireTimerHandle;
    FTimerHandle WeaponPoseTimerHandle;
    bool bRunWeaponAudit = false;
    void RunSlideCombatAcceptance(float DeltaSeconds);
    void RunReloadTimingAudit();
    bool bRunInfiniteAmmoAudit = false;
    bool bRunDrumGripAudit = false;
    bool bRunAKMIntegrationAudit = false;
    bool bRunWeaponHandlingAudit = false;
    bool bRunMuzzleMigrationAudit = false;
    bool bRunSlideCombatAudit = false;
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
