#include "FPSGAMECharacter.h"
#include "Characters/FPSPlayerBodyComponent.h"
#include "Characters/FPSModularOutfitComponent.h"
#include "Weapons/PistolDualWieldComponent.h"
#include "Development/DevelopmentTuningSubsystem.h"
#include "Production/ProductionToolComponent.h"
#include "Weapons/RuneSwordComponent.h"
#include "Weapons/Bow/BowWeaponComponent.h"
#include "Weapons/RuneOrbBladesComponent.h"
#include "Weapons/FrostRuneVisualDiagnosis.h"
#include "Weapons/RuneSwordGuardTuning.h"
#include "Skills/ColdSteelSkillRules.h"
#include "Skills/FPSFireballComponent.h"
#include "Skills/FPSIceSpikeComponent.h"
#include "Skills/FPSLightningComponent.h"
#include "Skills/FPSHolyLightComponent.h"
#include "Skills/FPSFireMagicComponent.h"
#include "Skills/FPSQuickCombatComponent.h"
#include "Weapons/QuickCombatRecovery.h"
#include "Skills/FPSCastingMeshComponent.h"
#include "Perception/AISense_Hearing.h"
#include "Weapons/AKMSovietCalibration.h"
#include "Weapons/A762WeaponAssets.h"
#include "Weapons/PKMLowpolyWeaponAssets.h"
#include "Weapons/PKMAttachments.h"
#include "Weapons/A762Attachments.h"
#include "Weapons/AKMAttachmentVisual.h"
#include "Movement/FPSTraversalComponent.h"
#include "Movement/FPSFootstepAudioComponent.h"
#include "Movement/FPSCharacterMovementComponent.h"
#include "Movement/FPSStairAudit.h"
#include "UI/ColdSteelStatusModel.h"
#include "UI/TransitLoadingSubsystem.h"
#include "Building/VoxelBuildComponent.h"
#include "Engine/GameInstance.h"
#include "Monsters/FPSCombatHealthComponent.h"
#include "Weapons/FPSGunplayAnimInstance.h"
#include "Weapons/M4DrumReloadTiming.h"
#include "Weapons/M1911WeaponAssets.h"
#include "Weapons/DanWesson715WeaponAssets.h"
#include "Weapons/ASH12WeaponAssets.h"
#include "Weapons/SVDWeaponAssets.h"
#include "Weapons/SVDAttachments.h"
#include "Weapons/M16WeaponAssets.h"
#include "Weapons/M16Attachments.h"
#include "Weapons/GunsmithSystem.h"
#include "Weapons/FPSWeaponFXComponent.h"
#include "Weapons/FPSBallisticsComponent.h"
#include "Weapons/WeaponDamageFalloff.h"
#include "Weapons/ColdSteelEnchantmentCombat.h"

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
#include "Sound/SoundConcurrency.h"
#include "Weapons/FPSVisualRecoil.h"
#include "Weapons/WeaponBipodDeploymentComponent.h"
#include "Weapons/PistolLocomotionAssets.h"
#include "Weapons/M4TacticalSprintComponent.h"
#include "Weapons/WeaponActionCameraComponent.h"
#include "TimerManager.h"
#include "HAL/IConsoleManager.h"

// Voxel build mode snaps to a 20 cm lattice, so full FPS look sensitivity overshoots the wanted
// cell. Tune live with `fps.Building.LookSensitivity` (1 = unchanged).
static TAutoConsoleVariable<float> BuildLookSensitivity(TEXT("fps.Building.LookSensitivity"),0.45f,
    TEXT("Mouse look multiplier while the voxel build mode is active."));

// Single live dial for the strength of the shot camera layer. The authored
// bases inside AKMSource already carry the wanted default punch; this only
// scales presentation (camera offsets and FOV punch), never aim, traces,
// cadence or the viewmodel springs. Reload/equip camera strength is separate
// (fps.Camera.ActionShake in WeaponActionCameraComponent).
static TAutoConsoleVariable<float> CameraShakeScale(TEXT("fps.Camera.Shake"),1.f,
    TEXT("Multiplier on the per-shot camera shake: kick, jitter, trauma and FOV punch. 1 = authored base."));

// The M4 fire clip carries the gun kick inside the animation; the AKM and QBZ
// clips do not (see Docs/Weapons/rifle-fire-clip-recoil-20260917.md). This dial
// scales the compensation layer that fills that gap. 0 disables it.
static TAutoConsoleVariable<float> ClipRecoilScale(TEXT("fps.Weapon.ClipRecoil"),1.f,
    TEXT("Multiplier on the fire clip recoil compensation for weapons whose fire animation carries no gun motion. 0 disables it, a negative value flips its direction."));

namespace AKMSource
{
    constexpr float FireVolume = 0.562341f;
    constexpr float ActionVolume = 0.630957f;
    // Retrigger fades. Long enough to remove the click from cutting a live voice,
    // short enough that fast fire still reads as a fresh transient per shot.
    constexpr float FireVoiceFadeSeconds = 0.015f;
    constexpr float MechanicalVoiceFadeSeconds = 0.012f;
    constexpr float KickStiffness = 210.0f;
    constexpr float KickDamping = 16.0f;
    constexpr float JitterStiffness = 7000.0f;
    constexpr float JitterDamping = 48.0f;
    constexpr float FlipStiffness = 260.0f;
    constexpr float FlipDamping = 16.0f;
    constexpr float CameraKickStiffness = FWeaponHandling::CameraStiffness;
    constexpr float CameraKickDamping = FWeaponHandling::CameraDamping;
    constexpr float CameraADSExtraDamping = FWeaponHandling::CameraADSDamping;
    // Amplitude base of the whole shot camera layer (kick, jitter, trauma). It
    // was 0.5, which left the per-shot camera motion around 0.2 degrees - the
    // viewmodel shook while the view behind the crosshair barely moved.
    constexpr float FeedbackScale = 1.0f;
    constexpr float ViewmodelGain = 0.35f;
    constexpr float ADSCameraImpulse = 34.0f;
    constexpr float ADSAxialScale = 3.2f;
    constexpr float HipAxialScale = 2.2f;
    constexpr float ADSHorizontalScale = 0.30f;
    // Trauma is squared when rendered, so the gain sets how many shots it takes
    // for the sustained burst shake to become visible. 0.11 reaches full trauma
    // inside one magazine; 3.0 keeps it alive across the gaps of a burst.
    constexpr float ShakeDecay = 3.0f;
    constexpr float FOVPunchDecay = 6.5f;
    constexpr float FOVSmooth = 10.0f;
    constexpr float RecoveryDelay = 0.30f;
    constexpr float RecoveryInterval = 0.05f;
}

namespace M1911Source
{
    constexpr const TCHAR* MeshPath = TEXT("/Game/Weapons/M1911/RearFinish20260913/SK_M1911_Manny.SK_M1911_Manny");
    constexpr float MagazineOut = 38.f / 120.f;
    constexpr float MagazineInsert = 126.f / 120.f;
    constexpr float MagazineSeat = 128.f / 120.f;
    constexpr float SlideRelease = 192.f / 120.f;
}

namespace FPSComfortLighting
{
    void Apply(UCameraComponent* Camera)
    {
        // Camera overrides apply consistently in Home and generated worlds.
        // Exposure remains owned by the map/weather, preserving night brightness.
        FPostProcessSettings& Settings = Camera->PostProcessSettings;
        Camera->PostProcessBlendWeight = 1.0f;
        Settings.bOverride_LensFlareIntensity = true;
        Settings.LensFlareIntensity = 0.0f;
        Settings.bOverride_BloomDirtMaskIntensity = true;
        Settings.BloomDirtMaskIntensity = 0.0f;
        Settings.bOverride_BloomMethod = true;
        Settings.BloomMethod = BM_SOG;
        Settings.bOverride_BloomIntensity = true;
        Settings.BloomIntensity = 0.15f;
        Settings.bOverride_BloomGaussianIntensity = true;
        Settings.BloomGaussianIntensity = 1.0f;
        Settings.bOverride_BloomThreshold = true;
        Settings.BloomThreshold = 2.0f;
    }
}

AFPSGAMECharacter::AFPSGAMECharacter(const FObjectInitializer& ObjectInitializer)
    : Super(ObjectInitializer.SetDefaultSubobjectClass<UFPSCharacterMovementComponent>(ACharacter::CharacterMovementComponentName))
{
    PrimaryActorTick.bCanEverTick = true;
    CreateDefaultSubobject<UFPSPlayerBodyComponent>(TEXT("PlayerBody"));
    CreateDefaultSubobject<UFPSModularOutfitComponent>(TEXT("ModularOutfit"));
    Traversal = CreateDefaultSubobject<UFPSTraversalComponent>(TEXT("Traversal"));
    CreateDefaultSubobject<UProductionToolComponent>(TEXT("ProductionTools"));
    CreateDefaultSubobject<UM4TacticalSprintComponent>(TEXT("M4TacticalSprint"));
    CreateDefaultSubobject<UWeaponActionCameraComponent>(TEXT("WeaponActionCamera"));
    BipodDeployment=CreateDefaultSubobject<UWeaponBipodDeploymentComponent>(TEXT("BipodDeployment"));
    RuneSword=CreateDefaultSubobject<URuneSwordComponent>(TEXT("RuneSword"));
    Bow=CreateDefaultSubobject<UBowWeaponComponent>(TEXT("Bow"));
    RuneOrbBlades=CreateDefaultSubobject<URuneOrbBladesComponent>(TEXT("RuneOrbBlades"));
    CreateDefaultSubobject<UFPSCombatHealthComponent>(TEXT("CombatHealth"));
    CreateDefaultSubobject<UFPSFireballComponent>(TEXT("FireballSkill"));
    CreateDefaultSubobject<UFPSIceSpikeComponent>(TEXT("IceSpikeSkill"));
    CreateDefaultSubobject<UFPSLightningComponent>(TEXT("LightningSkill"));
    CreateDefaultSubobject<UFPSHolyLightComponent>(TEXT("HolyLightSkill"));
    CreateDefaultSubobject<UFPSFireMagicComponent>(TEXT("FireMagicSkills"));
    QuickCombatPistol=CreateDefaultSubobject<UFPSQuickCombatComponent>(TEXT("QuickCombatPistol"));
    GetCapsuleComponent()->InitCapsuleSize(42.0f, 96.0f);
    GetCapsuleComponent()->SetCollisionProfileName(TEXT("Pawn"));
    // ACharacter restores the class-default mesh offset after crouching, not the
    // offset assigned later by PlayerBody::BeginPlay. Keep both at the capsule feet.
    GetMesh()->SetRelativeLocation(FVector(0.f, 0.f, -GetCapsuleComponent()->GetUnscaledCapsuleHalfHeight()));
    GetMesh()->SetRelativeRotation(FRotator(0.f, -90.f, 0.f));

    USceneComponent* StairVisualRoot = CreateDefaultSubobject<USceneComponent>(TEXT("StairVisualRoot"));
    StairVisualRoot->SetupAttachment(GetCapsuleComponent());
    CastChecked<UFPSCharacterMovementComponent>(GetCharacterMovement())->SetStairVisualRoot(StairVisualRoot);
    FirstPersonCamera = CreateDefaultSubobject<UCameraComponent>(TEXT("FirstPersonCamera"));
    FirstPersonCamera->SetupAttachment(StairVisualRoot);
    FirstPersonCamera->SetRelativeLocation(FVector(0.0f, 0.0f, StandingCameraHeight));
    // UpdateCamera composes control aim and presentation once. GetCameraView must not overwrite it.
    FirstPersonCamera->bUsePawnControlRotation = false;
    FirstPersonCamera->AspectRatio = 16.0f / 9.0f;
    FirstPersonCamera->bOverrideAspectRatioAxisConstraint = true;
    FirstPersonCamera->AspectRatioAxisConstraint = EAspectRatioAxisConstraint::AspectRatio_MaintainYFOV;
    // Preserve sight and hand readability during quick turns and reload contacts.
    FirstPersonCamera->PostProcessSettings.bOverride_MotionBlurAmount = true;
    FirstPersonCamera->PostProcessSettings.MotionBlurAmount = 0.0f;
    FPSComfortLighting::Apply(FirstPersonCamera);

    AKMViewmodel = CreateDefaultSubobject<UFPSCastingMeshComponent>(TEXT("AKMViewmodel"));
    AKMViewmodel->SetupAttachment(FirstPersonCamera);
    AKMViewmodel->SetRelativeLocation(HipViewmodelLocation);
    AKMViewmodel->SetRelativeRotation(GetViewmodelBaseRotation());
    AKMViewmodel->SetRelativeScale3D(ViewmodelScale);
    AKMViewmodel->SetCollisionEnabled(ECollisionEnabled::NoCollision);
    AKMViewmodel->SetCastShadow(false);
    AKMViewmodel->SetOnlyOwnerSee(false);
    AKMViewmodel->SetOwnerNoSee(false);
    AKMViewmodel->bReceivesDecals = false;
    AKMViewmodel->VisibilityBasedAnimTickOption = EVisibilityBasedAnimTickOption::AlwaysTickPoseAndRefreshBones;
    AKMViewmodel->PrimaryComponentTick.AddPrerequisite(this, PrimaryActorTick);
    WeaponFX = CreateDefaultSubobject<UFPSWeaponFXComponent>(TEXT("WeaponFX"));
    DualPistols = CreateDefaultSubobject<UPistolDualWieldComponent>(TEXT("DualPistols"));
    Ballistics = CreateDefaultSubobject<UFPSBallisticsComponent>(TEXT("Ballistics"));
    CreateDefaultSubobject<UFPSFootstepAudioComponent>(TEXT("FootstepAudio"));
    M4FireVoice = CreateDefaultSubobject<UAudioComponent>(TEXT("M4FireVoice"));
    M4FireVoice->SetupAttachment(FirstPersonCamera);
    M4FireVoice->bAutoActivate = false;
    M4FireVoice->bAllowSpatialization = false;
    M4FireVoice->bIsUISound = true;
    M4FireVoice->bStopWhenOwnerDestroyed = true;
    // Three rotating voices carry every weapon that is not the M4. A shot holds
    // its slot for the sample length (about 0.13 s) and the shortest interval is
    // 0.0923 s, so three slots cover it with room to spare; the M4 keeps slot 0.
    FireVoices.Add(M4FireVoice);
    for (int32 Index = 1; Index < 4; ++Index)
    {
        UAudioComponent* Voice = CreateDefaultSubobject<UAudioComponent>(*FString::Printf(TEXT("FireVoice%d"), Index));
        Voice->SetupAttachment(FirstPersonCamera);
        Voice->bAutoActivate = false;
        Voice->bAllowSpatialization = false;
        Voice->bIsUISound = true;
        Voice->bStopWhenOwnerDestroyed = true;
        FireVoices.Add(Voice);
    }

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
    Movement->MaxStepHeight = 40.0f;
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
    FPSComfortLighting::Apply(FirstPersonCamera);
    ConfirmedMonsterHitSound = LoadObject<USoundBase>(nullptr, TEXT("/Game/Audio/PlayerHitFeedback20260914/S_Player_MonsterHit.S_Player_MonsterHit"));
    if (FParse::Param(FCommandLine::Get(), TEXT("WeaponVolumeAudit")))
    {
        RunWeaponVolumeAudit();
        return;
    }
    if (FParse::Param(FCommandLine::Get(), TEXT("StairMovementAudit")))
    {
        auto* StairAudit = NewObject<UFPSStairAudit>(this);
        AddInstanceComponent(StairAudit); StairAudit->RegisterComponent();
    }
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
    bRunInfiniteAmmoAudit = FParse::Param(FCommandLine::Get(), TEXT("InfiniteAmmoAudit"));
    bRunDrumGripAudit = FParse::Param(FCommandLine::Get(), TEXT("DrumGripAudit"));
    bRunAKMIntegrationAudit = FParse::Param(FCommandLine::Get(), TEXT("AKMIntegrationAudit"));
    bRunWeaponHandlingAudit = FParse::Param(FCommandLine::Get(), TEXT("WeaponHandlingAudit"));
    bRunMuzzleMigrationAudit = FParse::Param(FCommandLine::Get(), TEXT("MuzzleMigrationAudit"));
    bRunSlideCombatAudit = FParse::Param(FCommandLine::Get(), TEXT("SlideCombatAudit"));
    if (APlayerController* PC = Cast<APlayerController>(Controller))
    {
        // 启动方式菜单／加载遮罩是模态的且先于本函数取得光标与输入模式（Pawn 的
        // BeginPlay 晚于 PlayerController 的），此时抢占第一人称默认会让初始界面看不见鼠标。
        // 菜单与遮罩自行拆除时都会还原 GameOnly + 隐藏光标，跳过这里不会留下错误状态。
        auto* Loading = GetGameInstance()->GetSubsystem<UTransitLoadingSubsystem>();
        if (!Loading || !Loading->OwnsPlayerCursor())
        {
            PC->SetShowMouseCursor(false);
            PC->SetInputMode(FInputModeGameOnly());
        }
    }
}

void AFPSGAMECharacter::InitializeWeaponVisuals(bool bPresentationOnly)
{
    bWeaponVisualPartsApplied=false;
    // Reset per-weapon trigger semantics here, not inside a weapon branch: the branches only
    // assign their own weapon, so a flag set by the SVD would otherwise stick to every weapon
    // equipped afterwards and turn the rifles semiautomatic.
    bSingleShotTrigger=false;
    PKMLowpolyWeaponAssets::RemoveBipod(this);PKMAttachments::RemoveRail(this);
    if(RearGripAttachment)RearGripAttachment->DestroyComponent();
    RearGripAttachment=nullptr;
    if(StockAttachment)StockAttachment->DestroyComponent();
    StockAttachment=nullptr;bSkeletonStock=false;
    // Mounts and meshes belong to a weapon definition; rebuild them on a weapon swap.
    for(auto* Part:{LPVORing.Get(),AKMOpticBridge.Get(),HolographicOptic.Get(),LargeDrum.Get(),MuzzleAttachment.Get(),PrismHandstop.Get(),AngledForegrip.Get(),VerticalForegrip.Get(),CantedForegrip.Get()})if(Part)Part->DestroyComponent();
    AKMOpticBridge=nullptr;
    LPVORing=nullptr;LPVOMagnification=1.f;HolographicOptic=nullptr;LargeDrum=nullptr;MuzzleAttachment=nullptr;PrismHandstop=nullptr;AngledForegrip=nullptr;VerticalForegrip=nullptr;CantedForegrip=nullptr;
    bHolographicOptic=false;OpticVariant.Reset();bDrumVisual=false;MuzzleVariant.Reset();
    bSightCalibrated = false;
    bUsingM4Infima = false;
    // Each weapon starts from its own framing, never the previous rifle's ADS.
    HipViewmodelLocation=M4HipViewmodelLocation;
    ADSRearEyeDistance=18.f;
    EquipAnimation=nullptr;
    // Quick-combat clips belong to the weapon that authored them; leaving the
    // previous pistol's clip alive would let a clip-less pistol play it.
    QuickCombatAnimation=nullptr;
    USkeletalMesh* ViewmodelMesh = nullptr;
    if (!bPresentationOnly || ActiveInventoryWeaponDefinition == TEXT("ue_akm"))
    {
    ViewmodelMesh = LoadObject<USkeletalMesh>(nullptr, TEXT("/Game/Weapons/AKMIntegration/SovietFab/RearGrip20260913/SK_AKM_MannyNative.SK_AKM_MannyNative"), nullptr, LOAD_NoWarn);
    if (!ViewmodelMesh) ViewmodelMesh = LoadObject<USkeletalMesh>(nullptr, TEXT("/Game/Weapons/AKMIntegration/SovietFab/StockV2/SK_AKM_MannyNative.SK_AKM_MannyNative"), nullptr, LOAD_NoWarn);
    if (!ViewmodelMesh) ViewmodelMesh = LoadObject<USkeletalMesh>(nullptr, TEXT("/Game/Weapons/AKMIntegration/SovietFab/Attachments/SK_AKM_MannyNative.SK_AKM_MannyNative"), nullptr, LOAD_NoWarn);
    if (!ViewmodelMesh) ViewmodelMesh = LoadObject<USkeletalMesh>(nullptr, TEXT("/Game/Weapons/AKMIntegration/SovietFab/SK_AKM_MannyNative.SK_AKM_MannyNative"), nullptr, LOAD_NoWarn);
    if (!ViewmodelMesh) ViewmodelMesh = LoadObject<USkeletalMesh>(nullptr, TEXT("/Game/Weapons/AKMIntegration/WalnutFab/SK_AKM_MannyNative.SK_AKM_MannyNative"), nullptr, LOAD_NoWarn);
    if (ViewmodelMesh && ViewmodelMesh->GetPathName().Contains(TEXT("/AKMIntegration/SovietFab/")))
        HipViewmodelLocation = M4HipViewmodelLocation + FVector(6.f, 0.f, 0.f);
    if (!ViewmodelMesh) ViewmodelMesh = LoadObject<USkeletalMesh>(nullptr, TEXT("/Game/Weapons/AKMIntegration/SourceMatched/SK_AKM_MannyNative.SK_AKM_MannyNative"), nullptr, LOAD_NoWarn);
    if (!ViewmodelMesh) ViewmodelMesh = LoadObject<USkeletalMesh>(nullptr, TEXT("/Game/Weapons/AKMIntegration/Materials/SK_AKM_MannyNative.SK_AKM_MannyNative"), nullptr, LOAD_NoWarn);
    if (!ViewmodelMesh) ViewmodelMesh = LoadObject<USkeletalMesh>(nullptr, TEXT("/Game/Weapons/AKMIntegration/Native/SK_AKM_MannyNative.SK_AKM_MannyNative"), nullptr, LOAD_NoWarn);
    if (!ViewmodelMesh) ViewmodelMesh = LoadObject<USkeletalMesh>(nullptr, TEXT("/Game/Weapons/AKMReplacement/Rendering/SK_AKM_Replacement_Game.SK_AKM_Replacement_Game"), nullptr, LOAD_NoWarn);
    if (!ViewmodelMesh) ViewmodelMesh = LoadObject<USkeletalMesh>(nullptr, TEXT("/Game/Weapons/AKMReplacement/SK_AKM_Replacement.SK_AKM_Replacement"), nullptr, LOAD_NoWarn);
    if (!ViewmodelMesh || ViewmodelMesh->GetName()!=TEXT("SK_AKM_MannyNative"))
    {
        HipViewmodelLocation=FVector(10.f,31.f,-3.f);
        ADSRearEyeDistance=42.f;
    }
    }
    if ((bUseM4Infima || bUseQBZ191) && (!bPresentationOnly || !bUseQBZ191))
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
    if (bUseQBZ191)
    {
        ViewmodelMesh = LoadObject<USkeletalMesh>(nullptr, TEXT("/Game/Weapons/QBZ191/RearGrip20260913/SK_QBZ191_Manny.SK_QBZ191_Manny"));
        if (!ViewmodelMesh) ViewmodelMesh = LoadObject<USkeletalMesh>(nullptr, TEXT("/Game/Weapons/QBZ191/Attachments20260913/SK_QBZ191_Manny.SK_QBZ191_Manny"));
        bUsingM4Infima = ViewmodelMesh != nullptr;
        HipViewmodelLocation = M4HipViewmodelLocation;
        ADSRearEyeDistance = 12.f;
        UE_LOG(LogTemp, Display, TEXT("QBZ191_ACTIVE mesh=%s"), *GetPathNameSafe(ViewmodelMesh));
    }
    if (bUseASH12)
    {
        ViewmodelMesh = LoadObject<USkeletalMesh>(nullptr, ASH12WeaponAssets::MeshPath, nullptr, LOAD_NoWarn);
        bUsingM4Infima = ViewmodelMesh != nullptr; // Shared Manny pose/cue clock.
        // Move the complete bullpup rig forward from the M4/QBZ hip anchor.
        // The larger rear receiver needs slightly more room than the AKM's 6 cm.
        HipViewmodelLocation = M4HipViewmodelLocation + FVector(8.f, 0.f, 0.f);
        ADSRearEyeDistance = ASH12WeaponAssets::ADSRearEyeDistance;
        UE_LOG(LogTemp, Display, TEXT("ASH12_ACTIVE mesh=%s eye=%.2f"), *GetPathNameSafe(ViewmodelMesh), ADSRearEyeDistance);
    }
    if (bUseM16)
    {
        ViewmodelMesh = LoadObject<USkeletalMesh>(nullptr, M16WeaponAssets::MeshPath);
        bUsingM4Infima = ViewmodelMesh != nullptr;
        HipViewmodelLocation = M4HipViewmodelLocation + FVector(5.f, 0.f, 0.f);
        ADSRearEyeDistance = 18.f;
        if (!bPresentationOnly) QuickCombatAnimation = LoadObject<UAnimSequence>(nullptr, *M16WeaponAssets::AnimationPath(TEXT("quick_melee")));
    }
    if (bUseM1911)
    {
        ViewmodelMesh = LoadObject<USkeletalMesh>(nullptr, M1911Source::MeshPath);
        bUsingM4Infima = ViewmodelMesh != nullptr; // Common Manny pose/cue clock.
        HipViewmodelLocation = PistolHipViewmodelLocation;
        ADSRearEyeDistance = 38.f;
        bPistolShotPending = false;
        if (!bPresentationOnly) QuickCombatAnimation = LoadObject<UAnimSequence>(nullptr, M1911WeaponAssets::QuickCombatAnimationPath);
    }
    if (bUseDanWesson715)
    {
        ViewmodelMesh = LoadObject<USkeletalMesh>(nullptr, DanWesson715WeaponAssets::MeshPath);
        bUsingM4Infima = ViewmodelMesh != nullptr;
        HipViewmodelLocation = RevolverHipViewmodelLocation;
        ADSRearEyeDistance = 38.f;
        bPistolShotPending = false;
        if (!bPresentationOnly) QuickCombatAnimation = LoadObject<UAnimSequence>(nullptr, DanWesson715WeaponAssets::QuickCombatAnimationPath);
    }
    if (ActiveInventoryWeaponDefinition == A762WeaponAssets::Definition)
    {
        ViewmodelMesh = LoadObject<USkeletalMesh>(nullptr,A762WeaponAssets::MeshPath);
        bUsingM4Infima = false;
        HipViewmodelLocation = M4HipViewmodelLocation + FVector(6.f,0.f,0.f);
        ADSRearEyeDistance = 18.f;
        if (!bPresentationOnly) SuppressedFireSound = LoadObject<USoundBase>(nullptr,TEXT("/Game/Weapons/M4MuzzlesV1/S_M4_Suppressed"));
    }
    if (ActiveInventoryWeaponDefinition == SVDWeaponAssets::Definition)
    {
        ViewmodelMesh=LoadObject<USkeletalMesh>(nullptr,SVDWeaponAssets::MeshPath,nullptr,LOAD_NoWarn);
        // Dedicated SVD clips share the Manny skeleton and source-time cue clock.
        bUsingM4Infima=ViewmodelMesh!=nullptr;
        bSingleShotTrigger=SVDWeaponAssets::bSingleShotTrigger;
        bPistolShotPending=false;
        HipViewmodelLocation=M4HipViewmodelLocation+FVector(6.f,0.f,0.f);
        if (!bPresentationOnly) QuickCombatAnimation=LoadObject<UAnimSequence>(nullptr,*SVDWeaponAssets::AnimationPath(TEXT("quick_melee")));
        // Measured eye relief behind the baked PSO-1 rear sight marker.
        ADSRearEyeDistance=SVDWeaponAssets::ADSRearEyeDistance;
        UE_LOG(LogTemp, Display, TEXT("SVD_ACTIVE mesh=%s eye=%.2f single_shot=%d"),
            *GetPathNameSafe(ViewmodelMesh), ADSRearEyeDistance, bSingleShotTrigger ? 1 : 0);
    }
    if (ActiveInventoryWeaponDefinition == PKMLowpolyWeaponAssets::Definition)
    {
        ViewmodelMesh=LoadObject<USkeletalMesh>(nullptr,PKMLowpolyWeaponAssets::MeshPath);
        bUsingM4Infima=ViewmodelMesh!=nullptr;
        // Clear the central view of the raised carry handle as a complete
        // weapon/arms assembly. Reload framing and calibrated ADS stay separate.
        HipViewmodelLocation=M4HipViewmodelLocation+FVector(9.f,2.f,-4.f);
        ADSRearEyeDistance=20.f;
        if (!bPresentationOnly) QuickCombatAnimation=LoadObject<UAnimSequence>(nullptr,*PKMLowpolyWeaponAssets::AnimationPath(TEXT("quick_melee")));
    }
    bUsingReplacement = ViewmodelMesh != nullptr;
    if (!ViewmodelMesh) ViewmodelMesh = LoadObject<USkeletalMesh>(nullptr, TEXT("/Game/Weapons/AKM/SK_AKM_Viewmodel.SK_AKM_Viewmodel"));
    if (ViewmodelMesh)
    {
        // Restore the family baseline on swaps; a pistol's reference-pose bounds
        // otherwise cull the live receiver while its static attachments survive.
        AKMViewmodel->SetBoundsScale(ActiveInventoryWeaponDefinition==PKMLowpolyWeaponAssets::Definition ? 2.f : bUseDanWesson715 ? DanWesson715WeaponAssets::ViewmodelBoundsScale : bUseM1911 ? M1911WeaponAssets::ViewmodelBoundsScale : 1.f);
        AKMViewmodel->EmptyOverrideMaterials();
        AKMViewmodel->SetSkeletalMeshAsset(ViewmodelMesh);
        AKMViewmodel->SetRelativeLocation(HipViewmodelLocation);
        AKMViewmodel->SetRelativeRotation(GetViewmodelBaseRotation());
        // Component LOD visibility survives a mesh swap when the LOD count is
        // unchanged. M4 suppressor/drum section indices are unrelated to AKM.
        for(int32 L=0;L<ViewmodelMesh->GetLODNum();++L)AKMViewmodel->ShowAllMaterialSections(L);
        InitializeFoldingSights();
        PKMLowpolyWeaponAssets::SetSections(AKMViewmodel,false,false,0.f,100);
    }
    IdleAnimation = LoadAKMAnimation(TEXT("A_AKM_idle"));
    if (bPresentationOnly)
    {
        // Callers pose the preview explicitly. No combat clips, grip families, audio or FX are needed.
        AKMViewmodel->SetAnimationMode(EAnimationMode::AnimationSingleNode);
        return;
    }
    AimAnimation = LoadAKMAnimation(TEXT("A_AKM_aim"));
    FireAnimation = LoadAKMAnimation(TEXT("A_AKM_fire"));
    AimFireAnimation = LoadAKMAnimation(TEXT("A_AKM_aim_fire"));
    ReloadAnimation = LoadAKMAnimation(TEXT("A_AKM_reload"));
    ReloadEmptyAnimation = LoadAKMAnimation(TEXT("A_AKM_reload_empty"));
    DrumReloadAnimation=SVDWeaponAssets::Matches(AKMViewmodel)?nullptr:LoadObject<UAnimSequence>(nullptr,TEXT("/Game/Weapons/M4DrumDrop/Contact/A_M4_DrumContact_reload.A_M4_DrumContact_reload"));
    DrumReloadEmptyAnimation=SVDWeaponAssets::Matches(AKMViewmodel)?nullptr:LoadObject<UAnimSequence>(nullptr,TEXT("/Game/Weapons/M4DrumDrop/Contact/A_M4_DrumContact_reload_empty.A_M4_DrumContact_reload_empty"));
    if(AKMSoviet::Matches(AKMViewmodel)){
        ReloadAnimation=LoadObject<UAnimSequence>(nullptr,TEXT("/Game/Weapons/AKMIntegration/SovietFab/ReloadPolish/base/A_AKM_reload"));
        ReloadEmptyAnimation=LoadObject<UAnimSequence>(nullptr,TEXT("/Game/Weapons/AKMIntegration/SovietFab/ReloadPolish/base/A_AKM_reload_empty"));
        DrumReloadAnimation=LoadObject<UAnimSequence>(nullptr,TEXT("/Game/Weapons/AKMDrumFreeDrop20260920/base/A_AKM_drum_reload"));
        DrumReloadEmptyAnimation=LoadObject<UAnimSequence>(nullptr,TEXT("/Game/Weapons/AKMDrumFreeDrop20260920/base/A_AKM_drum_reload_empty"));
    }
    if (bUseQBZ191) {
        DrumReloadAnimation=LoadAKMAnimation(TEXT("A_AKM_drum_reload"));
        DrumReloadEmptyAnimation=LoadAKMAnimation(TEXT("A_AKM_drum_reload_empty"));
    }
    if (bUseM16)
    {
        DrumReloadAnimation=LoadObject<UAnimSequence>(nullptr,*M16Attachments::AnimationPath(TEXT("base"),TEXT("drum_reload")));
        DrumReloadEmptyAnimation=LoadObject<UAnimSequence>(nullptr,*M16Attachments::AnimationPath(TEXT("base"),TEXT("drum_reload_empty")));
    }
    // The accepted pistol set has no inspection clip; do not resolve a fictional asset.
    InspectAnimation = SVDWeaponAssets::Matches(AKMViewmodel) || bUseDanWesson715 || bUseM16 || PKMLowpolyWeaponAssets::Matches(AKMViewmodel) ? LoadAKMAnimation(TEXT("A_AKM_inspect")) : bUsingM4Infima || bUseM1911 ? nullptr : LoadAKMAnimation(TEXT("A_AKM_inspect"));
    if (bUsingReplacement) EquipAnimation = LoadAKMAnimation(TEXT("A_AKM_equip"));
    DrumSupportAnimations.Reset();
    if (bUsingM4Infima && !bUseQBZ191 && !bUseM16 && !IsPistolWeapon() && !SVDWeaponAssets::Matches(AKMViewmodel) && !PKMLowpolyWeaponAssets::Matches(AKMViewmodel))
        for (UAnimSequence* Base : {IdleAnimation.Get(), AimAnimation.Get(), FireAnimation.Get(), AimFireAnimation.Get(), EquipAnimation.Get()})
            if (Base)
            {
                const FString Path=FString::Printf(TEXT("/Game/Weapons/M4DrumGripRebuilt/Support/%s.%s"),*Base->GetName(),*Base->GetName());
                if (auto* Support=LoadObject<UAnimSequence>(nullptr,*Path))DrumSupportAnimations.Add(Base,Support);
            }

    if (A762WeaponAssets::Matches(AKMViewmodel))
    {
        DrumReloadAnimation=LoadObject<UAnimSequence>(nullptr,*A762Attachments::AnimationPath(TEXT("base"),TEXT("drum_reload")));
        DrumReloadEmptyAnimation=LoadObject<UAnimSequence>(nullptr,*A762Attachments::AnimationPath(TEXT("base"),TEXT("drum_reload_empty")));
    }
    ForegripAnimations.Reset(); PrismGripAnimations.Reset(); VerticalGripAnimations.Reset(); CantedGripAnimations.Reset();
    if (bUseM16)
    {
        const TPair<UAnimSequence*,const TCHAR*> Support[]={{IdleAnimation,TEXT("idle")},{AimAnimation,TEXT("aim")},
            {FireAnimation,TEXT("fire")},{AimFireAnimation,TEXT("aim_fire")},{EquipAnimation,TEXT("equip")},{InspectAnimation,TEXT("inspect")}};
        for(const auto& Pair:Support)
            if(Pair.Key)
                if(auto* Clip=LoadObject<UAnimSequence>(nullptr,*M16Attachments::AnimationPath(TEXT("drum"),Pair.Value)))
                    DrumSupportAnimations.Add(Pair.Key,Clip);
    }
    if (!IsPistolWeapon())
    {
        InitializeForegripAnimations();
        InitializePrismGripAnimations();
        InitializeVerticalGripAnimations();
        InitializeCantedGripAnimations();
    }
    PistolIdleEmptyAnimation = bUseM1911 ? LoadAKMAnimation(TEXT("A_AKM_idle_empty")) : nullptr;
    PistolSprintAnimation = IsPistolWeapon()
        ? LoadObject<UAnimSequence>(nullptr, *PistolLocomotionAssets::AnimationPath(bUseDanWesson715)) : nullptr;
    PistolSprintEmptyAnimation = bUseM1911
        ? LoadObject<UAnimSequence>(nullptr, *PistolLocomotionAssets::AnimationPath(false, true)) : nullptr;
    PistolAimEmptyAnimation = bUseM1911 ? LoadAKMAnimation(TEXT("A_AKM_aim_empty")) : nullptr;
    PistolFireLastAnimation = bUseM1911 ? LoadAKMAnimation(TEXT("A_AKM_fire_last")) : nullptr;
    PistolAimFireLastAnimation = bUseM1911 ? LoadAKMAnimation(TEXT("A_AKM_aim_fire_last")) : nullptr;
    if (IsPistolWeapon()) { DrumReloadAnimation = nullptr; DrumReloadEmptyAnimation = nullptr; }
    ActiveActionAnimation = nullptr;
    AKMViewmodel->SetAnimInstanceClass(UFPSGunplayAnimInstance::StaticClass());
    if (auto* Sprint = FindComponentByClass<UM4TacticalSprintComponent>())
        Sprint->Configure(IsPistolWeapon() ? ERifleSprintWeapon::None
            : SVDWeaponAssets::Matches(AKMViewmodel) ? ERifleSprintWeapon::SVD
            : PKMLowpolyWeaponAssets::Matches(AKMViewmodel) ? ERifleSprintWeapon::PKM
            : bUseM16 ? ERifleSprintWeapon::M16
            : bUseASH12 ? ERifleSprintWeapon::ASH12
            : bUseQBZ191 ? ERifleSprintWeapon::QBZ191
            : bUsingM4Infima && bUseM4Infima ? ERifleSprintWeapon::M4
            : AKMSoviet::Matches(AKMViewmodel) || A762WeaponAssets::Matches(AKMViewmodel) ? ERifleSprintWeapon::AKM : ERifleSprintWeapon::None);
    GunplayAnimation = Cast<UFPSGunplayAnimInstance>(AKMViewmodel->GetAnimInstance());
    if (GunplayAnimation)
    {
        GunplayAnimation->IdleClip = IdleAnimation;
        GunplayAnimation->AimClip = AimAnimation;
    }
    WeaponFX->Initialize(AKMViewmodel, FirstPersonCamera);
    FireSound = LoadAKMSound(TEXT("S_AKM_Fire"));
    // PKM owns its fire one-shot; the AKM family fallback above stays untouched
    // for every other rifle and remains the fallback if this asset is absent.
    if (PKMLowpolyWeaponAssets::Matches(AKMViewmodel))
        if (USoundBase* PKMFire = LoadObject<USoundBase>(nullptr, PKMLowpolyWeaponAssets::FireSoundPath))
            FireSound = PKMFire;
    RevolverSpeedloaderSounds.Reset();
    if (bUseDanWesson715)
        for (const auto& Cue : DanWesson715WeaponAssets::SpeedloaderSoundCues)
            RevolverSpeedloaderSounds.Add(LoadObject<USoundBase>(nullptr, *DanWesson715WeaponAssets::SpeedloaderSoundPath(Cue.Name)));
    RifleFireVariants.Reset();
    RifleSuppressedVariants.Reset();
    LastRifleFireVariant = INDEX_NONE;
    if (bUsingM4Infima && !IsPistolWeapon() && !PKMLowpolyWeaponAssets::Matches(AKMViewmodel))
    {
        const TCHAR* AudioWeapon = bUseQBZ191 ? TEXT("QBZ191") : TEXT("M4");
        for (int32 Index = 1; Index <= 4; ++Index)
        {
            const FString Base = FString::Printf(TEXT("/Game/Weapons/FreeFirearmAudio20260913/S_%s_"), AudioWeapon);
            const FString FirePath = bUseQBZ191
                ? Base + FString::Printf(TEXT("Fire_%02d"), Index)
                : FString::Printf(TEXT("/Game/Weapons/M4OriginalAudio20260913/S_M4_Original_%02d"), Index);
            if (!bUseASH12 && !bUseM16 && !SVDWeaponAssets::Matches(AKMViewmodel))
                if (USoundBase* Sound = LoadObject<USoundBase>(nullptr, *FirePath))
                    RifleFireVariants.Add(Sound);
            const FString SuppressedPath = bUseASH12
                ? FString::Printf(TEXT("/Game/Weapons/ASH12/SuppressedAudio20260920/S_ASH12_Suppressed_%02d"), Index)
                : !bUseQBZ191 && !bUseM16
                    ? FString::Printf(TEXT("/Game/Weapons/M4SuppressedAudio20260921/S_M4_Suppressed_%02d"), Index)
                    : Base + FString::Printf(TEXT("Suppressed_%02d"), Index);
            if (USoundBase* Sound = LoadObject<USoundBase>(nullptr, *SuppressedPath))
                RifleSuppressedVariants.Add(Sound);
        }
        // ASH-12 uses the supplied one-shot in the overlapping-tail player;
        // the generic M4 variant bank must not replace it on equip.
        if (bUseASH12 && FireSound) RifleFireVariants.Add(FireSound);
        if (bUseM16 && FireSound) RifleFireVariants.Add(FireSound);
        if (SVDWeaponAssets::Matches(AKMViewmodel))
            for(int32 Index=1;Index<=SVDWeaponAssets::FireVariantCount;++Index)
                if(auto* Sound=LoadObject<USoundBase>(nullptr,*SVDWeaponAssets::FireSoundPath(Index)))RifleFireVariants.Add(Sound);
        if (!RifleFireVariants.IsEmpty()) FireSound = RifleFireVariants[0];
        if (!RifleSuppressedVariants.IsEmpty()) SuppressedFireSound = RifleSuppressedVariants[0];
        RifleFireConcurrency = NewObject<USoundConcurrency>(this);
        RifleFireConcurrency->Concurrency.MaxCount = 6;
        RifleFireConcurrency->Concurrency.bLimitToOwner = true;
        RifleFireConcurrency->Concurrency.ResolutionRule = EMaxConcurrentResolutionRule::StopOldest;
        RifleFireConcurrency->Concurrency.VoiceStealReleaseTime = 0.02f;
    }
    if (AKMSoviet::Matches(AKMViewmodel))
        if (!bPresentationOnly) SuppressedFireSound = LoadObject<USoundBase>(nullptr, TEXT("/Game/Weapons/AKM/SuppressedAudio20260921/S_AKM_Suppressed"));
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
    Input->BindAction(TEXT("Fire"), IE_Released, this, &AFPSGAMECharacter::FireInputReleased);
    Input->BindAction(TEXT("Aim"), IE_Pressed, this, &AFPSGAMECharacter::AimPressed);
    Input->BindAction(TEXT("Aim"), IE_Released, this, &AFPSGAMECharacter::AimReleased);
    Input->BindAction(TEXT("Reload"), IE_Pressed, this, &AFPSGAMECharacter::ReloadInputPressed);
    Input->BindAction(TEXT("Reload"), IE_Released, this, &AFPSGAMECharacter::ReloadInputReleased);
    Input->BindAction(TEXT("InspectWeapon"), IE_Pressed, this, &AFPSGAMECharacter::InspectPressed);
    Input->BindAction(TEXT("QuickCombat"), IE_Pressed, this, &AFPSGAMECharacter::QuickCombatPressed);
    Input->BindAction(TEXT("RuneBlades"), IE_Pressed, this, &AFPSGAMECharacter::RuneBladesPressed);
}

void AFPSGAMECharacter::Tick(float DeltaSeconds)
{
    Super::Tick(DeltaSeconds);
    UpdateAmmoSelection();
    Traversal->Advance(DeltaSeconds);
    if (auto* Profile = GetGameInstance()->GetSubsystem<UColdSteelStatusModel>()) Profile->TickRuntime(DeltaSeconds, this);
    SprintToFireLeft = static_cast<float>(FMath::Max(0.0, SprintFireUnlockTime - GetWorld()->GetTimeSeconds()));
    SlideBoostCooldownRemaining = FMath::Max(0.0f, SlideBoostCooldownRemaining - DeltaSeconds);
    JumpBufferRemaining = FMath::Max(0.0f, JumpBufferRemaining - DeltaSeconds);
    if (bIsSliding) UpdateSlide(DeltaSeconds);
    TryBufferedJump();
    RefreshMovementState();
    UpdateWeaponState(DeltaSeconds);
    ServicePendingReloadCycle();
    ServiceReloadAfterCasting();
    ServiceRevolverReloadAfterFire();
    // Also recover an empty magazine loaded from a saved profile after equipping.
    if (!IsDualWieldingPistols() && (HasInfiniteReserveAmmo() || (bUseM16 && ReserveAmmo > 0))
        && bInventoryWeaponReady && MagazineAmmo == 0 && !IsWeaponBusy() && !IsChoosingAmmo()) ReloadPressed();
    if(BipodDeployment)BipodDeployment->Advance(DeltaSeconds);
    UpdateWeaponFeedback(DeltaSeconds);
    UpdateCamera(DeltaSeconds);
    UpdateViewmodel(DeltaSeconds);
    UpdateScopePresentation();
    Traversal->UpdatePresentation(DeltaSeconds);
    if(BipodDeployment)BipodDeployment->ApplyPresentation();
    ServiceHeldFire();
    UpdateActionPose(DeltaSeconds);
    UpdateDrumDropVisual();
    UpdateFoldingSights(DeltaSeconds);
    if (bRunWeaponAudit) RunWeaponAudit(DeltaSeconds);
    if (bRunInfiniteAmmoAudit) RunInfiniteAmmoAudit();
    if (bRunDrumGripAudit) RunDrumGripAudit();
    if (FParse::Param(FCommandLine::Get(), TEXT("SkeletonStockAudit"))) RunStockAudit();
    if (FParse::Param(FCommandLine::Get(), TEXT("ReloadTimingAudit"))) RunReloadTimingAudit();
    if (FParse::Param(FCommandLine::Get(), TEXT("ForegripAudit")) || FParse::Param(FCommandLine::Get(), TEXT("PrismGripAudit")) || FParse::Param(FCommandLine::Get(), TEXT("VerticalGripAudit")) || FParse::Param(FCommandLine::Get(), TEXT("CantedGripAudit"))) RunForegripAudit();
    if (bRunAKMIntegrationAudit) RunAKMIntegrationAudit();
    if (FParse::Param(FCommandLine::Get(), TEXT("QBZ191IntegrationAudit"))) RunQBZ191IntegrationAudit();
    if (FParse::Param(FCommandLine::Get(), TEXT("ASH12SightCapture"))) RunASH12IntegrationAudit();
    if (bRunSlideCombatAudit) RunSlideCombatAcceptance(DeltaSeconds);
    else if (bRunGunplayAcceptance) RunGunplayAcceptance(DeltaSeconds);
    if (bRunWeaponHandlingAudit) RunWeaponHandlingAudit();
    if (FParse::Param(FCommandLine::Get(), TEXT("M1911Audit"))) RunM1911DevelopmentAudit();
    if (FParse::Param(FCommandLine::Get(), TEXT("FrostRuneVisualAudit"))) TickFrostRuneVisualDiagnosis(this);
    if (FParse::Param(FCommandLine::Get(), TEXT("BallisticPresentationAudit"))) RunBallisticPresentationAudit();
    if (bRunMuzzleMigrationAudit) RunMuzzleMigrationAudit();
    LookInput = FVector2D::ZeroVector;
}

bool AFPSGAMECharacter::IsMeleeSkillMovementLocked() const
{
    return RuneSword && (RuneSword->IsWhirlwindActive() || RuneSword->IsDashAttackActive());
}

void AFPSGAMECharacter::StopMovementForMeleeSkill()
{
    ExitSprintForWeapon();
    SprintPressedAt = -1.0;
    MoveInput = FVector2D::ZeroVector;
    ConsumeMovementInputVector();
    JumpBufferRemaining = 0.f;
    StopJumping();
    Traversal->SetJumpHeld(false);
    auto* Movement = GetCharacterMovement();
    // Stop locomotion without suspending gravity if the cast starts in the air.
    const double FallingSpeed = Movement->IsFalling() ? Movement->Velocity.Z : 0.0;
    Movement->StopMovementImmediately();
    Movement->Velocity.Z = FallingSpeed;
    Movement->UpdateComponentVelocity();
}

void AFPSGAMECharacter::MoveForward(float Value)
{
    if(BipodDeployment&&BipodDeployment->BlocksMovement())return; // 架枪锁定：移动输入被忽略，退出后恢复
    if (IsMeleeSkillMovementLocked()) { MoveInput.Y = 0.f; return; }
    MoveInput.Y = Value;
    if (!bIsSliding && !IsDodging() && !FMath::IsNearlyZero(Value) && Controller)
        AddMovementInput(FRotationMatrix(FRotator(0.0f, Controller->GetControlRotation().Yaw, 0.0f)).GetUnitAxis(EAxis::X), Value);
}

void AFPSGAMECharacter::MoveRight(float Value)
{
    if(BipodDeployment&&BipodDeployment->BlocksMovement())return; // 架枪锁定：移动输入被忽略，退出后恢复
    if (IsMeleeSkillMovementLocked()) { MoveInput.X = 0.f; return; }
    MoveInput.X = Value;
    if (!bIsSliding && !IsDodging() && !FMath::IsNearlyZero(Value) && Controller)
        AddMovementInput(FRotationMatrix(FRotator(0.0f, Controller->GetControlRotation().Yaw, 0.0f)).GetUnitAxis(EAxis::Y), Value);
}

void AFPSGAMECharacter::Turn(float Value)
{
    if(IsAmmoWheelOpen()){MoveAmmoPointer(FVector2D(Value,0));return;}
    if(IsMeleeSkillMovementLocked())return;
    if (const auto* PC=Cast<APlayerController>(Controller); PC && PC->bShowMouseCursor) return;
    LookInput.X += Value; AddControllerYawInput(Value * LookSensitivityScale());
}
void AFPSGAMECharacter::LookUp(float Value)
{
    if(IsAmmoWheelOpen()){MoveAmmoPointer(FVector2D(0,Value));return;}
    if(IsMeleeSkillMovementLocked())return;
    if (const auto* PC=Cast<APlayerController>(Controller); PC && PC->bShowMouseCursor) return;
    LookInput.Y += Value; AddControllerPitchInput(Value * LookSensitivityScale());
}
void AFPSGAMECharacter::SprintPressed()
{
    if(BipodDeployment&&BipodDeployment->BlocksMovement())return; // 架枪锁定：冲刺/疾避键无效
    if (IsMeleeSkillMovementLocked()) return;
    if (bSprintHeld) return;
    SprintPressedAt=(!IsDodging() && !IsTraversing() && Controller && !Controller->IsMoveInputIgnored())
        ? GetWorld()->GetTimeSeconds() : -1.0;
    bSprintHeld = true;
    if (IsDodging()) return;
    if (bIsSliding && CanStand()) StopSlide(true);
    else if (bIsCrouched && CanStand()) UnCrouch();
}
void AFPSGAMECharacter::SprintReleased()
{
    const bool bTap=bSprintHeld && SprintPressedAt>=0.0 &&
        GetWorld()->GetTimeSeconds()-SprintPressedAt<=DodgeTapMaximumHold;
    bSprintHeld=false;
    SprintPressedAt=-1.0;
    if (bTap) TryDodge();
}

void AFPSGAMECharacter::SlidePressed()
{
    if(BipodDeployment&&BipodDeployment->BlocksMovement())return; // 架枪锁定：蹲/滑铲键无效
    if (IsMeleeSkillMovementLocked() || IsTraversing() || IsDodging()) return;
    if (bIsSliding) { StopSlide(false); return; }
    if (bIsCrouched) { if (CanStand()) UnCrouch(); return; }
    // 门槛跟持械移速乘区走：满速要求仍是 600，持机枪降到 402（即 600×0.67），
    // 否则机枪的疾跑上限 469 永远跨不过固定的 600，滑铲静默失效。
    if (GetCharacterMovement()->IsMovingOnGround() && HorizontalSpeed() >= SlideEntrySpeed()) StartSlide(); else Crouch();
}

void AFPSGAMECharacter::JumpPressed()
{
    if(BipodDeployment&&BipodDeployment->BlocksMovement())return; // 架枪锁定：跳跃/翻越键无效
    if (IsMeleeSkillMovementLocked() || IsDodging()) return;
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
    if(IsAmmoWheelOpen() || IsSwitchingWeapon())return;
    if(IsDualWieldingPistols()){DualPistols->Trigger(0,true);return;}
    // 手枪砸击进行中不接开火（枪已离姿态，动作结束才恢复）。
    if(QuickCombatPistol && QuickCombatPistol->IsOccupyingLeftHand())return;
    if(IsCastBlockingLeftHandAction())
    {
        if(Bow && Bow->IsEquipped())return;
        if(RuneSword && RuneSword->IsEquipped())return;
        if(auto* Tools=FindComponentByClass<UProductionToolComponent>();Tools&&Tools->IsEquipped())return;
    }
    // 冲刺攻击是连续奔跑就绪后的被动；未就绪沿用轻／重攻击。
    if(RuneSword && RuneSword->IsEquipped())
    {
        // 就绪检测须在退出奔跑前完成；未就绪沿用普通左键轻／重攻击。
        if(RuneSword->DashReadyFraction()>=1.f){RuneSword->TryBeginDashAttack();return;}
        ExitSprintForWeapon();
        RuneSword->BeginPrimaryAttack();
        return;
    }
    // 弓：左键一次按下＝弦上空先搭箭、已搭箭开始拉开；只有真实松手才结算发射。
    if(Bow&&Bow->IsEquipped()){ExitSprintForWeapon();Bow->SetTriggerHeld(true);Bow->BeginPrimaryAttack();return;}
    if(auto* Tools=FindComponentByClass<UProductionToolComponent>();Tools&&Tools->IsEquipped())
    {ExitSprintForWeapon();Tools->BeginUse();return;}
    if (bUseM16)
    {
        if (bBurstTriggerHeld) return;
        bBurstTriggerHeld = true;
        // A click during an existing group is not queued as another group.
        if (BurstShotsRemaining > 0 || !bInventoryWeaponReady || IsWeaponBusy()
            || IsCastBlockingLeftHandAction() || GetWorld()->GetTimeSeconds() < NextAllowedShotTime) return;
        BurstShotsRemaining = BurstShotCount;
    }
    if (!bFireHeld)
    {
        NextAllowedShotTime = FMath::Max(NextAllowedShotTime, static_cast<double>(GetWorld()->GetTimeSeconds()));
        TriggerFirstShotWorldTime = -1.0;
    }
    if (UsesSingleShotTrigger() && !bFireHeld) bPistolShotPending = true;
    bFireHeld = true;
    ExitSprintForWeapon();
    ServiceHeldFire();
}

void AFPSGAMECharacter::FireInputReleased()
{
    // Only the physical input release may commit a charged sword attack.
    // Menu/traversal/equipment callers still use FireReleased to stop actions.
    // 松手是弓唯一的发射入口；菜单／翻越等打断走 FireReleased，不放箭。
    if(Bow&&Bow->IsEquipped()){Bow->SetTriggerHeld(false);Bow->ReleasePrimaryAttack();return;}
    if(RuneSword && RuneSword->IsEquipped()){RuneSword->ReleasePrimaryAttack();return;}
    if (bUseM16) { bBurstTriggerHeld = false; return; }
    FireReleased();
}

void AFPSGAMECharacter::FireReleased()
{
    bFireHeld=false;bPistolShotPending=false;GetWorldTimerManager().ClearTimer(FireTimerHandle);
    bBurstTriggerHeld=false;BurstShotsRemaining=0;
    if(IsDualWieldingPistols()){DualPistols->Trigger(0,false);return;}
    // 切枪／菜单这类"非真实松手"只收弓，箭留在弦上，不结算发射。
    if(Bow&&Bow->IsEquipped()){Bow->SetTriggerHeld(false);Bow->CancelAction();}
    if(RuneSword && RuneSword->IsEquipped())RuneSword->CancelAction();
    const double Now=GetWorld()->GetTimeSeconds();
    AdvanceVisualWeaponRecoil(Now);
    // Preserve the initial kick even when a tap is released in the shot frame.
    VisualRecoverAt=FMath::Min(VisualRecoverAt,FMath::Max(Now,LastVisualShotAt+.055));
}

void AFPSGAMECharacter::AimPressed()
{
    if(IsAmmoWheelOpen() || IsSwitchingWeapon())return;
    if(IsDualWieldingPistols()){DualPistols->Trigger(1,true);return;}
    if(IsCastBlockingLeftHandAction())return;
    // 弓的右键＝稳持（压住满拉呼吸抖动），不进枪械机瞄状态机。
    if(Bow&&Bow->IsEquipped()){ExitSprintForWeapon();Bow->SetSteadyHeld(true);return;}
    if(RuneSword && RuneSword->IsEquipped()){ExitSprintForWeapon();RuneSword->BeginGuard();return;}
    // Right-click with a production tool out is the shovel's refill, never ADS.
    if(auto* Tools=FindComponentByClass<UProductionToolComponent>();Tools&&Tools->IsEquipped()){Tools->BeginRefill();return;}
    bAimHeld = true;
    ExitSprintForWeapon();
    if (!IsWeaponBusy()) { SetAimingState(true); ResumeWeaponPose(); }
}

void AFPSGAMECharacter::AimReleased()
{
    if(IsDualWieldingPistols()){DualPistols->Trigger(1,false);bAimHeld=false;return;}
    bAimHeld=false;
    if(Bow&&Bow->IsEquipped()){Bow->SetSteadyHeld(false);return;}
    if(RuneSword && RuneSword->IsEquipped()){RuneSword->ReleaseGuard();return;}
    SetAimingState(false);if(!IsWeaponBusy())ResumeWeaponPose();
}

void AFPSGAMECharacter::ReloadPressed()
{
    // 弓的 R＝从箭袋取箭上弦；已上弦时不重复消耗。
    if(Bow&&Bow->IsEquipped()){Bow->BeginNock();return;}
    if(IsChoosingAmmo())return;
    if(IsDualWieldingPistols()){DualPistols->Reload();return;}
    if(IsCastBlockingLeftHandAction())
    {
        if(bInventoryWeaponReady && (MagazineAmmo==0 || NeedsReloadCycle()))bReloadAfterCasting=true;
        return;
    }
    const bool ResumeCycle=PendingAmmoType.IsEmpty() && NeedsReloadCycle();
    if (!bInventoryWeaponReady || IsWeaponBusy() || (!ResumeCycle && PendingAmmoType.IsEmpty() && (MagazineAmmo >= MagazineCapacity || (!HasInfiniteReserveAmmo() && ReserveAmmo <= 0)))) return;
    if (IsRevolverFireActionPlaying())
    {
        // A fired round makes the magazine empty while the recoil clip is
        // still playing. Retain both automatic and manual reload requests.
        bRevolverReloadAfterFire = true;
        return;
    }
    if (bUseM16) FireReleased();
    bRevolverReloadAfterFire = false;
    bReloadAfterCasting=false;
    bRevolverSingleReload = bUseDanWesson715 && !bRevolverSpeedloaderInstalled;
    UAnimSequence* RevolverClip = nullptr;
    if (bUseDanWesson715)
    {
        const bool Switching=!PendingAmmoType.IsEmpty();
        RevolverReloadStartLive = Switching||ResumeCycle?0:MagazineAmmo;
        const int32 RetainedRounds = bRevolverSingleReload && !Switching ? MagazineAmmo : 0;
        const int32 Available=Switching?int32(FMath::Min<int64>(MagazineCapacity,GetGameInstance()->GetSubsystem<UColdSteelStatusModel>()->PouchCount(PendingAmmoType))):HasInfiniteReserveAmmo()?MagazineCapacity:ReserveAmmo;
        RevolverReloadCount = ResumeCycle?1:FMath::Min(MagazineCapacity - RetainedRounds, Available);
        RevolverReloadCommitted = 0;
        bRevolverCasesCleared = Switching||ResumeCycle;
        const FString ClipPath = bRevolverSingleReload
            ? DanWesson715WeaponAssets::SingleAnimationPath(RevolverReloadStartLive, RevolverReloadCount)
            : DanWesson715WeaponAssets::SpeedAnimationPath();
        RevolverClip = LoadObject<UAnimSequence>(nullptr, *ClipPath);
        if (!RevolverClip) return;
    }
    StopMechanicalAudio();
    GetWorldTimerManager().ClearTimer(FireTimerHandle);
    SetAimingState(false);
    // Speedloaders use the full extraction action even with unfired rounds.
    // Keep those rounds until the extraction contact commits their loss.
    bPendingEmptyReload = ResumeCycle || !PendingAmmoType.IsEmpty() || MagazineAmmo == 0 || (bUseDanWesson715 && !bRevolverSingleReload);
    if(ResumeCycle)
        if(const auto* Item=GetGameInstance()->GetSubsystem<UColdSteelStatusModel>()->FindItem(ActiveInventoryWeapon))
            bPendingEmptyReload=WeaponReloadStages::UsesEmptyCycle(*Item);
    WeaponState = bPendingEmptyReload ? EAKMWeaponState::ReloadingEmpty : EAKMWeaponState::Reloading;
    WeaponActionStartedAt = GetWorld()->GetTimeSeconds();
    WeaponStateElapsed = 0.0f;
    WeaponStateDuration = FMath::Max(0.01f, bPendingEmptyReload ? EmptyReloadDuration : ReloadDuration);
    UAnimSequence* Animation = bPendingEmptyReload ? ReloadEmptyAnimation : ReloadAnimation;
    if (bUseDanWesson715) Animation = RevolverClip;
    if(bDrumInstalled)Animation=bPendingEmptyReload?DrumReloadEmptyAnimation:DrumReloadAnimation;
    if (bUsingM4Infima && bUseM4Infima && !bUseQBZ191 && !bUseASH12
        && !IsPistolWeapon() && !bDrumInstalled
        && (MagazineAttachmentId.IsEmpty() || MagazineAttachmentId == TEXT("ext_mag")))
    {
        // bUsingM4Infima also marks QBZ/pistol shared timing. This contact
        // animation belongs only to the actual M4 mesh and skeleton. Standard
        // and extended magazines share the unchanged upper contact surface;
        // both use the same wrapped grasp. Drums keep their separate action.
        const TCHAR* ExtMagClip = bPendingEmptyReload
            ? TEXT("/Game/Weapons/ExtMagContact20260919/A_M4_ExtContact_reload_empty")
            : TEXT("/Game/Weapons/ExtMagContact20260919/A_M4_ExtContact_reload");
        if (UAnimSequence* ExtMagAnimation = LoadObject<UAnimSequence>(nullptr, ExtMagClip))
            if (ExtMagAnimation->GetSkeleton() == AKMViewmodel->GetSkeletalMeshAsset()->GetSkeleton())
                Animation = ExtMagAnimation;
    }
    else if (MagazineAttachmentId == TEXT("ext_mag") && AKMSoviet::Matches(AKMViewmodel))
    {
        // Keep each attachment's approach/return, with local finger clearance
        // during the magazine contact. Never route QBZ through this branch.
        const TCHAR* Grip = HasAngledForegrip() ? TEXT("angled_")
            : HasCantedForegrip() ? TEXT("canted_")
            : HasVerticalForegrip() ? TEXT("vertical_")
            : HasPrismHandstop() ? TEXT("prism_") : TEXT("");
        const FString ExtMagClip = FString::Printf(
            TEXT("/Game/Weapons/ExtMagContact20260919/A_AKM_ExtContact_%s%s"),
            Grip, bPendingEmptyReload ? TEXT("reload_empty") : TEXT("reload"));
        if (UAnimSequence* ExtMagAnimation = LoadObject<UAnimSequence>(nullptr, *ExtMagClip))
            if (ExtMagAnimation->GetSkeleton() == AKMViewmodel->GetSkeletalMeshAsset()->GetSkeleton())
                Animation = ExtMagAnimation;
    }
    const float ClipLength = Animation ? Animation->GetPlayLength() : WeaponStateDuration;
    if (IsPistolWeapon() && Animation)
    {
        float DurationScale = 1.f;
        if (const auto* Gunsmith = GetGameInstance()->GetSubsystem<UGunsmithSystem>())
            if (const auto* Weapon = Gunsmith->Weapon(bUseDanWesson715 ? DanWesson715WeaponAssets::Definition : TEXT("ue_m1911")))
            {
                const float BaseDuration = bUseDanWesson715 && !bRevolverSingleReload
                    ? (bPendingEmptyReload ? DanWesson715WeaponAssets::EmptyReload : DanWesson715WeaponAssets::NormalReload)
                    : static_cast<float>(bPendingEmptyReload ? Weapon->Base.EmptyReload : Weapon->Base.Reload);
                DurationScale = WeaponStateDuration / FMath::Max(.01f, BaseDuration);
            }
        WeaponStateDuration = FMath::Max(.01f, ClipLength * DurationScale);
    }
    if(!Animation){InterruptReload();return;}
    PlayWeaponAnimation(Animation, false, ClipLength / WeaponStateDuration);
    // The state owns completion. Animation and all contact events consume this
    // same duration; changing a reload stat scales the complete action.
    ActionDuration = WeaponStateDuration;

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
    // AKM base/extended/drum share the insertion contact. Delay the new short
    // sample in source time so reload-speed modifiers keep audio and pose aligned.
    if (AKMSoviet::Matches(AKMViewmodel) || A762WeaponAssets::Matches(AKMViewmodel)) MechanicalCueTimes[1] += .18f * Scale;
    // The AKM drum releases directly from the well at source frame 36 / 120 Hz.
    if((AKMSoviet::Matches(AKMViewmodel)||A762WeaponAssets::Matches(AKMViewmodel))&&bDrumInstalled)MechanicalCueTimes[0]=.3f*Scale;
    for (float& Cue : MechanicalCueTimes) Cue = ReloadRuntimeTime(Cue / Scale);
    if (bUsingM4Infima)
    {
        // Source animation seconds, evaluated by the very same clock as the pose.
        if (PKMLowpolyWeaponAssets::Matches(AKMViewmodel))
        {
            // Dedicated reference cuts, scheduled on the pose's source clock.
            // The queue holds the loaded objects for the entire reload action.
            const auto PKMContact=[](const TCHAR* Name, USoundBase* Fallback)
            {
                const FString Path=FString(Name).StartsWith(TEXT("Charge"))
                    ? PKMLowpolyWeaponAssets::ChargeSoundPath(Name)
                    : PKMLowpolyWeaponAssets::ReloadSoundPath(Name);
                if (auto* Sound=LoadObject<USoundBase>(nullptr,*Path)) return Sound;
                UE_LOG(LogTemp,Warning,TEXT("PKM reload contact missing: %s"),*Path);
                return Fallback;
            };
            MechanicalCueTimes={.65f};
            MechanicalCueSounds={PKMContact(TEXT("CoverOpen"),ChargeReleaseSound)};
            if (!bPendingEmptyReload)
            {
                MechanicalCueTimes.Add(1.65f);
                MechanicalCueSounds.Add(PKMContact(TEXT("BeltLift"),MagOutSound));
            }
            for (const float Contact : {2.6f,4.35f,5.1f,5.72f})
                MechanicalCueTimes.Add(PKMLowpolyWeaponAssets::ReloadEventTime(Contact,bPendingEmptyReload));
            MechanicalCueSounds.Append({PKMContact(TEXT("BoxOut"),MagOutSound),
                PKMContact(TEXT("BoxInsert"),MagInsertSound),PKMContact(TEXT("BeltSeat"),MagSeatSound),
                PKMContact(TEXT("CoverClose"),ChargeReleaseSound)});
            if (bPendingEmptyReload)
            {
                // Charge34/Audio35: travel and stop are separate reference cuts.
                // Both metal attacks stay on their exact pose-clock contacts.
                MechanicalCueTimes.Append({5.13f, 5.36f, 5.48f, 5.82f});
                MechanicalCueSounds.Append({PKMContact(TEXT("ChargePullMove"),ChargePullSound),
                    PKMContact(TEXT("ChargeRearStop"),ChargePullSound),
                    PKMContact(TEXT("ChargePushMove"),ChargePullSound),
                    PKMContact(TEXT("ChargeFrontStop"),ChargeReleaseSound)});
            }
        }
        else if (SVDWeaponAssets::Matches(AKMViewmodel))
        {
            MechanicalCueTimes={SVDWeaponAssets::MagazineOut,SVDWeaponAssets::MagazineInsert,SVDWeaponAssets::MagazineSeat};
            MechanicalCueSounds={MagOutSound,MagInsertSound,MagSeatSound};
            if(bPendingEmptyReload)
            {
                MechanicalCueTimes.Append({SVDWeaponAssets::ChargePull,SVDWeaponAssets::ChargeRelease});
                MechanicalCueSounds.Append({ChargePullSound,ChargeReleaseSound});
            }
        }
        else if (bUseASH12)
        {
            // Reference remake: drop, retrieve, insert, seat, then (empty only)
            // overhand pull and release. The two charging contacts are distinct.
            MechanicalCueTimes = {ASH12WeaponAssets::MagazineOut,
                ASH12WeaponAssets::MagazineInsert, ASH12WeaponAssets::MagazineSeat};
            MechanicalCueSounds = {MagOutSound, MagInsertSound, MagSeatSound};
            if (bPendingEmptyReload)
            {
                MechanicalCueTimes.Add(ASH12WeaponAssets::ChargePull);
                MechanicalCueTimes.Add(ASH12WeaponAssets::ChargeRelease);
                MechanicalCueSounds.Add(ChargePullSound);
                MechanicalCueSounds.Add(ChargeReleaseSound);
            }
        }
        else if (bUseM16 && bPendingEmptyReload)
        {
            MechanicalCueTimes = {M16WeaponAssets::MagazineOut, M16WeaponAssets::MagazineInsert,
                M16WeaponAssets::MagazineSeat, M16WeaponAssets::ChargePull, M16WeaponAssets::ChargeRelease};
            MechanicalCueSounds = {MagOutSound, MagInsertSound, MagSeatSound, ChargePullSound, ChargeReleaseSound};
        }
        else
        {
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
        if(bDrumInstalled)
        {
            MechanicalCueTimes=bUseM16&&bPendingEmptyReload
                ? TArray<float>{14.f/60.f,54.f/60.f,80.f/60.f,M16WeaponAssets::ChargePull,M16WeaponAssets::ChargeRelease}
                : bPendingEmptyReload
                ? TArray<float>{14.0f/60.0f,54.0f/60.0f,80.0f/60.0f,116.0f/60.0f}
                : TArray<float>{18.0f/60.0f,76.0f/60.0f,95.0f/60.0f};
        }
        if (bUseM1911)
        {
            MechanicalCueTimes = {M1911Source::MagazineOut, M1911Source::MagazineInsert, M1911Source::MagazineSeat};
            MechanicalCueSounds = {MagOutSound, MagInsertSound, MagSeatSound};
            if (bPendingEmptyReload)
            {
                MechanicalCueTimes.Add(M1911Source::SlideRelease);
                MechanicalCueSounds.Add(ChargeReleaseSound);
            }
        }
        if (bUseDanWesson715)
        {
            if (bRevolverSingleReload)
            {
                // The three phases single-round loading shares with the speedloader
                // route -- swinging the cylinder out, clearing spent cases and
                // closing it -- use the recorded 715 one-shots, which are the same
                // mechanism. The four loader-only recordings (Retrieve/Insert/
                // Release/Withdraw) have no single-round equivalent and are
                // deliberately not used here.
                // Index into SpeedloaderSoundCues: 0 Open, 2 Eject, 6 Close.
                // Explicit USoundBase* throughout: the recorded sounds are held as
                // TObjectPtr and must not meet a raw pointer inside a conditional.
                auto RecordedCue = [this](int32 CueIndex, float& OutLead) -> USoundBase*
                {
                    const float Lead = DanWesson715WeaponAssets::SpeedloaderSoundCues[CueIndex].LeadSeconds;
                    OutLead = Lead;
                    TObjectPtr<USoundBase> Recorded = RevolverSpeedloaderSounds.IsValidIndex(CueIndex)
                        ? RevolverSpeedloaderSounds[CueIndex] : nullptr;
                    // Missing asset, or a clip too short to hold its own pre-roll:
                    // fall back to the revolver's own contact with no advance.
                    if (!Recorded || Recorded->GetDuration() <= Lead) { OutLead = 0.f; return MagOutSound; }
                    return Recorded.Get();
                };
                // Eject uses EmptyCaseClear for the same reason AdvanceReloadStages
                // does: on an empty cylinder the authored clip clears cases there,
                // not at the speedloader-bound .Eject constant.
                const float OpenContact = DanWesson715WeaponAssets::Open;
                const float EjectContact = DanWesson715WeaponAssets::EmptyCaseClear;
                const float CloseContact = DanWesson715WeaponAssets::SingleLoopBegin(bPendingEmptyReload)
                    + RevolverReloadCount * DanWesson715WeaponAssets::SingleStep
                    + DanWesson715WeaponAssets::SingleCloseContact;
                float OpenLead = 0.f, EjectLead = 0.f, CloseLead = 0.f;
                USoundBase* OpenCue = RecordedCue(0, OpenLead);
                USoundBase* EjectCue = RecordedCue(2, EjectLead);
                USoundBase* CloseCue = RecordedCue(6, CloseLead);
                // Each recording carries unpitched pre-roll before its impact, so
                // the trigger advances by that lead and the impact -- not the file
                // start -- meets the contact. Same rule as the speedloader route.
                MechanicalCueTimes = {OpenContact - OpenLead};
                MechanicalCueSounds = {OpenCue};
                if (bPendingEmptyReload)
                {
                    MechanicalCueTimes.Add(EjectContact - EjectLead);
                    MechanicalCueSounds.Add(EjectCue);
                }
                for (int32 Index = 0; Index < RevolverReloadCount; ++Index)
                {
                    // Seating one cartridge. MagSeat is the sample named for this
                    // mechanism but it is soft and mid-weighted (79% of its energy in
                    // the first 30 ms, only 27% above 1.5 kHz), so six in a row read
                    // as mushy. DryClick is the tightest sample the revolver has --
                    // 98.9% of its energy inside 30 ms and 81% above 1.5 kHz, with a
                    // 0.33 ms attack -- which gives each cartridge an audible click.
                    // Swap back to MagSeatSound if the sharper sound reads as too dry.
                    MechanicalCueTimes.Add(DanWesson715WeaponAssets::SingleSeatTime(Index, bPendingEmptyReload));
                    MechanicalCueSounds.Add(DryClickSound ? DryClickSound.Get() : MagSeatSound.Get());
                }
                MechanicalCueTimes.Add(CloseContact - CloseLead);
                MechanicalCueSounds.Add(CloseCue);
            }
            else
            {
                const float CueScale = bPendingEmptyReload ? DanWesson715WeaponAssets::EmptyReload / DanWesson715WeaponAssets::NormalReload : 1.f;
                const float SourcePerSecond = ClipLength / WeaponStateDuration;
                struct FScheduledCue { float Time; USoundBase* Sound; };
                TArray<FScheduledCue> Cues;
                int32 SoundIndex = 0;
                for (const auto& Cue : DanWesson715WeaponAssets::SpeedloaderSoundCues)
                {
                    USoundBase* Sound = RevolverSpeedloaderSounds.IsValidIndex(SoundIndex) ? RevolverSpeedloaderSounds[SoundIndex].Get() : nullptr;
                    ++SoundIndex;
                    if (Cue.bEmptyOnly && !bPendingEmptyReload) continue;
                    // Advance the trigger so the recorded impact, not the file
                    // start, meets the contact. Stat changes scale the pose,
                    // while the recording retains its natural pitch and length.
                    Cues.Add({FMath::Max(0.f, Cue.Contact * CueScale - Cue.LeadSeconds * SourcePerSecond), Sound});
                }
                Cues.Sort([](const FScheduledCue& A, const FScheduledCue& B) { return A.Time < B.Time; });
                MechanicalCueTimes.Reset();
                MechanicalCueSounds.Reset();
                for (const auto& Cue : Cues)
                {
                    MechanicalCueTimes.Add(Cue.Time);
                    MechanicalCueSounds.Add(Cue.Sound);
                }
            }
        }
        if (bUseQBZ191)
        {
            // QBZ uses the normal magazine exchange followed by its dedicated
            // charging-handle action, not the M4 bolt-release slap.
            MechanicalCueTimes = {29.f/60.f, 76.f/60.f, 95.f/60.f};
            MechanicalCueSounds = {MagOutSound, MagInsertSound, MagSeatSound};
            if(bPendingEmptyReload){
                MechanicalCueTimes.Append({142.f/60.f,151.f/60.f});
                MechanicalCueSounds.Append({ChargePullSound,ChargeReleaseSound});
            }
        }
    }
    InitializeReloadStages(ResumeCycle);
}

void AFPSGAMECharacter::InspectPressed()
{
    // Dual hands own their own clips. Starting the single-pistol inspect here
    // leaves WeaponState stuck: UpdateWeaponState does not advance it in dual.
    if(IsDualWieldingPistols())return;
    if(RuneSword && RuneSword->IsEquipped())
    {
        if(IsCastBlockingLeftHandAction() || IsWeaponBusy())return;
        ExitSprintForWeapon();RuneSword->BeginInspect();return;
    }
    if (IsCastBlockingLeftHandAction() || IsWeaponBusy() || !InspectAnimation) return;
    FireReleased();
    SetAimingState(false);
    WeaponState = EAKMWeaponState::Inspecting;
    WeaponActionStartedAt = GetWorld()->GetTimeSeconds();
    WeaponStateElapsed = 0.0f;
    WeaponStateDuration = InspectAnimation->GetPlayLength();
    PlayWeaponAnimation(InspectAnimation, false);
}

// 「快速进战」F 键入口：转交状态模型，由其按当前武器路由（剑 → 配重锤 / 手枪 → 握把砸击 /
// 其余枪械 → 步枪枪托砸击）。武器类型锁已于 2026-09-18 按用户要求取消。
void AFPSGAMECharacter::QuickCombatPressed()
{
    if(auto* Profile=GetGameInstance()?GetGameInstance()->GetSubsystem<UColdSteelStatusModel>():nullptr)
        Profile->TriggerQuickCombat();
}

// 符文长剑·环绕飞剑（G）：未激活时开剑阵，激活中每次按发射一把，口径对齐 2D 项目。
// 2D 合同"攻击动画未播完不触发"：剑在做任何动作（挥砍/格挡/旋刃/收刀）期间不响应。
void AFPSGAMECharacter::RuneBladesPressed()
{
    if(RuneSword && RuneSword->IsBusy())return;
    if(RuneOrbBlades)RuneOrbBlades->Trigger();
}

// 手枪版快速进战：单持时松开左手、右手持枪以握把前砸。这里只做武装与动作仲裁，
// 时钟、接触结算与技能提交在动作组件里。
bool AFPSGAMECharacter::TriggerPistolQuickCombat()
{
    auto Gate=[&](const TCHAR* Reason)
    {
        UE_LOG(LogTemp,Log,TEXT("[QuickCombat] 手枪砸击被拒绝：%s"),Reason);
        return false;
    };
    if(!IsPistolWeapon())return Gate(TEXT("当前不是手枪"));
    if(!CanStartQuickCombatPriority())return Gate(TEXT("切换武器或输入不可用"));
    if(const auto* Health=FindComponentByClass<UFPSCombatHealthComponent>();Health&&Health->IsDead())return Gate(TEXT("已死亡"));
    if(IsDualWieldingPistols())return DualPistols->BeginQuickCombat();
    if(!AKMViewmodel||!AKMViewmodel->GetSkeletalMeshAsset())return Gate(TEXT("视模不可用"));
    // 没有作者源 clip 的手枪不要"提交冷却但什么都不播"，宁可明确拒绝。
    if(!QuickCombatAnimation)return Gate(TEXT("该枪没有快速进战 clip"));
    InterruptActionsForPriority(false);
    FireReleased();
    SetAimingState(false);
    ExitSprintForWeapon();
    bFireHeld=false;bPistolShotPending=false;
    // 组件的时间轴按实际 clip 长度换算（作者源改节奏不需要同步改代码）。
    if (QuickCombatPistol && QuickCombatAnimation)
        QuickCombatPistol->ConfigureForClipLength(QuickCombatAnimation->GetPlayLength());
    const bool bStarted=QuickCombatPistol&&QuickCombatPistol->BeginAction();
    if (bStarted && QuickCombatAnimation)
    {
        // 动作本体是作者源 clip（WPN_root 驱动右手、左手松握下垂回握），
        // 组件只负责命中射线、冷却与修炼；两者共用 0.60s / 接触 0.30s 的时钟。
        WeaponState = EAKMWeaponState::QuickCombat;
        WeaponActionStartedAt = GetWorld()->GetTimeSeconds();
        WeaponStateElapsed = 0.0f;
        WeaponStateDuration = QuickCombatAnimation->GetPlayLength();
        PlayWeaponAnimation(QuickCombatAnimation, false);
    }
    // R0 诊断：动作入口带枪型，和入场快照那行日志一起用于对齐实机反馈。
    const TCHAR* WeaponName=bUseDanWesson715?TEXT("DanWesson715"):(bUseM1911?TEXT("M1911"):TEXT("OtherPistol"));
    UE_LOG(LogTemp,Log,TEXT("[QuickCombat] 手枪砸击%s 枪型=%s"),bStarted?TEXT("开始"):TEXT("启动失败"),WeaponName);
    return bStarted;
}

// 步枪版快速进战：M4 的枪托砸击。双手全程持枪，动作本体是作者源 clip
// （整枪刚体搬运写在 WPN_ 骨上，双手由握把关系带动），与手枪版共用同一个
// 动作组件（时钟/命中射线/冷却/修炼/镜头）与同一套 skill 数值合同。
EM4SprintGrip AFPSGAMECharacter::ResolveRifleGripProfile() const
{
    // 与战术冲刺同源：握把配置由当前配件解析，六个配置各有自己的 clip。
    return HasAngledForegrip() ? EM4SprintGrip::Angled
        : HasCantedForegrip() ? EM4SprintGrip::Canted
        : HasVerticalForegrip() ? EM4SprintGrip::Vertical
        : HasPrismHandstop() ? EM4SprintGrip::Prism
        : bDrumInstalled ? EM4SprintGrip::Drum : EM4SprintGrip::Base;
}

UAnimSequence* AFPSGAMECharacter::RifleQuickCombatClip(EM4SprintGrip Grip)
{
    if(SVDWeaponAssets::Matches(AKMViewmodel))
    {
        const TCHAR* Families[]={TEXT("base"),TEXT("base"),TEXT("angled"),TEXT("vertical"),TEXT("canted"),TEXT("prism")};
        const int32 Index=static_cast<int32>(Grip);
        return Index>1&&Index<UE_ARRAY_COUNT(Families)?LoadObject<UAnimSequence>(nullptr,*SVDAttachments::AnimationPath(Families[Index],TEXT("quick_melee"))):QuickCombatAnimation.Get();
    }
    if (PKMLowpolyWeaponAssets::Matches(AKMViewmodel))
    {
        const TCHAR* Families[]={TEXT("base"),TEXT("base"),TEXT("angled"),TEXT("vertical"),TEXT("canted"),TEXT("prism")};
        const int32 Index=static_cast<int32>(Grip);
        return Index>1&&Index<UE_ARRAY_COUNT(Families)?LoadObject<UAnimSequence>(nullptr,*PKMAttachments::AnimationPath(Families[Index],TEXT("quick_melee"))):QuickCombatAnimation.Get();
    }
    if (bUseM16)
    {
        const TCHAR* Families[]={TEXT("base"),TEXT("drum"),TEXT("angled"),TEXT("vertical"),TEXT("canted"),TEXT("prism")};
        const int32 Index=static_cast<int32>(Grip);
        return Index>0&&Index<UE_ARRAY_COUNT(Families)
            ?LoadObject<UAnimSequence>(nullptr,*M16Attachments::AnimationPath(Families[Index],TEXT("QuickCombat")))
            :QuickCombatAnimation.Get();
    }
    // Each rifle starts and returns to its own fitted idle. All four families
    // share the reference rhythm; QBZ191 keeps its O grip-locked correction.
    if (RifleQuickCombatClips.Num() != 24)
    {
        RifleQuickCombatClips.Reset();
        const TCHAR* Weapons[] = {TEXT("AKM"), TEXT("M4"), TEXT("QBZ191"), TEXT("ASH12")};
        for (int32 Family = 0; Family < 4; ++Family)
        {
            const FString Folder = Family == 1 ? TEXT("M4QuickMeleeReplica20260919")
                : FString::Printf(TEXT("RifleQuickMelee20260919/%s"), Weapons[Family]);
            for (const TCHAR* Name : {TEXT("Base"), TEXT("Drum"), TEXT("Angled"),
                                      TEXT("Vertical"), TEXT("Canted"), TEXT("Prism")})
            {
                // Each ASH foregrip keeps its fitted support hand during the strike.
                if (Family == 3 && FCString::Strcmp(Name, TEXT("Base")) != 0 && FCString::Strcmp(Name, TEXT("Drum")) != 0)
                {
                    RifleQuickCombatClips.Add(LoadObject<UAnimSequence>(nullptr,
                        *ASH12WeaponAssets::GripAnimationPath(*FString(Name).ToLower(), TEXT("QuickCombat"))));
                    continue;
                }
                // AKM/QBZ drums retain the base support hand, as in their idle and sprint layers.
                const TCHAR* Profile = (Family != 1 && FCString::Strcmp(Name, TEXT("Drum")) == 0)
                    ? TEXT("Base") : Name;
                RifleQuickCombatClips.Add(LoadObject<UAnimSequence>(nullptr,
                    *FString::Printf(TEXT("/Game/Weapons/%s/%s/A_%s_QuickCombat_%s.A_%s_QuickCombat_%s"),
                        *Folder, Profile, Weapons[Family], Profile, Weapons[Family], Profile)));
            }
        }
    }
    const int32 Family = bUseASH12 ? 3 : bUseQBZ191 ? 2 : bUsingM4Infima ? 1 : 0;
    const int32 Index = static_cast<int32>(Grip) + Family * 6;
    return RifleQuickCombatClips.IsValidIndex(Index) ? RifleQuickCombatClips[Index].Get() : nullptr;
}

bool AFPSGAMECharacter::TriggerRifleStockMelee()
{
    auto Gate=[&](const TCHAR* Reason)
    {
        UE_LOG(LogTemp,Log,TEXT("[QuickCombat] 步枪砸击被拒绝：%s"),Reason);
        return false;
    };
    // 用户 2026-09-18：取消武器类型锁——任何非手枪的枪械都可以用这记枪托砸击。
    // AKM、QBZ191、ASH-12 均使用自己的抓握源和 N 版腕臂适配 clip。
    if(IsPistolWeapon())return Gate(TEXT("当前是手枪"));
    if(!CanStartQuickCombatPriority())return Gate(TEXT("切换武器或输入不可用"));
    if(const auto* Health=FindComponentByClass<UFPSCombatHealthComponent>();Health&&Health->IsDead())return Gate(TEXT("已死亡"));
    if(!AKMViewmodel||!AKMViewmodel->GetSkeletalMeshAsset())return Gate(TEXT("视模不可用"));
    const EM4SprintGrip Grip=ResolveRifleGripProfile();
    UAnimSequence* Clip=RifleQuickCombatClip(Grip);
    if(!Clip)return Gate(TEXT("枪托砸击 clip 未加载"));
    InterruptActionsForPriority(false);
    FireReleased();
    SetAimingState(false);
    ExitSprintForWeapon();
    bFireHeld=false;bPistolShotPending=false;
    // 组件按实际 clip 长度换算时钟（作者源改节奏不需要同步改代码）。
    if(QuickCombatPistol)QuickCombatPistol->ConfigureForRifle(Clip->GetPlayLength(),true);
    const bool bStarted=QuickCombatPistol&&QuickCombatPistol->BeginAction();
    if(bStarted)
    {
        WeaponState=EAKMWeaponState::QuickCombat;
        WeaponActionStartedAt=GetWorld()->GetTimeSeconds();
        WeaponStateElapsed=0.0f;
        WeaponStateDuration=Clip->GetPlayLength();
        PlayWeaponAnimation(Clip,false);
        if(bUseASH12&&GunplayAnimation)
        {
            // The contact sampler can run on the first update after a hitch.
            // Publish this action now so it cannot evaluate an earlier fire clip.
            GunplayAnimation->ActionClip=Clip;
            GunplayAnimation->ActionTime=0.f;
            GunplayAnimation->ActionAlpha=0.f;
        }
    }
    static const TCHAR* const GripNames[]={TEXT("Base"),TEXT("Drum"),TEXT("Angled"),TEXT("Vertical"),TEXT("Canted"),TEXT("Prism")};
    const TCHAR* WeaponName=bUseASH12?TEXT("ASH12"):bUseQBZ191?TEXT("QBZ191"):bUsingM4Infima?TEXT("M4"):TEXT("AKM");
    UE_LOG(LogTemp,Log,TEXT("[QuickCombat] 步枪砸击%s 枪型=%s（clip=%s）握把=%s 总长=%.3f"),
        bStarted?TEXT("开始"):TEXT("启动失败"),WeaponName,bUsingM4Infima?TEXT("本枪"):TEXT("M4 回退"),
        GripNames[static_cast<int32>(Grip)],Clip->GetPlayLength());
    if(bStarted&&bUseASH12)
    {
        const float Contact=Clip->GetPlayLength()*QuickCombatRifleMotion::M4ReferenceContactFraction;
        UE_LOG(LogTemp,Log,TEXT("[QuickCombat] ASH12 节奏 接触=%.3f 空挥=%.3f 命中停顿=%.3f"),
            Contact/QuickCombatRifleMotion::ASH12EntryRate,
            Contact/QuickCombatRifleMotion::ASH12EntryRate+(Clip->GetPlayLength()-Contact)/QuickCombatRifleMotion::ASH12RecoveryRate,
            QuickCombatRifleMotion::ASH12HitStopSeconds);
    }
    return bStarted;
}

void AFPSGAMECharacter::RefreshMovementState()
{
    const bool bForwardIntent = MoveInput.Y > 0.5f && MoveInput.Size() > 0.7f;
    const bool bPreviouslySprinting = bIsSprinting;
    const auto* StaminaProfile=GetGameInstance()->GetSubsystem<UColdSteelStatusModel>();
    const bool Guarding=RuneSword && RuneSword->IsGuarding();
    SetAimingState(bAimHeld && !IsWeaponBusy());
    bIsSprinting = !IsMeleeSkillMovementLocked() && !Guarding && bSprintHeld && (!StaminaProfile||StaminaProfile->CanSprint()) && !IsDodging() && GetCharacterMovement()->IsMovingOnGround() && !bIsSliding && !bIsCrouched && !bIsAiming && (!IsWeaponFireHeld() || IsReloading()) && bForwardIntent;
    if (!bPreviouslySprinting && bIsSprinting) SprintStartedAt = GetWorld()->GetTimeSeconds();
    if (bPreviouslySprinting && !bIsSprinting) StartSprintToFireLock(GetWorld()->GetTimeSeconds());
    // SprintSpeed already carries the held-weapon movement multiplier, and
    // SlideEntrySpeed() scales the slide gate by that same ratio - changing one
    // without the other silently disables sliding for the affected weapons.
    GetCharacterMovement()->MaxWalkSpeed = bIsSprinting ? SprintSpeed : (bIsAiming ? ADSWalkSpeed : WalkSpeed);
    GetCharacterMovement()->MaxWalkSpeedCrouched = bIsAiming ? 220.0f * PistolMoveSpeedMultiplier : CrouchSpeed;
    // CrouchSpeed already carries the multiplier; only the aiming crouch above
    // reads the raw ratio, so keep the reason explicit for the next reader.
    if(Guarding)
    {
        GetCharacterMovement()->MaxWalkSpeed*=RuneSwordGuardTuning::MoveMultiplier;
        GetCharacterMovement()->MaxWalkSpeedCrouched*=RuneSwordGuardTuning::MoveMultiplier;
    }
}

void AFPSGAMECharacter::StartSlide()
{
    // Sliding changes locomotion only; weapon actions keep their own state/clock.
    ExitSprintForWeapon();
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
    if (IsMeleeSkillMovementLocked() || IsDodging()) return;
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
    if(IsDualWieldingPistols())
    {
        // Recover instances which entered the old, invisible single-hand
        // inspect before this fix was applied to the running editor.
        if(WeaponState==EAKMWeaponState::Inspecting)
        {
            WeaponState=EAKMWeaponState::Idle;
            WeaponStateElapsed=WeaponStateDuration=0.f;
            ActiveActionAnimation=nullptr;
        }
        return;
    }
    if(bUseASH12&&QuickCombatPistol&&WeaponState!=EAKMWeaponState::QuickCombat)
        QuickCombatPistol->Cancel();
    if (WeaponState == EAKMWeaponState::Idle) return;
    if(IsReloading())
    {
        const auto* Health=FindComponentByClass<UFPSCombatHealthComponent>();
        if(IsTraversing() || IsCastBlockingLeftHandAction() || (Health && Health->IsDead())){InterruptReload();return;}
    }
    if (WeaponState == EAKMWeaponState::QuickCombat && bUseASH12 && QuickCombatPistol)
    {
        // Pose, recovery, contact and action ownership share the source clock.
        // Real time continues during impact freeze for camera kick and movement.
        const float SinceStart=static_cast<float>(FMath::Max(0.0,GetWorld()->GetTimeSeconds()-WeaponActionStartedAt));
        QuickCombatPistol->AdvanceAction(FMath::Min(DeltaSeconds,SinceStart));
        WeaponStateElapsed=QuickCombatPistol->IsOccupyingLeftHand()
            ?QuickCombatPistol->GetActionAge():WeaponStateDuration;
        if(!QuickCombatPistol->IsOccupyingLeftHand())FinishWeaponAction();
        return;
    }
    // Input can start an action immediately before Tick. Do not charge that new
    // action for the elapsed interval which preceded the input event.
    WeaponStateElapsed = static_cast<float>(FMath::Max(0.0, GetWorld()->GetTimeSeconds() - WeaponActionStartedAt));
    if(IsReloading() && !AdvanceReloadStages())return;
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
    const FWeaponHandling FeedbackHandling=BipodDeployment?BipodDeployment->ApplyStability(WeaponHandling):WeaponHandling;
    const float FeedbackDelta = DeltaSeconds * FeedbackHandling.RecoveryRate();
    AdvanceVisualWeaponRecoil(GetWorld()->GetTimeSeconds());
    if(ClipRecoilSeconds>=0.f)ClipRecoilSeconds+=DeltaSeconds;
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
    if(IsDualWieldingPistols())bNewAiming=false;
    // A waiting cast leaves existing ADS untouched until the player releases it.
    // An active cast cannot enter ADS through input or an action-completion callback.
    if(bNewAiming && IsCastingWithLeftHand())bNewAiming=false;
    if (bIsAiming == bNewAiming) return;
    // Finish the old direction at the input/state-change time. A new transition
    // cannot consume time from before that event, including on a hitch frame.
    UpdateADSProgress();
    ADSStartProgress = ADSProgress;
    ADSStartedAt = GetWorld()->GetTimeSeconds();
    bIsAiming = bNewAiming;
    if(BipodDeployment)
    {
        if(bIsAiming)BipodDeployment->TryDeployFromADS();
        else BipodDeployment->Release();
    }
}

FTransform AFPSGAMECharacter::GetMeleeAimTransform() const
{
    FVector Eye=CameraRestLocation;
    Eye.Z=(bIsSliding || bIsCrouched)?SlidingCameraHeight:StandingCameraHeight;
    const auto* Parent=FirstPersonCamera->GetAttachParent();
    const FTransform& ParentWorld=Parent?Parent->GetComponentTransform():GetActorTransform();
    const FQuat Aim=Controller?Controller->GetControlRotation().Quaternion():GetActorQuat();
    return FTransform(Aim,ParentWorld.TransformPosition(Eye));
}

void AFPSGAMECharacter::RefreshQuickCombatCamera()
{
    UpdateCamera(0.f);
}

void AFPSGAMECharacter::UpdateCamera(float DeltaSeconds)
{
    if(BipodDeployment)BipodDeployment->RestoreCameraOffset();
    auto* ProductionTools=FindComponentByClass<UProductionToolComponent>();
    // 弓的拉距时钟与镜头同帧：先推进动作，再合成相机，抖动与释放冲量读到同一个 age。
    if(Bow)Bow->AdvanceActionBeforeCamera(DeltaSeconds);
    if(ProductionTools)ProductionTools->AdvanceActionBeforeCamera(DeltaSeconds);
    UpdateADSProgress();
    CameraADSFactor = FMath::SmoothStep(0.0f, 1.0f, ADSProgress);
    WeaponADSFactor = CameraADSFactor;
    UpdateLocomotionPresentation(DeltaSeconds);
    auto* ActionCamera = FindComponentByClass<UWeaponActionCameraComponent>();
    const auto* TacticalSprint = FindComponentByClass<UM4TacticalSprintComponent>();
    const bool bRifleSprintCamera = bInventoryWeaponReady && !IsPistolWeapon() && !IsDualWieldingPistols()
        && TacticalSprint && TacticalSprint->OwnsPose() && !bGunsmithInspection
        && !IsTraversing() && !IsCastBlockingLeftHandAction() && !IsDodging() && !bIsSliding;
    const bool bSwordSprintCamera = RuneSword && RuneSword->IsEquipped() && !RuneSword->IsBusy()
        && !IsTraversing() && !IsCastBlockingLeftHandAction() && !IsDodging() && !bIsSliding;
    const float SwordSprintWeight = bSwordSprintCamera ? RuneSword->TacticalSprintPoseWeight() : 0.f;
    const bool bRifleSprintRequested = bIsSprinting && !IsWeaponBusy() && !bAimHeld && !bFireHeld && HorizontalSpeed() > 50.f;
    if (ActionCamera)
        ActionCamera->UpdateSprint(DeltaSeconds, bRifleSprintCamera || bSwordSprintCamera,
            bSwordSprintCamera ? SwordSprintWeight > UE_SMALL_NUMBER : bRifleSprintRequested,
            M4SprintPhase, GroundLocomotionWeight * FMath::Clamp(HorizontalSpeed() / FMath::Max(SprintSpeed, 1.f), 0.f, 1.f)
                * (bSwordSprintCamera ? .65f * SwordSprintWeight : 1.f));
    // Crossfade from the ordinary walking bob into the stronger rendered view
    // offset, keeping both layers on the same footstep phase.
    const float LegacyBobWeight = ActionCamera ? 1.f - ActionCamera->SprintCameraWeight() : 1.f;
    SprintCameraFactor = FMath::Lerp(SprintCameraFactor, bIsSprinting ? 1.0f : 0.0f, 1.0f - FMath::Exp(-9.0f * DeltaSeconds));
    const bool bGrounded = GetCharacterMovement()->IsMovingOnGround();
    if (bGrounded && !bWasGrounded)
        LandingVelocity -= FMath::Clamp(-PreviousVerticalVelocity / 650.0f, 0.0f, 1.8f) * 36.0f;
    bWasGrounded = bGrounded;
    PreviousVerticalVelocity = GetVelocity().Z;
    AdvanceSpring(LandingOffset, LandingVelocity, 150.0f, 20.0f, DeltaSeconds);
    FVector TargetLocation = CameraRestLocation;
    TargetLocation.Z = (bIsSliding || bIsCrouched) ? SlidingCameraHeight : StandingCameraHeight;
    float MovementRoll = 0.0f;
    float MovementPitch = 0.0f;
    if (GroundLocomotionWeight > 0.001f)
    {
        const float Weight = 1.0f - CameraADSFactor * 0.85f;
        const float Amplitude = FMath::Lerp(1.0f, 2.4f, SprintCameraFactor) * GroundLocomotionWeight * Weight * CameraMotionScale * LegacyBobWeight;
        const float Side = FMath::Cos(CameraBobPhase);
        const float Step = FMath::Cos(CameraBobPhase * 2.0f);
        TargetLocation.Y += Side * Amplitude * .65f;
        TargetLocation.Z -= Step * Amplitude * .75f;
        MovementRoll = Side * Amplitude * .14f;
        MovementPitch = -Step * Amplitude * .08f;
    }
    MovementRoll -= LocomotionSideAlpha * .35f * (1.f - CameraADSFactor * .9f) * CameraMotionScale;
    const float DodgeWeight=DodgePresentationWeight()*CameraMotionScale;
    TargetLocation.Z-=3.f*DodgeWeight;
    if (IsDodging())
    {
        const auto* Move=CastChecked<UFPSCharacterMovementComponent>(GetCharacterMovement());
        const FVector ViewRight=FRotationMatrix(FRotator(0.f,GetViewRotation().Yaw,0.f)).GetUnitAxis(EAxis::Y);
        MovementRoll+=3.f*DodgeWeight*FVector::DotProduct(Move->GetDodgeDirection(),ViewRight);
    }
    TargetLocation.Z += LandingOffset * (1.0f - CameraADSFactor * 0.8f) * CameraMotionScale;
    const float TraumaStrength = FMath::Square(FireTrauma) * AKMSource::FeedbackScale * CameraShakeScale.GetValueOnGameThread() * CameraMotionScale * (1.0f - 0.8f * CameraADSFactor);
    const float NoiseRight = FMath::PerlinNoise1D(FeedbackTime * 11.0f) * 4.5f * TraumaStrength;
    const float NoiseUp = FMath::PerlinNoise1D(FeedbackTime * 13.0f + 91.3f) * 4.5f * TraumaStrength;
    TargetLocation += FVector(-CameraJitterPosition.Z * 100.0f, CameraJitterPosition.X * 100.0f + NoiseRight, CameraJitterPosition.Y * 100.0f + NoiseUp);
    FVector SwordCameraLocation=FVector::ZeroVector;
    FRotator SwordCameraRotation=FRotator::ZeroRotator;
    RuneSword->GetCameraMotion(SwordCameraLocation,SwordCameraRotation);
    // 手枪砸击的镜头语言（上抬随动/前捅压头/命中下压冲量）与剑版同一叠加口径。
    FVector BashCameraLocation=FVector::ZeroVector;
    FRotator BashCameraRotation=FRotator::ZeroRotator;
    if(QuickCombatPistol)QuickCombatPistol->GetCameraMotion(BashCameraLocation,BashCameraRotation);
    FVector ToolCameraLocation=FVector::ZeroVector;
    FRotator ToolCameraRotation=FRotator::ZeroRotator;
    // 拉弓的镜头语言（弓身后带、满拉呼吸抖动、撒弦回弹）与工具／剑同一叠加口径。
    FVector BowCameraLocation=FVector::ZeroVector;
    FRotator BowCameraRotation=FRotator::ZeroRotator;
    if(Bow)Bow->GetCameraMotion(BowCameraLocation,BowCameraRotation);
    if(ProductionTools)ProductionTools->GetCameraMotion(ToolCameraLocation,ToolCameraRotation);
    FVector FireMagicLocation=FVector::ZeroVector;FRotator FireMagicRotation=FRotator::ZeroRotator;
    if(const auto* FireMagic=FindComponentByClass<UFPSFireMagicComponent>())FireMagic->GetCameraMotion(FireMagicLocation,FireMagicRotation);
    const FQuat ControlAim = Controller ? Controller->GetControlRotation().Quaternion() : GetActorQuat();
    TargetLocation+=GetActorQuat().UnrotateVector(ControlAim.RotateVector(SwordCameraLocation))*CameraMotionScale;
    TargetLocation+=GetActorQuat().UnrotateVector(ControlAim.RotateVector(BashCameraLocation))*CameraMotionScale;
    TargetLocation+=GetActorQuat().UnrotateVector(ControlAim.RotateVector(BowCameraLocation))*CameraMotionScale;
    TargetLocation+=GetActorQuat().UnrotateVector(ControlAim.RotateVector(ToolCameraLocation))*CameraMotionScale;
    TargetLocation+=GetActorQuat().UnrotateVector(ControlAim.RotateVector(FireMagicLocation))*CameraMotionScale*CameraShakeScale.GetValueOnGameThread();
    // Whirlwind publishes its final action sample in PostPhysics, including
    // contact holds. Do not smooth its camera position against the previous
    // action frame while rotation and attached arms use the current frame.
    FirstPersonCamera->SetRelativeLocation((Traversal->IsCameraRecovering() || (RuneSword && RuneSword->IsWhirlwindActive()))?TargetLocation:
        FMath::Lerp(FirstPersonCamera->GetRelativeLocation(), TargetLocation, 1.0f - FMath::Exp(-18.0f * DeltaSeconds)));

    const float NoisePitch = FMath::PerlinNoise1D(FeedbackTime * 9.0f + 17.0f) * 0.03f * TraumaStrength;
    const float NoiseYaw = FMath::PerlinNoise1D(FeedbackTime * 7.0f + 55.0f) * 0.03f * TraumaStrength;
    FRotator CameraFeedback(
        MovementPitch + FMath::RadiansToDegrees(CameraKickPitch + CameraJitterRotation.X + NoisePitch),
        FMath::RadiansToDegrees(CameraKickYaw + CameraJitterRotation.Y + NoiseYaw),
        MovementRoll + FMath::RadiansToDegrees(CameraJitterRotation.Z));
    CameraFeedback+=SwordCameraRotation*CameraMotionScale;
    CameraFeedback+=BashCameraRotation*CameraMotionScale;
    CameraFeedback+=BowCameraRotation*CameraMotionScale;
    CameraFeedback+=ToolCameraRotation*CameraMotionScale;
    CameraFeedback+=FireMagicRotation*CameraMotionScale*CameraShakeScale.GetValueOnGameThread();
    FirstPersonCamera->SetWorldRotation(ControlAim * CameraFeedback.Quaternion());

    float TargetHorizontalFOV = VerticalToHorizontalFOV(FMath::Lerp(BaseVerticalFieldOfView, EffectiveADSVerticalFOV(), CameraADSFactor) + FOVPunch);
    TargetHorizontalFOV = FMath::Lerp(TargetHorizontalFOV, SprintFieldOfView, SprintCameraFactor * (1.0f - CameraADSFactor));
    FirstPersonCamera->SetFieldOfView(TargetHorizontalFOV);
    if (ActionCamera)
    {
        EM4CameraAction CameraAction = EM4CameraAction::None;
        float SourceTime = 0.f;
        float SourceEnd = 0.f;
        // Each family selects its own contact order and source-clock profile.
        const bool bPKMActionCamera = PKMLowpolyWeaponAssets::Matches(AKMViewmodel);
        const bool bActionCamera = bInventoryWeaponReady && bUsingM4Infima && (bUseM4Infima || bUseASH12 || bUseM16 || bPKMActionCamera)
            && !bUseQBZ191 && !IsPistolWeapon() && !IsDualWieldingPistols()
            && !bGunsmithInspection && !IsTraversing() && !IsCastBlockingLeftHandAction();
        if (bActionCamera && ActiveActionAnimation)
        {
            if (IsReloading())
            {
                if (bPKMActionCamera)
                    CameraAction = bPendingEmptyReload ? EM4CameraAction::PKMReloadEmpty : EM4CameraAction::PKMReload;
                else if (bUseASH12 || (bUseM16 && bPendingEmptyReload))
                    CameraAction = bPendingEmptyReload ? EM4CameraAction::Ash12ReloadEmpty : EM4CameraAction::Ash12Reload;
                else
                    CameraAction = bDrumInstalled
                    ? (bPendingEmptyReload ? EM4CameraAction::DrumReloadEmpty : EM4CameraAction::DrumReload)
                    : (bPendingEmptyReload ? EM4CameraAction::ReloadEmpty : EM4CameraAction::Reload);
                SourceTime = ReloadSourceTime(WeaponStateElapsed);
                SourceEnd = ReloadSourceTime(WeaponStateDuration);
            }
            else if (WeaponState == EAKMWeaponState::Equipping && ActiveActionAnimation == EquipAnimation)
            {
                CameraAction = bPKMActionCamera ? EM4CameraAction::PKMEquip : EM4CameraAction::EquipCharge;
                SourceTime = ActionStartPosition + WeaponStateElapsed * ActionPlayRate;
                SourceEnd = ActiveActionAnimation->GetPlayLength();
            }
        }
        float ActionCameraWeight = CameraMotionScale * (1.f - CameraADSFactor);
        if (bUseM16 && CameraAction == EM4CameraAction::Ash12ReloadEmpty && MechanicalCueTimes.Num() > 4)
        {
            // Reuse the existing five-contact pull/release camera profile with
            // a lighter M16 charging tail; magazine contacts keep their weight.
            const float PullTime = MechanicalCueTimes[3], ReleaseTime = MechanicalCueTimes[4];
            const float ChargeBlend = FMath::SmoothStep(PullTime - .20f, PullTime, SourceTime)
                * (1.f - FMath::SmoothStep(FMath::Min(ReleaseTime + .22f, SourceEnd - .02f), SourceEnd, SourceTime));
            ActionCameraWeight *= FMath::Lerp(1.f, .45f, ChargeBlend);
        }
        ActionCamera->Apply(*FirstPersonCamera, CameraAction, SourceTime, SourceEnd,
            MechanicalCueTimes, ActionCameraWeight);
    }
}

FRotator AFPSGAMECharacter::GetViewmodelBaseRotation() const
{
    // P9 is authored toward Blender -Y and imports toward UE +Y.
    // Its camera basis is the opposite of the existing rifle assets (-Y).
    return IsPistolWeapon() ? FRotator(0.f, -90.f, 0.f) : ViewmodelRotation;
}

void AFPSGAMECharacter::UpdateViewmodel(float DeltaSeconds)
{
    if(IsDualWieldingPistols()){DualPistols->Advance(DeltaSeconds);return;}
    const float BipodMotion=BipodDeployment?BipodDeployment->MotionMultiplier():1.f;
    const float BipodRecoil=BipodDeployment?BipodDeployment->RecoilMultiplier():1.f;
    UpdateADSPose();
    // Reload/inspection need room for the support hand. Equip is performed at
    // this weapon's hip anchor and must not visit the centered action framing.
    const bool bUseActionFraming = bUsingM4Infima && !IsPistolWeapon() && !IsTraversing() && IsWeaponBusy() && WeaponState != EAKMWeaponState::Equipping;
    float ActionFramingTarget = bUseActionFraming ? 1.0f : 0.0f;
    if(!QuickCombatPistol||!QuickCombatPistol->IsImpactPaused())
        M4ActionFramingAlpha = FMath::Lerp(M4ActionFramingAlpha, ActionFramingTarget,
            1.0f - FMath::Exp(-16.0f * DeltaSeconds));
    if (WeaponState == EAKMWeaponState::QuickCombat)
    {
        // Reach the hip anchor inside the clip's recovery. Filtering this tail
        // would leave a second component-space correction after the pose ends.
        M4ActionFramingAlpha = FMath::Min(M4ActionFramingAlpha,
            QuickCombatRecovery::RemainingWeight(WeaponStateElapsed, WeaponStateDuration,
                QuickCombatRecovery::FramingReturnStart));
    }
    else if ((bUseM16 || SVDWeaponAssets::Matches(AKMViewmodel)) && IsReloading() && ActiveActionAnimation)
    {
        // The M16 pose already ends at idle. Return the component anchor in
        // that same authored tail, rather than starting a filtered correction
        // after FinishReload. Empty reload keeps its charging-handle contact
        // through source frame 143; normal reload recovers from frame 108.
        const float ReturnSeconds = SVDWeaponAssets::Matches(AKMViewmodel) ? .45f : WeaponState == EAKMWeaponState::ReloadingEmpty
            ? 19.f / 60.f : 18.f / 60.f;
        const float RemainingSourceSeconds = ActiveActionAnimation->GetPlayLength()
            - ReloadSourceTime(WeaponStateElapsed);
        M4ActionFramingAlpha = FMath::Min(M4ActionFramingAlpha,
            FMath::Clamp(RemainingSourceSeconds / ReturnSeconds, 0.f, 1.f));
    }
    else if (QuickCombatPistol && QuickCombatPistol->IsOccupyingLeftHand())
    {
        // The component can finish its tick after the weapon state. Its final
        // busy frame must not restart action framing after the handoff.
        M4ActionFramingAlpha = 0.f;
    }
    const float SpeedM = HorizontalSpeed() / 100.0f;
    const bool bPistol = IsPistolWeapon();
    WeaponBobTime += DeltaSeconds * (5.0f + SpeedM * 0.85f);
    const float SprintSpeedAlpha = FMath::Clamp((HorizontalSpeed() - 50.0f) / FMath::Max(SprintSpeed - 50.0f, 1.0f), 0.0f, 1.0f);
    const bool bPistolActionTransition = IsWeaponBusy() || bIsAiming || bFireHeld
        || IsTraversing() || IsDodging() || (bPistol && IsCastBlockingLeftHandAction());
    const float SprintTarget = bIsSprinting && !IsWeaponBusy() && !(bPistol && bPistolActionTransition)
        ? ((bUsingM4Infima || bPistol) ? SprintSpeedAlpha : 1.0f) : 0.0f;
    const float SprintBlendRate = bPistol
        ? (bPistolActionTransition ? 28.f : (SprintTarget < SprintPoseFactor ? 12.f : 8.f))
        : (bUsingM4Infima && SprintTarget < SprintPoseFactor ? 24.0f : 12.0f);
    SprintPoseFactor = FMath::Lerp(SprintPoseFactor, SprintTarget, 1.0f - FMath::Exp(-SprintBlendRate * DeltaSeconds));
    UpdatePistolLocomotion(DeltaSeconds);
    auto* TacticalSprint = FindComponentByClass<UM4TacticalSprintComponent>();
    if (TacticalSprint)
    {
        // 与枪托砸击共用同一解析口径，避免两处各写一份判定。
        const EM4SprintGrip Grip = ResolveRifleGripProfile();
        const bool bReady = bInventoryWeaponReady && !bPistol;
        const bool bRequest = bIsSprinting && !IsWeaponBusy() && !bAimHeld && !bFireHeld
            && !IsTraversing() && !IsDodging() && !bIsSliding && !IsCastBlockingLeftHandAction()
            && !bGunsmithInspection && HorizontalSpeed() > 50.f;
        TacticalSprint->Advance(DeltaSeconds, bReady, bRequest, Grip, M4SprintPhase, GroundLocomotionWeight,
            bAimHeld || bFireHeld || IsWeaponBusy());
    }
    const bool bAuthoredRifleSprint = TacticalSprint && TacticalSprint->OwnsPose();
    FVector BobTarget = FVector::ZeroVector;
    FVector BobRotationTarget = FVector::ZeroVector;
    if (bPistol)
    {
        // Authored stride and pistol breathing replace the unrelated legacy bob clock.
    }
    else
    {
        const float Amplitude = ((bUsingM4Infima || bAuthoredRifleSprint) ? .7f * (1.f - (bAuthoredRifleSprint ? TacticalSprint->PoseProgress() : SprintPoseFactor))
            : FMath::Lerp(.7f, 1.15f, SprintPoseFactor)) * GroundLocomotionWeight
            * RifleLocomotionWeight * RifleLocomotionScale;
        const float Side = FMath::Cos(CameraBobPhase);
        const float Step = FMath::Cos(2.f * CameraBobPhase);
        BobTarget = FVector(Side * .010f, -Step * .008f, FMath::Sin(2.f * CameraBobPhase) * .002f) * Amplitude;
        BobRotationTarget = FVector(FMath::Sin(2.f * CameraBobPhase) * .004f, 0.f, Side * .007f) * Amplitude;
        BobTarget.Y += FMath::Sin(WeaponBobTime * .5f) * .0015f * (1.f - GroundLocomotionWeight)
            * RifleLocomotionWeight * RifleLocomotionScale;
    }
    WeaponBobPosition = FMath::Lerp(WeaponBobPosition, BobTarget, 1.0f - FMath::Exp(-14.0f * DeltaSeconds));
    WeaponBobRotation = FMath::Lerp(WeaponBobRotation, BobRotationTarget, 1.0f - FMath::Exp(-14.0f * DeltaSeconds));
    const FVector2D LookRate = (LookInput / FMath::Max(DeltaSeconds, 0.001f) / 60.0f).GetClampedToMaxSize(8.0f);
    WeaponSwayPosition = FMath::Lerp(WeaponSwayPosition, FVector(LookRate.X * 0.0006f, LookRate.Y * 0.0006f, 0.0f), 1.0f - FMath::Exp(-10.0f * DeltaSeconds));
    WeaponSwayRotation = FMath::Lerp(WeaponSwayRotation, FVector(LookRate.Y * 0.002f, LookRate.X * 0.003f, 0.0f), 1.0f - FMath::Exp(-10.0f * DeltaSeconds));

    // Fire clip compensation. A weapon whose fire animation carries no gun
    // motion reads the reference punch here instead, so both present the same
    // recoil. It is added after the spring clamps: it stands in for authored
    // animation motion and must not be flattened by a spring limit.
    const auto RecoilProfile=FPSVisualRecoil::ForWeapon(IsPistolWeapon(),bUseDanWesson715,bUseQBZ191,bUseM4Infima || bUseM16);
    // A negative multiplier flips the whole compensation, which is how the
    // direction of the added motion is checked in game without a rebuild.
    const float ClipWave=FPSVisualRecoil::ClipWave(ClipRecoilSeconds)*ClipRecoilScale.GetValueOnGameThread()*BipodRecoil;
    const FVector ClipPosition=RecoilProfile.ClipPosition*ClipWave;
    const FVector ClipRotation=RecoilProfile.ClipRotation*ClipWave;
    const FVector ClipADSPosition=RecoilProfile.ClipADSPosition*ClipWave;
    const FVector ClipADSRotation=RecoilProfile.ClipADSRotation*ClipWave;
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
    const float LegacySprint = (bUsingM4Infima || bPistol || bAuthoredRifleSprint) ? 0.0f : SprintPoseFactor;
    const float SprintSide = FMath::Cos(M4SprintPhase);
    const float SprintStep = FMath::Cos(2.0f * M4SprintPhase);
    const float RifleSprintAlpha = FMath::SmoothStep(0.f, 1.f, SprintPoseFactor);
    const FVector SprintOffset = bPistol ? PistolLocomotionOffset : bUsingM4Infima && !bAuthoredRifleSprint
        ? (M4SprintOffset + FVector(0.25f * SprintStep, M4SprintSwayCM * SprintSide, -0.45f * SprintStep) * GroundLocomotionWeight) * RifleSprintAlpha
            + M4SprintMidpointOffset * (4.f * RifleSprintAlpha * (1.f - RifleSprintAlpha))
        : FVector::ZeroVector;
    const FVector GodotPose = HipOffset + (WeaponBobPosition + WeaponSwayPosition + FVector(0.0f, -0.10f * LegacySprint, 0.0f)) * Suppress * BipodMotion + ClipPosition;
    const FVector UEHipPose(-GodotPose.Z * 100.0f, GodotPose.X * 100.0f, GodotPose.Y * 100.0f);
    const float ScopeWeight=GetScopePresentationAlpha();
    const float ScopeConvergence=FMath::Lerp(1.f,FMath::Clamp(
        FMath::Tan(FMath::DegreesToRadians(EffectiveADSVerticalFOV()*.5f)) /
        FMath::Max(.01f,FMath::Tan(FMath::DegreesToRadians(ADSVerticalFieldOfView*.5f))),.22f,1.f),ScopeWeight);
    // The clip compensation is added at its measured scale, not through the
    // spring conversions: it stands in for authored animation motion, and a
    // matched rearward push is what keeps the sights on the eye line.
    const float RecoilDistance = FMath::Clamp(GunKickPosition.Z * AKMSource::ADSAxialScale + ClipADSPosition.Z, -0.01f, 0.055f);
    FVector2D Lateral(GunKickPosition.X * AKMSource::ADSHorizontalScale + GunJitterPosition.X + ClipADSPosition.X, GunKickPosition.Y + GunJitterPosition.Y + ClipADSPosition.Y);
    Lateral = Lateral.GetClampedToMaxSize(0.012f) * ScopeConvergence;
    const FVector UEADSRecoil(-RecoilDistance * 100.0f, Lateral.X * 18.0f, Lateral.Y * 18.0f);
    FHitResult WallHit;
    const FVector Eye = FirstPersonCamera->GetComponentLocation();
    FCollisionQueryParams WallParams(SCENE_QUERY_STAT(GunplayNearWall), false, this);
    const bool bNearWall = GetWorld()->LineTraceSingleByChannel(WallHit, Eye, Eye + FirstPersonCamera->GetForwardVector() * 80.0f, ECC_Visibility, WallParams);
    const float WallTarget = bNearWall ? (1.0f - FMath::Clamp((WallHit.Distance - 25.0f) / 55.0f, 0.0f, 1.0f))
        * (1.f-(BipodDeployment?BipodDeployment->GetDeploymentBlend():0.f)) : 0.0f;
    NearWallAlpha = FMath::Lerp(NearWallAlpha, WallTarget, 1.0f - FMath::Exp(-12.0f * DeltaSeconds));
    const FVector ADSTarget = bSightCalibrated ? CalibratedADSLocation : ADSViewmodelLocation;
    // Standard magazine and drum share the same camera-space framing.
    const FVector HipLocation = HipViewmodelLocation;
    const FVector ActionLocation = M4ActionViewmodelLocation;
    const FVector HipFraming = bUsingM4Infima
        ? FMath::Lerp(HipLocation, ActionLocation, M4ActionFramingAlpha)
        : HipLocation;
    FVector TargetLocation = FMath::Lerp(HipFraming + UEHipPose + SprintOffset, ADSTarget + UEADSRecoil, WeaponADSFactor);
    const float RifleMotionWeight = bPistol ? 0.f : RifleLocomotionWeight * Suppress * Suppress * BipodMotion;
    TargetLocation += RifleInertiaOffset * RifleMotionWeight;
    TargetLocation += FVector(-NearWallAlpha * 12.0f, 0.0f, LandingOffset * 0.35f * (1.0f - WeaponADSFactor));

    FVector ADSKickAngles = GunKickRotation + GunJitterRotation + FVector(GunFlip, 0.0f, 0.0f);
    ADSKickAngles.Y = GunKickRotation.Y * AKMSource::ADSHorizontalScale + GunJitterRotation.Y;
    // The clip compensation rides outside the spring clamp: it stands in for
    // authored animation motion, so it must not be flattened by a spring limit.
    // Unlike the springs it keeps its measured scale (no VisualRecoilScale): the
    // reference aimed clip is nearly rotation free, and scaling it down here
    // would break the sight line it is meant to preserve. ADSRotationScale keeps
    // long iron sight radii (AKM: 38.7 cm) from swinging the post out of the notch.
    ADSKickAngles = ADSKickAngles.GetClampedToMaxSize(0.025f) * VisualRecoilScale * RecoilProfile.ADSRotationScale * ScopeConvergence
        + ClipADSRotation * ScopeConvergence;
    const FVector GodotAngles = HipAngles + (WeaponBobRotation + WeaponSwayRotation + FVector(0.39f * LegacySprint, 0.0f, 0.0f)) * Suppress * BipodMotion + ClipRotation;
    const FRotator BaseRotation = GetViewmodelBaseRotation();
    const FRotator HipRotation(BaseRotation.Pitch + FMath::RadiansToDegrees(GodotAngles.X), BaseRotation.Yaw - FMath::RadiansToDegrees(GodotAngles.Y), BaseRotation.Roll - FMath::RadiansToDegrees(GodotAngles.Z));
    // Premultiply in camera space: adding pitch to a mesh already yawed 90 degrees
    // rotates about the wrong axis and fails to raise the muzzle.
    const FRotator SprintAngles = M4SprintRotation + FRotator(-0.8f * SprintStep, 2.3f * SprintSide, 1.6f * FMath::Sin(M4SprintPhase)) * GroundLocomotionWeight;
    const FQuat SprintRotation = bPistol ? PistolLocomotionRotation.Quaternion() : bUsingM4Infima && !bAuthoredRifleSprint
        ? FQuat::Slerp(FQuat::Identity, SprintAngles.Quaternion(), RifleSprintAlpha)
        : FQuat::Identity;
    const FQuat ADSBase = bSightCalibrated ? CalibratedADSRotation : (IsPistolWeapon() ? BaseRotation : ADSViewmodelRotation).Quaternion();
    const FQuat ADSRotation = FRotator(FMath::RadiansToDegrees(ADSKickAngles.X), -FMath::RadiansToDegrees(ADSKickAngles.Y), -FMath::RadiansToDegrees(ADSKickAngles.Z)).Quaternion() * ADSBase;
    TargetLocation+=FVector(-2.f,0.f,-6.f)*DodgePresentationWeight();
    AKMViewmodel->SetRelativeLocation(TargetLocation);
    const FQuat InertiaRotation = FRotator(RifleInertiaAngles.X, RifleInertiaAngles.Y, RifleInertiaAngles.Z).Quaternion();
    AKMViewmodel->SetRelativeRotation(FQuat::Slerp(FQuat::Identity, InertiaRotation, RifleMotionWeight)
        * FQuat::Slerp(SprintRotation * HipRotation.Quaternion(), ADSRotation, WeaponADSFactor));
    // The gunsmith side view uses the actual equipped assembly and its attachments.
    if(bGunsmithInspection)
    {
        AKMViewmodel->SetRelativeLocation(FVector(42.f,-2.f,6.f));
        AKMViewmodel->SetRelativeRotation(FRotator(0.f,20.f,0.f));
    }
}

void AFPSGAMECharacter::ServiceHeldFire()
{
    if(IsDualWieldingPistols())return;
    if (!bFireHeld || (UsesSingleShotTrigger() && !bPistolShotPending)) return;
    const double Now = GetWorld()->GetTimeSeconds();
    if (IsWeaponBusy() || bIsSprinting || (bUseM16 && IsCastBlockingLeftHandAction()))
    {
        if (bUseM16) FireReleased();
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
        if (UsesSingleShotTrigger()) break;
        if (IsWeaponBusy() || bIsSprinting || !bFireHeld
            || NextAllowedShotTime <= PreviousDeadline) break;
    }
    if (bFireHeld && !IsWeaponBusy() && !bIsSprinting && Now + 1.e-6 >= NextAllowedShotTime)
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
    if(IsDualWieldingPistols())return;
    if(BipodDeployment && BipodDeployment->BlocksFire())return;
    if (!bInventoryWeaponReady) return;
    if (bUseM16 && BurstShotsRemaining <= 0) return;
    const float WeaponAudioGain = bUseQBZ191 ? 1.0f : 2.0f;
    const double Now = GetWorld()->GetTimeSeconds();
    if (IsWeaponBusy() || bIsSprinting || Now < SprintFireUnlockTime || Now + 1.e-6 < NextAllowedShotTime) return;
    if(NeedsReloadCycle()){ReloadPressed();return;}
    if (MagazineAmmo <= 0)
    {
        if (HasInfiniteReserveAmmo() || ReserveAmmo > 0) ReloadPressed();
        else { FireReleased(); PlaySound2D(DryClickSound, 0.501187f * WeaponAudioGain); }
        return;
    }
    --MagazineAmmo;
    if(MagazineAmmo==0 && IsCastBlockingLeftHandAction())bReloadAfterCasting=true;
    if (UsesSingleShotTrigger()) bPistolShotPending = false;
    ++ShotsFired;
    UAISense_Hearing::ReportNoiseEvent(this,GetActorLocation(),1.f,this,IsMuzzleSuppressed()?500.f:1800.f,TEXT("Gunshot"));
    LastShotWorldTime = Now; // Actual execution time, not a backdated cadence deadline.
    if (TriggerFirstShotWorldTime < 0.0) TriggerFirstShotWorldTime = Now;
    NextAllowedShotTime += FMath::Max(0.001, static_cast<double>(FireInterval));
    if (bUseM16 && (--BurstShotsRemaining == 0 || MagazineAmmo == 0))
    {
        BurstShotsRemaining=0;
        bFireHeld=false;
        NextAllowedShotTime=FMath::Max(NextAllowedShotTime,Now+BurstRecoverySeconds);
    }
    // Snapshot visible aim before restarting the mechanical action or adding recoil.
    const FVector TraceStart = FirstPersonCamera->GetComponentLocation();
    const FVector TraceDirection = ComputeShotDirection();
    const FVector Muzzle = GetEffectiveMuzzleLocation() + GetEffectiveMuzzleForward().GetSafeNormal() * 2.f; // 2 cm clearance beyond the current attachment exit, before animation.
    UAnimSequence* Animation = bIsAiming ? AimFireAnimation : FireAnimation;
    if (bUseM1911 && MagazineAmmo == 0)
        Animation = bIsAiming ? PistolAimFireLastAnimation : PistolFireLastAnimation;
    // PKM advances one belt pitch per shot. Complete the authored cycle before
    // the next shot even when the effective fire interval is shortened.
    float ShotAnimationRate = 1.0f;
    if (Animation && ActiveInventoryWeaponDefinition == PKMLowpolyWeaponAssets::Definition)
        ShotAnimationRate = FMath::Max(1.0f, Animation->GetPlayLength() / FMath::Max(0.01f, FireInterval));
    PlayWeaponAnimation(Animation, false, ShotAnimationRate);
    GetWorldTimerManager().ClearTimer(WeaponPoseTimerHandle);
    USoundBase* ShotSound=IsMuzzleSuppressed()&&SuppressedFireSound?SuppressedFireSound.Get():FireSound.Get();
    const auto& RifleVariants = IsMuzzleSuppressed() ? RifleSuppressedVariants : RifleFireVariants;
    // PKM raises bUsingM4Infima too, but it must not inherit the M4's
    // stop-and-restart voice: a 650 RPM machine gun needs its previous one-shot
    // to keep ringing under the next one. Only the M4 keeps that dedicated
    // component (the muzzle-migration audit reads it by name).
    const bool bUsesDedicatedM4Voice = bUsingM4Infima
        && ActiveInventoryWeaponDefinition != PKMLowpolyWeaponAssets::Definition;
    if (!RifleVariants.IsEmpty())
    {
        int32 Variant = FMath::RandRange(0, RifleVariants.Num() - 1);
        if (RifleVariants.Num() > 1 && Variant == LastRifleFireVariant)
            Variant = (Variant + FMath::RandRange(1, RifleVariants.Num() - 1)) % RifleVariants.Num();
        LastRifleFireVariant = Variant;
        // Overlapping short recording tails survive the next shot; concurrency bounds burst buildup.
        UGameplayStatics::PlaySound2D(this, RifleVariants[Variant], AKMSource::FireVolume * WeaponAudioGain,
            bUseQBZ191 ? FMath::FRandRange(0.992f, 1.008f) : 1.0f, 0.0f, RifleFireConcurrency, this);
    }
    else if (bUsesDedicatedM4Voice && M4FireVoice && ShotSound)
    {
        // Match Godot's single AudioStreamPlayer: restart each shot at original pitch.
        M4FireVoice->Stop();
        M4FireVoice->SetSound(ShotSound);
        M4FireVoice->SetVolumeMultiplier(AKMSource::FireVolume * (IsPistolWeapon() ? 1.5f : 1.0f) * WeaponAudioGain);
        M4FireVoice->SetPitchMultiplier(1.0f);
        M4FireVoice->Play();
    }
    else PlayFireVoice(ShotSound, AKMSource::FireVolume * (IsPistolWeapon() ? 1.5f : 1.0f) * WeaponAudioGain);

    const float ShotDamage=DamagePerShot;
    const auto Training=ColdSteelSkills::Snapshot(this,nullptr,true);
    const auto Effects=ColdSteelCombat::Snapshot(this);
    FHitResult Hit;
    FCollisionQueryParams Params(SCENE_QUERY_STAT(AKMFire), true, this);
    Params.bReturnPhysicalMaterial = true;
    Params.bReturnFaceIndex = true; // Reuse the hit triangle for cosmetic surface selection; no extra trace.
    FHitResult AimHit;
    const bool bAimHit = GetWorld()->LineTraceSingleByChannel(AimHit, TraceStart, TraceStart + TraceDirection * TraceDistance, ECC_Visibility, Params);
    const FVector AimTarget = bAimHit ? AimHit.ImpactPoint : TraceStart + TraceDirection * TraceDistance;
    // A muzzle beyond a wall must not damage targets through it, even if the camera can see them.
    bool bHit = GetWorld()->LineTraceSingleByChannel(Hit, TraceStart, Muzzle, ECC_Visibility, Params);
    bLastShotMuzzleBlocked = bHit;
    if (!bHit)
    {
        if(ProjectileSpeedCM>0)Ballistics->Launch(Muzzle,(AimTarget-Muzzle).GetSafeNormal(),ProjectileSpeedCM,TraceDistance,DamagePerShot,WeaponFX,CriticalHitSound,EffectiveWeaponRangeCM);
        else
        {
            bHit=GetWorld()->LineTraceSingleByChannel(Hit,Muzzle,AimTarget+TraceDirection*2.f,ECC_Visibility,Params);
            WeaponFX->OnTracerSegment(Muzzle,bHit?Hit.ImpactPoint:AimTarget);
        }
    }
    if (bHit && Hit.GetActor())
    {
        const float HitDamage=ShotDamage*WeaponDamageFalloff::Multiplier(FVector::Distance(Muzzle,Hit.ImpactPoint),EffectiveWeaponRangeCM);
        FWeaponDamageResult DamageResult;
        const float Applied=ColdSteelSkills::ApplyHit(this,Hit,HitDamage,TraceDirection,Training,&DamageResult);
        NotifyConfirmedWeaponHit(Hit.GetActor(),Applied,&DamageResult,true);
        ColdSteelCombat::OnHit(Hit.GetActor(),this,Effects.Poison);
        if(!bLastShotMuzzleBlocked&&ProjectileSpeedCM<=0){
            FHitResult NextHit=Hit;int32 Remaining=Effects.Piercing;
            while(Remaining-->0&&Cast<APawn>(NextHit.GetActor())){
                Params.AddIgnoredActor(NextHit.GetActor());
                if(!GetWorld()->LineTraceSingleByChannel(NextHit,Muzzle,TraceStart+TraceDirection*TraceDistance,ECC_Visibility,Params))break;
                const float NextDamage=ShotDamage*WeaponDamageFalloff::Multiplier(FVector::Distance(Muzzle,NextHit.ImpactPoint),EffectiveWeaponRangeCM);
                if(NextHit.GetActor())
                {
                    FWeaponDamageResult NextResult;
                    const float NextApplied=ColdSteelSkills::ApplyHit(this,NextHit,NextDamage,TraceDirection,Training,&NextResult);
                    NotifyConfirmedWeaponHit(NextHit.GetActor(),NextApplied,&NextResult,true);
                }
                ColdSteelCombat::OnHit(NextHit.GetActor(),this,Effects.Poison);WeaponFX->OnImpact(NextHit);
            }
        }
        if (ColdSteelSkills::IsCriticalHit(Hit))
            PlaySound2D(CriticalHitSound, AKMSource::ActionVolume);
    }
    WeaponFX->OnShot(bIsAiming);
    if (bHit) WeaponFX->OnImpact(Hit);
    ApplyShotFeedback();
    if(!bIsAiming)CurrentSpread = FMath::Min(0.018f, CurrentSpread + 0.003f);
}

void AFPSGAMECharacter::ApplyShotFeedback()
{
    const float BipodRecoil=BipodDeployment?BipodDeployment->RecoilMultiplier():1.f;
    const FWeaponHandling FeedbackHandling=BipodDeployment?BipodDeployment->ApplyStability(WeaponHandling):WeaponHandling;
    const double VisualNow=GetWorld()->GetTimeSeconds();
    AdvanceVisualWeaponRecoil(VisualNow);
    const double BurstReset=FMath::Clamp(static_cast<double>(FireInterval)*2.5,.25,.45);
    VisualBurstIndex=VisualNow-LastVisualShotAt>BurstReset?0:FMath::Min(VisualBurstIndex+1,8);
    LastVisualShotAt=VisualNow;
    ClipRecoilSeconds=0.f;
    VisualRecoverAt=VisualNow+FMath::Clamp(static_cast<double>(FireInterval)*.8,.065,.12);
    const auto VisualProfile=FPSVisualRecoil::ForWeapon(IsPistolWeapon(),bUseDanWesson715,bUseQBZ191,bUseM4Infima || bUseM16);
    const float CameraShake=FMath::Max(0.f,CameraShakeScale.GetValueOnGameThread());
    // A defined first pulse followed by smaller settled pulses, rather than
    // increasing random tumbling as the automatic burst continues.
    const float BurstGain=VisualBurstIndex==0?1.12f:FMath::Lerp(1.f,.86f,VisualBurstIndex/8.f);
    const int32 PatternCount = FWeaponHandling::PatternCount;
    const FVector2D Pattern = FWeaponHandling::Pattern(RecoilPatternIndex);
    if(RecoilPatternIndex==0)ADSHorizontalRecoilIndex=0;
    const float HorizontalDegrees=bIsAiming?WeaponHandling.ADSHorizontalDegrees(ADSHorizontalRecoilIndex)
        :FMath::RadiansToDegrees(Pattern.Y)*BallisticRecoilScale;
    if (Controller)
    {
        FRotator Aim = Controller->GetControlRotation();
        Aim.Pitch = FMath::Clamp(FRotator::NormalizeAxis(Aim.Pitch) + FMath::RadiansToDegrees(Pattern.X) * BallisticRecoilScale * BipodRecoil, -85.0f, 85.0f);
        Aim.Yaw += HorizontalDegrees * BipodRecoil;
        Controller->SetControlRotation(Aim);
    }
    RecoilPatternIndex = FMath::Min(RecoilPatternIndex + 1, PatternCount - 1);
    if(bIsAiming)ADSHorizontalRecoilIndex=(ADSHorizontalRecoilIndex+1)%FWeaponHandling::PatternCount;
    TimeSinceLastShot = 0.0f;
    PatternRecoveryAccumulator = 0.0f;
    const float Horizontal = FMath::Clamp(Pattern.Y / 0.003f + FMath::FRandRange(-0.35f, 0.35f), -1.0f, 1.0f);
    const float RecoilLoad = (1.0f + FMath::Clamp((CurrentSpread + MoveSpread + AirSpread) / 0.024f, 0.0f, 2.0f) * 0.7f) * BipodRecoil;
    GunKickPositionVelocity += FVector(-Horizontal * 0.24f, FMath::FRandRange(0.04f, 0.10f), FMath::FRandRange(0.55f, 0.85f)) * VisualProfile.Position * AKMSource::ViewmodelGain * RecoilLoad * WeaponHandling.RecoilScale * BurstGain;
    GunKickRotationVelocity += FVector(FMath::FRandRange(0.55f, 1.0f), Horizontal * 0.50f, FMath::FRandRange(-0.7f, 0.7f)) * VisualProfile.Rotation * AKMSource::ViewmodelGain * RecoilLoad * WeaponHandling.RecoilScale * BurstGain;
    // Godot's ADS convergence is applied once to the common gun/camera pulse.
    // Aim progress already eases continuously through both ADS transitions.
    const float JitterScale = RecoilLoad * FeedbackHandling.ShakeScale
        * FMath::Lerp(1.f, FWeaponHandling::ADSJitterMultiplier, WeaponADSFactor);
    const FVector PositionImpulse = FVector(FMath::FRandRange(-0.7f, 0.7f), FMath::FRandRange(-0.7f, 0.7f), FMath::FRandRange(-0.7f, 0.7f)) * JitterScale;
    const FVector RotationImpulse = FVector(FMath::FRandRange(-2.2f, 2.2f), FMath::FRandRange(-2.2f, 2.2f), FMath::FRandRange(-2.2f, 2.2f)) * JitterScale;
    GunJitterPositionVelocity += PositionImpulse * VisualProfile.Jitter;
    GunJitterRotationVelocity += RotationImpulse * VisualProfile.Jitter;
    GunFlipVelocity += 1.5f * RecoilLoad * WeaponHandling.RecoilScale * VisualProfile.Flip * BurstGain;
    CameraJitterPositionVelocity += PositionImpulse * 0.11f * AKMSource::FeedbackScale * CameraShake;
    CameraJitterRotationVelocity += RotationImpulse * 0.34f * AKMSource::FeedbackScale * CameraShake;
    const float ImpulseScale = FMath::Lerp(13.0f, 19.0f, WeaponADSFactor) * VisualRecoilScale * FeedbackHandling.ShakeScale * CameraShake * BipodRecoil;
    CameraKickPitchVelocity += (Pattern.X + FMath::FRandRange(-0.0012f, 0.0012f)) * ImpulseScale * AKMSource::FeedbackScale;
    CameraKickYawVelocity += (Pattern.Y + FMath::FRandRange(-0.0008f, 0.0008f)) * ImpulseScale * AKMSource::FeedbackScale;
    FOVPunch = FMath::Lerp(1.2f, 0.4f, WeaponADSFactor) * CameraShake * BipodRecoil;
    // Trauma is squared when rendered: sqrt keeps a single-shot amplitude linear,
    // and the gain below is what makes a burst build up before the crosshair.
    FireTrauma = FMath::Min(1.0f, FireTrauma + 0.11f * RecoilLoad * FMath::Sqrt(FeedbackHandling.ShakeScale));
}

// Dual wield fires two independent triggers into one camera. The per-hand
// control-rotation pattern already lives in UPistolDualWieldComponent, so this
// adds the layers the single-weapon path receives from ApplyShotFeedback(): one
// viewmodel spring set per hand plus the shared camera kick, jitter, trauma and
// FOV punch. Presentation only - ballistics, cadence and damage are untouched.
void AFPSGAMECharacter::ApplyDualWieldShotFeedback(int32 HandIndex, bool bRevolver, const FWeaponHandling& Handling,
    int32 ShotIndex, float Interval, float RecoilLoad)
{
    auto& R=DualRecoil[FMath::Clamp(HandIndex,0,1)];
    const double Now=GetWorld()->GetTimeSeconds();
    const auto Profile=FPSVisualRecoil::ForWeapon(true,bRevolver,false,false);
    const auto Dual=FPSVisualRecoil::ForDualWield(bRevolver);
    const float CameraShake=FMath::Max(0.f,CameraShakeScale.GetValueOnGameThread());
    // A defined first pulse then smaller settled pulses, exactly like the single
    // rig; the dual hand keeps its own burst clock instead of the rifle's.
    const float BurstGain=ShotIndex<=0?1.12f:FMath::Lerp(1.f,.86f,FMath::Min(ShotIndex,8)/8.f);
    R.RecoverAt=Now+static_cast<double>(FMath::Clamp(Interval*.8f,.065f,.12f));
    R.UpdatedAt=Now;
    const FVector2D Pattern=FWeaponHandling::Pattern(ShotIndex);
    const float Horizontal=FMath::Clamp(Pattern.Y/0.003f+FMath::FRandRange(-0.35f,0.35f),-1.0f,1.0f);
    const float HandGain=Dual.HandGain*RecoilLoad*Handling.RecoilScale*BurstGain;
    R.PositionVelocity+=FVector(-Horizontal*0.24f,FMath::FRandRange(0.04f,0.10f),FMath::FRandRange(0.55f,0.85f))
        *Profile.Position*AKMSource::ViewmodelGain*HandGain;
    R.RotationVelocity+=FVector(FMath::FRandRange(0.55f,1.0f),Horizontal*0.50f,FMath::FRandRange(-0.7f,0.7f))
        *Profile.Rotation*AKMSource::ViewmodelGain*HandGain;
    R.FlipVelocity+=1.5f*HandGain*Profile.Flip;
    const float JitterScale=RecoilLoad*Handling.ShakeScale*Dual.HandGain;
    const FVector PositionImpulse=FVector(FMath::FRandRange(-0.7f,0.7f),FMath::FRandRange(-0.7f,0.7f),FMath::FRandRange(-0.7f,0.7f))*JitterScale;
    const FVector RotationImpulse=FVector(FMath::FRandRange(-2.2f,2.2f),FMath::FRandRange(-2.2f,2.2f),FMath::FRandRange(-2.2f,2.2f))*JitterScale;
    R.JitterPositionVelocity+=PositionImpulse*Profile.Jitter;
    R.JitterRotationVelocity+=RotationImpulse*Profile.Jitter;
    // Shared camera layers. Dual pistols never aim down sights, so only the hip
    // weighting of the single rig applies.
    CameraJitterPositionVelocity+=PositionImpulse*0.11f*AKMSource::FeedbackScale*CameraShake;
    CameraJitterRotationVelocity+=RotationImpulse*0.34f*AKMSource::FeedbackScale*CameraShake;
    const float CameraGain=Dual.CameraGain*Handling.ShakeScale;
    const float ImpulseScale=FMath::Lerp(13.0f,19.0f,0.0f)*VisualRecoilScale*CameraGain*CameraShake;
    CameraKickPitchVelocity+=(Pattern.X+FMath::FRandRange(-0.0012f,0.0012f))*ImpulseScale*AKMSource::FeedbackScale;
    CameraKickYawVelocity+=(Pattern.Y+FMath::FRandRange(-0.0008f,0.0008f))*ImpulseScale*AKMSource::FeedbackScale;
    FOVPunch=FMath::Max(FOVPunch,1.2f*Dual.CameraGain*CameraShake);
    FireTrauma=FMath::Min(1.0f,FireTrauma+0.11f*RecoilLoad*FMath::Sqrt(Handling.ShakeScale)*Dual.CameraGain);
}

void AFPSGAMECharacter::AdvanceDualWieldHandRecoil(int32 HandIndex, bool bRevolver, const FWeaponHandling& Handling, float DeltaSeconds)
{
    auto& R=DualRecoil[FMath::Clamp(HandIndex,0,1)];
    const double Now=GetWorld()->GetTimeSeconds();
    const double Previous=R.UpdatedAt<0.?Now:R.UpdatedAt;
    R.UpdatedAt=Now;
    const float Elapsed=FMath::Max(0.f,static_cast<float>(Now-Previous));
    if(Elapsed<=0.f)return;
    const auto Profile=FPSVisualRecoil::ForWeapon(true,bRevolver,false,false);
    // Same event-boundary split as the single rig: the impulse shares use the
    // attack damping, the remainder recovers. No frame integrates twice.
    const float Attack=FMath::Clamp(static_cast<float>(R.RecoverAt-Previous),0.f,Elapsed);
    auto Integrate=[&](float Seconds,bool Recovering)
    {
        if(Seconds<=0.f)return;
        const float Dt=Seconds*Handling.RecoveryRate();
        const float PositionDamping=Recovering?1.94f*FMath::Sqrt(Profile.PositionStiffness):Profile.PositionDamping;
        const float RotationDamping=Recovering?1.94f*FMath::Sqrt(Profile.RotationStiffness):Profile.RotationDamping;
        AdvanceSpring(R.Position,R.PositionVelocity,Profile.PositionStiffness,PositionDamping,Dt);
        AdvanceSpring(R.Rotation,R.RotationVelocity,Profile.RotationStiffness,RotationDamping,Dt);
        AdvanceSpring(R.Flip,R.FlipVelocity,Profile.RotationStiffness,RotationDamping,Dt);
        AdvanceSpring(R.JitterPosition,R.JitterPositionVelocity,7000.f,Recovering?70.f:54.f,Dt);
        AdvanceSpring(R.JitterRotation,R.JitterRotationVelocity,7000.f,Recovering?70.f:54.f,Dt);
    };
    Integrate(Attack,false);
    Integrate(Elapsed-Attack,true);
}

void AFPSGAMECharacter::GetDualWieldHandRecoil(int32 HandIndex, FVector& OutOffset, FVector& OutAngles) const
{
    const auto& R=DualRecoil[FMath::Clamp(HandIndex,0,1)];
    // Identical camera-space conversion and clamps to the single-pistol hip rig
    // below, so a dual hand and a lone pistol share one recoil language.
    FVector Offset(R.Position.X,R.Position.Y*0.4f,R.Position.Z*AKMSource::HipAxialScale);
    Offset+=R.JitterPosition*0.35f;
    Offset.X=0.018f*FMath::Tanh(Offset.X/0.018f);
    Offset.Y=0.008f*FMath::Tanh(Offset.Y/0.008f);
    Offset.Z=0.065f*FMath::Tanh(Offset.Z/0.065f);
    FVector Angles(R.Rotation.X*0.45f+R.Flip*0.18f,R.Rotation.Y,R.Rotation.Z*0.6f);
    Angles+=R.JitterRotation*0.35f;
    Angles.X=0.045f*FMath::Tanh(Angles.X/0.045f);
    Angles.Y=0.030f*FMath::Tanh(Angles.Y/0.030f);
    Angles.Z=0.025f*FMath::Tanh(Angles.Z/0.025f);
    OutOffset=Offset;OutAngles=Angles;
}

float AFPSGAMECharacter::GetHipSpread() const
{
    // Dual pistols never aim down sights, so there is no ADS tightening to fall
    // back on: the reticle carries the whole cone, including each hand's own
    // bloom, averaged across both guns. Ballistics stay where they were - the dual
    // component still owns the shot direction and pattern.
    if(IsDualWieldingPistols()&&DualPistols)return DualPistols->SharedConeSpread();
    return 2.f*(0.0175f+CurrentSpread+MoveSpread+AirSpread)*HipSpreadMultiplier
        *(BipodDeployment?BipodDeployment->SpreadMultiplier():1.f);
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

FVector AFPSGAMECharacter::ComputeShotDirection() const
{
    const bool bPreciseAim = bIsAiming || WeaponADSFactor > 0.98f;
    // The optical overlay is camera-centered, including recoil feedback.
    if (bPreciseAim && GetScopePresentationAlpha() > .5f)
        return FirstPersonCamera->GetForwardVector();
    if (bHolographicOptic && bPreciseAim)
        return (HolographicAimPoint() - FirstPersonCamera->GetComponentLocation()).GetSafeNormal();
    const FVector Forward = FirstPersonCamera->GetForwardVector();
    if (bPreciseAim && AKMSoviet::Matches(AKMViewmodel))
        return (AKMViewmodel->GetSocketTransform(TEXT("WPN_root")).TransformPosition(AKMSoviet::Front) - FirstPersonCamera->GetComponentLocation()).GetSafeNormal();
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
    if (bUseM1911)
    {
        const auto* Profile = GetGameInstance() ? GetGameInstance()->GetSubsystem<UColdSteelStatusModel>() : nullptr;
        const auto* Item = Profile ? Profile->Equipped() : nullptr;
        EquipAnimation = LoadAKMAnimation(Item && Item->Magazine == 0 ? TEXT("A_AKM_equip_charge_empty") : TEXT("A_AKM_equip_charge"));
    }
    StopMechanicalAudio();
    // Switching can interrupt ADS, reload or sprint. Their cached presentation
    // offsets belong to the previous weapon, not the new equip animation.
    SetAimingState(false);
    FirstPersonCamera->ClearAdditiveOffset();
    if (auto* ActionCamera = FindComponentByClass<UWeaponActionCameraComponent>()) ActionCamera->ResetSprint();
    ADSProgress = ADSStartProgress = CameraADSFactor = WeaponADSFactor = 0.0f;
    ADSStartedAt = GetWorld()->GetTimeSeconds();
    M4ActionFramingAlpha = SprintPoseFactor = 0.0f;
    if (auto* Sprint = FindComponentByClass<UM4TacticalSprintComponent>()) Sprint->Reset();
    ResetPistolLocomotion();
    ResetRifleLocomotion();
    WeaponBobPosition = WeaponBobRotation = FVector::ZeroVector;
    AKMViewmodel->SetRelativeLocation(HipViewmodelLocation);
    AKMViewmodel->SetRelativeRotation(GetViewmodelBaseRotation());
    if (GunplayAnimation)
    {
        GunplayAnimation->AimAlpha = 0.0f;
        GunplayAnimation->ActionAlpha = 0.0f;
        GunplayAnimation->SprintAlpha = 0.0f;
    }
    WeaponState = EAKMWeaponState::Equipping;
    WeaponActionStartedAt = GetWorld()->GetTimeSeconds();
    if (IsPistolWeapon()) NextAllowedShotTime = WeaponActionStartedAt;
    WeaponStateElapsed = 0.0f;
    MechanicalCueTimes.Reset(); MechanicalCueSounds.Reset(); NextMechanicalCue = 0;
    const bool bAKMChargeOnly = !bUsingM4Infima && EquipAnimation && (EquipAnimation->GetPathName().Contains(TEXT("/AKMIntegration/EquipCharge/")) || A762WeaponAssets::Matches(AKMViewmodel));
    if (bAKMChargeOnly)
    {
        MechanicalCueTimes = {0.55f, 0.80f};
        MechanicalCueSounds = {ChargePullSound, ChargeReleaseSound};
        UE_LOG(LogTemp, Display, TEXT("AKM_EQUIP_CHARGE: clip=%s magazine=attached left=idle duration=%.3f"), *EquipAnimation->GetPathName(), EquipAnimation->GetPlayLength());
    }
    else if (SVDWeaponAssets::Matches(AKMViewmodel))
    {
        MechanicalCueTimes={SVDWeaponAssets::EquipPull,SVDWeaponAssets::EquipRelease};
        MechanicalCueSounds={ChargePullSound,ChargeReleaseSound};
    }
    else if (IsPistolWeapon())
    {
        // Original P9 Unholster: no slide pull occurs in the equip donor.
        MechanicalCueTimes.Reset();
        MechanicalCueSounds.Reset();
    }
    else if (bUseQBZ191)
    {
        // Equip audio uses the same 38-frame source mapped to the .72s action.
        MechanicalCueTimes = {16.f / 38.f * .72f, 25.f / 38.f * .72f};
        MechanicalCueSounds = {ChargePullSound, ChargeReleaseSound};
    }
    else PlayMechanicalSound(EquipSound, AKMSource::ActionVolume);
    if (EquipAnimation)
    {
        // PKM's video-authored raise/catch/settle uses its own clip clock.
        WeaponStateDuration = bUsingM4Infima && !IsPistolWeapon() && !SVDWeaponAssets::Matches(AKMViewmodel)
            && !PKMLowpolyWeaponAssets::Matches(AKMViewmodel) ? 0.72f : EquipAnimation->GetPlayLength();
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
    PendingAmmoType.Reset();PendingAmmoWeapon.Reset();
    bReloadAmmoCommitted=bReloadCycleOnly=false;ReloadResumeElapsed=0.f;
    const bool bFinishedQuickCombat = WeaponState == EAKMWeaponState::QuickCombat;
    const bool bFinishedM16Reload = (bUseM16 || SVDWeaponAssets::Matches(AKMViewmodel)) && IsReloading();
    const double CompletedAt = bFinishedQuickCombat && bUseASH12
        ? GetWorld()->GetTimeSeconds() : WeaponActionStartedAt + WeaponStateDuration;
    // Only the eligible tail after completion can catch up. Keep a newer input
    // deadline or another active blocker rather than rewinding it to completion.
    NextAllowedShotTime = FMath::Max(NextAllowedShotTime, CompletedAt);
    WeaponState = EAKMWeaponState::Idle;
    if (bFireHeld) ExitSprintForWeapon(CompletedAt);
    WeaponStateElapsed = WeaponStateDuration = 0.0f;
    if (IsPistolWeapon() || bFinishedQuickCombat || bFinishedM16Reload)
    {
        ActiveActionAnimation = nullptr;
        ActionElapsed = ActionDuration = 0.f;
        if (GunplayAnimation) GunplayAnimation->ActionAlpha = 0.f;
    }
    if (bFinishedQuickCombat || bFinishedM16Reload) M4ActionFramingAlpha = 0.f;
    MechanicalCueTimes.Reset(); MechanicalCueSounds.Reset(); NextMechanicalCue = 0;
    SetAimingState(bAimHeld);
    ResumeWeaponPose();
}

void AFPSGAMECharacter::FinishReload()
{
    // Ammunition was committed at insertion. The tail only returns the pose.
    RecoilPatternIndex = 0;
    bPendingEmptyReload = false;
    FinishWeaponAction();
}

bool AFPSGAMECharacter::HasInfiniteReserveAmmo() const
{
    const auto* Model=GetGameInstance()?GetGameInstance()->GetSubsystem<UColdSteelStatusModel>():nullptr;
    return HasInfiniteReserveAmmoFor(Model?Model->AmmoDefinition():FString());
}
bool AFPSGAMECharacter::HasInfiniteReserveAmmoFor(const FString& AmmoType) const
{
    if(const auto* Model=GetGameInstance()?GetGameInstance()->GetSubsystem<UColdSteelStatusModel>():nullptr)
        if(const auto* Type=Model->AmmoType(AmmoType);Type&&!Type->AllowInfiniteReserve)return false;
    if (const auto* Tuning = UDevelopmentTuningSubsystem::Find(this))
        return Tuning->IsEnabled(EDevelopmentTuningOption::InfiniteReserveAmmo);
    // Retain the original range default if no game-instance subsystem exists.
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
        ActionBlendIn = (Animation == FireAnimation || Animation == AimFireAnimation || Animation == PistolFireLastAnimation || Animation == PistolAimFireLastAnimation) ? 0.008f : 0.035f;
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

void AFPSGAMECharacter::PlayFireVoice(USoundBase* Sound, float Volume, float PitchMultiplier)
{
    if (!Sound || FireVoices.Num() < 2) return;
    // Pick a voice that is not still sounding. With three rotating slots and the
    // shortest catalog fire interval, a reused slot has always finished, so the
    // incoming fade starts from silence and can never chop a live tail.
    int32 Chosen = INDEX_NONE;
    for (int32 Offset = 0; Offset < FireVoices.Num(); ++Offset)
    {
        const int32 Index = 1 + (NextFireVoice - 1 + Offset) % (FireVoices.Num() - 1);
        UAudioComponent* Candidate = FireVoices.IsValidIndex(Index) ? FireVoices[Index].Get() : nullptr;
        if (Candidate && !Candidate->IsPlaying()) { Chosen = Index; break; }
    }
    if (Chosen == INDEX_NONE)
    {
        // Sustained fire faster than the pool: retire the oldest slot gracefully
        // instead of hard-cutting it, then take it.
        Chosen = 1 + (NextFireVoice - 1) % (FireVoices.Num() - 1);
        if (UAudioComponent* Oldest = FireVoices.IsValidIndex(Chosen) ? FireVoices[Chosen].Get() : nullptr)
            Oldest->FadeOut(AKMSource::FireVoiceFadeSeconds, 0.f, EAudioFaderCurve::Sin);
    }
    // Advance past the slot just taken so the next shot starts its search from
    // the following one.
    NextFireVoice = 1 + (Chosen - 1 + 1) % (FireVoices.Num() - 1);
    UAudioComponent* Voice = FireVoices[Chosen];
    if (!Voice) return;
    Voice->SetSound(Sound);
    Voice->SetVolumeMultiplier(Volume);
    Voice->SetPitchMultiplier(PitchMultiplier);
    Voice->FadeIn(AKMSource::FireVoiceFadeSeconds, 1.f, 0.f, EAudioFaderCurve::Logarithmic);
}

void AFPSGAMECharacter::PlayMechanicalSound(USoundBase* Sound, float Volume, float StartTime)
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
    Voice->SetSound(Sound);
    Voice->SetVolumeMultiplier(Volume * (bUseQBZ191 ? 1.0f : 2.0f));
    Voice->SetPitchMultiplier(1.0f);
    // Retriggering a mechanical cue (fast tap-fire, re-entry after a stall) used
    // to Stop() at full amplitude, which clicks. FadeIn starts from silence.
    Voice->FadeIn(AKMSource::MechanicalVoiceFadeSeconds, 1.f, StartTime, EAudioFaderCurve::Logarithmic);
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
    if(ActiveInventoryWeaponDefinition==SVDWeaponAssets::Definition)
    {
        FString Clip(AssetName);Clip.RemoveFromStart(TEXT("A_AKM_"));
        if(Clip.StartsWith(TEXT("equip")))Clip=TEXT("equip");
        return LoadObject<UAnimSequence>(nullptr,*SVDWeaponAssets::AnimationPath(*Clip));
    }
    if (ActiveInventoryWeaponDefinition==PKMLowpolyWeaponAssets::Definition)
    {
        FString Clip(AssetName);Clip.RemoveFromStart(TEXT("A_AKM_"));
        if (Clip.StartsWith(TEXT("equip"))) Clip=TEXT("equip");
        return LoadObject<UAnimSequence>(nullptr,*PKMLowpolyWeaponAssets::AnimationPath(*Clip));
    }
    if (ActiveInventoryWeaponDefinition == A762WeaponAssets::Definition)
    {
        FString Clip(AssetName);Clip.RemoveFromStart(TEXT("A_AKM_"));
        if (Clip.StartsWith(TEXT("equip"))) Clip=TEXT("equip");
        return LoadObject<UAnimSequence>(nullptr,*A762WeaponAssets::AnimationPath(*Clip));
    }
    if (bUseM16)
    {
        FString Clip(AssetName); Clip.RemoveFromStart(TEXT("A_AKM_"));
        if (Clip == TEXT("equip")) Clip = TEXT("equip_charge");
        return LoadObject<UAnimSequence>(nullptr, *M16WeaponAssets::AnimationPath(*Clip));
    }
    if (bUseDanWesson715)
    {
        FString Clip(AssetName); Clip.RemoveFromStart(TEXT("A_AKM_"));
        if (Clip == TEXT("equip") || Clip == TEXT("equip_charge_empty")) Clip = TEXT("equip_charge");
        return LoadObject<UAnimSequence>(nullptr, *DanWesson715WeaponAssets::AnimationPath(*Clip));
    }
    if (bUseM1911)
    {
        FString Clip(AssetName); Clip.RemoveFromStart(TEXT("A_AKM_"));
        if (Clip == TEXT("equip")) Clip = TEXT("equip_charge");
        return LoadObject<UAnimSequence>(nullptr, *M1911WeaponAssets::AnimationPath(*Clip));
    }
    if (bUseQBZ191)
    {
        FString Clip(AssetName); Clip.RemoveFromStart(TEXT("A_AKM_"));
        if (Clip == TEXT("equip")) Clip = TEXT("equip_charge");
        const TCHAR* Revision=(Clip.Contains(TEXT("reload")) || Clip==TEXT("equip_charge"))?TEXT("Attachments20260913"):TEXT("Refined20260913");
        return LoadObject<UAnimSequence>(nullptr, *FString::Printf(TEXT("/Game/Weapons/QBZ191/%s/Animations/base/A_QBZ191_%s.A_QBZ191_%s"), Revision, *Clip, *Clip));
    }
    if (bUseASH12)
    {
        FString Clip(AssetName); Clip.RemoveFromStart(TEXT("A_AKM_"));
        if (Clip == TEXT("equip")) Clip = TEXT("equip_charge");
        return LoadObject<UAnimSequence>(nullptr, *ASH12WeaponAssets::AnimationPath(*Clip));
    }
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
    FString Folder = bUsingM4Infima ? TEXT("M4ContactImpactFinal") : (AKMViewmodel->GetSkeletalMeshAsset() && AKMViewmodel->GetSkeletalMeshAsset()->GetName()==TEXT("SK_AKM_MannyNative") ? TEXT("AKMIntegration/Native") : (bUsingReplacement ? TEXT("AKMReplacement") : TEXT("AKM")));
    if (!bUsingM4Infima && AKMViewmodel->GetSkeletalMeshAsset() && (AKMViewmodel->GetSkeletalMeshAsset()->GetPathName().Contains(TEXT("/AKMIntegration/SourceMatched/")) || AKMViewmodel->GetSkeletalMeshAsset()->GetPathName().Contains(TEXT("/AKMIntegration/WalnutFab/")) || AKMViewmodel->GetSkeletalMeshAsset()->GetPathName().Contains(TEXT("/AKMIntegration/SovietFab/"))))
        Folder = TEXT("AKMIntegration/SourceMatched");
    const bool bCurledReload = bUsingM4Infima && (FCString::Strcmp(AssetName, TEXT("A_AKM_reload")) == 0
        || FCString::Strcmp(AssetName, TEXT("A_AKM_reload_empty")) == 0);
    if (bCurledReload) Folder += TEXT("/ReloadFinger");
    if (!bUsingM4Infima && Folder == TEXT("AKMIntegration/SourceMatched") && FCString::Strcmp(AssetName, TEXT("A_AKM_equip")) == 0)
        Folder = TEXT("AKMIntegration/EquipCharge");
    const FString Path = FString::Printf(TEXT("/Game/Weapons/%s/%s.%s"), *Folder, AssetName, AssetName);
    UAnimSequence* Animation = LoadObject<UAnimSequence>(nullptr, *Path);
    if (bCurledReload && Animation) UE_LOG(LogTemp, Display, TEXT("M4_RELOAD_FINGER_ACTIVE %s"), *Path);
    return Animation;
}

USoundBase* AFPSGAMECharacter::LoadAKMSound(const TCHAR* AssetName)
{
    if(SVDWeaponAssets::Matches(AKMViewmodel))
    {
        if(FCString::Strcmp(AssetName,TEXT("S_AKM_Fire"))==0)
            return LoadObject<USoundBase>(nullptr,*SVDWeaponAssets::FireSoundPath(1));
        if(FCString::Strcmp(AssetName,TEXT("S_AKM_MagOut"))==0 ||
           FCString::Strcmp(AssetName,TEXT("S_AKM_MagInsert"))==0 ||
           FCString::Strcmp(AssetName,TEXT("S_AKM_MagSeat"))==0 ||
           FCString::Strcmp(AssetName,TEXT("S_AKM_ChargePull"))==0 ||
           FCString::Strcmp(AssetName,TEXT("S_AKM_ChargeRelease"))==0)
        {
            FString Cue(AssetName);
            Cue.RemoveFromStart(TEXT("S_AKM_"));
            return LoadObject<USoundBase>(nullptr,*SVDWeaponAssets::MechanicalSoundPath(*Cue));
        }
        return LoadObject<USoundBase>(nullptr,*FString::Printf(TEXT("/Game/Weapons/AKM/Audio/%s.%s"),AssetName,AssetName));
    }
    if (PKMLowpolyWeaponAssets::Matches(AKMViewmodel))
        return LoadObject<USoundBase>(nullptr,*FString::Printf(TEXT("/Game/Weapons/AKM/Audio/%s.%s"),AssetName,AssetName));
    // These rifles reuse the current AKM video cues and original fallbacks.
    if ((AKMSoviet::Matches(AKMViewmodel) || A762WeaponAssets::Matches(AKMViewmodel)) &&
        (FCString::Strcmp(AssetName, TEXT("S_AKM_Fire")) == 0 ||
         FCString::Strcmp(AssetName, TEXT("S_AKM_MagOut")) == 0 ||
         FCString::Strcmp(AssetName, TEXT("S_AKM_MagInsert")) == 0 ||
         FCString::Strcmp(AssetName, TEXT("S_AKM_MagSeat")) == 0 ||
         FCString::Strcmp(AssetName, TEXT("S_AKM_ChargePull")) == 0 ||
         FCString::Strcmp(AssetName, TEXT("S_AKM_ChargeRelease")) == 0))
    {
        const FString VideoPath = FString::Printf(TEXT("/Game/Weapons/AKM/VideoAudio20260921/%s.%s"), AssetName, AssetName);
        if (USoundBase* VideoSound = LoadObject<USoundBase>(nullptr, *VideoPath))
            return VideoSound;
    }
    if (bUseM16 && FCString::Strcmp(AssetName, TEXT("S_AKM_Fire")) == 0)
        return LoadObject<USoundBase>(nullptr, M16WeaponAssets::FireSoundPath);
    if (bUseASH12 && FCString::Strcmp(AssetName, TEXT("S_AKM_Fire")) == 0)
        return LoadObject<USoundBase>(nullptr, ASH12WeaponAssets::FireSoundPath);
    if (bUseDanWesson715 && FCString::Strcmp(AssetName, TEXT("S_AKM_CriticalHit")) != 0)
    {
        FString Cue(AssetName); Cue.RemoveFromStart(TEXT("S_AKM_"));
        return LoadObject<USoundBase>(nullptr, *DanWesson715WeaponAssets::SoundPath(Cue));
    }
    if (bUseM1911 && FCString::Strcmp(AssetName, TEXT("S_AKM_Fire")) == 0)
        return LoadObject<USoundBase>(nullptr, TEXT("/Game/Weapons/M1911/Integrated20260913/Audio/S_M1911_Fire.S_M1911_Fire"));
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
bool AFPSGAMECharacter::IsLeftHandBusyForCast() const
{
    if(IsDualWieldingPistols() && DualPistols->LeftBusy())return true;
    if(IsTraversing() || WeaponState!=EAKMWeaponState::Idle || bAimHeld || bIsAiming || ADSProgress>UE_KINDA_SMALL_NUMBER)return true;
    if(RuneSword && RuneSword->IsBusy())return true;
    const auto* Tools=FindComponentByClass<UProductionToolComponent>();
    return Tools && Tools->IsBusy();
}
bool AFPSGAMECharacter::IsCastingWithLeftHand() const
{
    const auto* Magic=FindComponentByClass<UFPSFireballComponent>();
    const auto* Bash=FindComponentByClass<UFPSQuickCombatComponent>();
    return (Magic && Magic->IsOccupyingLeftHand())||(Bash&&Bash->IsOccupyingLeftHand());
}
bool AFPSGAMECharacter::IsLeftHandHeldForCast() const { return IsDualWieldingPistols(); }
void AFPSGAMECharacter::SuspendWeaponForMenu()
{
    if(BipodDeployment)BipodDeployment->Release(true);
    CancelAmmoSelection();
    InterruptReload();
    if(IsDualWieldingPistols())DualPistols->InterruptReloads();
    FireReleased();AimReleased();
    // A menu owns the keyboard from here on, so the preview's key release will never arrive.
    if(auto* Fireball=FindComponentByClass<UFPSFireballComponent>())Fireball->SetAimPreview(false);
    if(auto* Ice=FindComponentByClass<UFPSIceSpikeComponent>())Ice->SetAimPreview(false);
    if(auto* Lightning=FindComponentByClass<UFPSLightningComponent>())Lightning->Cancel();
    if(auto* HolyLight=FindComponentByClass<UFPSHolyLightComponent>())HolyLight->Cancel();
    if(auto* FireMagic=FindComponentByClass<UFPSFireMagicComponent>())FireMagic->CancelPending();
}
bool AFPSGAMECharacter::IsCastBlockingLeftHandAction() const
{
    const auto* Magic=FindComponentByClass<UFPSFireballComponent>();
    const auto* Ice=FindComponentByClass<UFPSIceSpikeComponent>();
    const auto* Lightning=FindComponentByClass<UFPSLightningComponent>();
    const auto* HolyLight=FindComponentByClass<UFPSHolyLightComponent>();
    if(const auto* FireMagic=FindComponentByClass<UFPSFireMagicComponent>();FireMagic&&FireMagic->HasQueuedAction())return true;
    const auto* Bash=FindComponentByClass<UFPSQuickCombatComponent>();
    return (Magic && Magic->BlocksNewLeftHandAction())||(Ice&&Ice->HasQueuedAction())||(Lightning&&Lightning->HasQueuedAction())||(HolyLight&&HolyLight->HasQueuedAction())||(Bash&&Bash->IsOccupyingLeftHand());
}
void AFPSGAMECharacter::ServiceReloadAfterCasting()
{
    if(!bReloadAfterCasting)return;
    if(!bInventoryWeaponReady || (MagazineAmmo>0 && !NeedsReloadCycle())){bReloadAfterCasting=false;return;}
    if(IsCastBlockingLeftHandAction() || IsWeaponBusy())return;
    if(const auto* H=FindComponentByClass<UFPSCombatHealthComponent>();H&&H->IsDead()){bReloadAfterCasting=false;return;}
    bReloadAfterCasting=false;
    ReloadPressed();
}
bool AFPSGAMECharacter::IsRevolverFireActionPlaying() const
{
    return bUseDanWesson715 && ActiveActionAnimation
        && (ActiveActionAnimation == FireAnimation || ActiveActionAnimation == AimFireAnimation)
        && GetWorld()->GetTimeSeconds() < LastShotWorldTime + ActionDuration;
}
void AFPSGAMECharacter::ServiceRevolverReloadAfterFire()
{
    if (!bRevolverReloadAfterFire) return;
    if (!bInventoryWeaponReady || !bUseDanWesson715 || MagazineAmmo >= MagazineCapacity
        || (!HasInfiniteReserveAmmo() && ReserveAmmo <= 0))
    {
        bRevolverReloadAfterFire = false;
        return;
    }
    if (const auto* Health = FindComponentByClass<UFPSCombatHealthComponent>(); Health && Health->IsDead())
    {
        bRevolverReloadAfterFire = false;
        return;
    }
    if (IsRevolverFireActionPlaying() || IsWeaponBusy() || IsCastBlockingLeftHandAction()) return;
    bRevolverReloadAfterFire = false;
    ReloadPressed();
}
bool AFPSGAMECharacter::IsDualWieldingPistols() const { return DualPistols && DualPistols->IsActive(); }
bool AFPSGAMECharacter::IsWeaponFireHeld() const { return IsDualWieldingPistols()?DualPistols->HasHeldTrigger():bFireHeld; }
bool AFPSGAMECharacter::IsReloading() const { return IsDualWieldingPistols()?DualPistols->IsReloading():WeaponState == EAKMWeaponState::Reloading || WeaponState == EAKMWeaponState::ReloadingEmpty; }
bool AFPSGAMECharacter::IsWeaponBusy() const { return IsTraversing() || (RuneSword && RuneSword->IsBusy()) || (IsDualWieldingPistols()?DualPistols->IsReloading():WeaponState != EAKMWeaponState::Idle) || (QuickCombatPistol && QuickCombatPistol->IsOccupyingLeftHand()); }
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
    float Scale = FMath::Lerp(1.0f, Ratio * ADSMouseSensitivity, CameraADSFactor);
    // Voxel building snaps to 20 cm cells, so full FPS sensitivity overshoots the cell the player is
    // aiming at. Scale the look down while build mode is active; tune live with the console variable.
    if (const auto* PC = Cast<APlayerController>(Controller))
    {
        if (const auto* Builder = PC->FindComponentByClass<UVoxelBuildComponent>())
        {
            if (Builder->IsBuilding()) Scale *= FMath::Clamp(BuildLookSensitivity.GetValueOnGameThread(), .05f, 1.f);
        }
    }
    return Scale;
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
    if (AKMSoviet::Matches(AKMViewmodel))
    {
        FTransform Root = FTransform::Identity;
        for (int32 Index=Ref.FindBoneIndex(TEXT("WPN_root")); Index!=INDEX_NONE; Index=Ref.GetParentIndex(Index))
        {
            FTransform Local;
            AimAnimation->GetBoneTransform(Local,FSkeletonPoseBoneIndex(Index),FAnimExtractContext(0.0,false),false);
            Root=Root*Local;
        }
        Rear=Root.TransformPosition(AKMSoviet::Rear)*ViewmodelScale;
        Front=Root.TransformPosition(AKMSoviet::Front)*ViewmodelScale;
    }
    if (SVDWeaponAssets::Matches(AKMViewmodel))
    {
        // The SVD aims down the PSO-1 tube, and its sights are not at the shared M4 sight
        // bone positions, so the weapon supplies its own pair (like AKMSoviet above).
        FTransform Root = FTransform::Identity;
        for (int32 Index=Ref.FindBoneIndex(TEXT("WPN_root")); Index!=INDEX_NONE; Index=Ref.GetParentIndex(Index))
        {
            FTransform Local;
            AimAnimation->GetBoneTransform(Local,FSkeletonPoseBoneIndex(Index),FAnimExtractContext(0.0,false),false);
            Root=Root*Local;
        }
        // SVD clips carry their measured ocular/objective marker positions.
        SightUp=Root.GetRotation().RotateVector(FVector::UpVector);
    }
    if (bHolographicOptic)
    {
        FTransform Root = FTransform::Identity;
        const FName OpticBone=HolographicOptic?HolographicOptic->GetAttachSocketName():FName(TEXT("WPN_root"));
        for (int32 Index=Ref.FindBoneIndex(OpticBone); Index!=INDEX_NONE; Index=Ref.GetParentIndex(Index))
        {
            FTransform Local;
            AimAnimation->GetBoneTransform(Local,FSkeletonPoseBoneIndex(Index),FAnimExtractContext(0.0,false),false);
            Root=Root*Local;
        }
        const FTransform Mount=HolographicMount*Root;
        Rear=Mount.TransformPosition(OpticLocalAimPoint())*ViewmodelScale;
        Front=Rear+Mount.GetRotation().RotateVector(AKMSoviet::Matches(AKMViewmodel)&&OpticVariant==TEXT("holographic")?FVector::RightVector:FVector::ForwardVector)*10.f;
        SightUp=Mount.GetRotation().RotateVector(FVector::UpVector);
    }
    const FVector Axis = (Front - Rear).GetSafeNormal();
    if (Axis.IsNearlyZero() || Rear.ContainsNaN() || Front.ContainsNaN()) return;
    const FQuat Base = GetViewmodelBaseRotation().Quaternion();
    CalibratedADSRotation = FQuat::FindBetweenNormals(Base.RotateVector(Axis), FVector::ForwardVector) * Base;
    // Mapping a single axis leaves roll unconstrained. Align the complete optic
    // frame with camera forward/up so ADS is level without twisting it off the rail.
    if (IsPistolWeapon() && !bHolographicOptic)
    {
        FTransform Root = FTransform::Identity;
        for (int32 Index=Ref.FindBoneIndex(TEXT("WPN_root")); Index!=INDEX_NONE; Index=Ref.GetParentIndex(Index))
        {
            FTransform Local;
            AimAnimation->GetBoneTransform(Local,FSkeletonPoseBoneIndex(Index),FAnimExtractContext(0.0,false),false);
            Root=Root*Local;
        }
        SightUp=Root.GetRotation().RotateVector(FVector::UpVector);
    }
    if(bHolographicOptic || IsPistolWeapon() || SVDWeaponAssets::Matches(AKMViewmodel))CalibratedADSRotation=FRotationMatrix::MakeFromXZ(Axis,SightUp).ToQuat().Inverse();
    const float EyeDistance = bHolographicOptic && !IsPistolWeapon() ? (OpticVariant==TEXT("lpvo_1_6x")?28.f:(GetOpticMagnification()>1.f?20.f:26.f)) : ADSRearEyeDistance;
    CalibratedADSLocation = FVector(EyeDistance, 0.0f, 0.0f) - CalibratedADSRotation.RotateVector(Rear);
    bSightCalibrated = true;
    UE_LOG(LogTemp, Display, TEXT("GUNPLAY_ADS_CALIBRATED rear=%s front=%s offset=%s rotation=%s"), *Rear.ToCompactString(), *Front.ToCompactString(), *CalibratedADSLocation.ToCompactString(), *CalibratedADSRotation.Rotator().ToCompactString());
}

float AFPSGAMECharacter::ReloadSourceTime(float RuntimeTime) const
{
    if (bUsingM4Infima)
    {
        const UAnimSequence* Clip = ActiveActionAnimation;
        float Phase=FMath::Clamp(RuntimeTime / FMath::Max(WeaponStateDuration, 0.01f), 0.0f, 1.0f);
        if(bDrumInstalled&&!bUseQBZ191&&!bUseM16)return M4DrumReloadTiming::SourceSeconds(Phase,bPendingEmptyReload);
        return Phase*(Clip ? Clip->GetPlayLength() : 0.0f);
    }
    const float Length = ActiveActionAnimation ? ActiveActionAnimation->GetPlayLength()
        : (bPendingEmptyReload ? 4.291667f : 3.333333f);
    // AKM contact shaping is already authored into the clips. Stat changes
    // adjust the speed of the entire clip, including its return to the grip.
    const float Fraction = FMath::Clamp(RuntimeTime / FMath::Max(WeaponStateDuration, 0.01f), 0.0f, 1.0f);
    return Fraction * Length;
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
    const bool bSourceCueClock = bUsingM4Infima && IsReloading();
    const float ScheduledTime = bSourceCueClock ? ReloadRuntimeTime(MechanicalCueTimes[CueIndex]) : MechanicalCueTimes[CueIndex];
    const float Lateness = FMath::Max(0.0f, WeaponStateElapsed - ScheduledTime);
    const bool bPKMReload = PKMLowpolyWeaponAssets::Matches(AKMViewmodel) && IsReloading();
    const int32 BoltReleaseCueIndex = bPKMReload ? (bPendingEmptyReload ? 8 : INDEX_NONE)
        : bUsingM4Infima && !bUseASH12 && !bUseM16 ? 3 : 4;
    const bool bM16ChargeRelease = bUseM16 && bPendingEmptyReload && IsReloading() && CueIndex == BoltReleaseCueIndex;
    // Do not emit an obsolete burst of old contacts after a long game-thread stall.
    const float ContactVolume = AKMSource::ActionVolume * (bM16ChargeRelease ? .90f :
        ((bUsingM4Infima && !bUseDanWesson715 && bPendingEmptyReload && CueIndex == BoltReleaseCueIndex) ? 1.25f : 1.0f));
    // A short clip is still relevant until the next contact (or action end).
    // Using clip duration here dropped the seat click on a 170 ms render hitch.
    const float ContactValidUntil = MechanicalCueTimes.IsValidIndex(CueIndex + 1)
        ? (bSourceCueClock ? ReloadRuntimeTime(MechanicalCueTimes[CueIndex + 1]) : MechanicalCueTimes[CueIndex + 1])
        : WeaponStateDuration;
    const bool bPlayContact = Sound && ((bUsingM4Infima && !bDrumInstalled)
        ? WeaponStateElapsed < ContactValidUntil
        : Lateness < Sound->GetDuration());
    const bool bRecordedLoader = bUseDanWesson715 && IsReloading() && !bRevolverSingleReload;
    if (bPlayContact && (!bRecordedLoader || Lateness < Sound->GetDuration()))
        PlayMechanicalSound(Sound, ContactVolume, bRecordedLoader ? Lateness : 0.f);
    if (bDrumInstalled && FParse::Param(FCommandLine::Get(),TEXT("DrumGripAudit")))
        UE_LOG(LogTemp,Display,TEXT("DRUM_AUDIO: empty=%d index=%d target=%.6f runtime=%.6f late=%.6f sound=%s played=%d"),bPendingEmptyReload,CueIndex,MechanicalCueTimes[CueIndex],WeaponStateElapsed,Lateness,*GetNameSafe(Sound),bPlayContact);
    if (bRunGunplayAcceptance && bUsingM4Infima && !FParse::Param(FCommandLine::Get(), TEXT("EquipFramingAudit")))
    {
        if (bPendingEmptyReload) ++AuditEmptyMechanicalCues; else ++AuditNormalMechanicalCues;
        if (bPendingEmptyReload && CueIndex == BoltReleaseCueIndex) ++AuditBoltReleaseCues;
        AuditMaxMechanicalLateness = FMath::Max(AuditMaxMechanicalLateness, Lateness);
        UE_LOG(LogTemp, Display, TEXT("M4_AUDIO_CUE empty=%d index=%d source=%.6f target=%.6f runtime=%.6f late=%.6f sound=%s played=%d"),
            bPendingEmptyReload, CueIndex, ReloadSourceTime(WeaponStateElapsed), MechanicalCueTimes[CueIndex], WeaponStateElapsed, Lateness, *GetNameSafe(Sound), bPlayContact);
    }
    // PKM's gun/hand impulses are baked; its camera contacts are sampled by
    // WeaponActionCamera. Do not add the M4 index-based impulse to either layer.
    if (!bUseDanWesson715 && !bPKMReload && (CueIndex == 2 || CueIndex == BoltReleaseCueIndex))
    {
        // A seated magazine and released bolt push the whole supported weapon; wrists retain their source pose.
        const float ContactKickScale = bM16ChargeRelease ? .45f : 1.f;
        GunKickPositionVelocity.Z += (CueIndex == 2 ? 0.10f : 0.16f) * ContactKickScale;
        GunKickRotationVelocity.X += (CueIndex == 2 ? -0.08f : 0.14f) * ContactKickScale;
        // M4 contacts now use a separately sampled camera layer. Keep the gun
        // impulse and other weapon families' existing camera behavior.
        if (!(bUsingM4Infima && (bUseM4Infima || bUseM16) && !bUseQBZ191 && !IsPistolWeapon()))
            CameraKickPitchVelocity += 0.018f;
    }
}

void AFPSGAMECharacter::UpdateActionPose(float DeltaSeconds)
{
    if(IsDualWieldingPistols())return;
    if (!GunplayAnimation) return;
    const bool bPKMWeapon = PKMLowpolyWeaponAssets::Matches(AKMViewmodel);
    const bool bPKMFeedAction = bPKMWeapon && ActiveActionAnimation
        && (ActiveActionAnimation == FireAnimation || ActiveActionAnimation == AimFireAnimation);
    const double PKMShotAge = bPKMFeedAction ? FMath::Max(0.0, GetWorld()->GetTimeSeconds() - LastShotWorldTime) : 0.0;
    // Keep the final shot's visible feed until its cycle finishes. Ammo and
    // reload eligibility still use the real magazine count immediately.
    const int32 PKMPresentationRounds = bPKMFeedAction && !IsReloading() && PKMShotAge < ActionDuration
        ? FMath::Max(1, MagazineAmmo) : MagazineAmmo;
    PKMLowpolyWeaponAssets::SetSections(AKMViewmodel,IsReloading(),bPendingEmptyReload,
        IsReloading()?ReloadSourceTime(WeaponStateElapsed):0.f,bGunsmithInspection?100:PKMPresentationRounds);
    if (auto* View=Cast<UFPSCastingMeshComponent>(AKMViewmodel))
        View->OutgoingBeltDynamics.Configure(bPKMWeapon,IsReloading(),bPendingEmptyReload,
            IsReloading()?ReloadSourceTime(WeaponStateElapsed):0.f,MagazineAmmo,MagazineCapacity,
            bPKMFeedAction,ActionStartPosition+static_cast<float>(PKMShotAge)*ActionPlayRate,bGunsmithInspection);
    const auto DrumPose=[this](UAnimSequence* Clip)->UAnimSequence*
    {
        if(HasAngledForegrip())if(const auto* Support=ForegripAnimations.Find(Clip))return Support->Get();
        if(HasCantedForegrip())if(const auto* Support=CantedGripAnimations.Find(Clip))return Support->Get();
        if(HasVerticalForegrip())if(const auto* Support=VerticalGripAnimations.Find(Clip))return Support->Get();
        if(HasPrismHandstop())if(const auto* Support=PrismGripAnimations.Find(Clip))return Support->Get();
        if(bDrumInstalled)if(const auto* Support=DrumSupportAnimations.Find(Clip))return Support->Get();
        return Clip;
    };
    bool bPistolWorkbench = false;
    if (IsPistolWeapon() && GetGameInstance())
    {
        const auto* Gunsmith = GetGameInstance()->GetSubsystem<UGunsmithSystem>();
        const auto* Profile = GetGameInstance()->GetSubsystem<UColdSteelStatusModel>();
        bPistolWorkbench = Gunsmith && Gunsmith->IsOpen() && Profile && Profile->Equipped()
            && Profile->Equipped()->InstanceId == Gunsmith->Instance();
    }
    // The workbench presents an assembled, closed-slide pistol independently of
    // ammunition. Closing it restores the live empty/action pose on the next tick.
    const bool PistolEmpty = bUseM1911 && !bPistolWorkbench && (MagazineAmmo == 0 || NeedsReloadCycle())
        && (!IsReloading() || ReloadSourceTime(WeaponStateElapsed) < M1911Source::SlideRelease);
    GunplayAnimation->IdleClip=PistolEmpty ? PistolIdleEmptyAnimation.Get() : DrumPose(IdleAnimation);
    GunplayAnimation->AimClip=PistolEmpty ? PistolAimEmptyAnimation.Get() : DrumPose(AimAnimation);
    GunplayAnimation->BaseTime = FeedbackTime;
    GunplayAnimation->AimAlpha = WeaponADSFactor;
    GunplayAnimation->SprintClip = PistolEmpty ? PistolSprintEmptyAnimation : PistolSprintAnimation;
    GunplayAnimation->SprintTime = GunplayAnimation->SprintClip
        ? PistolSprintPhase / (2.f * PI) * GunplayAnimation->SprintClip->GetPlayLength() : 0.f;
    GunplayAnimation->SprintAlpha = IsPistolWeapon() && !bPistolWorkbench && !IsTraversing()
        && !IsCastBlockingLeftHandAction() ? PistolLocomotionAlpha : 0.f;
    GunplayAnimation->SprintLoopClip = nullptr;
    GunplayAnimation->SprintLoopAlpha = 0.f;
    GunplayAnimation->SprintLoopTime = 0.f;
    if (!IsPistolWeapon() && bInventoryWeaponReady)
        if (const auto* Sprint = FindComponentByClass<UM4TacticalSprintComponent>()) Sprint->Apply(*GunplayAnimation);
    if (ActiveActionAnimation)
    {
        // A reload can start during input, before this frame's Tick. Adding
        // DeltaSeconds counts time before that input and used to retire the
        // animation early (especially on a hitch) while firing stayed locked.
        const bool bFireAction = ActiveActionAnimation == FireAnimation || ActiveActionAnimation == AimFireAnimation || ActiveActionAnimation == PistolFireLastAnimation || ActiveActionAnimation == PistolAimFireLastAnimation;
        const bool bQuickCombatAction = WeaponState == EAKMWeaponState::QuickCombat;
        if ((bUseDanWesson715 || bPKMWeapon) && bFireAction)
            ActionElapsed = static_cast<float>(FMath::Max(0.0, GetWorld()->GetTimeSeconds() - LastShotWorldTime));
        else if (bQuickCombatAction || IsReloading() || ((bUsingM4Infima || bUseQBZ191 || IsPistolWeapon()) && WeaponState == EAKMWeaponState::Equipping)) ActionElapsed = WeaponStateElapsed;
        else ActionElapsed += DeltaSeconds;
        const float BlendScale = IsReloading() ? 1.f / FMath::Max(0.01f, ActionPlayRate) : 1.f;
        const float BlendOut = (bFireAction ? 0.028f : (IsPistolWeapon() && IsReloading() ? 0.025f : 0.10f)) * BlendScale;
        const float In = FMath::Clamp((ActionElapsed-(IsReloading()?ReloadResumeElapsed:0.f)) / (ActionBlendIn * BlendScale), 0.0f, 1.0f);
        const float Out = bQuickCombatAction
            ? QuickCombatRecovery::RemainingWeight(ActionElapsed, ActionDuration, QuickCombatRecovery::IdleHandoffStart)
            : FMath::Clamp((ActionDuration - ActionElapsed) / BlendOut, 0.0f, 1.0f);
        GunplayAnimation->ActionClip = DrumPose(ActiveActionAnimation);
        GunplayAnimation->ActionAlpha = FMath::Min(In, Out);
        // Both prop sets have different parked poses. Fade only into the reload;
        // its authored grip return hands off to idle without blending props through the gun.
        if (bPKMWeapon && IsReloading()) GunplayAnimation->ActionAlpha=In;
        // The equip starts below the view and ends at the exact family idle.
        // Blending against visible idle would shorten the authored lifting arc.
        if (bPKMWeapon && WeaponState == EAKMWeaponState::Equipping && ActiveActionAnimation == EquipAnimation)
            GunplayAnimation->ActionAlpha=1.0f;
        // At the end of a feed, identical visible belt units occupy the prior
        // unit's slot. Fading indexed bones back to idle would reverse the feed.
        // The source starts at idle and finishes its recoil before the handoff.
        if (bPKMFeedAction) GunplayAnimation->ActionAlpha=1.0f;
        float SourceTime = ActionStartPosition + ActionElapsed * ActionPlayRate;
        if (IsReloading()) SourceTime = ReloadSourceTime(WeaponStateElapsed);
        else if (WeaponState == EAKMWeaponState::Equipping && !EquipAnimation)
            SourceTime = ActionStartPosition + FMath::Max(0.0f, ActionElapsed - 0.18f);
        GunplayAnimation->ActionTime = FMath::Min(SourceTime, ActiveActionAnimation->GetPlayLength());
        if (!IsReloading() && ActionElapsed >= ActionDuration)
        {
            ActiveActionAnimation = nullptr;
            GunplayAnimation->ActionAlpha = 0.0f;
        }
    }
    else GunplayAnimation->ActionAlpha = 0.0f;
    if (bPistolWorkbench) GunplayAnimation->ActionAlpha = 0.0f;
    GunplayAnimation->bRevolver = bUseDanWesson715;
    GunplayAnimation->RevolverLiveRounds = bPistolWorkbench ? 6 : MagazineAmmo;
    GunplayAnimation->RevolverCartridges = bPistolWorkbench ? 6 : RevolverCaseCount;
    if (bUseDanWesson715 && IsReloading() && !bPistolWorkbench && !bReloadCycleOnly)
    {
        const float SourceSeconds = ReloadSourceTime(WeaponStateElapsed);
        if (bRevolverSingleReload)
        {
            const float Local = SourceSeconds - DanWesson715WeaponAssets::SingleLoopBegin(bPendingEmptyReload);
            const int32 Index = FMath::FloorToInt(Local / DanWesson715WeaponAssets::SingleStep);
            if (Index >= 0 && Index < RevolverReloadCount && Local - Index * DanWesson715WeaponAssets::SingleStep >= DanWesson715WeaponAssets::SingleVisible)
            {
                // The new cartridge is visible in the hand before it is seated.
                const int32 Visible = RevolverReloadStartLive + Index + 1;
                GunplayAnimation->RevolverLiveRounds = FMath::Max(MagazineAmmo, Visible);
                GunplayAnimation->RevolverCartridges = FMath::Max(RevolverCaseCount, Visible);
            }
        }
        else
        {
            const float NormalSeconds = SourceSeconds * (bPendingEmptyReload ? DanWesson715WeaponAssets::NormalReload / DanWesson715WeaponAssets::EmptyReload : 1.f);
            if (NormalSeconds >= DanWesson715WeaponAssets::RoundsVisible)
            {
                const int32 Loaded = HasInfiniteReserveAmmo() ? 6 : FMath::Min(6, MagazineAmmo + ReserveAmmo);
                GunplayAnimation->RevolverLiveRounds = Loaded;
                GunplayAnimation->RevolverCartridges = Loaded;
            }
        }
    }
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
