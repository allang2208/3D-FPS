#include "BlindSupplicantMonster.h"
#include "BlindSupplicantAnimInstance.h"
#include "M07MagicAttack.h"
#include "HumanoidKnockdownComponent.h"
#include "MonsterCombatComponent.h"
#include "MonsterCombatTuning.h"
#include "AIController.h"
#include "Animation/AnimSequence.h"
#include "Components/CapsuleComponent.h"
#include "Components/AudioComponent.h"
#include "Components/SkeletalMeshComponent.h"
#include "Engine/DamageEvents.h"
#include "Engine/SkeletalMesh.h"
#include "Engine/World.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "GameFramework/PlayerController.h"
#include "TimerManager.h"
#include "Sound/SoundAttenuation.h"
#include "NiagaraComponent.h"
#include "UObject/ConstructorHelpers.h"

ABlindSupplicantMonster::ABlindSupplicantMonster(const FObjectInitializer& Initializer) : Super(Initializer)
{
    Tags.Remove(TEXT("NurseZombie"));
    Tags.Add(TEXT("BlindSupplicantM07"));
    MonsterDisplayName = FText::FromString(TEXT("M-07 盲祷者"));
    GetCapsuleComponent()->InitCapsuleSize(50.f, 155.f);
    auto* Movement = GetCharacterMovement();
    Movement->SetUpdateNavAgentWithOwnersCollisions(false);
    Movement->NavAgentProps.AgentRadius = 50.f;
    Movement->NavAgentProps.AgentHeight = 312.f;
    Movement->NavAgentProps.AgentStepHeight = 40.f;
    Movement->MaxStepHeight = 40.f;
    // Provisional encounter tuning; data remains editable for user playtesting.
    MaxHealth = Health = 420.f;
    AttackDamage = 36.f;
    AttackRange = 180.f;
    WalkSpeed = 160.f;
    Movement->MaxWalkSpeed = ChaseSpeed;
    Level = 7;
    Rank = EMonsterRank::Elite;
    ExperienceReward = 360;
    RecoveryTime = .9f;
    CorpseSeconds = 18.f;
    ContactTime = LeftContactTime;
    ContactEnd = ContactTime + ContactWindowSeconds;
    AggroRadius = 1400.f;

    static ConstructorHelpers::FObjectFinder<USkeletalMesh> Model(TEXT("/Game/Monsters/BlindSupplicantM07/SK_M07_BodyMotionV18.SK_M07_BodyMotionV18"));
    VisualMesh = Model.Object;
    auto FindClip = [](const TCHAR* Name)
    {
        const FString Path = FString::Printf(TEXT("/Game/Monsters/BlindSupplicantM07/AnimationsOriginalV13/%s.%s"), Name, Name);
        ConstructorHelpers::FObjectFinder<UAnimSequence> Found(*Path);
        return Found.Object;
    };
    IdleClip = FindClip(TEXT("A_M07_Idle"));
    static ConstructorHelpers::FObjectFinder<UAnimSequence> LargerWalk(TEXT("/Game/Monsters/BlindSupplicantM07/AnimationsBodyMotionV18/A_M07_SlowWalk.A_M07_SlowWalk"));
    SlowWalkClip = LargerWalk.Object;
    static ConstructorHelpers::FObjectFinder<UAnimSequence> RunningChase(TEXT("/Game/Monsters/BlindSupplicantM07/AnimationsBodyMotionV18/A_M07_Chase.A_M07_Chase"));
    ChaseClip = RunningChase.Object;
    WalkClip = ChaseClip ? ChaseClip : SlowWalkClip;
    auto FindCombatClip = [](const TCHAR* Name)
    {
        const FString Path = FString::Printf(TEXT("/Game/Monsters/BlindSupplicantM07/AnimationsBodyMotionV18/%s.%s"), Name, Name);
        ConstructorHelpers::FObjectFinder<UAnimSequence> Found(*Path);
        return Found.Object;
    };
    MeleeLeftClip = FindCombatClip(TEXT("A_M07_SweepLeft"));
    MeleeRightClip = FindCombatClip(TEXT("A_M07_SweepRight"));
    auto FindMotionClip = [](const TCHAR* Name)
    {
        const FString Path = FString::Printf(TEXT("/Game/Monsters/BlindSupplicantM07/AnimationsMotionRecoveryV15/%s.%s"), Name, Name);
        ConstructorHelpers::FObjectFinder<UAnimSequence> Found(*Path);
        return Found.Object;
    };
    MagicGatherClip = FindMotionClip(TEXT("A_M07_MagicGather"));
    MagicReleaseClip = FindMotionClip(TEXT("A_M07_MagicRelease"));
    AttackClip = MeleeLeftClip;
    DeathClip = FindMotionClip(TEXT("A_M07_Death"));
    WallListenClip = FindClip(TEXT("A_M07_WallListen"));
    Combat->HitClip = FindClip(TEXT("A_M07_Hit"));
    Combat->DizzyClip = FindClip(TEXT("A_M07_Dizzy"));
    Knockdown->FallClip = FindClip(TEXT("A_M07_Fall"));
    Knockdown->GetUpClip = FindClip(TEXT("A_M07_GetUp"));
    Knockdown->ProneGetUpClip = FindClip(TEXT("A_M07_ProneGetUp"));
    Knockdown->LaunchScale = .85f;
    Knockdown->CorpseSettleDeadline = 4.f;
    static ConstructorHelpers::FClassFinder<AAIController> AI(TEXT("/Game/Monsters/AI/BP_MonsterAIController"));
    if (AI.Succeeded()) AIControllerClass = AI.Class;
    GetMesh()->SetAnimInstanceClass(UBlindSupplicantAnimInstance::StaticClass());
    GetMesh()->SetEnableGravity(true);
    WallMimicVoice = CreateDefaultSubobject<UAudioComponent>(TEXT("M07WallMimicVoice"));
    WallMimicVoice->SetupAttachment(GetMesh(), TEXT("head"));
    WallMimicVoice->bAutoActivate = false;
    WallMimicVoice->bStopWhenOwnerDestroyed = true;
    WallMimicVoice->bAllowSpatialization = true;
    FSoundAttenuationSettings VoiceAttenuation;
    VoiceAttenuation.bAttenuate = true;
    VoiceAttenuation.bSpatialize = true;
    VoiceAttenuation.AttenuationShapeExtents = FVector(90.f, 0.f, 0.f);
    VoiceAttenuation.FalloffDistance = 1350.f;
    WallMimicVoice->SetAttenuationOverrides(VoiceAttenuation);
    WallMimicVoice->SetOverrideAttenuation(true);
    AlignVisual();
}

void ABlindSupplicantMonster::AlignVisual()
{
    if (!VisualMesh) return;
    GetMesh()->SetSkeletalMeshAsset(VisualMesh);
    const auto& Ref = VisualMesh->GetRefSkeleton();
    auto Position = [&Ref](FName Name, FVector& Out)
    {
        const int32 Index = Ref.FindBoneIndex(Name);
        if (Index == INDEX_NONE) return false;
        FTransform Pose = Ref.GetRefBonePose()[Index];
        for (int32 Parent = Ref.GetParentIndex(Index); Parent != INDEX_NONE; Parent = Ref.GetParentIndex(Parent))
            Pose *= Ref.GetRefBonePose()[Parent];
        Out = Pose.GetLocation();
        return true;
    };
    FVector Foot, Ball, Forward = FVector::ZeroVector;
    for (const TCHAR* Side : {TEXT("l"), TEXT("r")})
        if (Position(FName(*FString::Printf(TEXT("foot_%s"), Side)), Foot) &&
            Position(FName(*FString::Printf(TEXT("ball_%s"), Side)), Ball))
            Forward += (Ball - Foot).GetSafeNormal2D();
    if (!Forward.IsNearlyZero()) GetMesh()->SetRelativeRotation(FRotator(0.f, -Forward.Rotation().Yaw, 0.f));
    const auto Bounds = VisualMesh->GetBounds();
    const float Bottom = Bounds.Origin.Z - Bounds.BoxExtent.Z;
    GetMesh()->SetRelativeLocation(FVector(0.f, 0.f, -GetCapsuleComponent()->GetUnscaledCapsuleHalfHeight() - Bottom));
}

void ABlindSupplicantMonster::OnConstruction(const FTransform& Transform)
{
    Super::OnConstruction(Transform);
    AlignVisual();
}

void ABlindSupplicantMonster::BeginPlay()
{
    ApplyPlayerSkillCooldownDefaults();
    AlignVisual();
    Super::BeginPlay();
    if (!VisualMesh || !IdleClip || !WalkClip || !AttackClip) return;
    GetCharacterMovement()->MaxWalkSpeed = ChaseSpeed;
    if (HasAuthority() && bWallListening && WallListenClip)
        GetWorldTimerManager().SetTimer(WallPresentationTimer, this, &ThisClass::RefreshWallPresentation, 1.f, true);
}

void ABlindSupplicantMonster::EndPlay(const EEndPlayReason::Type Reason)
{
    CancelPendingAttack();
    GetWorldTimerManager().ClearTimer(WallPresentationTimer);
    StopWallMimic();
    Super::EndPlay(Reason);
}

UBlindSupplicantAnimInstance* ABlindSupplicantMonster::PosePlayer()
{
    if (!Cast<UBlindSupplicantAnimInstance>(GetMesh()->GetAnimInstance()))
        GetMesh()->SetAnimInstanceClass(UBlindSupplicantAnimInstance::StaticClass());
    return Cast<UBlindSupplicantAnimInstance>(GetMesh()->GetAnimInstance());
}

void ABlindSupplicantMonster::StartStateAnimation(UAnimSequence* Clip, bool bLoop)
{
    bPresentingWallListen = false;
    StopWallMimic();
    if (State == ENurseState::Attack)
    {
        if (IsMagicAttack())
        {
            Clip = MagicGatherClip;
            BeginMagicCharge();
        }
        else
        {
            Clip = AttackClip;
            PreviousClaw = AttackClawPosition();
        }
    }
    else { CancelPendingAttack(); ActiveAttack = EAttack::None; ActiveAttackDuration = 0.f; }
    if (auto* Animation = PosePlayer())
    {
        FMonsterClipTransition Transition;
        if (State == ENurseState::Chase)
        {
            const float Speed = GetVelocity().Size2D();
            Clip = Speed < (WalkSpeed + ChaseSpeed) * .5f && SlowWalkClip ? SlowWalkClip.Get() : ChaseClip.Get();
            if (!Clip) Clip = WalkClip;
            const float SourceSpeed = Clip == SlowWalkClip ? SourceWalkSpeed : SourceChaseSpeed;
            Transition.InitialPlayRate = FMath::Clamp(Speed / FMath::Max(1.f, SourceSpeed), 0.f, 2.f);
        }
        const float BlendSeconds = State == ENurseState::Attack && !IsMagicAttack()
            ? FMath::Min(AnimationBlendSeconds, .10f) : AnimationBlendSeconds;
        Animation->TransitionTo(Clip, bLoop, State == ENurseState::Attack, BlendSeconds, Transition);
    }
}

void ABlindSupplicantMonster::SetAttackAnimationTime(float Seconds)
{
    auto* Animation = PosePlayer();
    if (!Animation) return;
    if (!IsMagicAttack()) { Animation->SetCombatTime(Seconds * ActiveMeleePlaybackRate); return; }
    if (!bMagicReleaseStarted)
    {
        if (IsLivingPlayer(LockedAttackTarget.Get()) && CombatTarget() == LockedAttackTarget.Get())
            LockedAimPoint = LockedAttackTarget->GetActorLocation();
        else CancelPendingAttack();
        if (Seconds >= ActiveGatherDuration)
        {
            // Keep the release pose fixed. ReleaseMagic takes its final target
            // snapshot and flight-time lead at contact; the projectile never homes.
            bMagicReleaseStarted = true;
            // The release begins from the complete bent-elbow gathering pose,
            // not the previous frame's partly extended locomotion/charge snapshot.
            Animation->SetCombatTime(ActiveGatherDuration);
            GetMesh()->TickAnimation(0.f, false);
            GetMesh()->RefreshBoneTransforms();
            Animation->TransitionTo(MagicReleaseClip, false, true, .06f);
        }
    }
    Animation->SetCombatTime(bMagicReleaseStarted ? Seconds - ActiveGatherDuration : Seconds);
    MagicChargeFraction = Seconds / FMath::Max(.01f, ActiveGatherDuration);
    // Charge placement/parameters follow the final evaluated bones in
    // UpdateMagicChargePose, sharing the same origin with projectile release.
}

void ABlindSupplicantMonster::SetWalkAnimationRate(float Rate)
{
    RefreshLocomotionPresentation();
}

void ABlindSupplicantMonster::RefreshLocomotionPresentation()
{
    auto* Animation = PosePlayer();
    if (!Animation || State != ENurseState::Chase) return;
    const float Speed = GetVelocity().Size2D();
    const float PaceBoundary=(WalkSpeed+ChaseSpeed)*.5f;
    const float PaceHysteresis=FMath::Abs(ChaseSpeed-WalkSpeed)*.45f;
    // Keep phase-aligned gaits from repeatedly crossfading as path following
    // accelerates/decelerates near the walk/run boundary.
    float SwitchSpeed=PaceBoundary;
    if (Animation->ActiveClip==SlowWalkClip) SwitchSpeed+=PaceHysteresis;
    else if (Animation->ActiveClip==ChaseClip) SwitchSpeed-=PaceHysteresis;
    UAnimSequence* Desired = Speed < SwitchSpeed && SlowWalkClip ? SlowWalkClip : ChaseClip;
    if (!Desired) Desired = WalkClip;
    if (!Desired) return;
    const float SourceSpeed = Desired == SlowWalkClip ? SourceWalkSpeed : SourceChaseSpeed;
    const float LocomotionRate = FMath::Clamp(Speed / FMath::Max(1.f, SourceSpeed), 0.f, 2.f);
    if (Animation->ActiveClip != Desired)
    {
        FMonsterClipTransition Transition;
        Transition.bContinueOutgoingLoop = true;
        Transition.InitialPlayRate = LocomotionRate;
        // Both authored gaits use the same left/right contact phase. Keep the
        // planted foot when changing pace instead of resuming an unrelated
        // time retained from the last use of the destination sequence.
        if ((Animation->ActiveClip == SlowWalkClip || Animation->ActiveClip == ChaseClip) &&
            Animation->ActiveClip->GetPlayLength() > UE_SMALL_NUMBER)
        {
            const float Phase = FMath::Fmod(Animation->ClipTime / Animation->ActiveClip->GetPlayLength(), 1.f);
            Transition.StartTime = Phase * Desired->GetPlayLength();
        }
        Animation->TransitionTo(Desired, true, false, AnimationBlendSeconds, Transition);
    }
    Animation->SetLocomotionRate(LocomotionRate);
}

void ABlindSupplicantMonster::RefreshWallPresentation()
{
    // This is a bounded idle-pose opportunity. The shared Behavior Tree retains
    // target selection and movement; wall sensing never writes an AI state.
    const bool Eligible = bWallListening && WallListenClip && State == ENurseState::Idle &&
        (!Knockdown || !Knockdown->IsControlling()) && GetVelocity().SizeSquared2D() < 25.f;
    bool NearWall = false;
    if (Eligible)
    {
        const FVector Ear = GetMesh()->DoesSocketExist(TEXT("head")) ? GetMesh()->GetSocketLocation(TEXT("head")) :
            GetActorLocation() + FVector(0.f, 0.f, 120.f);
        FCollisionQueryParams Params(SCENE_QUERY_STAT(M07WallListen), false, this);
        FHitResult Wall;
        NearWall = GetWorld()->LineTraceSingleByChannel(Wall, Ear, Ear + GetActorForwardVector() * WallListenDistance,
            ECC_Visibility, Params) && FMath::Abs(Wall.ImpactNormal.Z) < .45f;
    }
    if (NearWall != bPresentingWallListen)
    {
        bPresentingWallListen = NearWall;
        if (Eligible)
            if (auto* Animation = PosePlayer())
                Animation->TransitionTo(NearWall ? WallListenClip.Get() : IdleClip.Get(), true, false, .3f);
    }
    if (!NearWall)
    {
        StopWallMimic();
        return;
    }
    const double Now = GetWorld()->GetTimeSeconds();
    if (WallMimicSound && WallMimicVoice && GetNetMode() != NM_DedicatedServer &&
        !WallMimicVoice->IsPlaying() && Now >= NextWallMimicTime)
    {
        WallMimicVoice->SetSound(WallMimicSound);
        WallMimicVoice->SetVolumeMultiplier(WallMimicVolume);
        WallMimicVoice->FadeIn(.35f);
        NextWallMimicTime = Now + WallMimicIntervalSeconds;
    }
}

void ABlindSupplicantMonster::StopWallMimic()
{
    if (WallMimicVoice && WallMimicVoice->IsPlaying()) WallMimicVoice->Stop();
}

void ABlindSupplicantMonster::Tick(float DeltaSeconds)
{
    Super::Tick(DeltaSeconds);
    UpdateDeathPresentation();
    if (State != ENurseState::Attack || (Knockdown && Knockdown->IsControlling())) StopMagicCharge();
    if (Knockdown && Knockdown->IsControlling()) CancelPendingAttack();
    if (!bClothSuspendedForCorpse && Knockdown && Knockdown->IsFrozen())
    {
        GetMesh()->SuspendClothingSimulation();
        bClothSuspendedForCorpse = true;
    }
    if (!bClothSuspendedForCorpse) UpdateClothDistance(DeltaSeconds);
    if (bPresentingWallListen && (State != ENurseState::Idle || (Knockdown && Knockdown->IsControlling())))
    {
        bPresentingWallListen = false;
        StopWallMimic();
    }
}

void ABlindSupplicantMonster::UpdateClothDistance(float DeltaSeconds)
{
    if (State==ENurseState::Dead || (Knockdown && Knockdown->IsControlling()))
    {
        // Match the Witch handoff: independent live drapes stop during the
        // articulated fall; the corrected V35 skin follows the same skeleton.
        auto* CharacterMesh=GetMesh();
        bWantsClothSimulation=false;
        CharacterMesh->ClothBlendWeight=FMath::FInterpConstantTo(CharacterMesh->ClothBlendWeight,0.f,DeltaSeconds,1.f/.18f);
        if(CharacterMesh->ClothBlendWeight<=0.f && !CharacterMesh->IsClothingSimulationSuspended())
            CharacterMesh->SuspendClothingSimulation();
        return;
    }
    if (bUseCoherentGillMotion)
    {
        auto* CharacterMesh=GetMesh();
        bWantsClothSimulation=false;
        CharacterMesh->ClothBlendWeight=0.f;
        if (!CharacterMesh->IsClothingSimulationSuspended()) CharacterMesh->SuspendClothingSimulation();
        // Pure skinning can use the existing distance LODs; no near-cloth lock.
        if (CharacterMesh->GetForcedLOD()!=0) CharacterMesh->SetForcedLOD(0);
        return;
    }
    const APlayerController* ViewerController = GetWorld()->GetFirstPlayerController();
    const APawn* Viewer = ViewerController ? ViewerController->GetPawn() : nullptr;
    const double DistanceSquared = Viewer ? FVector::DistSquared(Viewer->GetActorLocation(), GetActorLocation()) : 0.;
    if (DistanceSquared <= FMath::Square(ClothResumeDistance)) bWantsClothSimulation = true;
    else if (DistanceSquared >= FMath::Square(FMath::Max(ClothResumeDistance + 100.f, ClothSuspendDistance))) bWantsClothSimulation = false;
    auto* CharacterMesh = GetMesh();
    // Keep the accepted near-cloth binding on LOD0 until its fade completes.
    const int32 ForcedLOD = bWantsClothSimulation || CharacterMesh->ClothBlendWeight > 0.f ? 1 : 0;
    if (CharacterMesh->GetForcedLOD() != ForcedLOD) CharacterMesh->SetForcedLOD(ForcedLOD);
    if (bWantsClothSimulation && CharacterMesh->IsClothingSimulationSuspended())
    {
        CharacterMesh->ResumeClothingSimulation();
        CharacterMesh->ForceClothNextUpdateTeleportAndReset();
    }
    CharacterMesh->ClothBlendWeight = FMath::FInterpConstantTo(CharacterMesh->ClothBlendWeight,
        bWantsClothSimulation ? 1.f : 0.f, DeltaSeconds, 1.f / .35f);
    if (!bWantsClothSimulation && CharacterMesh->ClothBlendWeight <= 0.f && !CharacterMesh->IsClothingSimulationSuspended())
        CharacterMesh->SuspendClothingSimulation();
}

float ABlindSupplicantMonster::TakeDamage(float Damage, const FDamageEvent& Event, AController* EventInstigator, AActor* Causer)
{
    IncomingHitDirection = -GetActorForwardVector();
    if (Event.IsOfType(FPointDamageEvent::ClassID))
        IncomingHitDirection = static_cast<const FPointDamageEvent&>(Event).ShotDirection;
    else if (Event.IsOfType(FRadialDamageEvent::ClassID))
        IncomingHitDirection = GetActorLocation() - static_cast<const FRadialDamageEvent&>(Event).Origin;
    else if (Causer) IncomingHitDirection = GetActorLocation() - Causer->GetActorLocation();
    if (IncomingHitDirection.IsNearlyZero() && EventInstigator && EventInstigator->GetPawn())
        IncomingHitDirection = GetActorLocation() - EventInstigator->GetPawn()->GetActorLocation();
    // ANurseZombie owns the sole health/reward edge and shared toughness gate.
    const float Applied = Super::TakeDamage(Damage, Event, EventInstigator, Causer);
    if (State == ENurseState::Dead) CancelPendingAttack();
    return Applied;
}

void ABlindSupplicantMonster::StartHitPresentation(UAnimSequence* Clip, float Duration)
{
    CancelPendingAttack();
    bPresentingWallListen = false;
    StopWallMimic();
    if (auto* Animation = PosePlayer())
        Animation->BeginHitReaction(Clip, Combat->IsParryReaction() ? Combat->GetParryDirection() : IncomingHitDirection,
            Combat->IsParryReaction(), .08f);
}

void ABlindSupplicantMonster::SetHitPresentationTime(UAnimSequence* Clip, float Elapsed, float Remaining)
{
    const float ReactionTime = Combat->IsParryReaction() ? FMath::Max(0.f, Elapsed - .1f) : Elapsed;
    if (auto* Animation = PosePlayer()) Animation->SetHitReactionTime(ReactionTime, Remaining);
}
