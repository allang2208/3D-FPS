#include "RuneSwordComponent.h"
#include "HighlandBreakSweep.h"
#include "RingChainSweepMotion.h"
#include "../Characters/FPSPlayerBodyComponent.h"
#include "HighlandRidgeThrust.h"
#include "HighlandRidgeGatherComponent.h"
#include "RuneSwordGuardTuning.h"
#include "StarMarrowChargeMotion.h"
#include "../Characters/FPSComponentVisibility.h"
#include "../Skills/LightningHasteSpeed.h"
#include "BeiweiSwordTrailComponent.h"
#include "../Multiplayer/ColdSteelAuthorityContext.h"
#include "../Multiplayer/ColdSteelGenericMelee.h"
#include "../Multiplayer/ColdSteelPlayerState.h"
#include "SprintCameraMotion.h"
#include "TangDaoGuardComponent.h"
#include "PanChiGuardComponent.h"
#include "RuneSwordMeshComponent.h"
#include "RuneSwordWhirlwindFeel.h"
#include "RuneSwordOverheadFeel.h"
#include "RuneSwordUppercutMotion.h"
#include "../Skills/ChainSlashAssets.h"
#include "RuneSwordInspectFeel.h"
#include "RuneSwordRisingDragon.h"
#include "MeleeRuneVisual.h"
#include "MeleeGuardAssets.h"
#include "ModularSwordVisual.h"
#include "../Combat/CombatStatusFormula.h"
#include "../Monsters/MonsterCombatComponent.h"
#include "RuneSwordCombatTuning.h"
#include "MeleeSmallTargetQuery.h"
#include "../Skills/FPSCastingMeshComponent.h"
#include "../Skills/QuickCombatPistolMotion.h"
#include "../Skills/QuickCombatImpactShake.h"
#include "ColdSteelEnchantmentCombat.h"
#include "FPSRiftSlashProjectile.h"
#include "SwordWaveTuning.h"
#include "GunsmithSystem.h"
#include "Engine/AssetManager.h"
#include "Engine/StreamableManager.h"
#include "NiagaraSystem.h"
#include "../Skills/ColdSteelSkillRules.h"
#include "../FPSGAMECharacter.h"
#include "../FPSGAMEPlayerController.h"
#include "../UI/ColdSteelStatusModel.h"
#include "../UI/ColdSteelEnhancementSystem.h"
#include "../Monsters/FPSCombatHealthComponent.h"
#include "../Monsters/BoundCongregateCaptureComponent.h"
#include "../Building/VoxelBuildComponent.h"
#include "../Movement/FPSCharacterMovementComponent.h"
#include "Animation/AnimSequence.h"
#include "WeaponGripProfile.h"
#include "Camera/CameraComponent.h"
#include "Components/SkeletalMeshComponent.h"
#include "Components/SceneComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Engine/GameInstance.h"
#include "Engine/SkeletalMesh.h"
#include "Engine/StaticMesh.h"
#include "Engine/World.h"
#include "GameFramework/PlayerController.h"
#include "GameFramework/GameStateBase.h"
#include "Kismet/GameplayStatics.h"
#include "Sound/SoundBase.h"
#include "Materials/MaterialInstanceDynamic.h"
#include "Materials/MaterialInterface.h"
#include "Misc/ScopeExit.h"

URuneSwordComponent::URuneSwordComponent()
{
    SetIsReplicatedByDefault(true);
    PrimaryComponentTick.bCanEverTick=true;
    // Lunge movement and the attached arms must finish before World caches the
    // player camera. Keep this order for every state: changing groups on attack
    // entry can be too late for the first frame's already queued tick.
    PrimaryComponentTick.TickGroup=TG_PostPhysics;
    SlashWaveMeshAsset=TSoftObjectPtr<UStaticMesh>(FSoftObjectPath(TEXT("/Game/Weapons/RiftSlash20260930/SM_RiftSlash.SM_RiftSlash")));
    SlashWaveMaterialAsset=TSoftObjectPtr<UMaterialInterface>(FSoftObjectPath(TEXT("/Game/Weapons/RiftSlash20260930/M_RiftSlash.M_RiftSlash")));
    SlashWaveMotesAsset=TSoftObjectPtr<UNiagaraSystem>(FSoftObjectPath(TEXT("/Game/Weapons/RiftSlash20260930/NS_RiftSlashMotes.NS_RiftSlashMotes")));
    UppercutStandard=TSoftObjectPtr<UAnimSequence>(FSoftObjectPath(TEXT("/Game/Weapons/SwordUppercut20261003/Standard/A_Sword_UppercutV1_Standard.A_Sword_UppercutV1_Standard")));
    UppercutLongGrip=TSoftObjectPtr<UAnimSequence>(FSoftObjectPath(TEXT("/Game/Weapons/SwordUppercut20261003/LongGrip/A_Sword_UppercutV1_LongGrip.A_Sword_UppercutV1_LongGrip")));
}

bool URuneSwordComponent::TriggerHeavySkill()
{
    if(UBoundCongregateCaptureComponent::IsCaptured(GetOwner()))return false;
    if(!IsEquipped()||IsBusy()||!CanUse())return false;
    BeginHeavyCharge();
    bAutoHeavyRelease=bCharging;
    return bCharging;
}

void URuneSwordComponent::FinishHeavyTraining()
{
    if(!bHeavyTrainingPending)return;
    bHeavyTrainingPending=false;
    if(GetWorld()&&GetWorld()->GetGameInstance())
        if(auto* Profile=GetWorld()->GetGameInstance()->GetSubsystem<UColdSteelStatusModel>())
        {
            if(bUppercut&&GetNetMode()==NM_Client)
            {
                if(Character.IsValid())if(auto* PS=Character->GetPlayerState<AColdSteelPlayerState>())PS->FinishSwordUppercut();
            }
            else if(bUppercut)Profile->TrainSwordUppercut(HeavyTrainingHits,HeavyTrainingKills);
            else Profile->TrainHeavyStrike(HeavyTrainingHits,HeavyTrainingKills);
        }
}

void URuneSwordComponent::BeginPlay()
{
    Super::BeginPlay();
    auto* Pawn=Cast<AFPSGAMECharacter>(GetOwner()); Character=Pawn;
    auto* World=GetWorld();
    auto* GameInstance=World?World->GetGameInstance():nullptr;
    // IsGameWorld includes GamePreview; visual rigs must not access inventory.
    if(!Pawn || !GameInstance || (World->WorldType!=EWorldType::Game && World->WorldType!=EWorldType::PIE))
    {SetComponentTickEnabled(false);return;}
    // Client possession can arrive after BeginPlay. RefreshEquipment will create
    // the local presentation when OnRep_Controller attaches the owner's profile.
    if(Pawn->HasAuthority() || Pawn->IsLocallyControlled())InitializePresentation();
    if(Pawn->IsLocallyControlled())RefreshEquipment(GameInstance->GetSubsystem<UColdSteelStatusModel>());
    else if(Pawn->HasAuthority())RefreshEquipment(Pawn->GetNetShadowProfile());
}

bool URuneSwordComponent::CanPresent() const
{
    auto* Pawn=Character.Get();const auto* PC=Pawn?Cast<APlayerController>(Pawn->GetController()):nullptr;
    const auto* Health=Pawn?Pawn->FindComponentByClass<UFPSCombatHealthComponent>():nullptr;
    const auto* Build=PC?PC->FindComponentByClass<UVoxelBuildComponent>():nullptr;
    // A panel owns input, but the equipped rig still owns its idle presentation.
    return PC && !Pawn->IsTraversing() && (!Health || !Health->IsDead())
        && (!Build || !Build->IsBuilding() || Build->IsPanelOpen());
}

bool URuneSwordComponent::CanUse(bool bContinuing) const
{
    const auto* PC=Character.IsValid()?Cast<APlayerController>(Character->GetController()):nullptr;
    const auto* Build=PC?PC->FindComponentByClass<UVoxelBuildComponent>():nullptr;
    return CanPresent() && !(bContinuing?AFPSGAMEPlayerController::BlocksActionContinuation(PC):AFPSGAMEPlayerController::BlocksOngoingActions(PC)) && (!Build || !Build->IsBuilding());
}

void URuneSwordComponent::TickComponent(float Delta,ELevelTick Type,FActorComponentTickFunction* Tick)
{
    Super::TickComponent(Delta,Type,Tick);
    if(GaleSwiftUntil>0.)TickGaleSwift();
    ON_SCOPE_EXIT { TickOath(); };
    if(ChainWaveAt>=0.)TickChainWave();
    if(bChainSlash&&ChainTool.IsValid()){TickChainSlash(Delta);return;}
    // Remote first-person rigs do not advance local combat/input state.
    if(Character.IsValid()&&!Character->IsLocallyControlled())
    {
        bEquipping=false;
        TickNetworkGuard();
        TickNetworkHeavyCharge();
        if(bChainSlash)TickChainSlash(Delta);
        return;
    }
    ON_SCOPE_EXIT { UpdateAzureDragonPose();TickBeiweiTrail();PresentRidgeGather(); };
    TickAzureDragon(Delta);
    if(!bWhirlwind)
        if(auto* Arms=Cast<URuneSwordMeshComponent>(Viewmodel))Arms->AdvanceLocomotionEntry(Delta);
    TickDashReadiness(Delta);
    if(!Viewmodel || !IsEquipped())return;
    if(JumpPresentationRoot)
        JumpPresentationRoot->SetRelativeTransform(Character->GetWeaponJumpTransform(EFirstPersonJumpRig::Sword));
    if(TickGuardBreak(Delta))return;
    if(TickKnockdown(Delta))return;
    const bool Present=CanPresent();
    const bool Usable=CanUse(true);
    FPSComponentVisibility::SetVisibilityTree(Viewmodel,Present && Viewmodel->GetSkeletalMeshAsset());
    if(!Usable)ClearClovenCounter();
    TickClovenCounter(Delta);
    if(!Usable)
    {
        if(IsBusy()||bInspecting||RingPrimaryDownAt>=0.)CancelAction();
        ImpactAge=1.f;StopRift();
        if(Present)
        {
            // These clips are sampled manually. Keep breathing behind UI without
            // advancing attacks, queued input or automatic inspection.
            if(CurrentClip!=TEXT("Idle"))SetClip(TEXT("Idle"),true);
            if(CurrentAnimation)
            {
                Elapsed=FMath::Fmod(Elapsed+Delta,FMath::Max(.01f,CurrentAnimation->GetPlayLength()));
                SamplePose(Elapsed);
            }
            Viewmodel->SetRelativeLocation(FMath::VInterpTo(Viewmodel->GetRelativeLocation(),FVector::ZeroVector,Delta,9.f));
            Viewmodel->SetRelativeRotation(FMath::RInterpTo(Viewmodel->GetRelativeRotation(),FRotator(0,90,0),Delta,9.f));
        }
        return;
    }
    if((bUppercut || IsRisingDragonFinisher() || bCharging || bReturningCharge || bInspecting) && Character->IsCastBlockingLeftHandAction()){CancelAction();return;}
    if(RingPrimaryDownAt>=0.)AdvanceRingPrimaryHold();
    ImpactAge=FMath::Min(1.f,ImpactAge+Delta);
    if(!bChainSlash&&!HighlandBreakSweep::UsesRibbon(CurrentClip)&&!(bRiftUppercutReveal&&(bUppercut||IsRisingDragonFinisher())))TickRift(Delta);
    TickWalkInspect(Delta);
    if(bWhirlwind){TickWhirlwind(Delta);return;}
    if(!bChainSlash&&TickGuard(Delta))return;
    if(!CurrentAnimation)
    {
        if(bChainSlash)CancelAction();
        return;
    }
    const float End=CurrentAnimation->GetPlayLength();
    if(bChainSlash)
    {
        // Finish the normal viewmodel transform update below, including the
        // transition out of a sprint lean on the first frames of the skill.
        TickChainSlash(Delta);
    }
    else if(bChixiaoHeavy&&bAttacking)
    {
        TickChixiaoHeavy(Delta);
    }
    else if(bUppercut||IsRisingDragonFinisher())
    {
        TickUppercut(Delta);
    }
    else if(bAttacking)
    {
        const bool bOverheadFinisher=bOverheadAttack&&!bDashAttack&&(SwingSkills.AttackMeta&0x0F)==3;
        // Map through real playback time so a frame crossing the windup boundary
        // spends only its remaining time on the original-speed strike/recovery.
        const float Held=FMath::Min(Delta,SweepHitPause);
        SweepHitPause-=Held;
        float Next=Elapsed+(Delta-Held)*SwingRate;
        if(HighlandRidgeThrust::IsRelease(CurrentClip))
        {
            const float Lead=HighlandRidgeThrust::LeadFor(CurrentClip);
            Next=HighlandRidgeThrust::ToClip(HighlandRidgeThrust::ToWall(Elapsed,Lead,SwingRate)+Delta-Held,Lead,SwingRate);
        }
        else if(bQuickCombatStrike)
            Next=RuneSwordPommelRhythm::QuickCombatSourceTime(RuneSwordPommelRhythm::QuickCombatTime(Elapsed)+Delta*SwingRate);
        Next=FMath::Min(End,Next);
        const FTransform AimBeforeLunge=Character->GetMeleeAimTransform();
        const FVector LungeMoved=AdvanceThrustLunge(Elapsed,Next);
        const FTransform AimNow=Character->GetMeleeAimTransform();
        if((bThrustAttack || bPommelAttack || bOverheadFinisher) && bRiftActive)
        {
            // Carry the strike rift with the actual step, including collision stops.
            RiftOrigin.AddToTranslation(LungeMoved);TickRift(0.f);
        }
        const bool bEnteredContactThisFrame=!bSwingCuePlayed&&Next>=ContactStart;
        if(bEnteredContactThisFrame)
        {
            bSwingCuePlayed=true;
            if(bPommelAttack && PommelHitSound)
            {
                // The fourth hit carries its own cue and replaces the shared sword swing
                // for this clip, so the counterweight reads as the striking end whether
                // or not the swing connects.
                UGameplayStatics::PlaySound2D(this,PommelHitSound,1.f,1.f);
            }
            else
            {
                if(AttackLayerSound)UGameplayStatics::PlaySound2D(this,AttackLayerSound,1.f,1.f);
                if(SwingSound)
                {
                    const bool bSweep=CurrentClip==HighlandBreakSweep::Clip;
                    const float Pitch=bSweep?.94f:FMath::Clamp(SwingRate*(bOverheadAttack?.95f:(bHeavyAttack?.95f:(bThrustAttack?1.25f:1.1f))),.7f,1.4f);
                    UGameplayStatics::PlaySound2D(this,SwingSound,bSweep?.90f:(bOverheadAttack?.90f:(bHeavyAttack?.95f:.72f)),Pitch);
                }
            }
            if(!HighlandBreakSweep::UsesRibbon(CurrentClip))StartRift(Next-ContactStart);
            ReleaseSlashWave(AimNow);
        }
        const auto FrameAt=[&](float Time)
        {
            // A hitch may run past the clip end. Aim still spans the full real
            // frame, rather than compressing all player movement into the clip.
            FTransform Frame;Frame.Blend(PreviousAimFrame,AimBeforeLunge,(Time-Elapsed)/FMath::Max(UE_SMALL_NUMBER,Delta*SwingRate));
            // Attribute real capsule displacement to the thrust's phase curve.
            // When blocked, the trace stops travelling with the blocked capsule.
            const float ForwardMoved=FVector::DotProduct(LungeMoved,LungeDirection);
            if(!bDashAttack && ForwardMoved>UE_SMALL_NUMBER)
            {
                const float Requested=bThrustAttack?
                    RuneSwordThrustRhythm::LungeDistance*(RuneSwordThrustRhythm::LungeAlpha(Time)-RuneSwordThrustRhythm::LungeAlpha(Elapsed)):
                    RuneSwordPommelRhythm::LungeDistance*(RuneSwordPommelRhythm::LungeAlpha(Time)-RuneSwordPommelRhythm::LungeAlpha(Elapsed));
                Frame.AddToTranslation(LungeMoved*FMath::Clamp(Requested/ForwardMoved,0.f,1.f));
            }
            return Frame;
        };
        const float HitStart=FMath::Max(Elapsed,ContactStart),HitEnd=FMath::Min(Next,ContactEnd);
        if(HighlandRidgeThrust::IsRelease(CurrentClip))
        {
            if(HitEnd>HitStart)
            {
                if(bDashAttack)DashAttackContractHit();
                else
                {
                    const FVector Forward=AimNow.GetUnitAxis(EAxis::X).GetSafeNormal2D();
                    const auto Hits=RuneSwordCombat::QueryRectangle(GetWorld(),Character.Get(),Character->GetActorLocation(),Forward,
                        AzureDragonRange(SwingReach),HighlandRidgeThrust::HalfWidthCM,HitActors);
                    ApplySwingHits(Hits,Forward);
                }
            }
        }
        else if(bDashAttack)
        {
            if(HitEnd>HitStart)DashAttackContractHit();
        }
        else if(CurrentClip==HighlandBreakSweep::Clip||CurrentClip==RingChainSweepMotion::Release)
        {
            if(HitEnd>HitStart)
            {
                const float From=HighlandBreakSweep::Angle(HitStart),To=HighlandBreakSweep::Angle(HitEnd);
                const FVector Forward=AimNow.GetUnitAxis(EAxis::X).GetSafeNormal2D(UE_SMALL_NUMBER,Character->GetActorForwardVector().GetSafeNormal2D());
                const FVector Across=Forward.RotateAngleAxis((From+To)*.5f,FVector::UpVector);
                const float ReachCM=CurrentClip==RingChainSweepMotion::Release?AzureDragonSwingRange(SwingReach):SwingReach;
                ApplySwingHits(RuneSwordCombat::QuerySector(GetWorld(),Character.Get(),Character->GetActorLocation(),
                    Across,ReachCM,FMath::Abs(To-From),HitActors),Across);
            }
        }
        else if(bOverheadFinisher)
        {
            // A single oriented box query per active frame replaces BOTH the
            // swept blade and the low sector. Nothing outside this rectangle
            // can be added by the ordinary slash/thrust fallback.
            if(HitEnd>HitStart)
            {
                const FVector Forward=AimNow.GetUnitAxis(EAxis::X).GetSafeNormal2D();
                const auto Hits=RuneSwordCombat::QueryRectangle(GetWorld(),Character.Get(),Character->GetActorLocation(),Forward,
                    AzureDragonSwingRange(SwingReach),RuneSwordOverheadRhythm::FinisherRectangleHalfWidthCM,HitActors);
                ApplySwingHits(Hits,Forward);
            }
        }
        else if(bQuickCombatStrike)
        {
            // 快速进战不走动画路径采样：配重接触帧（ExtensionEnd）只做一次
            // 手枪同款单次判定，包含小手低位范围补充，不沿动画弧线重复结算。
            if(!bQuickCombatContactDone&&Next>=RuneSwordPommelRhythm::ExtensionEnd)
            {
                bQuickCombatContactDone=true;
                SamplePose(RuneSwordPommelRhythm::ExtensionEnd);
                QuickCombatContractHit();
            }
        }
        else if(HitEnd>HitStart)
        {
            const FTransform StartFrame=FrameAt(HitStart),EndFrame=FrameAt(HitEnd);
            const float AimTravel=FVector::Distance(StartFrame.GetLocation(),EndFrame.GetLocation())+
                SwingReach*StartFrame.GetRotation().AngularDistance(EndFrame.GetRotation());
            const float SampleRate=bOverheadAttack?RuneSwordOverheadRhythm::SampleRate:(bThrustAttack?RuneSwordThrustRhythm::SampleRate:(bPommelAttack?RuneSwordPommelRhythm::SampleRate:(bHeavyAttack?RuneSwordHeavyRhythm::SampleRate:240.f)));
            const float TraceRadius=(bThrustAttack?RuneSwordThrustRhythm::BladeRadius:(bPommelAttack?RuneSwordPommelRhythm::HeadRadius:RuneSwordCombat::BladeRadius))*SwingRangeMultiplier;
            const int32 Steps=FMath::Max(1,FMath::Max(FMath::CeilToInt((HitEnd-HitStart)*SampleRate),FMath::CeilToInt(AimTravel/TraceRadius)));
            SamplePose(HitStart);FRuneSwordBladeSample Previous=ReadBlade(StartFrame);
            for(int32 Step=1;Step<=Steps;++Step)
            {
                const float T=FMath::Lerp(HitStart,HitEnd,float(Step)/Steps);
                SamplePose(T);const auto Current=ReadBlade(FrameAt(T));SweepBlade(Previous,Current);Previous=Current;
            }
            // Once per active frame, never once per blade lane/substep. All hits
            // share HitActors, damage and reaction handling with the real blade.
            const bool bSingleTarget=bThrustAttack||bPommelAttack;
            if(!bSingleTarget||HitActors.IsEmpty())
            {
                const auto LowHits=MeleeSmallTargets::QueryLowSector(GetWorld(),Character.Get(),EndFrame,
                    AzureDragonSwingRange(SwingReach),HitActors,!bSingleTarget,
                    (bThrustAttack||HighlandRidgeThrust::IsRelease(CurrentClip))?30.f:MeleeSmallTargets::LowArcDegrees,
                    AzureDragonSwingRange(MeleeSmallTargets::LowReachCM*(bHeavyAttack?MeleeModifiers.MartialRange:1.)));
                ApplySwingHits(LowHits,EndFrame.GetUnitAxis(EAxis::X));
            }
        }
        // Resolve the real blade first, then the instant extension in the same frame.
        // Its launch must not lift a nearby victim out of the original thrust's contact.
        if(bEnteredContactThisFrame)ReleaseRiftPiercer(AimNow);
        if(bHeavyTrainingPending&&Next>=ContactEnd)FinishHeavyTraining();
        SamplePose(Next);PreviousAimFrame=AimNow;
        Elapsed=Next;
        if(HighlandBreakSweep::UsesRibbon(CurrentClip))
        {
            if(bEnteredContactThisFrame)StartRift(Next-ContactStart);
            else TickRift(Delta);
        }
        if(bQueuedAttack && bHeavyAttack && Elapsed>=RuneSwordHeavyRhythm::FollowEnd &&
            Elapsed<=RuneSwordHeavyRhythm::ArrestEnd && BeginBroadbladeSweep())return;
        if(bQuickCombatStrike)
            if(auto* Profile=GetWorld()->GetGameInstance()->GetSubsystem<UColdSteelStatusModel>())
            {
                const float Duration=RuneSwordPommelRhythm::QuickCombatTime(End)/FMath::Max(.01f,SwingRate);
                const float Remaining=(RuneSwordPommelRhythm::QuickCombatTime(End)-RuneSwordPommelRhythm::QuickCombatTime(Elapsed))/FMath::Max(.01f,SwingRate);
                Profile->UpdateQuickCombatAction(Remaining,Duration);
            }
        if(Elapsed>=End)
        {
            FinishDashAttack();
            const bool Queued=bQueuedAttack;const bool QueuedSkill=bQueuedQuickCombat;
            bAttacking=bQueuedAttack=bHeavyAttack=bThrustAttack=bPommelAttack=bOverheadAttack=bQuickCombatStrike=false;
            bQueuedQuickCombat=false;
            // Keep the completed query marker for the short camera tail.
            // StartSwing and CancelAction reset it before another action.
            bLungeStarted=bLungeBlocked=false;LastAttackEnd=GetWorld()->GetTimeSeconds();
            if(auto* Profile=GetWorld()->GetGameInstance()->GetSubsystem<UColdSteelStatusModel>())
            {
                // Full recovery ends the action gate; there is no follow-up cooldown.
                Profile->FinishQuickCombatCast();
                if(QuickCombatKillPending)Profile->TrainQuickCombat(Profile->QuickCombatDefinition().KillExperience);
            }
            QuickCombatKillPending=false;
            SetClip(TEXT("Idle"),true);
            if(QueuedSkill)BeginQuickCombatStrike();else if(Queued)BeginAttack();
        }
    }
    else if(bCharging)
    {
        const float ChargePoseLength=CurrentClip==RingChainSweepMotion::Charge?RingChainSweepMotion::Chamber:
            CurrentClip==HighlandRidgeThrust::Charge?End:RuneSwordHeavyRhythm::ChargeSeconds;
        Elapsed=HeavyChargeFraction()*ChargePoseLength;
        SamplePose(Elapsed); // Retiming keeps the authored charge pose synchronized with the skill clock.
        if(bAutoHeavyRelease&&GetWorld()->GetTimeSeconds()-ChargeStartedAt>=RequiredChargeSeconds)ReleaseHeavyCharge();
    }
    else if(bReturningCharge)
    {
        CancelChargeAge=FMath::Min(CancelChargeDuration,CancelChargeAge+Delta);
        Elapsed=CancelChargeFrom*(1.f-FMath::SmoothStep(0.f,CancelChargeDuration,CancelChargeAge));
        SamplePose(Elapsed); // Reverse the same supported two-hand path, without damage.
        if(CancelChargeAge>=CancelChargeDuration){bReturningCharge=false;SetClip(TEXT("Idle"),true);}
    }
    else if(bInspecting)
    {
        namespace Feel=RuneSwordInspectFeel;
        const float From=Elapsed, Rate=LightningHaste::ActionSpeed(GetOwner());
        Elapsed=FMath::Min(End,Elapsed+Delta*Rate);SamplePose(Elapsed);
        if(Elapsed<Feel::CatchAt)
        {
            InspectAir.PlayBeat(this,From,Elapsed,Feel::TurnPeak,.60f,Rate);
            InspectAir.PlayBeat(this,From,Elapsed,Feel::ReturnPeak,.38f,Rate);
        }
        if(From<Feel::CatchAt&&Elapsed>=Feel::CatchAt)
        {
            InspectAir.Stop();
            if(InspectCatchSound)UGameplayStatics::PlaySound2D(this,InspectCatchSound,RuneSwordInspectFeel::CatchVolume,RuneSwordInspectFeel::CatchPitch);
        }
        if(Elapsed>=End)
        {
            InspectAir.Stop();
            bInspecting=false;
            const bool GroundStride=Character->GetCharacterMovement()->IsMovingOnGround()
                && !Character->bWeaponJumpAirborne && !Character->IsSliding();
            SetClip(GroundStride&&Character->GetVelocity().SizeSquared2D()>400.f?TEXT("Walk"):TEXT("Idle"),true);
        }
    }
    else if(bEquipping)
    {
        const float Rate=IsStarMarrowChargeMotionPlaying()?1.f:LightningHaste::ActionSpeed(GetOwner());
        Elapsed=FMath::Min(End,Elapsed+Delta*Rate);
        if(IsStarMarrowChargeMotionPlaying())Character->RefreshQuickCombatCamera();
        SamplePose(Elapsed);
        if(Elapsed>=End){const bool Queued=bQueuedAttack;bEquipping=bQueuedAttack=false;SetClip(TEXT("Idle"),true);if(Queued)BeginAttack();}
    }
    else if(!TickTacticalSprintPose(Delta))
    {
        const bool GroundStride=Character->GetCharacterMovement()->IsMovingOnGround()
            && !Character->bWeaponJumpAirborne && !Character->IsSliding();
        const FName Clip=GroundStride&&Character->GetVelocity().SizeSquared2D()>400?TEXT("Walk"):TEXT("Idle");
        if(Clip!=CurrentClip)SetClip(Clip,true);
        if(CurrentAnimation){Elapsed=FMath::Fmod(Elapsed+Delta*(GroundStride&&Character->IsSprinting()?1.45f:1.f),FMath::Max(.01f,CurrentAnimation->GetPlayLength()));SamplePose(Elapsed);}
    }
    const bool Sprint=Character->IsSprinting() && !Character->bWeaponJumpAirborne && !IsBusy() && !HasTacticalSprintAnimations();
    FVector TargetLocation=Sprint?FVector(-4,0,-9):FVector::ZeroVector;
    FRotator TargetRotation(0,90,Sprint?22:0);
    float Follow=9.f;
    if(CurrentClip==HighlandRidgeThrust::Charge&&bCharging)
    {
        FRotator Strain;
        HighlandRidgeThrust::ChargeStrain(GetWorld()->GetTimeSeconds()-ChargeStartedAt,HeavyChargeFraction(),TargetLocation,Strain);
        TargetRotation+=Strain;Follow=48.f;
    }
    else if(CurrentClip==HighlandRidgeThrust::Release||CurrentClip==HighlandRidgeThrust::Charge)
        Follow=32.f;
    Viewmodel->SetRelativeLocation(FMath::VInterpTo(Viewmodel->GetRelativeLocation(),TargetLocation,Delta,Follow));
    Viewmodel->SetRelativeRotation(FMath::RInterpTo(Viewmodel->GetRelativeRotation(),TargetRotation,Delta,Follow));
}

void URuneSwordComponent::EndPlay(const EEndPlayReason::Type Reason)
{
    bChainSlash=bChainSlashPending=false;
    FinishChainSlashTraining();
    if(StarMarrowMotionLoad)StarMarrowMotionLoad->CancelHandle();StarMarrowMotionLoad.Reset();
    if(BeiweiTrail){GetOwner()->RemoveInstanceComponent(BeiweiTrail);BeiweiTrail->DestroyComponent();BeiweiTrail=nullptr;}
    if(RidgeGather){RidgeGather->DestroyComponent();RidgeGather=nullptr;}
    DestroyAzureDragon();
    FinishHeavyTraining();
    bUppercut=false;
    if(UppercutLoad)UppercutLoad->CancelHandle();UppercutLoad.Reset();
    if(ChixiaoLoad)ChixiaoLoad->CancelHandle();ChixiaoLoad.Reset();
    if(SlashWaveLoad)SlashWaveLoad->CancelHandle();SlashWaveLoad.Reset();
    FinishWhirlwind();
    FinishHeavyTraining();
    // Release a cast that ended with teardown instead of a finished swing, so the
    // cooldown starts and the reserved flag is not left set for the next session.
    if(auto* Profile=ColdSteelAuthority::ForPawn(Character.Get()))Profile->FinishQuickCombatCast();
    ClearGuard();
    SetHeavyCharging(false);
    InspectAir.Stop(0.f);
    bAttacking=bEquipping=bInspecting=bQueuedAttack=bReturningCharge=bHeavyAttack=false;HitActors.Reset();
    SwingCooldownReduceSeconds=0.f;bSwingCooldownReduced=false;
    bThrustAttack=bPommelAttack=bOverheadAttack=bLungeStarted=bLungeBlocked=false;
    ImpactAge=1.f;
    if(ModularSword){ColdSteelModularSword::Clear(ModularSword);ModularSword->DestroyComponent();ModularSword=nullptr;}
    if(Viewmodel)Viewmodel->DestroyComponent();
    if(JumpPresentationRoot)JumpPresentationRoot->DestroyComponent();
    if(RiftVisual)RiftVisual->DestroyComponent();
    if(ChainImpactWave){ChainImpactWave->DestroyComponent();ChainImpactWave=nullptr;ChainWaveMaterial=nullptr;}
    ChainWaveAt=-1.;
    Super::EndPlay(Reason);
}
