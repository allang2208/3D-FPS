#include "FPSGAMECharacter.h"

#include "Animation/AnimSequence.h"
#include "Camera/CameraComponent.h"
#include "Components/CapsuleComponent.h"
#include "Components/SkeletalMeshComponent.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "GameFramework/PlayerController.h"
#include "Kismet/GameplayStatics.h"
#include "Misc/CommandLine.h"
#include "Misc/Parse.h"
#include "Misc/Paths.h"
#include "HAL/PlatformMisc.h"
#include "HighResScreenshot.h"
#include "Sound/SoundBase.h"
#include "TimerManager.h"

namespace AKMSource
{
    constexpr float FireVolume = 0.562341f;
    constexpr float ActionVolume = 0.630957f;
    constexpr float KickStiffness = 210.0f;
    constexpr float KickDamping = 16.0f;
    constexpr float JitterStiffness = 7000.0f;
    constexpr float JitterDamping = 48.0f;
    constexpr float FlipStiffness = 260.0f;
    constexpr float FlipDamping = 16.0f;
    constexpr float CameraKickStiffness = 170.0f;
    constexpr float CameraKickDamping = 15.0f;
    constexpr float CameraADSExtraDamping = 8.0f;
    constexpr float FeedbackScale = 0.5f;
    constexpr float ViewmodelGain = 0.35f;
    constexpr float ADSCameraImpulse = 34.0f;
    constexpr float ADSAxialScale = 3.2f;
    constexpr float HipAxialScale = 2.2f;
    constexpr float ADSHorizontalScale = 0.30f;
    constexpr float ShakeDecay = 3.5f;
    constexpr float FOVPunchDecay = 6.5f;
    constexpr float FOVSmooth = 10.0f;
    constexpr float RecoveryDelay = 0.30f;
    constexpr float RecoveryInterval = 0.05f;
    const FVector2D Pattern[] = {
        {0.009f, 0.0f}, {0.012f, -0.002f}, {0.015f, 0.0025f},
        {0.018f, -0.0015f}, {0.020f, 0.003f}, {0.022f, -0.002f},
        {0.024f, 0.002f}, {0.026f, -0.001f}, {0.028f, 0.0005f}
    };
}

AFPSGAMECharacter::AFPSGAMECharacter()
{
    PrimaryActorTick.bCanEverTick = true;
    GetCapsuleComponent()->InitCapsuleSize(42.0f, 96.0f);
    GetCapsuleComponent()->SetCollisionProfileName(TEXT("Pawn"));

    FirstPersonCamera = CreateDefaultSubobject<UCameraComponent>(TEXT("FirstPersonCamera"));
    FirstPersonCamera->SetupAttachment(GetCapsuleComponent());
    FirstPersonCamera->SetRelativeLocation(FVector(0.0f, 0.0f, StandingCameraHeight));
    FirstPersonCamera->bUsePawnControlRotation = true;
    FirstPersonCamera->AspectRatio = 16.0f / 9.0f;
    FirstPersonCamera->bOverrideAspectRatioAxisConstraint = true;
    FirstPersonCamera->AspectRatioAxisConstraint = EAspectRatioAxisConstraint::AspectRatio_MaintainYFOV;

    AKMViewmodel = CreateDefaultSubobject<USkeletalMeshComponent>(TEXT("AKMViewmodel"));
    AKMViewmodel->SetupAttachment(FirstPersonCamera);
    AKMViewmodel->SetRelativeLocation(HipViewmodelLocation);
    AKMViewmodel->SetRelativeRotation(ViewmodelRotation);
    AKMViewmodel->SetRelativeScale3D(ViewmodelScale);
    AKMViewmodel->SetCollisionEnabled(ECollisionEnabled::NoCollision);
    AKMViewmodel->SetCastShadow(false);
    AKMViewmodel->SetOnlyOwnerSee(false);
    AKMViewmodel->SetOwnerNoSee(false);
    AKMViewmodel->bReceivesDecals = false;

    bUseControllerRotationPitch = false;
    bUseControllerRotationYaw = true;
    bUseControllerRotationRoll = false;
    UCharacterMovementComponent* Movement = GetCharacterMovement();
    Movement->bOrientRotationToMovement = false;
    Movement->GetNavAgentPropertiesRef().bCanCrouch = true;
    Movement->MaxWalkSpeed = WalkSpeed;
    Movement->MaxWalkSpeedCrouched = CrouchSpeed;
    Movement->JumpZVelocity = 650.0f;
    Movement->GravityScale = 2.04f;
    Movement->MaxAcceleration = 4550.0f;
    Movement->AirControl = 0.05f;
    Movement->GroundFriction = 6.0f;
    Movement->BrakingFrictionFactor = 1.0f;
    Movement->BrakingDecelerationWalking = 5400.0f;
    Movement->MaxStepHeight = 50.0f;
    Movement->SetWalkableFloorAngle(45.0f);
    Movement->bCanWalkOffLedgesWhenCrouching = true;
    Movement->SetCrouchedHalfHeight(72.0f);
}

void AFPSGAMECharacter::BeginPlay()
{
    Super::BeginPlay();
    CameraRestLocation = FirstPersonCamera->GetRelativeLocation();
    FirstPersonCamera->SetFieldOfView(VerticalToHorizontalFOV(BaseVerticalFieldOfView));
    SavedGroundFriction = GetCharacterMovement()->GroundFriction;
    SavedBrakingDeceleration = GetCharacterMovement()->BrakingDecelerationWalking;

    if (USkeletalMesh* ViewmodelMesh = LoadObject<USkeletalMesh>(nullptr, TEXT("/Game/Weapons/AKM/SK_AKM_Viewmodel.SK_AKM_Viewmodel")))
    {
        AKMViewmodel->SetSkeletalMeshAsset(ViewmodelMesh);
    }
    IdleAnimation = LoadAKMAnimation(TEXT("A_AKM_idle"));
    AimAnimation = LoadAKMAnimation(TEXT("A_AKM_aim"));
    FireAnimation = LoadAKMAnimation(TEXT("A_AKM_fire"));
    AimFireAnimation = LoadAKMAnimation(TEXT("A_AKM_aim_fire"));
    ReloadAnimation = LoadAKMAnimation(TEXT("A_AKM_reload"));
    ReloadEmptyAnimation = LoadAKMAnimation(TEXT("A_AKM_reload_empty"));
    InspectAnimation = LoadAKMAnimation(TEXT("A_AKM_inspect"));
    FireSound = LoadAKMSound(TEXT("S_AKM_Fire"));
    EquipSound = LoadAKMSound(TEXT("S_AKM_Equip"));
    MagOutSound = LoadAKMSound(TEXT("S_AKM_MagOut"));
    MagInsertSound = LoadAKMSound(TEXT("S_AKM_MagInsert"));
    MagSeatSound = LoadAKMSound(TEXT("S_AKM_MagSeat"));
    ChargePullSound = LoadAKMSound(TEXT("S_AKM_ChargePull"));
    ChargeReleaseSound = LoadAKMSound(TEXT("S_AKM_ChargeRelease"));
    DryClickSound = LoadAKMSound(TEXT("S_AKM_DryClick"));
    CriticalHitSound = LoadAKMSound(TEXT("S_AKM_CriticalHit"));

    MagazineAmmo = MagazineCapacity;
    ReserveAmmo = 90;
    StartEquipCharge();
    bRunWeaponAudit = FParse::Param(FCommandLine::Get(), TEXT("AKMWeaponAudit"));
    if (APlayerController* PC = Cast<APlayerController>(Controller))
    {
        PC->SetShowMouseCursor(false);
        PC->SetInputMode(FInputModeGameOnly());
    }
}

void AFPSGAMECharacter::SetupPlayerInputComponent(UInputComponent* Input)
{
    Super::SetupPlayerInputComponent(Input);
    Input->BindAxis(TEXT("MoveForward"), this, &AFPSGAMECharacter::MoveForward);
    Input->BindAxis(TEXT("MoveRight"), this, &AFPSGAMECharacter::MoveRight);
    Input->BindAxis(TEXT("Turn"), this, &AFPSGAMECharacter::Turn);
    Input->BindAxis(TEXT("LookUp"), this, &AFPSGAMECharacter::LookUp);
    Input->BindAction(TEXT("Jump"), IE_Pressed, this, &AFPSGAMECharacter::JumpPressed);
    Input->BindAction(TEXT("Jump"), IE_Released, this, &AFPSGAMECharacter::JumpReleased);
    Input->BindAction(TEXT("Sprint"), IE_Pressed, this, &AFPSGAMECharacter::SprintPressed);
    Input->BindAction(TEXT("Sprint"), IE_Released, this, &AFPSGAMECharacter::SprintReleased);
    Input->BindAction(TEXT("Slide"), IE_Pressed, this, &AFPSGAMECharacter::SlidePressed);
    Input->BindAction(TEXT("Fire"), IE_Pressed, this, &AFPSGAMECharacter::FirePressed);
    Input->BindAction(TEXT("Fire"), IE_Released, this, &AFPSGAMECharacter::FireReleased);
    Input->BindAction(TEXT("Aim"), IE_Pressed, this, &AFPSGAMECharacter::AimPressed);
    Input->BindAction(TEXT("Aim"), IE_Released, this, &AFPSGAMECharacter::AimReleased);
    Input->BindAction(TEXT("Reload"), IE_Pressed, this, &AFPSGAMECharacter::ReloadPressed);
    Input->BindAction(TEXT("InspectWeapon"), IE_Pressed, this, &AFPSGAMECharacter::InspectPressed);
}

void AFPSGAMECharacter::Tick(float DeltaSeconds)
{
    Super::Tick(DeltaSeconds);
    SlideBoostCooldownRemaining = FMath::Max(0.0f, SlideBoostCooldownRemaining - DeltaSeconds);
    JumpBufferRemaining = FMath::Max(0.0f, JumpBufferRemaining - DeltaSeconds);
    if (bIsSliding) UpdateSlide(DeltaSeconds);
    TryBufferedJump();
    RefreshMovementState();
    UpdateWeaponState(DeltaSeconds);
    UpdateWeaponFeedback(DeltaSeconds);
    UpdateCamera(DeltaSeconds);
    UpdateViewmodel(DeltaSeconds);
    if (bRunWeaponAudit) RunWeaponAudit(DeltaSeconds);
    LookInput = FVector2D::ZeroVector;
}

void AFPSGAMECharacter::MoveForward(float Value)
{
    MoveInput.Y = Value;
    if (!bIsSliding && !FMath::IsNearlyZero(Value) && Controller)
        AddMovementInput(FRotationMatrix(FRotator(0.0f, Controller->GetControlRotation().Yaw, 0.0f)).GetUnitAxis(EAxis::X), Value);
}

void AFPSGAMECharacter::MoveRight(float Value)
{
    MoveInput.X = Value;
    if (!bIsSliding && !FMath::IsNearlyZero(Value) && Controller)
        AddMovementInput(FRotationMatrix(FRotator(0.0f, Controller->GetControlRotation().Yaw, 0.0f)).GetUnitAxis(EAxis::Y), Value);
}

void AFPSGAMECharacter::Turn(float Value) { LookInput.X += Value; AddControllerYawInput(Value); }
void AFPSGAMECharacter::LookUp(float Value) { LookInput.Y += Value; AddControllerPitchInput(Value); }
void AFPSGAMECharacter::SprintPressed() { bSprintHeld = true; if (bIsSliding && CanStand()) StopSlide(true); }
void AFPSGAMECharacter::SprintReleased() { bSprintHeld = false; }

void AFPSGAMECharacter::SlidePressed()
{
    if (bIsSliding) { StopSlide(false); return; }
    if (bIsCrouched) { if (CanStand()) UnCrouch(); return; }
    if (GetCharacterMovement()->IsMovingOnGround() && HorizontalSpeed() >= SlideMinimumSpeed) StartSlide(); else Crouch();
}

void AFPSGAMECharacter::JumpPressed() { JumpBufferRemaining = JumpInputBufferTime; TryBufferedJump(); }
void AFPSGAMECharacter::JumpReleased() { StopJumping(); }

void AFPSGAMECharacter::FirePressed()
{
    bFireHeld = true;
    FireShot();
    if (bFireHeld && !IsWeaponBusy())
        GetWorldTimerManager().SetTimer(FireTimerHandle, this, &AFPSGAMECharacter::FireShot, FireInterval, true);
}

void AFPSGAMECharacter::FireReleased() { bFireHeld = false; GetWorldTimerManager().ClearTimer(FireTimerHandle); }

void AFPSGAMECharacter::AimPressed()
{
    if (!IsWeaponBusy() && !bIsSliding && !bIsSprinting) { bIsAiming = true; ResumeWeaponPose(); }
}

void AFPSGAMECharacter::AimReleased() { bIsAiming = false; if (!IsWeaponBusy()) ResumeWeaponPose(); }

void AFPSGAMECharacter::ReloadPressed()
{
    if (IsWeaponBusy() || MagazineAmmo >= MagazineCapacity || ReserveAmmo <= 0) return;
    FireReleased();
    bIsAiming = false;
    bPendingEmptyReload = MagazineAmmo == 0;
    WeaponState = bPendingEmptyReload ? EAKMWeaponState::ReloadingEmpty : EAKMWeaponState::Reloading;
    WeaponStateElapsed = 0.0f;
    WeaponStateDuration = bPendingEmptyReload ? EmptyReloadDuration : ReloadDuration;
    UAnimSequence* Animation = bPendingEmptyReload ? ReloadEmptyAnimation : ReloadAnimation;
    const float ClipLength = Animation ? Animation->GetPlayLength() : WeaponStateDuration;
    PlayWeaponAnimation(Animation, false, ClipLength / WeaponStateDuration);

    const float SourceLength = bPendingEmptyReload ? 4.291667f : 3.333333f;
    const float Scale = WeaponStateDuration / SourceLength;
    MechanicalCueTimes = bPendingEmptyReload
        ? TArray<float>{0.416667f * Scale, 1.15f * Scale, 1.466667f * Scale, 2.133333f * Scale, 2.333333f * Scale}
        : TArray<float>{0.433333f * Scale, 1.233333f * Scale, 1.483333f * Scale};
    MechanicalCueSounds.Reset();
    if (bPendingEmptyReload)
    {
        MechanicalCueSounds = {MagOutSound, MagInsertSound, MagSeatSound, ChargePullSound, ChargeReleaseSound};
    }
    else
    {
        MechanicalCueSounds = {MagOutSound, MagInsertSound, MagSeatSound};
    }
    NextMechanicalCue = 0;
}

void AFPSGAMECharacter::InspectPressed()
{
    if (IsWeaponBusy() || !InspectAnimation) return;
    FireReleased();
    bIsAiming = false;
    WeaponState = EAKMWeaponState::Inspecting;
    WeaponStateElapsed = 0.0f;
    WeaponStateDuration = InspectAnimation->GetPlayLength();
    PlayWeaponAnimation(InspectAnimation, false);
}

void AFPSGAMECharacter::RefreshMovementState()
{
    const bool bForwardIntent = MoveInput.Y > 0.5f && MoveInput.Size() > 0.7f;
    bIsSprinting = bSprintHeld && GetCharacterMovement()->IsMovingOnGround() && !bIsSliding && !bIsCrouched && !bIsAiming && !IsReloading() && bForwardIntent;
    GetCharacterMovement()->MaxWalkSpeed = bIsSprinting ? SprintSpeed : WalkSpeed;
}

void AFPSGAMECharacter::StartSlide()
{
    bIsAiming = false;
    bIsSliding = true;
    SlideAge = 0.0f;
    SlideTimeRemaining = SlideMaximumTime;
    Crouch();
    UCharacterMovementComponent* Movement = GetCharacterMovement();
    Movement->GroundFriction = 0.0f;
    Movement->BrakingDecelerationWalking = 0.0f;
    FVector HorizontalVelocity = Movement->Velocity; HorizontalVelocity.Z = 0.0f;
    if (SlideBoostCooldownRemaining <= 0.0f)
    {
        HorizontalVelocity = HorizontalVelocity.GetClampedToMaxSize(SprintSpeed) * SlideSpeedMultiplier;
        HorizontalVelocity = HorizontalVelocity.GetClampedToMaxSize(SprintSpeed * SlideSpeedMultiplier);
        SlideBoostCooldownRemaining = SlideBoostCooldown;
    }
    Movement->Velocity.X = HorizontalVelocity.X; Movement->Velocity.Y = HorizontalVelocity.Y;
}

void AFPSGAMECharacter::StopSlide(bool bTryToStand)
{
    bIsSliding = false;
    GetCharacterMovement()->GroundFriction = SavedGroundFriction;
    GetCharacterMovement()->BrakingDecelerationWalking = SavedBrakingDeceleration;
    if (bTryToStand && CanStand()) UnCrouch();
}

void AFPSGAMECharacter::TryBufferedJump()
{
    if (JumpBufferRemaining <= 0.0f || !GetCharacterMovement()->IsMovingOnGround() || !CanStand()) return;
    if (bIsSliding)
    {
        if (SlideAge < SlideJumpLockTime && HorizontalSpeed() > SprintSpeed * 1.75f) return;
        const FVector HorizontalVelocity(GetVelocity().X, GetVelocity().Y, 0.0f);
        StopSlide(true); JumpBufferRemaining = 0.0f;
        LaunchCharacter(HorizontalVelocity + FVector(0.0f, 0.0f, 650.0f), true, true);
        return;
    }
    if (bIsCrouched) UnCrouch();
    JumpBufferRemaining = 0.0f; Jump();
}

void AFPSGAMECharacter::UpdateSlide(float DeltaSeconds)
{
    UCharacterMovementComponent* Movement = GetCharacterMovement();
    SlideAge += DeltaSeconds; SlideTimeRemaining -= DeltaSeconds;
    FVector HorizontalVelocity = Movement->Velocity; HorizontalVelocity.Z = 0.0f;
    HorizontalVelocity *= FMath::Exp(-SlideFriction * DeltaSeconds);
    if (Movement->CurrentFloor.IsWalkableFloor())
    {
        const FVector DownSlope = FVector::VectorPlaneProject(FVector(0.0f, 0.0f, -2000.0f), Movement->CurrentFloor.HitResult.ImpactNormal);
        HorizontalVelocity += FVector(DownSlope.X, DownSlope.Y, 0.0f) * DeltaSeconds;
    }
    Movement->Velocity.X = HorizontalVelocity.X; Movement->Velocity.Y = HorizontalVelocity.Y;
    if (!Movement->IsMovingOnGround() || SlideTimeRemaining <= 0.0f || HorizontalSpeed() <= CrouchSpeed) StopSlide(false);
}

void AFPSGAMECharacter::UpdateWeaponState(float DeltaSeconds)
{
    if (WeaponState == EAKMWeaponState::Idle) return;
    WeaponStateElapsed += DeltaSeconds;
    while (NextMechanicalCue < MechanicalCueTimes.Num() && WeaponStateElapsed >= MechanicalCueTimes[NextMechanicalCue])
    {
        PlaySound2D(MechanicalCueSounds.IsValidIndex(NextMechanicalCue) ? MechanicalCueSounds[NextMechanicalCue] : nullptr, AKMSource::ActionVolume);
        ++NextMechanicalCue;
    }
    if (WeaponStateElapsed < WeaponStateDuration) return;
    if (WeaponState == EAKMWeaponState::Reloading || WeaponState == EAKMWeaponState::ReloadingEmpty) FinishReload(); else FinishWeaponAction();
}

void AFPSGAMECharacter::UpdateWeaponFeedback(float DeltaSeconds)
{
    FeedbackTime += DeltaSeconds;
    TimeSinceLastShot += DeltaSeconds;
    if (TimeSinceLastShot > AKMSource::RecoveryDelay && RecoilPatternIndex > 0)
    {
        PatternRecoveryAccumulator += DeltaSeconds;
        while (PatternRecoveryAccumulator >= AKMSource::RecoveryInterval && RecoilPatternIndex > 0)
        {
            --RecoilPatternIndex;
            PatternRecoveryAccumulator -= AKMSource::RecoveryInterval;
        }
    }
    AdvanceSpring(GunKickPosition, GunKickPositionVelocity, AKMSource::KickStiffness, AKMSource::KickDamping, DeltaSeconds);
    AdvanceSpring(GunKickRotation, GunKickRotationVelocity, AKMSource::KickStiffness, AKMSource::KickDamping, DeltaSeconds);
    AdvanceSpring(GunJitterPosition, GunJitterPositionVelocity, AKMSource::JitterStiffness, AKMSource::JitterDamping, DeltaSeconds);
    AdvanceSpring(GunJitterRotation, GunJitterRotationVelocity, AKMSource::JitterStiffness, AKMSource::JitterDamping, DeltaSeconds);
    AdvanceSpring(GunFlip, GunFlipVelocity, AKMSource::FlipStiffness, AKMSource::FlipDamping, DeltaSeconds);
    AdvanceSpring(CameraKickPitch, CameraKickPitchVelocity, AKMSource::CameraKickStiffness, AKMSource::CameraKickDamping + AKMSource::CameraADSExtraDamping * CameraADSFactor, DeltaSeconds);
    AdvanceSpring(CameraKickYaw, CameraKickYawVelocity, AKMSource::CameraKickStiffness, AKMSource::CameraKickDamping + AKMSource::CameraADSExtraDamping * CameraADSFactor, DeltaSeconds);
    AdvanceSpring(CameraJitterPosition, CameraJitterPositionVelocity, AKMSource::JitterStiffness, AKMSource::JitterDamping, DeltaSeconds);
    AdvanceSpring(CameraJitterRotation, CameraJitterRotationVelocity, AKMSource::JitterStiffness, AKMSource::JitterDamping, DeltaSeconds);
    FireTrauma *= FMath::Exp(-AKMSource::ShakeDecay * DeltaSeconds);
    FOVPunch *= FMath::Exp(-AKMSource::FOVPunchDecay * DeltaSeconds);
    const float RecoveryDelta = FMath::Max(0.0f, DeltaSeconds - SpreadRecoveryLeft);
    SpreadRecoveryLeft = FMath::Max(0.0f, SpreadRecoveryLeft - DeltaSeconds);
    CurrentSpread = FMath::Max(0.0f, CurrentSpread - RecoveryDelta * 0.03f);
    const float TargetMoveSpread = FMath::Clamp((HorizontalSpeed() / 100.0f) * 0.0018f, 0.0f, 0.012f);
    MoveSpread = FMath::Lerp(MoveSpread, TargetMoveSpread, 1.0f - FMath::Exp(-6.0f * DeltaSeconds));
    const float TargetAirSpread = (!GetCharacterMovement()->IsMovingOnGround() && !bIsAiming) ? 0.015f : 0.0f;
    AirSpread = FMath::Lerp(AirSpread, TargetAirSpread, 1.0f - FMath::Exp(-10.0f * DeltaSeconds));
}

void AFPSGAMECharacter::UpdateCamera(float DeltaSeconds)
{
    CameraADSFactor = FMath::Lerp(CameraADSFactor, bIsAiming ? 1.0f : 0.0f, 1.0f - FMath::Exp(-CameraADSSmooth * DeltaSeconds));
    const float Speed = HorizontalSpeed();
    const bool bGrounded = GetCharacterMovement()->IsMovingOnGround();
    FVector TargetLocation = CameraRestLocation;
    TargetLocation.Z = (bIsSliding || bIsCrouched) ? SlidingCameraHeight : StandingCameraHeight;
    float MovementRoll = 0.0f;
    if (bGrounded && !bIsSliding && Speed > 20.0f)
    {
        CameraBobPhase += DeltaSeconds * (bIsSprinting ? 12.0f : 8.0f);
        const float Weight = 1.0f - CameraADSFactor * 0.85f;
        const float Amplitude = (bIsSprinting ? 3.5f : 1.8f) * FMath::Min(Speed / 450.0f, 1.0f) * Weight;
        TargetLocation.Y += FMath::Sin(CameraBobPhase) * Amplitude;
        TargetLocation.Z += FMath::Cos(CameraBobPhase * 2.0f) * Amplitude;
        MovementRoll = FMath::RadiansToDegrees(FMath::Sin(CameraBobPhase) * (Amplitude / 100.0f) * 0.25f);
    }
    const float TraumaStrength = FMath::Square(FireTrauma) * AKMSource::FeedbackScale;
    const float NoiseRight = FMath::PerlinNoise1D(FeedbackTime * 11.0f) * 4.5f * TraumaStrength;
    const float NoiseUp = FMath::PerlinNoise1D(FeedbackTime * 13.0f + 91.3f) * 4.5f * TraumaStrength;
    TargetLocation += FVector(-CameraJitterPosition.Z * 100.0f, CameraJitterPosition.X * 100.0f + NoiseRight, CameraJitterPosition.Y * 100.0f + NoiseUp);
    FirstPersonCamera->SetRelativeLocation(FMath::VInterpTo(FirstPersonCamera->GetRelativeLocation(), TargetLocation, DeltaSeconds, 18.0f));

    const float NoisePitch = FMath::PerlinNoise1D(FeedbackTime * 9.0f + 17.0f) * 0.03f * TraumaStrength;
    const float NoiseYaw = FMath::PerlinNoise1D(FeedbackTime * 7.0f + 55.0f) * 0.03f * TraumaStrength;
    FirstPersonCamera->SetRelativeRotation(FRotator(
        FMath::RadiansToDegrees(CameraKickPitch + CameraJitterRotation.X + NoisePitch),
        FMath::RadiansToDegrees(CameraKickYaw + CameraJitterRotation.Y + NoiseYaw),
        MovementRoll + FMath::RadiansToDegrees(CameraJitterRotation.Z)));

    float TargetHorizontalFOV = VerticalToHorizontalFOV(FMath::Lerp(BaseVerticalFieldOfView, ADSVerticalFieldOfView, CameraADSFactor) + FOVPunch);
    if (bIsSprinting && CameraADSFactor < 0.01f) TargetHorizontalFOV = SprintFieldOfView;
    FirstPersonCamera->SetFieldOfView(FMath::Lerp(FirstPersonCamera->FieldOfView, TargetHorizontalFOV, 1.0f - FMath::Exp(-AKMSource::FOVSmooth * DeltaSeconds)));
}

void AFPSGAMECharacter::UpdateViewmodel(float DeltaSeconds)
{
    WeaponADSFactor = FMath::Lerp(WeaponADSFactor, bIsAiming ? 1.0f : 0.0f, 1.0f - FMath::Exp(-WeaponADSSmooth * DeltaSeconds));
    const float SpeedM = HorizontalSpeed() / 100.0f;
    WeaponBobTime += DeltaSeconds * (5.0f + SpeedM * 0.85f);
    SprintPoseFactor = FMath::Lerp(SprintPoseFactor, bIsSprinting ? 1.0f : 0.0f, 1.0f - FMath::Exp(-8.0f * DeltaSeconds));
    FVector BobTarget = FVector::ZeroVector;
    FVector BobRotationTarget = FVector::ZeroVector;
    if (SpeedM <= 0.5f || bIsSliding || !GetCharacterMovement()->IsMovingOnGround())
        BobTarget.Y = FMath::Sin(WeaponBobTime * 0.5f) * 0.003f;
    else
    {
        const float Amplitude = SprintPoseFactor > 0.5f ? 1.35f : 0.7f;
        BobTarget = FVector(FMath::Sin(WeaponBobTime) * 0.011f * Amplitude, FMath::Abs(FMath::Cos(WeaponBobTime)) * 0.016f * Amplitude, 0.0f);
        BobRotationTarget = FVector(FMath::Sin(WeaponBobTime * 0.5f) * 0.010f * Amplitude, 0.0f, FMath::Sin(WeaponBobTime) * 0.008f * Amplitude);
    }
    WeaponBobPosition = FMath::Lerp(WeaponBobPosition, BobTarget, 1.0f - FMath::Exp(-14.0f * DeltaSeconds));
    WeaponBobRotation = FMath::Lerp(WeaponBobRotation, BobRotationTarget, 1.0f - FMath::Exp(-14.0f * DeltaSeconds));
    WeaponSwayPosition = FMath::Lerp(WeaponSwayPosition, FVector(LookInput.X * 0.0006f, LookInput.Y * 0.0006f, 0.0f), 1.0f - FMath::Exp(-10.0f * DeltaSeconds));
    WeaponSwayRotation = FMath::Lerp(WeaponSwayRotation, FVector(LookInput.Y * 0.002f, LookInput.X * 0.003f, 0.0f), 1.0f - FMath::Exp(-10.0f * DeltaSeconds));

    FVector HipOffset(GunKickPosition.X, GunKickPosition.Y * 0.4f, GunKickPosition.Z * AKMSource::HipAxialScale);
    HipOffset += GunJitterPosition * 0.35f;
    HipOffset.X = 0.018f * FMath::Tanh(HipOffset.X / 0.018f);
    HipOffset.Y = 0.008f * FMath::Tanh(HipOffset.Y / 0.008f);
    HipOffset.Z = 0.065f * FMath::Tanh(HipOffset.Z / 0.065f);
    FVector HipAngles(GunKickRotation.X * 0.45f + GunFlip * 0.18f, GunKickRotation.Y, GunKickRotation.Z * 0.6f);
    HipAngles += GunJitterRotation * 0.35f;
    HipAngles.X = 0.045f * FMath::Tanh(HipAngles.X / 0.045f);
    HipAngles.Y = 0.030f * FMath::Tanh(HipAngles.Y / 0.030f);
    HipAngles.Z = 0.025f * FMath::Tanh(HipAngles.Z / 0.025f);

    const float Suppress = 1.0f - WeaponADSFactor;
    const FVector GodotPose = HipOffset + (WeaponBobPosition + WeaponSwayPosition + FVector(0.0f, -0.10f * SprintPoseFactor, 0.0f)) * Suppress;
    const FVector UEHipPose(-GodotPose.Z * 100.0f, GodotPose.X * 100.0f, GodotPose.Y * 100.0f);
    const float RecoilDistance = FMath::Clamp(GunKickPosition.Z * AKMSource::ADSAxialScale, -0.01f, 0.055f);
    FVector2D Lateral(GunKickPosition.X * AKMSource::ADSHorizontalScale + GunJitterPosition.X, GunKickPosition.Y + GunJitterPosition.Y);
    Lateral = Lateral.GetClampedToMaxSize(0.012f);
    const FVector UEADSRecoil(-RecoilDistance * 100.0f, Lateral.X * 100.0f, Lateral.Y * 100.0f);
    const FVector TargetLocation = FMath::Lerp(HipViewmodelLocation + UEHipPose, ADSViewmodelLocation + UEADSRecoil, WeaponADSFactor);

    FVector ADSKickAngles = GunKickRotation + GunJitterRotation + FVector(GunFlip, 0.0f, 0.0f);
    ADSKickAngles.Y = GunKickRotation.Y * AKMSource::ADSHorizontalScale + GunJitterRotation.Y;
    ADSKickAngles = ADSKickAngles.GetClampedToMaxSize(0.10f);
    const FVector GodotAngles = HipAngles + (WeaponBobRotation + WeaponSwayRotation + FVector(0.39f * SprintPoseFactor, 0.0f, 0.0f)) * Suppress;
    const FRotator HipRotation(ViewmodelRotation.Pitch + FMath::RadiansToDegrees(GodotAngles.X), ViewmodelRotation.Yaw - FMath::RadiansToDegrees(GodotAngles.Y), ViewmodelRotation.Roll - FMath::RadiansToDegrees(GodotAngles.Z));
    const FRotator ADSRotation(ADSViewmodelRotation.Pitch + FMath::RadiansToDegrees(ADSKickAngles.X), ADSViewmodelRotation.Yaw - FMath::RadiansToDegrees(ADSKickAngles.Y), ADSViewmodelRotation.Roll - FMath::RadiansToDegrees(ADSKickAngles.Z));
    AKMViewmodel->SetRelativeLocation(TargetLocation);
    AKMViewmodel->SetRelativeRotation(FMath::Lerp(HipRotation.Quaternion(), ADSRotation.Quaternion(), WeaponADSFactor));
}

void AFPSGAMECharacter::FireShot()
{
    if (IsWeaponBusy() || bIsSliding) return;
    if (MagazineAmmo <= 0)
    {
        FireReleased();
        if (ReserveAmmo > 0) ReloadPressed(); else PlaySound2D(DryClickSound, 0.501187f);
        return;
    }
    --MagazineAmmo;
    UAnimSequence* Animation = bIsAiming ? AimFireAnimation : FireAnimation;
    PlayWeaponAnimation(Animation, false);
    GetWorldTimerManager().ClearTimer(WeaponPoseTimerHandle);
    GetWorldTimerManager().SetTimer(WeaponPoseTimerHandle, this, &AFPSGAMECharacter::ResumeWeaponPose, Animation ? Animation->GetPlayLength() : 1.041667f, false);
    PlaySound2D(FireSound, AKMSource::FireVolume);

    const FVector TraceStart = FirstPersonCamera->GetComponentLocation();
    const FVector TraceDirection = ComputeShotDirection();
    FHitResult Hit;
    FCollisionQueryParams Params(SCENE_QUERY_STAT(AKMFire), true, this);
    if (GetWorld()->LineTraceSingleByChannel(Hit, TraceStart, TraceStart + TraceDirection * TraceDistance, ECC_Visibility, Params) && Hit.GetActor())
    {
        UGameplayStatics::ApplyPointDamage(Hit.GetActor(), DamagePerShot, TraceDirection, Hit, Controller, this, nullptr);
        if (Hit.BoneName.ToString().Contains(TEXT("head"), ESearchCase::IgnoreCase))
            PlaySound2D(CriticalHitSound, AKMSource::ActionVolume);
    }
    ApplyShotFeedback();
    SpreadRecoveryLeft = 0.20f;
    CurrentSpread = FMath::Min(0.024f, CurrentSpread + 0.002f);
}

void AFPSGAMECharacter::ApplyShotFeedback()
{
    const int32 PatternCount = UE_ARRAY_COUNT(AKMSource::Pattern);
    const FVector2D Pattern = AKMSource::Pattern[FMath::Clamp(RecoilPatternIndex, 0, PatternCount - 1)];
    RecoilPatternIndex = FMath::Min(RecoilPatternIndex + 1, PatternCount - 1);
    TimeSinceLastShot = 0.0f;
    PatternRecoveryAccumulator = 0.0f;
    const float Horizontal = FMath::Clamp(Pattern.Y / 0.003f + FMath::FRandRange(-0.35f, 0.35f), -1.0f, 1.0f);
    const float RecoilLoad = 1.0f + FMath::Clamp((CurrentSpread + MoveSpread + AirSpread) / 0.024f, 0.0f, 2.0f) * 0.7f;
    GunKickPositionVelocity += FVector(-Horizontal * 0.24f, FMath::FRandRange(0.04f, 0.10f), FMath::FRandRange(0.55f, 0.85f)) * AKMSource::ViewmodelGain * RecoilLoad;
    GunKickRotationVelocity += FVector(FMath::FRandRange(0.55f, 1.0f), Horizontal * 0.50f, FMath::FRandRange(-0.7f, 0.7f)) * AKMSource::ViewmodelGain * RecoilLoad;
    const FVector PositionImpulse = FVector(FMath::FRandRange(-0.7f, 0.7f), FMath::FRandRange(-0.7f, 0.7f), FMath::FRandRange(-0.7f, 0.7f)) * RecoilLoad;
    const FVector RotationImpulse = FVector(FMath::FRandRange(-2.2f, 2.2f), FMath::FRandRange(-2.2f, 2.2f), FMath::FRandRange(-2.2f, 2.2f)) * RecoilLoad;
    GunJitterPositionVelocity += PositionImpulse;
    GunJitterRotationVelocity += RotationImpulse;
    GunFlipVelocity += 1.5f;
    CameraJitterPositionVelocity += PositionImpulse * 0.06f * AKMSource::FeedbackScale;
    CameraJitterRotationVelocity += RotationImpulse * 0.18f * AKMSource::FeedbackScale;
    const float ImpulseScale = FMath::Lerp(1.0f, AKMSource::ADSCameraImpulse, WeaponADSFactor);
    CameraKickPitchVelocity += (Pattern.X + FMath::FRandRange(-0.0012f, 0.0012f)) * ImpulseScale * AKMSource::FeedbackScale;
    CameraKickYawVelocity += (Pattern.Y + FMath::FRandRange(-0.0008f, 0.0008f)) * ImpulseScale * AKMSource::FeedbackScale;
    FOVPunch = FMath::Lerp(2.5f, 0.65f, WeaponADSFactor) * AKMSource::FeedbackScale;
    FireTrauma = FMath::Min(1.0f, FireTrauma + 0.06f * RecoilLoad);
}

FVector AFPSGAMECharacter::ComputeShotDirection() const
{
    const FVector Forward = FirstPersonCamera->GetForwardVector();
    if (bIsAiming) return Forward;
    int32 Width = 1920, Height = 1080;
    if (const APlayerController* PC = Cast<APlayerController>(Controller))
        PC->GetViewportSize(Width, Height);
    const float BloomRatio = FMath::Clamp(CurrentSpread / 0.024f, 0.0f, 1.0f);
    const float RadiusPixels = 36.0f * (static_cast<float>(Height) / 1080.0f) * (1.0f + BloomRatio);
    const float Angle = FMath::FRandRange(0.0f, 2.0f * PI);
    const float Radius = FMath::Sqrt(FMath::FRand()) * RadiusPixels;
    const float FocalPixels = (static_cast<float>(Height) * 0.5f) / FMath::Tan(FMath::DegreesToRadians(BaseVerticalFieldOfView) * 0.5f);
    return (Forward
        + FirstPersonCamera->GetRightVector() * (FMath::Cos(Angle) * Radius / FocalPixels)
        - FirstPersonCamera->GetUpVector() * (FMath::Sin(Angle) * Radius / FocalPixels)).GetSafeNormal();
}

void AFPSGAMECharacter::RunWeaponAudit(float DeltaSeconds)
{
    WeaponAuditTime += DeltaSeconds;
    auto Capture = [this](const TCHAR* Name)
    {
        const FString File = FPaths::Combine(FPaths::ProjectSavedDir(), TEXT("Screenshots/Windows"), Name);
        FScreenshotRequest::RequestScreenshot(File, false, false);
        UE_LOG(LogTemp, Display, TEXT("AKM_AUDIT stage=%s state=%d ads=%.4f camera_ads=%.4f fov=%.3f ammo=%d reserve=%d view_loc=%s view_rot=%s"),
            Name, static_cast<int32>(WeaponState), WeaponADSFactor, CameraADSFactor, FirstPersonCamera->FieldOfView,
            MagazineAmmo, ReserveAmmo, *AKMViewmodel->GetRelativeLocation().ToCompactString(), *AKMViewmodel->GetRelativeRotation().ToCompactString());
    };

    if (WeaponAuditStage == 0 && WeaponAuditTime >= 3.10f)
    {
        Capture(TEXT("AKM_00_Hip.png"));
        WeaponAuditStage = 1;
    }
    else if (WeaponAuditStage == 1 && WeaponAuditTime >= 3.35f)
    {
        bIsAiming = true;
        ResumeWeaponPose();
        WeaponAuditStage = 2;
    }
    else if (WeaponAuditStage == 2 && WeaponAuditTime >= 4.05f)
    {
        Capture(TEXT("AKM_01_ADS.png"));
        FireShot();
        WeaponAuditStage = 3;
    }
    else if (WeaponAuditStage == 3 && WeaponAuditTime >= 4.12f)
    {
        Capture(TEXT("AKM_02_ADS_Fire.png"));
        WeaponAuditStage = 4;
    }
    else if (WeaponAuditStage == 4 && WeaponAuditTime >= 4.80f)
    {
        bIsAiming = false;
        MagazineAmmo = 5;
        ReloadPressed();
        WeaponAuditStage = 5;
    }
    else if (WeaponAuditStage == 5 && WeaponAuditTime >= 5.50f)
    {
        Capture(TEXT("AKM_03_Reload.png"));
        WeaponAuditStage = 6;
    }
    else if (WeaponAuditStage == 6 && WeaponAuditTime >= 7.65f)
    {
        MagazineAmmo = 0;
        ReloadPressed();
        WeaponAuditStage = 7;
    }
    else if (WeaponAuditStage == 7 && WeaponAuditTime >= 8.55f)
    {
        Capture(TEXT("AKM_04_EmptyReload.png"));
        WeaponAuditStage = 8;
    }
    else if (WeaponAuditStage == 8 && WeaponAuditTime >= 11.35f)
    {
        Capture(TEXT("AKM_05_Final.png"));
        UE_LOG(LogTemp, Display, TEXT("AKM_AUDIT_COMPLETE"));
        WeaponAuditStage = 9;
        FGenericPlatformMisc::RequestExit(false);
    }
}

void AFPSGAMECharacter::StartEquipCharge()
{
    WeaponState = EAKMWeaponState::Equipping;
    WeaponStateElapsed = 0.0f;
    MechanicalCueTimes.Reset(); MechanicalCueSounds.Reset(); NextMechanicalCue = 0;
    PlaySound2D(EquipSound, AKMSource::ActionVolume);
    if (ReloadEmptyAnimation)
    {
        const float StartAt = 1.57f;
        WeaponStateDuration = FMath::Max(0.1f, ReloadEmptyAnimation->GetPlayLength() - StartAt);
        PlayWeaponAnimation(ReloadEmptyAnimation, false, 1.0f, StartAt);
    }
    else WeaponStateDuration = 0.1f;
}

void AFPSGAMECharacter::FinishWeaponAction()
{
    WeaponState = EAKMWeaponState::Idle;
    WeaponStateElapsed = WeaponStateDuration = 0.0f;
    MechanicalCueTimes.Reset(); MechanicalCueSounds.Reset(); NextMechanicalCue = 0;
    ResumeWeaponPose();
}

void AFPSGAMECharacter::FinishReload()
{
    const int32 Loaded = FMath::Min(MagazineCapacity - MagazineAmmo, ReserveAmmo);
    MagazineAmmo += Loaded; ReserveAmmo -= Loaded;
    RecoilPatternIndex = 0;
    bPendingEmptyReload = false;
    FinishWeaponAction();
}

void AFPSGAMECharacter::PlayWeaponAnimation(UAnimSequence* Animation, bool bLoop, float PlayRate, float StartPosition)
{
    if (!Animation || !AKMViewmodel->GetSkeletalMeshAsset()) return;
    AKMViewmodel->PlayAnimation(Animation, bLoop);
    AKMViewmodel->SetPlayRate(PlayRate);
    if (StartPosition > 0.0f) AKMViewmodel->SetPosition(StartPosition, false);
}

void AFPSGAMECharacter::ResumeWeaponPose()
{
    if (WeaponState == EAKMWeaponState::Idle)
        PlayWeaponAnimation(bIsAiming ? AimAnimation : IdleAnimation, true);
}

void AFPSGAMECharacter::PlaySound2D(USoundBase* Sound, float VolumeMultiplier) const
{
    if (Sound) UGameplayStatics::PlaySound2D(this, Sound, VolumeMultiplier, 1.0f);
}

UAnimSequence* AFPSGAMECharacter::LoadAKMAnimation(const TCHAR* AssetName)
{
    const FString Path = FString::Printf(TEXT("/Game/Weapons/AKM/%s.%s"), AssetName, AssetName);
    return LoadObject<UAnimSequence>(nullptr, *Path);
}

USoundBase* AFPSGAMECharacter::LoadAKMSound(const TCHAR* AssetName)
{
    const FString Path = FString::Printf(TEXT("/Game/Weapons/AKM/Audio/%s.%s"), AssetName, AssetName);
    return LoadObject<USoundBase>(nullptr, *Path);
}

bool AFPSGAMECharacter::CanStand() const
{
    if (!bIsCrouched) return true;
    const UCapsuleComponent* Capsule = GetCapsuleComponent();
    const float Radius = Capsule->GetUnscaledCapsuleRadius();
    const FVector TestLocation = GetActorLocation() + FVector(0.0f, 0.0f, StandingCapsuleHalfHeight - Capsule->GetUnscaledCapsuleHalfHeight());
    FCollisionQueryParams Params(SCENE_QUERY_STAT(FPSCanStand), false, this);
    return !GetWorld()->OverlapBlockingTestByProfile(TestLocation, FQuat::Identity, Capsule->GetCollisionProfileName(), FCollisionShape::MakeCapsule(Radius, StandingCapsuleHalfHeight), Params);
}

bool AFPSGAMECharacter::IsWeaponBusy() const { return WeaponState != EAKMWeaponState::Idle; }
float AFPSGAMECharacter::HorizontalSpeed() const { return FVector(GetVelocity().X, GetVelocity().Y, 0.0f).Size(); }

float AFPSGAMECharacter::VerticalToHorizontalFOV(float VerticalFOV) const
{
    return FMath::RadiansToDegrees(2.0f * FMath::Atan(FMath::Tan(FMath::DegreesToRadians(VerticalFOV) * 0.5f) * (16.0f / 9.0f)));
}

void AFPSGAMECharacter::AdvanceSpring(FVector& Position, FVector& Velocity, float Stiffness, float Damping, float DeltaSeconds)
{
    const float Half = Damping * 0.5f;
    const float Frequency = FMath::Sqrt(FMath::Max(KINDA_SMALL_NUMBER, Stiffness - Half * Half));
    const float Decay = FMath::Exp(-Half * DeltaSeconds);
    const float Sine = FMath::Sin(Frequency * DeltaSeconds) / Frequency;
    const float Cosine = FMath::Cos(Frequency * DeltaSeconds);
    const float C0 = Decay * (Cosine + Half * Sine), C1 = Decay * Sine;
    const float C2 = -Decay * Stiffness * Sine, C3 = Decay * (Cosine - Half * Sine);
    const FVector OldPosition = Position;
    Position = OldPosition * C0 + Velocity * C1;
    Velocity = OldPosition * C2 + Velocity * C3;
}

void AFPSGAMECharacter::AdvanceSpring(float& Position, float& Velocity, float Stiffness, float Damping, float DeltaSeconds)
{
    const float Half = Damping * 0.5f;
    const float Frequency = FMath::Sqrt(FMath::Max(KINDA_SMALL_NUMBER, Stiffness - Half * Half));
    const float Decay = FMath::Exp(-Half * DeltaSeconds);
    const float Sine = FMath::Sin(Frequency * DeltaSeconds) / Frequency;
    const float Cosine = FMath::Cos(Frequency * DeltaSeconds);
    const float C0 = Decay * (Cosine + Half * Sine), C1 = Decay * Sine;
    const float C2 = -Decay * Stiffness * Sine, C3 = Decay * (Cosine - Half * Sine);
    const float OldPosition = Position;
    Position = OldPosition * C0 + Velocity * C1;
    Velocity = OldPosition * C2 + Velocity * C3;
}
