#include "FPSGAMECharacter.h"
#include "Perception/AISense_Hearing.h"
#include "Movement/FPSTraversalComponent.h"
#include "UI/ColdSteelStatusModel.h"
#include "Engine/GameInstance.h"
#include "Monsters/FPSCombatHealthComponent.h"
#include "Weapons/FPSGunplayAnimInstance.h"
#include "Weapons/FPSWeaponFXComponent.h"
#include "Weapons/FPSBallisticsComponent.h"

#include "Animation/AnimSequence.h"
#include "Animation/Skeleton.h"
#include "Camera/CameraComponent.h"
#include "Components/CapsuleComponent.h"
#include "Components/AudioComponent.h"
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
    constexpr float CameraKickStiffness = FWeaponHandling::CameraStiffness;
    constexpr float CameraKickDamping = FWeaponHandling::CameraDamping;
    constexpr float CameraADSExtraDamping = FWeaponHandling::CameraADSDamping;
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
}

AFPSGAMECharacter::AFPSGAMECharacter()
{
    PrimaryActorTick.bCanEverTick = true;
    Traversal = CreateDefaultSubobject<UFPSTraversalComponent>(TEXT("Traversal"));
    CreateDefaultSubobject<UFPSCombatHealthComponent>(TEXT("CombatHealth"));
    GetCapsuleComponent()->InitCapsuleSize(42.0f, 96.0f);
    GetCapsuleComponent()->SetCollisionProfileName(TEXT("Pawn"));

    FirstPersonCamera = CreateDefaultSubobject<UCameraComponent>(TEXT("FirstPersonCamera"));
    FirstPersonCamera->SetupAttachment(GetCapsuleComponent());
    FirstPersonCamera->SetRelativeLocation(FVector(0.0f, 0.0f, StandingCameraHeight));
    // UpdateCamera composes control aim and presentation once. GetCameraView must not overwrite it.
    FirstPersonCamera->bUsePawnControlRotation = false;
    FirstPersonCamera->AspectRatio = 16.0f / 9.0f;
    FirstPersonCamera->bOverrideAspectRatioAxisConstraint = true;
    FirstPersonCamera->AspectRatioAxisConstraint = EAspectRatioAxisConstraint::AspectRatio_MaintainYFOV;
    // Preserve sight and hand readability during quick turns and reload contacts.
    FirstPersonCamera->PostProcessSettings.bOverride_MotionBlurAmount = true;
    FirstPersonCamera->PostProcessSettings.MotionBlurAmount = 0.0f;

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
    AKMViewmodel->VisibilityBasedAnimTickOption = EVisibilityBasedAnimTickOption::AlwaysTickPoseAndRefreshBones;
    AKMViewmodel->PrimaryComponentTick.AddPrerequisite(this, PrimaryActorTick);
    WeaponFX = CreateDefaultSubobject<UFPSWeaponFXComponent>(TEXT("WeaponFX"));
    Ballistics = CreateDefaultSubobject<UFPSBallisticsComponent>(TEXT("Ballistics"));
    M4FireVoice = CreateDefaultSubobject<UAudioComponent>(TEXT("M4FireVoice"));
    M4FireVoice->SetupAttachment(FirstPersonCamera);
    M4FireVoice->bAutoActivate = false;
    M4FireVoice->bAllowSpatialization = false;
    M4FireVoice->bIsUISound = true;
    M4FireVoice->bStopWhenOwnerDestroyed = true;

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
    // Actor spawn inherits the global BeginPlay call depth, even in a separate
    // FPreviewScene. Visual rigs must never attach to the player profile or equip.
    if (GetWorld()->WorldType == EWorldType::GamePreview ||
        GetWorld()->WorldType == EWorldType::EditorPreview || !GetGameInstance())
    {
        SetActorTickEnabled(false);
        UE_LOG(LogTemp, Display, TEXT("WeaponPreview: skipped gameplay BeginPlay world=%s"), *GetWorld()->GetName());
        return;
    }
    CameraRestLocation = FirstPersonCamera->GetRelativeLocation();
    FirstPersonCamera->SetFieldOfView(VerticalToHorizontalFOV(BaseVerticalFieldOfView));
    SavedGroundFriction = GetCharacterMovement()->GroundFriction;
    SavedBrakingDeceleration = GetCharacterMovement()->BrakingDecelerationWalking;

    InitializeWeaponVisuals();
    MagazineAmmo = MagazineCapacity;
    ReserveAmmo = 90;
    if (auto* Profile = GetGameInstance()->GetSubsystem<UColdSteelStatusModel>()) Profile->AttachPawn(this);
    StartEquipCharge();
    bRunWeaponAudit = FParse::Param(FCommandLine::Get(), TEXT("AKMWeaponAudit"));
    bRunGunplayAcceptance = FParse::Param(FCommandLine::Get(), TEXT("GunplayAudit"));
    if (APlayerController* PC = Cast<APlayerController>(Controller))
    {
        PC->SetShowMouseCursor(false);
        PC->SetInputMode(FInputModeGameOnly());
    }
}

void AFPSGAMECharacter::InitializeWeaponVisuals()
{
    if(LPVORing)LPVORing->DestroyComponent();
    if(HolographicOptic)HolographicOptic->DestroyComponent();
    LPVORing=nullptr;HolographicOptic=nullptr;LPVOMagnification=1.f;OpticVariant.Reset();bHolographicOptic=false;
    bSightCalibrated = false;
    bUsingM4Infima = false;
    USkeletalMesh* ViewmodelMesh = LoadObject<USkeletalMesh>(nullptr, TEXT("/Game/Weapons/AKMReplacement/HandsRepair/SK_AKM_HandsRepair.SK_AKM_HandsRepair"), nullptr, LOAD_NoWarn);
    if (!ViewmodelMesh) ViewmodelMesh = LoadObject<USkeletalMesh>(nullptr, TEXT("/Game/Weapons/AKMReplacement/Rendering/SK_AKM_Replacement_Game.SK_AKM_Replacement_Game"), nullptr, LOAD_NoWarn);
    if (!ViewmodelMesh) ViewmodelMesh = LoadObject<USkeletalMesh>(nullptr, TEXT("/Game/Weapons/AKMReplacement/SK_AKM_Replacement.SK_AKM_Replacement"), nullptr, LOAD_NoWarn);
    if (bUseM4Infima)
    {
        if (USkeletalMesh* M4Mesh = LoadObject<USkeletalMesh>(nullptr, TEXT("/Game/Weapons/M4HK416Replica/SK_M4_FoldingSights_HK416.SK_M4_FoldingSights_HK416"), nullptr, LOAD_NoWarn))
        {
            ViewmodelMesh = M4Mesh;
            bUsingM4Infima = true;
            HipViewmodelLocation = M4HipViewmodelLocation;
            ADSRearEyeDistance = 12.0f;
            UE_LOG(LogTemp, Display, TEXT("M4_INFIMA_ACTIVE mesh=%s"), *M4Mesh->GetPathName());
        }
    }
    bUsingReplacement = ViewmodelMesh != nullptr;
    if (!ViewmodelMesh) ViewmodelMesh = LoadObject<USkeletalMesh>(nullptr, TEXT("/Game/Weapons/AKM/SK_AKM_Viewmodel.SK_AKM_Viewmodel"));
    if (ViewmodelMesh)
    {
        AKMViewmodel->SetSkeletalMeshAsset(ViewmodelMesh);
        InitializeFoldingSights();
    }
    IdleAnimation = LoadAKMAnimation(TEXT("A_AKM_idle"));
    AimAnimation = LoadAKMAnimation(TEXT("A_AKM_aim"));
    FireAnimation = LoadAKMAnimation(TEXT("A_AKM_fire"));
    AimFireAnimation = LoadAKMAnimation(TEXT("A_AKM_aim_fire"));
    ReloadAnimation = LoadAKMAnimation(TEXT("A_AKM_reload"));
    ReloadEmptyAnimation = LoadAKMAnimation(TEXT("A_AKM_reload_empty"));
    DrumReloadAnimation=LoadObject<UAnimSequence>(nullptr,TEXT("/Game/Weapons/M4DrumDrop/Throw/A_M4_DrumThrow_reload.A_M4_DrumThrow_reload"));
    DrumReloadEmptyAnimation=LoadObject<UAnimSequence>(nullptr,TEXT("/Game/Weapons/M4DrumDrop/Throw/A_M4_DrumThrow_reload_empty.A_M4_DrumThrow_reload_empty"));
    InspectAnimation = bUsingM4Infima ? nullptr : LoadAKMAnimation(TEXT("A_AKM_inspect"));
    if (bUsingReplacement) EquipAnimation = LoadAKMAnimation(TEXT("A_AKM_equip"));
    DrumSupportAnimations.Reset();
    if (bUsingM4Infima)
        for (UAnimSequence* Base : {IdleAnimation.Get(), AimAnimation.Get(), FireAnimation.Get(), AimFireAnimation.Get(), EquipAnimation.Get()})
            if (Base)
            {
                const FString Path=FString::Printf(TEXT("/Game/Weapons/M4DrumGripRebuilt/Support/%s.%s"),*Base->GetName(),*Base->GetName());
                if (auto* Support=LoadObject<UAnimSequence>(nullptr,*Path))DrumSupportAnimations.Add(Base,Support);
            }
    AKMViewmodel->SetAnimInstanceClass(UFPSGunplayAnimInstance::StaticClass());
    GunplayAnimation = Cast<UFPSGunplayAnimInstance>(AKMViewmodel->GetAnimInstance());
    if (GunplayAnimation)
    {
        GunplayAnimation->IdleClip = IdleAnimation;
        GunplayAnimation->AimClip = AimAnimation;
    }
    WeaponFX->Initialize(AKMViewmodel, FirstPersonCamera);
    FireSound = LoadAKMSound(TEXT("S_AKM_Fire"));
    EquipSound = LoadAKMSound(TEXT("S_AKM_Equip"));
    MagOutSound = LoadAKMSound(TEXT("S_AKM_MagOut"));
    MagInsertSound = LoadAKMSound(TEXT("S_AKM_MagInsert"));
    MagSeatSound = LoadAKMSound(TEXT("S_AKM_MagSeat"));
    ChargePullSound = LoadAKMSound(TEXT("S_AKM_ChargePull"));
    ChargeReleaseSound = LoadAKMSound(TEXT("S_AKM_ChargeRelease"));
    DryClickSound = LoadAKMSound(TEXT("S_AKM_DryClick"));
    CriticalHitSound = LoadAKMSound(TEXT("S_AKM_CriticalHit"));
    BoltReleaseSound = bUsingM4Infima ? LoadObject<USoundBase>(nullptr, TEXT("/Game/Weapons/M4AnimationAuditFinal/S_HK416_BoltRelease.S_HK416_BoltRelease")) : nullptr;

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
    Traversal->Advance(DeltaSeconds);
    if (auto* Profile = GetGameInstance()->GetSubsystem<UColdSteelStatusModel>()) Profile->TickRuntime(DeltaSeconds, this);
    SprintToFireLeft = static_cast<float>(FMath::Max(0.0, SprintFireUnlockTime - GetWorld()->GetTimeSeconds()));
    SlideBoostCooldownRemaining = FMath::Max(0.0f, SlideBoostCooldownRemaining - DeltaSeconds);
    JumpBufferRemaining = FMath::Max(0.0f, JumpBufferRemaining - DeltaSeconds);
    if (bIsSliding) UpdateSlide(DeltaSeconds);
    TryBufferedJump();
    RefreshMovementState();
    UpdateWeaponState(DeltaSeconds);
    // Also recover an empty magazine loaded from a saved profile after equipping.
    if (HasInfiniteReserveAmmo() && bInventoryWeaponReady && MagazineAmmo == 0 && !IsWeaponBusy()) ReloadPressed();
    UpdateWeaponFeedback(DeltaSeconds);
    UpdateCamera(DeltaSeconds);
    UpdateViewmodel(DeltaSeconds);
    UpdateScopePresentation();
    Traversal->UpdatePresentation(DeltaSeconds);
    ServiceHeldFire();
    UpdateActionPose(DeltaSeconds);
    UpdateDrumDropVisual();
    UpdateFoldingSights(DeltaSeconds);
    if (bRunWeaponAudit) RunWeaponAudit(DeltaSeconds);
    if (FParse::Param(FCommandLine::Get(), TEXT("BallisticPresentationAudit"))) RunBallisticPresentationAudit();
    if (FParse::Param(FCommandLine::Get(), TEXT("InfiniteAmmoAudit"))) RunInfiniteAmmoAudit();
    if (FParse::Param(FCommandLine::Get(), TEXT("DrumGripAudit"))) RunDrumGripAudit();
    if (bRunGunplayAcceptance) RunGunplayAcceptance(DeltaSeconds);
    if (FParse::Param(FCommandLine::Get(), TEXT("WeaponHandlingAudit"))) RunWeaponHandlingAudit();
    if (FParse::Param(FCommandLine::Get(), TEXT("MuzzleMigrationAudit"))) RunMuzzleMigrationAudit();
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

void AFPSGAMECharacter::Turn(float Value) { LookInput.X += Value; AddControllerYawInput(Value * LookSensitivityScale()); }
void AFPSGAMECharacter::LookUp(float Value) { LookInput.Y += Value; AddControllerPitchInput(Value * LookSensitivityScale()); }
void AFPSGAMECharacter::SprintPressed()
{
    bSprintHeld = true;
    if (bIsSliding && CanStand()) StopSlide(true);
    else if (bIsCrouched && CanStand()) UnCrouch();
}
void AFPSGAMECharacter::SprintReleased() { bSprintHeld = false; }

void AFPSGAMECharacter::SlidePressed()
{
    if (IsTraversing()) return;
    if (bIsSliding) { StopSlide(false); return; }
    if (bIsCrouched) { if (CanStand()) UnCrouch(); return; }
    if (GetCharacterMovement()->IsMovingOnGround() && HorizontalSpeed() >= SlideMinimumSpeed) StartSlide(); else Crouch();
}

void AFPSGAMECharacter::JumpPressed()
{
    Traversal->SetJumpHeld(true);
    if (IsTraversing()) return;
    if (Traversal->TryStart(!bIsSliding && !IsWeaponBusy())) { JumpBufferRemaining=0.f; StopJumping(); return; }
    JumpBufferRemaining = JumpInputBufferTime;
    TryBufferedJump();
}
void AFPSGAMECharacter::JumpReleased()
{
    Traversal->SetJumpHeld(false);
    StopJumping();
}

void AFPSGAMECharacter::FirePressed()
{
    if (!bFireHeld)
    {
        NextAllowedShotTime = FMath::Max(NextAllowedShotTime, static_cast<double>(GetWorld()->GetTimeSeconds()));
        TriggerFirstShotWorldTime = -1.0;
    }
    bFireHeld = true;
    ExitSprintForWeapon();
    ServiceHeldFire();
}

void AFPSGAMECharacter::FireReleased() { bFireHeld = false; GetWorldTimerManager().ClearTimer(FireTimerHandle); }

void AFPSGAMECharacter::AimPressed()
{
    bAimHeld = true;
    ExitSprintForWeapon();
    if (!IsWeaponBusy() && !bIsSliding) { SetAimingState(true); ResumeWeaponPose(); }
}

void AFPSGAMECharacter::AimReleased() { bAimHeld = false; SetAimingState(false); if (!IsWeaponBusy()) ResumeWeaponPose(); }

void AFPSGAMECharacter::ReloadPressed()
{
    if (!bInventoryWeaponReady || IsWeaponBusy() || MagazineAmmo >= MagazineCapacity || (!HasInfiniteReserveAmmo() && ReserveAmmo <= 0)) return;
    StopMechanicalAudio();
    GetWorldTimerManager().ClearTimer(FireTimerHandle);
    SetAimingState(false);
    bPendingEmptyReload = MagazineAmmo == 0;
    WeaponState = bPendingEmptyReload ? EAKMWeaponState::ReloadingEmpty : EAKMWeaponState::Reloading;
    WeaponActionStartedAt = GetWorld()->GetTimeSeconds();
    WeaponStateElapsed = 0.0f;
    WeaponStateDuration = bPendingEmptyReload ? EmptyReloadDuration : ReloadDuration;
    UAnimSequence* Animation = bPendingEmptyReload ? ReloadEmptyAnimation : ReloadAnimation;
    if(bDrumInstalled)Animation=bPendingEmptyReload?DrumReloadEmptyAnimation:DrumReloadAnimation;
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
    for (float& Cue : MechanicalCueTimes) Cue = ReloadRuntimeTime(Cue / Scale);
    if (bUsingM4Infima)
    {
        // Source animation seconds, evaluated by the very same clock as the pose.
        MechanicalCueTimes = bPendingEmptyReload
            ? TArray<float>{21.0f / 60.0f, 54.0f / 60.0f, 80.0f / 60.0f}
            : TArray<float>{29.0f / 60.0f, 76.0f / 60.0f, 95.0f / 60.0f};
        MechanicalCueSounds = {MagOutSound, MagInsertSound, MagSeatSound};
        if (bPendingEmptyReload)
        {
            MechanicalCueTimes.Add(130.0f / 60.0f);
            MechanicalCueSounds.Add(BoltReleaseSound);
        }
    }
}

void AFPSGAMECharacter::InspectPressed()
{
    if (IsWeaponBusy() || !InspectAnimation) return;
    FireReleased();
    SetAimingState(false);
    WeaponState = EAKMWeaponState::Inspecting;
    WeaponActionStartedAt = GetWorld()->GetTimeSeconds();
    WeaponStateElapsed = 0.0f;
    WeaponStateDuration = InspectAnimation->GetPlayLength();
    PlayWeaponAnimation(InspectAnimation, false);
}

void AFPSGAMECharacter::RefreshMovementState()
{
    const bool bForwardIntent = MoveInput.Y > 0.5f && MoveInput.Size() > 0.7f;
    const bool bPreviouslySprinting = bIsSprinting;
    SetAimingState(bAimHeld && !IsWeaponBusy() && !bIsSliding);
    bIsSprinting = bSprintHeld && GetCharacterMovement()->IsMovingOnGround() && !bIsSliding && !bIsCrouched && !bIsAiming && (!bFireHeld || IsReloading()) && bForwardIntent;
    if (!bPreviouslySprinting && bIsSprinting) SprintStartedAt = GetWorld()->GetTimeSeconds();
    if (bPreviouslySprinting && !bIsSprinting) StartSprintToFireLock(GetWorld()->GetTimeSeconds());
    GetCharacterMovement()->MaxWalkSpeed = bIsSprinting ? SprintSpeed : (bIsAiming ? ADSWalkSpeed : WalkSpeed);
    GetCharacterMovement()->MaxWalkSpeedCrouched = bIsAiming ? 220.0f : CrouchSpeed;
}

void AFPSGAMECharacter::StartSlide()
{
    SetAimingState(false);
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
    // Slide exit is observed now; its blocked interval never becomes fire debt.
    NextAllowedShotTime = FMath::Max(NextAllowedShotTime, static_cast<double>(GetWorld()->GetTimeSeconds()));
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
    // Input can start an action immediately before Tick. Do not charge that new
    // action for the elapsed interval which preceded the input event.
    WeaponStateElapsed = static_cast<float>(FMath::Max(0.0, GetWorld()->GetTimeSeconds() - WeaponActionStartedAt));
    const float CueClock = bUsingM4Infima && IsReloading() ? ReloadSourceTime(WeaponStateElapsed) : WeaponStateElapsed;
    while (NextMechanicalCue < MechanicalCueTimes.Num() && CueClock + 0.000001f >= MechanicalCueTimes[NextMechanicalCue])
    {
        EmitMechanicalCue(NextMechanicalCue);
        ++NextMechanicalCue;
    }
    if (GetWorld()->GetTimeSeconds() < WeaponActionStartedAt + WeaponStateDuration) return;
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
    // Scale spring time, not frame-dependent interpolation or damping alone.
    // Peak impulse response retains its amplitude; higher stability settles sooner.
    const float FeedbackDelta = DeltaSeconds * WeaponHandling.RecoveryRate();
    AdvanceSpring(GunKickPosition, GunKickPositionVelocity, AKMSource::KickStiffness, AKMSource::KickDamping, FeedbackDelta);
    AdvanceSpring(GunKickRotation, GunKickRotationVelocity, AKMSource::KickStiffness, AKMSource::KickDamping, FeedbackDelta);
    AdvanceSpring(GunJitterPosition, GunJitterPositionVelocity, AKMSource::JitterStiffness, AKMSource::JitterDamping, FeedbackDelta);
    AdvanceSpring(GunJitterRotation, GunJitterRotationVelocity, AKMSource::JitterStiffness, AKMSource::JitterDamping, FeedbackDelta);
    AdvanceSpring(GunFlip, GunFlipVelocity, AKMSource::FlipStiffness, AKMSource::FlipDamping, FeedbackDelta);
    AdvanceSpring(CameraKickPitch, CameraKickPitchVelocity, AKMSource::CameraKickStiffness, AKMSource::CameraKickDamping + AKMSource::CameraADSExtraDamping * CameraADSFactor, FeedbackDelta);
    AdvanceSpring(CameraKickYaw, CameraKickYawVelocity, AKMSource::CameraKickStiffness, AKMSource::CameraKickDamping + AKMSource::CameraADSExtraDamping * CameraADSFactor, FeedbackDelta);
    AdvanceSpring(CameraJitterPosition, CameraJitterPositionVelocity, AKMSource::JitterStiffness, AKMSource::JitterDamping, FeedbackDelta);
    AdvanceSpring(CameraJitterRotation, CameraJitterRotationVelocity, AKMSource::JitterStiffness, AKMSource::JitterDamping, FeedbackDelta);
    FireTrauma *= FMath::Exp(-AKMSource::ShakeDecay * FeedbackDelta);
    FOVPunch *= FMath::Exp(-AKMSource::FOVPunchDecay * DeltaSeconds);
    // Hold bloom across automatic shots, then recover continuously after release.
    const float SpreadRecoveryDelta=FMath::Clamp(static_cast<float>(GetWorld()->GetTimeSeconds()-LastShotWorldTime-.18),0.f,DeltaSeconds);
    CurrentSpread = FMath::Max(0.0f, CurrentSpread - SpreadRecoveryDelta * 0.018f);
    const float TargetMoveSpread = FMath::Clamp((HorizontalSpeed() / 100.0f) * 0.004f, 0.0f, 0.020f);
    MoveSpread = FMath::Lerp(MoveSpread, TargetMoveSpread, 1.0f - FMath::Exp(-6.0f * DeltaSeconds));
    const float TargetAirSpread = (!GetCharacterMovement()->IsMovingOnGround() && !bIsAiming) ? 0.025f : 0.0f;
    AirSpread = FMath::Lerp(AirSpread, TargetAirSpread, 1.0f - FMath::Exp(-10.0f * DeltaSeconds));
}

void AFPSGAMECharacter::UpdateADSProgress()
{
    const double Elapsed = FMath::Max(0.0, GetWorld()->GetTimeSeconds() - ADSStartedAt);
    const float Duration = FMath::Max(0.05f, bIsAiming ? ADSInDuration : ADSOutDuration);
    ADSProgress = FMath::Clamp(ADSStartProgress + (bIsAiming ? 1.0f : -1.0f) * static_cast<float>(Elapsed) / Duration, 0.0f, 1.0f);
}

void AFPSGAMECharacter::SetAimingState(bool bNewAiming)
{
    if (bIsAiming == bNewAiming) return;
    // Finish the old direction at the input/state-change time. A new transition
    // cannot consume time from before that event, including on a hitch frame.
    UpdateADSProgress();
    ADSStartProgress = ADSProgress;
    ADSStartedAt = GetWorld()->GetTimeSeconds();
    bIsAiming = bNewAiming;
}

void AFPSGAMECharacter::UpdateCamera(float DeltaSeconds)
{
    UpdateADSProgress();
    CameraADSFactor = FMath::SmoothStep(0.0f, 1.0f, ADSProgress);
    WeaponADSFactor = CameraADSFactor;
    const float Speed = HorizontalSpeed();
    const bool bGrounded = GetCharacterMovement()->IsMovingOnGround();
    if (bGrounded && !bWasGrounded)
        LandingVelocity -= FMath::Clamp(-PreviousVerticalVelocity / 650.0f, 0.0f, 1.8f) * 36.0f;
    bWasGrounded = bGrounded;
    PreviousVerticalVelocity = GetVelocity().Z;
    AdvanceSpring(LandingOffset, LandingVelocity, 150.0f, 20.0f, DeltaSeconds);
    FVector TargetLocation = CameraRestLocation;
    TargetLocation.Z = (bIsSliding || bIsCrouched) ? SlidingCameraHeight : StandingCameraHeight;
    float MovementRoll = 0.0f;
    if (bGrounded && !bIsSliding && Speed > 20.0f)
    {
        CameraBobPhase += DeltaSeconds * (bIsSprinting ? 12.0f : 8.0f);
        const float Weight = 1.0f - CameraADSFactor * 0.85f;
        const float Amplitude = (bIsSprinting ? 2.4f : 1.0f) * FMath::Min(Speed / 450.0f, 1.0f) * Weight * CameraMotionScale;
        TargetLocation.Y += FMath::Sin(CameraBobPhase) * Amplitude;
        TargetLocation.Z += FMath::Cos(CameraBobPhase * 2.0f) * Amplitude;
        MovementRoll = FMath::RadiansToDegrees(FMath::Sin(CameraBobPhase) * (Amplitude / 100.0f) * 0.25f);
    }
    TargetLocation.Z += LandingOffset * (1.0f - CameraADSFactor * 0.8f) * CameraMotionScale;
    const float TraumaStrength = FMath::Square(FireTrauma) * AKMSource::FeedbackScale * CameraMotionScale * (1.0f - 0.8f * CameraADSFactor);
    const float NoiseRight = FMath::PerlinNoise1D(FeedbackTime * 11.0f) * 4.5f * TraumaStrength;
    const float NoiseUp = FMath::PerlinNoise1D(FeedbackTime * 13.0f + 91.3f) * 4.5f * TraumaStrength;
    TargetLocation += FVector(-CameraJitterPosition.Z * 100.0f, CameraJitterPosition.X * 100.0f + NoiseRight, CameraJitterPosition.Y * 100.0f + NoiseUp);
    FirstPersonCamera->SetRelativeLocation(Traversal->IsCameraRecovering()?TargetLocation:
        FMath::Lerp(FirstPersonCamera->GetRelativeLocation(), TargetLocation, 1.0f - FMath::Exp(-18.0f * DeltaSeconds)));

    const float NoisePitch = FMath::PerlinNoise1D(FeedbackTime * 9.0f + 17.0f) * 0.03f * TraumaStrength;
    const float NoiseYaw = FMath::PerlinNoise1D(FeedbackTime * 7.0f + 55.0f) * 0.03f * TraumaStrength;
    const FRotator CameraFeedback(
        FMath::RadiansToDegrees(CameraKickPitch + CameraJitterRotation.X + NoisePitch),
        FMath::RadiansToDegrees(CameraKickYaw + CameraJitterRotation.Y + NoiseYaw),
        MovementRoll + FMath::RadiansToDegrees(CameraJitterRotation.Z));
    const FQuat ControlAim = Controller ? Controller->GetControlRotation().Quaternion() : GetActorQuat();
    FirstPersonCamera->SetWorldRotation(ControlAim * CameraFeedback.Quaternion());

    float TargetHorizontalFOV = VerticalToHorizontalFOV(FMath::Lerp(BaseVerticalFieldOfView, EffectiveADSVerticalFOV(), CameraADSFactor) + FOVPunch);
    SprintCameraFactor = FMath::Lerp(SprintCameraFactor, bIsSprinting ? 1.0f : 0.0f, 1.0f - FMath::Exp(-9.0f * DeltaSeconds));
    TargetHorizontalFOV = FMath::Lerp(TargetHorizontalFOV, SprintFieldOfView, SprintCameraFactor * (1.0f - CameraADSFactor));
    FirstPersonCamera->SetFieldOfView(TargetHorizontalFOV);
}

void AFPSGAMECharacter::UpdateViewmodel(float DeltaSeconds)
{
    UpdateADSPose();
    // Reload/inspection need room for the support hand. Equip is performed at
    // this weapon's hip anchor and must not visit the centered action framing.
    const bool bUseActionFraming = bUsingM4Infima && IsWeaponBusy() && WeaponState != EAKMWeaponState::Equipping;
    float ActionFramingTarget = bUseActionFraming ? 1.0f : 0.0f;
    if (bDrumInstalled && IsReloading())
    {
        // Center only after the support hand leaves the foregrip. Drum framing
        // moves sideways/up, without the previous 14 cm depth excursion.
        const float SourceFrame = ReloadSourceTime(WeaponStateElapsed) * 60.0f;
        ActionFramingTarget = FMath::SmoothStep(bPendingEmptyReload ? 16.0f : 20.0f,
            bPendingEmptyReload ? 43.0f : 50.0f, SourceFrame);
    }
    M4ActionFramingAlpha = FMath::Lerp(M4ActionFramingAlpha, ActionFramingTarget,
        1.0f - FMath::Exp(-16.0f * DeltaSeconds));
    const float SpeedM = HorizontalSpeed() / 100.0f;
    WeaponBobTime += DeltaSeconds * (5.0f + SpeedM * 0.85f);
    const float SprintSpeedAlpha = FMath::Clamp((HorizontalSpeed() - 50.0f) / FMath::Max(SprintSpeed - 50.0f, 1.0f), 0.0f, 1.0f);
    const float SprintTarget = bIsSprinting && !IsWeaponBusy() ? (bUsingM4Infima ? SprintSpeedAlpha : 1.0f) : 0.0f;
    const float SprintBlendRate = bUsingM4Infima && SprintTarget < SprintPoseFactor ? 24.0f : 12.0f;
    SprintPoseFactor = FMath::Lerp(SprintPoseFactor, SprintTarget, 1.0f - FMath::Exp(-SprintBlendRate * DeltaSeconds));
    // Distance-driven stride: 1.65 complete left/right cycles per second at full sprint.
    if (bUsingM4Infima)
        M4SprintPhase = FMath::Fmod(M4SprintPhase + DeltaSeconds * 2.0f * PI * 1.65f * SprintSpeedAlpha, 2.0f * PI);
    FVector BobTarget = FVector::ZeroVector;
    FVector BobRotationTarget = FVector::ZeroVector;
    if (SpeedM <= 0.5f || bIsSliding || !GetCharacterMovement()->IsMovingOnGround())
        BobTarget.Y = FMath::Sin(WeaponBobTime * 0.5f) * 0.003f;
    else
    {
        const float Amplitude = bUsingM4Infima ? 0.7f * (1.0f - SprintPoseFactor) : (SprintPoseFactor > 0.5f ? 1.35f : 0.7f);
        BobTarget = FVector(FMath::Sin(WeaponBobTime) * 0.011f * Amplitude, FMath::Abs(FMath::Cos(WeaponBobTime)) * 0.016f * Amplitude, 0.0f);
        BobRotationTarget = FVector(FMath::Sin(WeaponBobTime * 0.5f) * 0.010f * Amplitude, 0.0f, FMath::Sin(WeaponBobTime) * 0.008f * Amplitude);
    }
    WeaponBobPosition = FMath::Lerp(WeaponBobPosition, BobTarget, 1.0f - FMath::Exp(-14.0f * DeltaSeconds));
    WeaponBobRotation = FMath::Lerp(WeaponBobRotation, BobRotationTarget, 1.0f - FMath::Exp(-14.0f * DeltaSeconds));
    const FVector2D LookRate = (LookInput / FMath::Max(DeltaSeconds, 0.001f) / 60.0f).GetClampedToMaxSize(8.0f);
    WeaponSwayPosition = FMath::Lerp(WeaponSwayPosition, FVector(LookRate.X * 0.0006f, LookRate.Y * 0.0006f, 0.0f), 1.0f - FMath::Exp(-10.0f * DeltaSeconds));
    WeaponSwayRotation = FMath::Lerp(WeaponSwayRotation, FVector(LookRate.Y * 0.002f, LookRate.X * 0.003f, 0.0f), 1.0f - FMath::Exp(-10.0f * DeltaSeconds));

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
    const float LegacySprint = bUsingM4Infima ? 0.0f : SprintPoseFactor;
    const float SprintSide = FMath::Sin(M4SprintPhase);
    const float SprintStep = FMath::Cos(2.0f * M4SprintPhase);
    const FVector SprintOffset = bUsingM4Infima
        ? (M4SprintOffset + FVector(0.25f * SprintStep, M4SprintSwayCM * SprintSide, 0.45f * SprintStep)) * SprintPoseFactor
        : FVector::ZeroVector;
    const FVector GodotPose = HipOffset + (WeaponBobPosition + WeaponSwayPosition + FVector(0.0f, -0.10f * LegacySprint, 0.0f)) * Suppress;
    const FVector UEHipPose(-GodotPose.Z * 100.0f, GodotPose.X * 100.0f, GodotPose.Y * 100.0f);
    const float RecoilDistance = FMath::Clamp(GunKickPosition.Z * AKMSource::ADSAxialScale, -0.01f, 0.055f);
    FVector2D Lateral(GunKickPosition.X * AKMSource::ADSHorizontalScale + GunJitterPosition.X, GunKickPosition.Y + GunJitterPosition.Y);
    Lateral = Lateral.GetClampedToMaxSize(0.012f);
    const FVector UEADSRecoil(-RecoilDistance * 100.0f, Lateral.X * 18.0f, Lateral.Y * 18.0f);
    FHitResult WallHit;
    const FVector Eye = FirstPersonCamera->GetComponentLocation();
    FCollisionQueryParams WallParams(SCENE_QUERY_STAT(GunplayNearWall), false, this);
    const bool bNearWall = GetWorld()->LineTraceSingleByChannel(WallHit, Eye, Eye + FirstPersonCamera->GetForwardVector() * 80.0f, ECC_Visibility, WallParams);
    const float WallTarget = bNearWall ? 1.0f - FMath::Clamp((WallHit.Distance - 25.0f) / 55.0f, 0.0f, 1.0f) : 0.0f;
    NearWallAlpha = FMath::Lerp(NearWallAlpha, WallTarget, 1.0f - FMath::Exp(-12.0f * DeltaSeconds));
    const FVector ADSTarget = bSightCalibrated ? CalibratedADSLocation : ADSViewmodelLocation;
    // The bulky drum uses one fixed clearance in both idle and reload. Changing
    // only the reload depth made the rifle pull back and then extend again.
    const FVector HipLocation = HipViewmodelLocation + (bDrumInstalled ? FVector(6.0f, 0.0f, 0.0f) : FVector::ZeroVector);
    const FVector ActionLocation = bDrumInstalled
        ? FVector(HipLocation.X, 4.0f, 0.0f) : M4ActionViewmodelLocation;
    const FVector HipFraming = bUsingM4Infima
        ? FMath::Lerp(HipLocation, ActionLocation, M4ActionFramingAlpha)
        : HipLocation;
    FVector TargetLocation = FMath::Lerp(HipFraming + UEHipPose + SprintOffset, ADSTarget + UEADSRecoil, WeaponADSFactor);
    TargetLocation += FVector(-NearWallAlpha * 12.0f, 0.0f, LandingOffset * 0.35f * (1.0f - WeaponADSFactor));

    FVector ADSKickAngles = GunKickRotation + GunJitterRotation + FVector(GunFlip, 0.0f, 0.0f);
    ADSKickAngles.Y = GunKickRotation.Y * AKMSource::ADSHorizontalScale + GunJitterRotation.Y;
    ADSKickAngles = ADSKickAngles.GetClampedToMaxSize(0.025f) * VisualRecoilScale;
    const FVector GodotAngles = HipAngles + (WeaponBobRotation + WeaponSwayRotation + FVector(0.39f * LegacySprint, 0.0f, 0.0f)) * Suppress;
    const FRotator HipRotation(ViewmodelRotation.Pitch + FMath::RadiansToDegrees(GodotAngles.X), ViewmodelRotation.Yaw - FMath::RadiansToDegrees(GodotAngles.Y), ViewmodelRotation.Roll - FMath::RadiansToDegrees(GodotAngles.Z));
    // Premultiply in camera space: adding pitch to a mesh already yawed 90 degrees
    // rotates about the wrong axis and fails to raise the muzzle.
    const FRotator SprintAngles = M4SprintRotation + FRotator(0.8f * SprintStep, 2.3f * SprintSide, 1.6f * FMath::Cos(M4SprintPhase));
    const FQuat SprintRotation = bUsingM4Infima
        ? FQuat::Slerp(FQuat::Identity, SprintAngles.Quaternion(), SprintPoseFactor)
        : FQuat::Identity;
    const FQuat ADSBase = bSightCalibrated ? CalibratedADSRotation : ADSViewmodelRotation.Quaternion();
    const FQuat ADSRotation = FRotator(FMath::RadiansToDegrees(ADSKickAngles.X), -FMath::RadiansToDegrees(ADSKickAngles.Y), -FMath::RadiansToDegrees(ADSKickAngles.Z)).Quaternion() * ADSBase;
    AKMViewmodel->SetRelativeLocation(TargetLocation);
    AKMViewmodel->SetRelativeRotation(FQuat::Slerp(SprintRotation * HipRotation.Quaternion(), ADSRotation, WeaponADSFactor));
    // The gunsmith side view uses the actual equipped assembly and its attachments.
    if(bGunsmithInspection)
    {
        AKMViewmodel->SetRelativeLocation(FVector(42.f,-2.f,6.f));
        AKMViewmodel->SetRelativeRotation(FRotator(0.f,20.f,0.f));
    }
}

void AFPSGAMECharacter::ServiceHeldFire()
{
    if (!bFireHeld) return;
    const double Now = GetWorld()->GetTimeSeconds();
    if (IsWeaponBusy() || bIsSliding || bIsSprinting)
    {
        NextAllowedShotTime = FMath::Max(NextAllowedShotTime, Now);
        return;
    }
    NextAllowedShotTime = FMath::Max(NextAllowedShotTime, SprintFireUnlockTime);
    if (Now < SprintFireUnlockTime) return;

    // At 500 RPM, the world's default 0.4 s maximum delta has at most four due
    // shots. Process every eligible event, keeping the fractional cadence phase.
    for (int32 I = 0; I < MaxFireCatchUpShots && bFireHeld && Now + 1.e-6 >= NextAllowedShotTime; ++I)
    {
        const double PreviousDeadline = NextAllowedShotTime;
        FireShot();
        if (IsWeaponBusy() || bIsSliding || bIsSprinting || !bFireHeld
            || NextAllowedShotTime <= PreviousDeadline) break;
    }
    if (bFireHeld && !IsWeaponBusy() && !bIsSliding && !bIsSprinting && Now + 1.e-6 >= NextAllowedShotTime)
    {
        // A custom world limit may allow a much longer hitch. Discard excess
        // beyond the bounded batch, preserving cadence without future debt.
        const double Interval = FMath::Max(0.001, static_cast<double>(FireInterval));
        const double Remainder = FMath::Fmod(FMath::Max(0.0, Now - NextAllowedShotTime), Interval);
        NextAllowedShotTime = Now + Interval - Remainder;
    }
}

void AFPSGAMECharacter::FireShot()
{
    if (!bInventoryWeaponReady) return;
    const double Now = GetWorld()->GetTimeSeconds();
    if (IsWeaponBusy() || bIsSliding || bIsSprinting || Now < SprintFireUnlockTime || Now + 1.e-6 < NextAllowedShotTime) return;
    if (MagazineAmmo <= 0)
    {
        if (HasInfiniteReserveAmmo() || ReserveAmmo > 0) ReloadPressed();
        else { FireReleased(); PlaySound2D(DryClickSound, 0.501187f); }
        return;
    }
    --MagazineAmmo;
    ++ShotsFired;
    UAISense_Hearing::ReportNoiseEvent(this,GetActorLocation(),1.f,this,IsMuzzleSuppressed()?500.f:1800.f,TEXT("Gunshot"));
    LastShotWorldTime = Now; // Actual execution time, not a backdated cadence deadline.
    if (TriggerFirstShotWorldTime < 0.0) TriggerFirstShotWorldTime = Now;
    NextAllowedShotTime += FMath::Max(0.001, static_cast<double>(FireInterval));
    // Snapshot visible aim before restarting the mechanical action or adding recoil.
    const FVector TraceStart = FirstPersonCamera->GetComponentLocation();
    const FVector TraceDirection = ComputeShotDirection();
    const FVector Muzzle = GetEffectiveMuzzleLocation() + GetEffectiveMuzzleForward().GetSafeNormal() * 2.f; // Snapshot before restarting animation.
    UAnimSequence* Animation = bIsAiming ? AimFireAnimation : FireAnimation;
    PlayWeaponAnimation(Animation, false);
    GetWorldTimerManager().ClearTimer(WeaponPoseTimerHandle);
    USoundBase* ShotSound=IsMuzzleSuppressed()&&SuppressedFireSound?SuppressedFireSound.Get():FireSound.Get();
    if (bUsingM4Infima && M4FireVoice && ShotSound)
    {
        // Match Godot's single AudioStreamPlayer: restart each shot at original pitch.
        M4FireVoice->Stop();
        M4FireVoice->SetSound(ShotSound);
        M4FireVoice->SetVolumeMultiplier(AKMSource::FireVolume);
        M4FireVoice->SetPitchMultiplier(1.0f);
        M4FireVoice->Play();
    }
    else PlaySound2D(ShotSound, AKMSource::FireVolume);

    FHitResult Hit;
    FCollisionQueryParams Params(SCENE_QUERY_STAT(AKMFire), true, this);
    Params.bReturnPhysicalMaterial = true;
    FHitResult AimHit;
    const bool bAimHit = GetWorld()->LineTraceSingleByChannel(AimHit, TraceStart, TraceStart + TraceDirection * TraceDistance, ECC_Visibility, Params);
    const FVector AimTarget = bAimHit ? AimHit.ImpactPoint : TraceStart + TraceDirection * TraceDistance;
    // A muzzle beyond a wall must not damage targets through it, even if the camera can see them.
    bool bHit = GetWorld()->LineTraceSingleByChannel(Hit, TraceStart, Muzzle, ECC_Visibility, Params);
    bLastShotMuzzleBlocked = bHit;
    if (!bHit)
    {
        if(ProjectileSpeedCM>0)Ballistics->Launch(Muzzle,(AimTarget-Muzzle).GetSafeNormal(),ProjectileSpeedCM,TraceDistance,DamagePerShot,WeaponFX,CriticalHitSound);
        else {
            bHit=GetWorld()->LineTraceSingleByChannel(Hit,Muzzle,AimTarget+TraceDirection*2.f,ECC_Visibility,Params);
            WeaponFX->OnTracerSegment(Muzzle,bHit?Hit.ImpactPoint:AimTarget);
        }
    }
    if (bHit && Hit.GetActor())
    {
        NotifyConfirmedWeaponHit(Hit.GetActor(), UGameplayStatics::ApplyPointDamage(Hit.GetActor(), DamagePerShot, TraceDirection, Hit, Controller, this, nullptr));
        if (Hit.BoneName.ToString().Contains(TEXT("head"), ESearchCase::IgnoreCase))
            PlaySound2D(CriticalHitSound, AKMSource::ActionVolume);
    }
    WeaponFX->OnShot(bIsAiming);
    if (bHit) WeaponFX->OnImpact(Hit);
    ApplyShotFeedback();
    if(!bIsAiming)CurrentSpread = FMath::Min(0.018f, CurrentSpread + 0.003f);
}

void AFPSGAMECharacter::ApplyShotFeedback()
{
    const int32 PatternCount = FWeaponHandling::PatternCount;
    const FVector2D Pattern = FWeaponHandling::Pattern(RecoilPatternIndex);
    if(RecoilPatternIndex==0)ADSHorizontalRecoilIndex=0;
    const float HorizontalDegrees=bIsAiming?WeaponHandling.ADSHorizontalDegrees(ADSHorizontalRecoilIndex)
        :FMath::RadiansToDegrees(Pattern.Y)*BallisticRecoilScale;
    if (Controller)
    {
        FRotator Aim = Controller->GetControlRotation();
        Aim.Pitch = FMath::Clamp(FRotator::NormalizeAxis(Aim.Pitch) + FMath::RadiansToDegrees(Pattern.X) * BallisticRecoilScale, -85.0f, 85.0f);
        Aim.Yaw += HorizontalDegrees;
        Controller->SetControlRotation(Aim);
    }
    RecoilPatternIndex = FMath::Min(RecoilPatternIndex + 1, PatternCount - 1);
    if(bIsAiming)ADSHorizontalRecoilIndex=(ADSHorizontalRecoilIndex+1)%FWeaponHandling::PatternCount;
    TimeSinceLastShot = 0.0f;
    PatternRecoveryAccumulator = 0.0f;
    const float Horizontal = FMath::Clamp(Pattern.Y / 0.003f + FMath::FRandRange(-0.35f, 0.35f), -1.0f, 1.0f);
    const float RecoilLoad = (1.0f + FMath::Clamp((CurrentSpread + MoveSpread + AirSpread) / 0.024f, 0.0f, 2.0f) * 0.7f);
    GunKickPositionVelocity += FVector(-Horizontal * 0.24f, FMath::FRandRange(0.04f, 0.10f), FMath::FRandRange(0.55f, 0.85f)) * AKMSource::ViewmodelGain * RecoilLoad * WeaponHandling.RecoilScale;
    GunKickRotationVelocity += FVector(FMath::FRandRange(0.55f, 1.0f), Horizontal * 0.50f, FMath::FRandRange(-0.7f, 0.7f)) * AKMSource::ViewmodelGain * RecoilLoad * WeaponHandling.RecoilScale;
    const FVector PositionImpulse = FVector(FMath::FRandRange(-0.7f, 0.7f), FMath::FRandRange(-0.7f, 0.7f), FMath::FRandRange(-0.7f, 0.7f)) * RecoilLoad * WeaponHandling.ShakeScale;
    const FVector RotationImpulse = FVector(FMath::FRandRange(-2.2f, 2.2f), FMath::FRandRange(-2.2f, 2.2f), FMath::FRandRange(-2.2f, 2.2f)) * RecoilLoad * WeaponHandling.ShakeScale;
    GunJitterPositionVelocity += PositionImpulse;
    GunJitterRotationVelocity += RotationImpulse;
    GunFlipVelocity += 1.5f * RecoilLoad * WeaponHandling.RecoilScale;
    CameraJitterPositionVelocity += PositionImpulse * 0.06f * AKMSource::FeedbackScale;
    CameraJitterRotationVelocity += RotationImpulse * 0.18f * AKMSource::FeedbackScale;
    const float ImpulseScale = FMath::Lerp(9.0f, 13.0f, WeaponADSFactor) * VisualRecoilScale * WeaponHandling.ShakeScale;
    CameraKickPitchVelocity += (Pattern.X + FMath::FRandRange(-0.0012f, 0.0012f)) * ImpulseScale * AKMSource::FeedbackScale;
    CameraKickYawVelocity += (Pattern.Y + FMath::FRandRange(-0.0008f, 0.0008f)) * ImpulseScale * AKMSource::FeedbackScale;
    FOVPunch = FMath::Lerp(0.65f, 0.15f, WeaponADSFactor);
    // Trauma is squared when rendered: sqrt keeps a single-shot amplitude linear.
    FireTrauma = FMath::Min(1.0f, FireTrauma + 0.06f * RecoilLoad * FMath::Sqrt(WeaponHandling.ShakeScale));
}

FVector AFPSGAMECharacter::ComputeShotDirection() const
{
    const bool bPreciseAim = bIsAiming || WeaponADSFactor > 0.98f;
    // The optical overlay is camera-centered, including recoil feedback.
    if (bPreciseAim && GetScopePresentationAlpha() > .5f)
        return FirstPersonCamera->GetForwardVector();
    if (bHolographicOptic && bPreciseAim)
        return (HolographicAimPoint() - FirstPersonCamera->GetComponentLocation()).GetSafeNormal();
    const FVector Forward = FirstPersonCamera->GetForwardVector();
    if (bPreciseAim && AKMViewmodel->DoesSocketExist(TEXT("WPN_FrontSight")))
        return (AKMViewmodel->GetSocketLocation(TEXT("WPN_FrontSight")) - FirstPersonCamera->GetComponentLocation()).GetSafeNormal();
    if (bPreciseAim) return Forward;
    // Godot gun.gd: independent uniform offsets in camera right/up, in angular space.
    const float Spread = GetHipSpread();
    return (Forward
        + FirstPersonCamera->GetRightVector() * FMath::FRandRange(-Spread, Spread)
        + FirstPersonCamera->GetUpVector() * FMath::FRandRange(-Spread, Spread)).GetSafeNormal();
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
        AimPressed();
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
        AimReleased();
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
    StopMechanicalAudio();
    // Switching can interrupt ADS, reload or sprint. Their cached presentation
    // offsets belong to the previous weapon, not the new equip animation.
    SetAimingState(false);
    ADSProgress = ADSStartProgress = CameraADSFactor = WeaponADSFactor = 0.0f;
    ADSStartedAt = GetWorld()->GetTimeSeconds();
    M4ActionFramingAlpha = SprintPoseFactor = 0.0f;
    AKMViewmodel->SetRelativeLocation(HipViewmodelLocation);
    AKMViewmodel->SetRelativeRotation(ViewmodelRotation);
    if (GunplayAnimation)
    {
        GunplayAnimation->AimAlpha = 0.0f;
        GunplayAnimation->ActionAlpha = 0.0f;
    }
    WeaponState = EAKMWeaponState::Equipping;
    WeaponActionStartedAt = GetWorld()->GetTimeSeconds();
    WeaponStateElapsed = 0.0f;
    MechanicalCueTimes.Reset(); MechanicalCueSounds.Reset(); NextMechanicalCue = 0;
    PlayMechanicalSound(EquipSound, AKMSource::ActionVolume);
    if (EquipAnimation)
    {
        WeaponStateDuration = bUsingM4Infima ? 0.72f : EquipAnimation->GetPlayLength();
        PlayWeaponAnimation(EquipAnimation, false, EquipAnimation->GetPlayLength() / WeaponStateDuration);
    }
    else if (ReloadEmptyAnimation)
    {
        const float StartAt = 1.75f;
        WeaponStateDuration = 0.18f + FMath::Max(0.1f, ReloadEmptyAnimation->GetPlayLength() - StartAt);
        PlayWeaponAnimation(ReloadEmptyAnimation, false, 1.0f, StartAt);
        ActionBlendIn = 0.18f;
        ActionDuration = WeaponStateDuration;
    }
    else WeaponStateDuration = 0.1f;
}

void AFPSGAMECharacter::FinishWeaponAction()
{
    const double CompletedAt = WeaponActionStartedAt + WeaponStateDuration;
    // Only the eligible tail after completion can catch up. Keep a newer input
    // deadline or another active blocker rather than rewinding it to completion.
    NextAllowedShotTime = FMath::Max(NextAllowedShotTime, CompletedAt);
    WeaponState = EAKMWeaponState::Idle;
    if (bFireHeld) ExitSprintForWeapon(CompletedAt);
    WeaponStateElapsed = WeaponStateDuration = 0.0f;
    MechanicalCueTimes.Reset(); MechanicalCueSounds.Reset(); NextMechanicalCue = 0;
    SetAimingState(bAimHeld && !bIsSliding);
    ResumeWeaponPose();
}

void AFPSGAMECharacter::FinishReload()
{
    if (HasInfiniteReserveAmmo() && bInventoryWeaponReady)
    {
        MagazineAmmo = MagazineCapacity;
        // Publish the filled magazine without creating or consuming inventory stacks.
        if (auto* Profile = GetGameInstance()->GetSubsystem<UColdSteelStatusModel>()) Profile->SaveNow();
    }
    else if (auto* Profile = GetGameInstance()->GetSubsystem<UColdSteelStatusModel>())
        Profile->ConsumeAmmo(MagazineCapacity - MagazineAmmo);
    RecoilPatternIndex = 0;
    bPendingEmptyReload = false;
    FinishWeaponAction();
}

bool AFPSGAMECharacter::HasInfiniteReserveAmmo() const
{
    // GetCurrentLevelName strips the PIE prefix; the rule does not persist in saves.
    return GetWorld() && UGameplayStatics::GetCurrentLevelName(this, true) == TEXT("DayNight_Lighting");
}

void AFPSGAMECharacter::PlayWeaponAnimation(UAnimSequence* Animation, bool bLoop, float PlayRate, float StartPosition)
{
    if (!Animation || !AKMViewmodel->GetSkeletalMeshAsset()) return;
    if (GunplayAnimation)
    {
        if (bLoop) return; // The idle/aim graph remains running underneath every action.
        ActiveActionAnimation = Animation;
        ActionElapsed = 0.0f;
        ActionStartPosition = StartPosition;
        ActionPlayRate = PlayRate;
        ActionDuration = FMath::Max(0.01f, (Animation->GetPlayLength() - StartPosition) / FMath::Max(0.01f, PlayRate));
        ActionBlendIn = (Animation == FireAnimation || Animation == AimFireAnimation) ? 0.008f : 0.035f;
        return;
    }
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

void AFPSGAMECharacter::PlayMechanicalSound(USoundBase* Sound, float Volume)
{
    if (!Sound) return;
    auto& Voice = MechanicalVoices.FindOrAdd(Sound->GetFName());
    if (!Voice)
    {
        Voice = NewObject<UAudioComponent>(this);
        Voice->bAutoActivate = false;
        Voice->bAutoDestroy = false;
        Voice->bAllowSpatialization = false;
        Voice->bIsUISound = true;
        Voice->bStopWhenOwnerDestroyed = true;
        Voice->SetupAttachment(FirstPersonCamera);
        Voice->RegisterComponent();
    }
    Voice->Stop();
    Voice->SetSound(Sound);
    Voice->SetVolumeMultiplier(Volume);
    Voice->SetPitchMultiplier(1.0f);
    Voice->Play();
}

void AFPSGAMECharacter::StopMechanicalAudio()
{
    for (const auto& Pair : MechanicalVoices)
        if (Pair.Value) Pair.Value->Stop();
    MechanicalCueTimes.Reset();
    MechanicalCueSounds.Reset();
    NextMechanicalCue = 0;
}

UAnimSequence* AFPSGAMECharacter::LoadAKMAnimation(const TCHAR* AssetName)
{
    if (bUsingM4Infima)
    {
        const TCHAR* Clip = nullptr;
        if (FCString::Strcmp(AssetName, TEXT("A_AKM_reload")) == 0) Clip = TEXT("reload");
        else if (FCString::Strcmp(AssetName, TEXT("A_AKM_reload_empty")) == 0) Clip = TEXT("reload_empty");
        else if (FCString::Strcmp(AssetName, TEXT("A_AKM_equip")) == 0) Clip = TEXT("equip_charge");
        if (Clip)
        {
            const FString Path = FString::Printf(TEXT("/Game/Weapons/%s/A_M4_HK416_%s.A_M4_HK416_%s"),
                FCString::Strcmp(Clip, TEXT("reload_empty")) == 0 ? TEXT("M4SlapImpactFinal")
                : (FCString::Strcmp(Clip, TEXT("reload")) == 0 ? TEXT("M4TacticalTossFinal") : TEXT("M4WrapGripFinal")), Clip, Clip);
            UAnimSequence* Animation = LoadObject<UAnimSequence>(nullptr, *Path);
            UE_LOG(LogTemp, Display, TEXT("M4_ANIMATION_AUDIT_ACTIVE clip=%s loaded=%d duration=%.4f"),
                *Path, Animation != nullptr, Animation ? Animation->GetPlayLength() : 0.0f);
            return Animation;
        }
    }
    FString Folder = bUsingM4Infima ? TEXT("M4ContactImpactFinal") : (bUsingReplacement ? TEXT("AKMReplacement") : TEXT("AKM"));
    const bool bCurledReload = bUsingM4Infima && (FCString::Strcmp(AssetName, TEXT("A_AKM_reload")) == 0
        || FCString::Strcmp(AssetName, TEXT("A_AKM_reload_empty")) == 0);
    if (bCurledReload) Folder += TEXT("/ReloadFinger");
    const FString Path = FString::Printf(TEXT("/Game/Weapons/%s/%s.%s"), *Folder, AssetName, AssetName);
    UAnimSequence* Animation = LoadObject<UAnimSequence>(nullptr, *Path);
    if (bCurledReload && Animation) UE_LOG(LogTemp, Display, TEXT("M4_RELOAD_FINGER_ACTIVE %s"), *Path);
    return Animation;
}

USoundBase* AFPSGAMECharacter::LoadAKMSound(const TCHAR* AssetName)
{
    if (bUsingM4Infima)
    {
        const TCHAR* HKName = nullptr;
        if (FCString::Strcmp(AssetName, TEXT("S_AKM_Fire")) == 0) HKName = TEXT("S_HK416_Fire");
        else if (FCString::Strcmp(AssetName, TEXT("S_AKM_Equip")) == 0)
            return LoadObject<USoundBase>(nullptr, TEXT("/Game/Weapons/M4AnimationAuditFinal/S_HK416_Equip.S_HK416_Equip"));
        else if (FCString::Strcmp(AssetName, TEXT("S_AKM_MagOut")) == 0) HKName = TEXT("S_HK416_MagOut");
        else if (FCString::Strcmp(AssetName, TEXT("S_AKM_MagInsert")) == 0) HKName = TEXT("S_HK416_MagInsert");
        else if (FCString::Strcmp(AssetName, TEXT("S_AKM_MagSeat")) == 0) HKName = TEXT("S_HK416_MagSeat");
        if (HKName)
            return LoadObject<USoundBase>(nullptr, *FString::Printf(TEXT("/Game/Weapons/M4HK416Audio/%s.%s"), HKName, HKName));
    }
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

bool AFPSGAMECharacter::IsTraversing() const { return Traversal && Traversal->IsTraversing(); }
bool AFPSGAMECharacter::IsWeaponBusy() const { return IsTraversing() || WeaponState != EAKMWeaponState::Idle; }
float AFPSGAMECharacter::HorizontalSpeed() const { return FVector(GetVelocity().X, GetVelocity().Y, 0.0f).Size(); }

float AFPSGAMECharacter::VerticalToHorizontalFOV(float VerticalFOV) const
{
    return FMath::RadiansToDegrees(2.0f * FMath::Atan(FMath::Tan(FMath::DegreesToRadians(VerticalFOV) * 0.5f) * (16.0f / 9.0f)));
}

float AFPSGAMECharacter::LookSensitivityScale() const
{
    // Match screen-space motion across magnification; mouse deltas stay raw (no aim smoothing).
    const float Ratio = FMath::Tan(FMath::DegreesToRadians(FMath::Lerp(BaseVerticalFieldOfView, EffectiveADSVerticalFOV(), CameraADSFactor)) * 0.5f)
        / FMath::Tan(FMath::DegreesToRadians(BaseVerticalFieldOfView) * 0.5f);
    return FMath::Lerp(1.0f, Ratio * ADSMouseSensitivity, CameraADSFactor);
}

void AFPSGAMECharacter::StartSprintToFireLock(double StartTime)
{
    SprintFireUnlockTime = FMath::Max(SprintFireUnlockTime, StartTime + FMath::Max(0.0f, SprintToFireDuration));
    NextAllowedShotTime = FMath::Max(NextAllowedShotTime, SprintFireUnlockTime);
    SprintToFireLeft = static_cast<float>(FMath::Max(0.0, SprintFireUnlockTime - GetWorld()->GetTimeSeconds()));
}

void AFPSGAMECharacter::ExitSprintForWeapon(double ExitTime)
{
    if (bIsSprinting)
    {
        // A sprint entered in this Tick cannot exit retroactively at an older
        // reload completion time; its own start is the earliest valid boundary.
        StartSprintToFireLock(FMath::Max(SprintStartedAt, ExitTime >= 0.0 ? ExitTime : GetWorld()->GetTimeSeconds()));
        bIsSprinting = false;
    }
}

void AFPSGAMECharacter::UpdateADSPose()
{
    if (bSightCalibrated || !AimAnimation || !AimAnimation->GetSkeleton()) return;
    const FReferenceSkeleton& Ref = AimAnimation->GetSkeleton()->GetReferenceSkeleton();
    const int32 RearIndex = Ref.FindBoneIndex(TEXT("WPN_RearSight"));
    const int32 FrontIndex = Ref.FindBoneIndex(TEXT("WPN_FrontSight"));
    if (RearIndex == INDEX_NONE || FrontIndex == INDEX_NONE) return;
    const auto PositionAtRestAim = [&](int32 BoneIndex)
    {
        FTransform Transform = FTransform::Identity;
        for (int32 Index = BoneIndex; Index != INDEX_NONE; Index = Ref.GetParentIndex(Index))
        {
            FTransform Local;
            AimAnimation->GetBoneTransform(Local, FSkeletonPoseBoneIndex(Index), FAnimExtractContext(0.0, false), false);
            Transform = Transform * Local;
        }
        // Accumulating the full hierarchy includes the FBX root's unit conversion.
        // The resulting component-space position is already in centimetres.
        return Transform.GetLocation() * ViewmodelScale;
    };
    FVector Rear = PositionAtRestAim(RearIndex);
    FVector Front = PositionAtRestAim(FrontIndex);
    FVector SightUp = FVector::UpVector;
    if (bHolographicOptic)
    {
        FTransform Root = FTransform::Identity;
        for (int32 Index=Ref.FindBoneIndex(TEXT("WPN_root")); Index!=INDEX_NONE; Index=Ref.GetParentIndex(Index))
        {
            FTransform Local;
            AimAnimation->GetBoneTransform(Local,FSkeletonPoseBoneIndex(Index),FAnimExtractContext(0.0,false),false);
            Root=Root*Local;
        }
        const FTransform Mount=HolographicMount*Root;
        Rear=Mount.TransformPosition(OpticLocalAimPoint())*ViewmodelScale;
        Front=Rear+Mount.GetRotation().RotateVector(FVector::ForwardVector)*10.f;
        SightUp=Mount.GetRotation().RotateVector(FVector::UpVector);
    }
    const FVector Axis = (Front - Rear).GetSafeNormal();
    if (Axis.IsNearlyZero() || Rear.ContainsNaN() || Front.ContainsNaN()) return;
    const FQuat Base = ViewmodelRotation.Quaternion();
    CalibratedADSRotation = FQuat::FindBetweenNormals(Base.RotateVector(Axis), FVector::ForwardVector) * Base;
    // Mapping a single axis leaves roll unconstrained. Align the complete optic
    // frame with camera forward/up so ADS is level without twisting it off the rail.
    if(bHolographicOptic)CalibratedADSRotation=FRotationMatrix::MakeFromXZ(Axis,SightUp).ToQuat().Inverse();
    CalibratedADSLocation = FVector(bHolographicOptic ? (OpticVariant==TEXT("lpvo_1_6x")?28.f:(GetOpticMagnification()>1.f?20.f:26.f)) : ADSRearEyeDistance, 0.0f, 0.0f) - CalibratedADSRotation.RotateVector(Rear);
    bSightCalibrated = true;
    UE_LOG(LogTemp, Display, TEXT("GUNPLAY_ADS_CALIBRATED rear=%s front=%s offset=%s rotation=%s"), *Rear.ToCompactString(), *Front.ToCompactString(), *CalibratedADSLocation.ToCompactString(), *CalibratedADSRotation.Rotator().ToCompactString());
}

float AFPSGAMECharacter::ReloadSourceTime(float RuntimeTime) const
{
    if (bUsingM4Infima)
    {
        const UAnimSequence* Clip = bPendingEmptyReload ? ReloadEmptyAnimation : ReloadAnimation;
        float Phase=FMath::Clamp(RuntimeTime / FMath::Max(WeaponStateDuration, 0.01f), 0.0f, 1.0f);
        if(bDrumInstalled)
        {
            // Godot drum's hand and mechanical tracks share this same time mapping.
            const float Source[]={0,.20f,.38f,.56f,.72f,.88f,1};
            const float Target[]={0,.13f,.36f,.60f,.82f,.93f,1};
            for(int32 I=1;I<7;++I)if(Phase<=Target[I]){Phase=FMath::Lerp(Source[I-1],Source[I],(Phase-Target[I-1])/(Target[I]-Target[I-1]));break;}
        }
        return Phase*(Clip ? Clip->GetPlayLength() : 0.0f);
    }
    const float Length = bPendingEmptyReload ? 4.291667f : 3.333333f;
    // Contact landmarks stay fixed; approach accelerates and the last part seats with a short settle.
    const TArray<float> Source = bPendingEmptyReload
        ? TArray<float>{0.0f, 0.416667f, 1.15f, 1.466667f, 2.133333f, 2.333333f, Length}
        : TArray<float>{0.0f, 0.433333f, 1.233333f, 1.483333f, Length};
    const TArray<float> RuntimeFractions = bPendingEmptyReload
        ? TArray<float>{0.0f, 0.105f, 0.29f, 0.365f, 0.53f, 0.58f, 1.0f}
        : TArray<float>{0.0f, 0.12f, 0.36f, 0.44f, 1.0f};
    const float Fraction = FMath::Clamp(RuntimeTime / FMath::Max(WeaponStateDuration, 0.01f), 0.0f, 1.0f);
    for (int32 Index = 1; Index < Source.Num(); ++Index)
    {
        if (Fraction <= RuntimeFractions[Index])
        {
            float Alpha = (Fraction - RuntimeFractions[Index - 1]) / (RuntimeFractions[Index] - RuntimeFractions[Index - 1]);
            // Blend only 25% easing so the limbs never freeze at every landmark.
            Alpha = FMath::Lerp(Alpha, FMath::SmoothStep(0.0f, 1.0f, Alpha), 0.25f);
            return FMath::Lerp(Source[Index - 1], Source[Index], Alpha);
        }
    }
    return Length;
}

float AFPSGAMECharacter::ReloadRuntimeTime(float SourceTime) const
{
    float Low = 0.0f, High = WeaponStateDuration;
    for (int32 Iteration = 0; Iteration < 20; ++Iteration)
    {
        const float Mid = (Low + High) * 0.5f;
        if (ReloadSourceTime(Mid) < SourceTime) Low = Mid; else High = Mid;
    }
    return (Low + High) * 0.5f;
}

void AFPSGAMECharacter::EmitMechanicalCue(int32 CueIndex)
{
    USoundBase* Sound = MechanicalCueSounds.IsValidIndex(CueIndex) ? MechanicalCueSounds[CueIndex].Get() : nullptr;
    const float ScheduledTime = bUsingM4Infima ? ReloadRuntimeTime(MechanicalCueTimes[CueIndex]) : MechanicalCueTimes[CueIndex];
    const float Lateness = FMath::Max(0.0f, WeaponStateElapsed - ScheduledTime);
    // Do not emit an obsolete burst of old contacts after a long game-thread stall.
    const float ContactVolume = AKMSource::ActionVolume *
        ((bUsingM4Infima && !bDrumInstalled && bPendingEmptyReload && CueIndex == 3) ? 1.25f : 1.0f);
    // A short clip is still relevant until the next contact (or action end).
    // Using clip duration here dropped the seat click on a 170 ms render hitch.
    const float ContactValidUntil = MechanicalCueTimes.IsValidIndex(CueIndex + 1)
        ? (bUsingM4Infima ? ReloadRuntimeTime(MechanicalCueTimes[CueIndex + 1]) : MechanicalCueTimes[CueIndex + 1])
        : WeaponStateDuration;
    const bool bPlayContact = Sound && ((bUsingM4Infima && !bDrumInstalled)
        ? WeaponStateElapsed < ContactValidUntil
        : Lateness < Sound->GetDuration());
    if (bPlayContact) PlayMechanicalSound(Sound, ContactVolume);
    if (bRunGunplayAcceptance && bUsingM4Infima && !FParse::Param(FCommandLine::Get(), TEXT("EquipFramingAudit")))
    {
        if (bPendingEmptyReload) ++AuditEmptyMechanicalCues; else ++AuditNormalMechanicalCues;
        if (bPendingEmptyReload && CueIndex == 3) ++AuditBoltReleaseCues;
        AuditMaxMechanicalLateness = FMath::Max(AuditMaxMechanicalLateness, Lateness);
        UE_LOG(LogTemp, Display, TEXT("M4_AUDIO_CUE empty=%d index=%d source=%.6f target=%.6f runtime=%.6f late=%.6f sound=%s played=%d"),
            bPendingEmptyReload, CueIndex, ReloadSourceTime(WeaponStateElapsed), MechanicalCueTimes[CueIndex], WeaponStateElapsed, Lateness, *GetNameSafe(Sound), bPlayContact);
    }
    if (CueIndex == 2 || (bUsingM4Infima ? CueIndex == 3 : CueIndex == 4))
    {
        // A seated magazine and released bolt push the whole supported weapon; wrists retain their source pose.
        GunKickPositionVelocity.Z += CueIndex == 2 ? 0.10f : 0.16f;
        GunKickRotationVelocity.X += CueIndex == 2 ? -0.08f : 0.14f;
        CameraKickPitchVelocity += 0.018f;
    }
}

void AFPSGAMECharacter::UpdateActionPose(float DeltaSeconds)
{
    if (!GunplayAnimation) return;
    const auto DrumPose=[this](UAnimSequence* Clip)->UAnimSequence*
    {
        if(bDrumInstalled)if(const auto* Support=DrumSupportAnimations.Find(Clip))return Support->Get();
        return Clip;
    };
    GunplayAnimation->IdleClip=DrumPose(IdleAnimation);
    GunplayAnimation->AimClip=DrumPose(AimAnimation);
    GunplayAnimation->BaseTime = FeedbackTime;
    GunplayAnimation->AimAlpha = WeaponADSFactor;
    if (ActiveActionAnimation)
    {
        ActionElapsed += DeltaSeconds;
        const bool bFireAction = ActiveActionAnimation == FireAnimation || ActiveActionAnimation == AimFireAnimation;
        const float BlendOut = bFireAction ? 0.028f : 0.10f;
        const float In = FMath::Clamp(ActionElapsed / ActionBlendIn, 0.0f, 1.0f);
        const float Out = FMath::Clamp((ActionDuration - ActionElapsed) / BlendOut, 0.0f, 1.0f);
        GunplayAnimation->ActionClip = DrumPose(ActiveActionAnimation);
        GunplayAnimation->ActionAlpha = FMath::Min(In, Out);
        float SourceTime = ActionStartPosition + ActionElapsed * ActionPlayRate;
        if (IsReloading()) SourceTime = ReloadSourceTime(WeaponStateElapsed);
        else if (WeaponState == EAKMWeaponState::Equipping && !EquipAnimation)
            SourceTime = ActionStartPosition + FMath::Max(0.0f, ActionElapsed - 0.18f);
        GunplayAnimation->ActionTime = FMath::Min(SourceTime, ActiveActionAnimation->GetPlayLength());
        if (ActionElapsed >= ActionDuration)
        {
            ActiveActionAnimation = nullptr;
            GunplayAnimation->ActionAlpha = 0.0f;
        }
    }
    else GunplayAnimation->ActionAlpha = 0.0f;
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


FVector2D AFPSGAMECharacter::GetCrosshairHalfExtent(FVector2D LocalSize) const
{
    const auto* PC=Cast<APlayerController>(Controller);
    if(!PC)return FVector2D::ZeroVector;
    int32 Width=0,Height=0;PC->GetViewportSize(Width,Height);
    if(Width<=0||Height<=0)return FVector2D::ZeroVector;
    const FVector Center=FirstPersonCamera->GetComponentLocation()+FirstPersonCamera->GetForwardVector()*1000.f;
    const float Spread=GetHipSpread()*1000.f;
    FVector2D ScreenCenter,Right,Up;
    if(!PC->ProjectWorldLocationToScreen(Center,ScreenCenter,true)
        ||!PC->ProjectWorldLocationToScreen(Center+FirstPersonCamera->GetRightVector()*Spread,Right,true)
        ||!PC->ProjectWorldLocationToScreen(Center+FirstPersonCamera->GetUpVector()*Spread,Up,true))return FVector2D::ZeroVector;
    return FVector2D(FMath::Abs(Right.X-ScreenCenter.X)*LocalSize.X/Width,
        FMath::Abs(Up.Y-ScreenCenter.Y)*LocalSize.Y/Height);
}


void AFPSGAMECharacter::NotifyConfirmedWeaponHit(AActor* Target, float AppliedDamage)
{
    if (Target != this && Cast<APawn>(Target) && AppliedDamage > 0.f && GetWorld())
        LastConfirmedWeaponHitTime = GetWorld()->GetTimeSeconds();
}


float AFPSGAMECharacter::GetHitMarkerOpacity() const
{
    if (!GetWorld()) return 0.f;
    const double Age = GetWorld()->GetTimeSeconds() - LastConfirmedWeaponHitTime;
    // Hold for 60 ms, then fade over 180 ms. Repeated hits refresh the same marker.
    return .65f * FMath::Clamp(static_cast<float>((.24 - Age) / .18), 0.f, 1.f);
}
