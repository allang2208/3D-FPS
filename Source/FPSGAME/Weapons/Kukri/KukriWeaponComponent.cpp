#include "KukriWeaponComponent.h"
#include "../../Combat/FPSAttackQuery.h"
#include "KukriDecisiveComponent.h"
#include "KukriAttackTiming.h"
#include "../../Characters/FPSComponentVisibility.h"
#include "KukriArmsMeshComponent.h"
#include "KukriRhythm.h"
#include "KukriDrawRhythm.h"
#include "HatchetDrawRhythm.h"
#include "HatchetChopRhythm.h"
#include "HatchetDualChopRhythm.h"
#include "HatchetReadyRhythm.h"
#include "HatchetPairRhythm.h"
#include "KukriDualDashRhythm.h"
#include "KukriDualEquipBlade.h"
#include "KukriOffhandDraw.h"
#include "OffhandBladeDraw.h"
#include "KukriHeavyRhythm.h"
#include "SwiftFalconHeavy.h"
#include "../MeleeWeaponStats.h"
#include "../MeleeSmallTargetQuery.h"
#include "../RuneSwordRhythm.h"
#include "../../Combat/WeaponDamageTypes.h"
#include "../../Skills/ColdSteelSkillRules.h"
#include "../../Skills/LightningHasteSpeed.h"
#include "../../FPSGAMECharacter.h"
#include "../../FPSGAMEPlayerController.h"
#include "../../UI/ColdSteelStatusModel.h"
#include "../../Monsters/FPSCombatHealthComponent.h"
#include "../../Monsters/MonsterCombatComponent.h"
#include "../../Dungeons/WardBreakableGlass.h"
#include "../../Building/VoxelBuildComponent.h"
#include "../../Items/FPSPotionUseComponent.h"
#include "../../Movement/FPSCharacterMovementComponent.h"
#include "../../Multiplayer/ColdSteelPlayerState.h"
#include "Animation/AnimSequence.h"
#include "Camera/CameraComponent.h"
#include "Components/DynamicMeshComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Components/DynamicMeshComponent.h"
#include "Engine/GameInstance.h"
#include "Engine/SkeletalMesh.h"
#include "Engine/StaticMesh.h"
#include "Engine/World.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "GameFramework/PlayerController.h"
#include "Kismet/GameplayStatics.h"
#include "Sound/SoundBase.h"

#include "KukriWeaponPrivate.h"
using namespace KukriWeaponPrivate;
UKukriWeaponComponent::UKukriWeaponComponent()
{
    PrimaryComponentTick.bCanEverTick=true;
    // Character movement and camera have settled; the attached rig is sampled once.
    PrimaryComponentTick.TickGroup=TG_PostPhysics;
    // The heavy strike's charge / release receipt RPCs (KukriHeavy.cpp); no replicated properties.
    SetIsReplicatedByDefault(true);
}

bool UKukriWeaponComponent::IsKukri(const FColdSteelItem& Item)
{
    return ColdSteelInventory::UsesKukriMoveset(Item);
}

bool UKukriWeaponComponent::IsDualOn(const AActor* Owner)
{
    const auto* Kukri=Owner?Owner->FindComponentByClass<UKukriWeaponComponent>():nullptr;
    // A blade in the left hand: the pair's second one, or the lone off-hand blade (consumables stow it, casts keep off it).
    return Kukri&&(Kukri->IsDual()||Kukri->IsLoneOffhand());
}

AFPSGAMECharacter* UKukriWeaponComponent::Pawn() const
{
    return Cast<AFPSGAMECharacter>(GetOwner());
}

void UKukriWeaponComponent::BeginPlay()
{
    Super::BeginPlay();
    auto* P=Pawn();
    if(!P){SetComponentTickEnabled(false);return;}
    SetTickGroup(TG_PostPhysics);
    AddTickPrerequisiteActor(P);
    AddTickPrerequisiteComponent(P->GetCharacterMovement());
    Camera=P->FindComponentByClass<UCameraComponent>();
    if(P->IsLocallyControlled())
        if(auto* GI=GetWorld()?GetWorld()->GetGameInstance():nullptr)RefreshEquipment(GI->GetSubsystem<UColdSteelStatusModel>());
}

void UKukriWeaponComponent::EndPlay(const EEndPlayReason::Type Reason)
{
    ResetFalconHooks();
    PairedHeavyContacts.Reset();
    // The destroy path also releases a quick-melee reservation.
    if(bQuickCombat){bQuickCombat=false;FinishQuickCombat();}
    if(bUppercut){bUppercut=false;FinishUppercut(true);}
    if(bShadowStep){bShadowStep=false;FinishShadowStep(true);}
    if(bHeavyAttack){bHeavyAttack=false;FinishHeavy(true);}
    FinishWhirlwind();
    MainModules.Clear(Blade);OffhandModules.Clear(OffhandBlade);
    if(Blade)Blade->DestroyComponent();
    if(OffhandBlade)OffhandBlade->DestroyComponent();
    if(RiftVisual)RiftVisual->DestroyComponent();
    if(SkillRiftVisual)SkillRiftVisual->DestroyComponent();
    if(Viewmodel)Viewmodel->DestroyComponent();
    if(JumpRoot)JumpRoot->DestroyComponent();
    Super::EndPlay(Reason);
}

void UKukriWeaponComponent::BeginPrimaryAttack()
{
    auto* P=Pawn();
    if(bShadowStep)
    {
        if(TryTriggerShadowStepFollowup())return;
        if(!CanCancelShadowStepRecovery())return;
        bShadowStep=false;FinishShadowStep(true);HitActors.Reset();OffhandHitActors.Reset();
    }
    if(!IsEquipped()||!P||!Viewmodel||!CanUse()||bEquipping||bDashAttack||bQuickCombat||bUppercut||bHeavyCharging||bHeavyAttack||bWhirlwind||bShadowStep||
        P->IsSpellGestureBlocking()||UFPSPotionUseComponent::BlocksWeaponAttack(P))return;
    if(const auto* Health=P->FindComponentByClass<UFPSCombatHealthComponent>();Health&&Health->IsDead())return;
    if(bAttacking)
    {
        // Two-handed cadence (V11): one click buffered after this stage's contact; the next stage starts when
        // this one is back on the stance, so every stage keeps its full recovery as the attack interval.  The dual
        // sweep buffers after its second (left) contact.
        const float BufferOpen=bDualThrust?KukriRhythm::DualThrustBufferOpen:
            KukriRhythm::Swings[Stage].BufferOpen+(bDualSweep?KukriRhythm::DualSweepOffset(Stage):0.f);
        if(Elapsed>=BufferOpen)bQueued=true;
        return;
    }
    // Heavy strike learned: the press starts the charge and the release decides (KukriHeavy.cpp ReleasePrimaryAttack).
    if(CanBeginHeavyCharge()){BeginHeavyCharge();return;}
    StartComboClick();
}

void UKukriWeaponComponent::StartComboClick()
{
    // Shortly after a swing the combo continues; after a pause it starts over (RuneSword NextSlash rule).
    const bool bContinue=LastAttackEnd>=0.&&GetWorld()&&GetWorld()->GetTimeSeconds()-LastAttackEnd<=KukriRhythm::ComboResetSeconds;
    StartAttack(bContinue?NextStage:0);
}

void UKukriWeaponComponent::StartAttack(int32 NewStage)
{
    auto* P=Pawn();
    auto* Profile=GetWorld()&&GetWorld()->GetGameInstance()?GetWorld()->GetGameInstance()->GetSubsystem<UColdSteelStatusModel>():nullptr;
    const auto* Item=Profile?Profile->ActiveKukriWeapon():nullptr;
    bQueued=false;
    if(!P||!Item||Item->InstanceId!=InstanceId)return;
    NewStage=FMath::Clamp(NewStage,0,KukriRhythm::SwingCount-1);
    // Camera continuity if a stage is ever entered mid-swing: carry the outgoing offset and blend it out.
    // (V11 stages hand over on the stance, where every swing curve is back at zero.)
    FRotator OldCamera=FRotator::ZeroRotator;float OldFov=0.f;
    const bool bChain=bAttacking;
    if(bChain)
    {
        if(bDualSweep)KukriRhythm::DualSweepCamera(Stage,Elapsed,OldCamera,OldFov);
        else if(IsHatchetDualChop())PairChopCamera(Elapsed,OldCamera,OldFov);
        else if(bDualThrust)KukriRhythm::DualThrustCamera(Elapsed,OldCamera,OldFov);
        else StageSwingCamera(Stage,Elapsed,OldCamera,OldFov);
    }
    const auto* OffItem=IsDual()?ColdSteelMelee::PairedOneHandedWeapon(Item,Profile):nullptr;
    const bool DualSweep=OffItem&&NewStage<KukriRhythm::DualSweepStages&&Animations.FindRef(KukriDualAttacks[NewStage]);
    const bool DualThrust=OffItem&&NewStage==2&&Animations.FindRef(KukriDualThrust);
    // Hatchets on the double thrust (same gameplay clock): two hatchets chop down together; a hatchet + kukri pair chops
    // with the hatchet hand and thrusts with the kukri hand (HatchetPairRhythm.h).
    const bool MainHatchet=ColdSteelInventory::Text(*Item,TEXT("weaponType"))==TEXT("hatchet");
    const bool OffHatchet=OffItem&&ColdSteelInventory::Text(*OffItem,TEXT("weaponType"))==TEXT("hatchet");
    const FName PairClip=MainHatchet&&OffHatchet?KukriHatchetDualAttack3:MainHatchet?KukriPairAttack3HK:
        OffHatchet?KukriPairAttack3KH:NAME_None;
    const bool PairChop=DualThrust&&!PairClip.IsNone()&&Animations.FindRef(PairClip)&&(!(MainHatchet&&OffHatchet)||bHatchetChop);
    if(OffItem&&!DualSweep&&!DualThrust)return;
    // Debit the action once, including misses; each participating blade contributes its own half.
    const float Cost=ColdSteelMelee::ComboAttackStamina(Item,Profile,DualSweep||DualThrust);
    auto* Net=P->GetLocalRole()==ROLE_AutonomousProxy?P->GetPlayerState<AColdSteelPlayerState>():nullptr;
    if(P->GetLocalRole()==ROLE_AutonomousProxy&&!Net)return;
    if(Net?!Profile->CanSpendStamina(Cost):!Profile->SpendStamina(Cost))return;
    if(bChain)
    {
        FRotator NewCamera;float NewFov=0.f;
        StageSwingCamera(NewStage,0.f,NewCamera,NewFov);
        const float OldKeep=CameraCarryAge>=0.f?1.f-FMath::SmoothStep(0.f,1.f,CameraCarryAge/KukriRhythm::CameraCarrySeconds):0.f;
        CameraCarry=OldCamera+CameraCarry*OldKeep-NewCamera;CameraCarryFov=OldFov+CameraCarryFov*OldKeep-NewFov;CameraCarryAge=0.f;
    }
    Stage=NewStage;
    // Snapshot at swing start: damage, speed and reach stay fixed for this swing.
    const auto Stats=ColdSteelMelee::Evaluate(*Item,Profile);
    SwingDamage=Stats.Damage;
    // AttackRate is normalised to the sword's 1.775 s clip; the base product is this clip's authored length over the
    // item's attack_seconds (0.8 since 2026-10-26, user-set: ~1.58), and aspd/mastery/haste scale from there.
    PlayRate=KukriAttackTiming::PlayRate(Stats.AttackRate);
    Reach=Stats.BaseReach>0.?float(Stats.BaseReach):KukriRhythm::DefaultReachCM;
    Shot=ColdSteelSkills::Snapshot(P,Item);
    Shot.bRifle=false;Shot.bPistol=false;Shot.WeakpointPercent=0;
    Shot.AttackForm=KukriRhythm::Form;Shot.bMeleeStrike=true;
    if(DualSweep||DualThrust)
    {
        const auto OffStats=ColdSteelMelee::Evaluate(*OffItem,Profile);
        OffhandSwingDamage=OffStats.Damage;
        OffhandReach=OffStats.BaseReach>0.?float(OffStats.BaseReach):KukriRhythm::DefaultReachCM;
        OffhandPlayRate=KukriAttackTiming::PlayRate(OffStats.AttackRate);
        OffhandShot=ColdSteelSkills::Snapshot(P,OffItem);
        OffhandShot.bRifle=false;OffhandShot.bPistol=false;OffhandShot.WeakpointPercent=0;
        OffhandShot.AttackForm=KukriRhythm::Form;OffhandShot.bMeleeStrike=true;
        // One paired action, one mastery serial: the authority counts each target once across both blades.
        OffhandShot.MasteryAttackSerial=Shot.MasteryAttackSerial;
        // Simultaneous thrust has one pose clock: average the two independently calculated durations.
        // Sequential sweeps use each hand's own rate, switching at BeginOffhandSwing.
        if(DualThrust)PlayRate=KukriAttackTiming::PairedPlayRate(PlayRate,OffhandPlayRate);
    }
    if(Net)
    {
        Shot.KukriAttackSerial=Net->RequestKukriAttack(InstanceId,OffItem?OffItem->InstanceId:FString(),
            uint8(NewStage),false,P->GetMeleeAimTransform().GetUnitAxis(EAxis::X),Shot.MasteryAttackSerial);
        OffhandShot.KukriAttackSerial=Shot.KukriAttackSerial;
        if(!Shot.KukriAttackSerial)return;
    }
    bAttacking=true;bSwingPlayed=false;bImpactConfirmed=false;bWallHit=false;
    if(auto* Pendant=P->FindComponentByClass<UKukriDecisiveComponent>())Pendant->BeginLocal(Shot,false,OffItem?OffItem->InstanceId:FString());
    HitActors.Reset();HitStop=0.f;
    // Each blade keeps its own damage, toughness and item identity throughout the paired action.
    bDualSweep=DualSweep;bOffhandSwing=false;
    // ...and the stab becomes the double thrust (both blades at once, own clock, stride, knockback and camera).
    bDualThrust=DualThrust;bChopRight=PairChop&&MainHatchet;bChopLeft=PairChop&&OffHatchet;bDualChop=bChopRight&&bChopLeft;
    bDualThrustLungeStarted=bDualThrustLungeBlocked=false;OffhandHitActors.Reset();
    // V11: every stage starts and ends on the stance; the short local-space entry blend absorbs the idle/walk
    // offset when a swing starts from locomotion (a stage-to-stage hand-over is stance to stance).
    SetClip(bDualSweep?KukriDualAttacks[Stage]:PairChop?PairClip:bDualThrust?KukriDualThrust:FName(SwingProfile().Clip),false,
        KukriRhythm::EntryBlendSeconds);
    PreviousOffhandBlade=OffhandBladeFrame();
    PreviousBlade=BladeFrame();bHavePreviousBlade=true;
    ResetStrike();
}

void UKukriWeaponComponent::CancelAction()
{
    FlushPairedHeavyContacts(true);
    if(bFalconHeavy)ResetFalconHooks();
    FinishNetworkAttack(true);
    const bool WasActive=bAttacking||bEquipping||bDashAttack||bQuickCombat||bUppercut||bHeavyCharging||bHeavyAttack||bWhirlwind||bShadowStep;
    // A cancelled whirlwind keeps its paid stamina and cooldown; hits that already landed still train (one exit path).
    FinishWhirlwind();
    // A cancelled charge bills nothing more (its camera eases out); a cancelled release keeps its paid stamina and trains once.
    const bool bWasCharging=bHeavyCharging;
    if(bWasCharging)(bFalconHeavy?SwiftFalconHeavy::ChargeCamera:bDualHeavy?KukriHeavyRhythm::DualChargeCamera:KukriHeavyRhythm::ChargeCamera)(Elapsed,CameraCarry,CameraCarryFov);
    SetHeavyCharging(false,false);bHeavyAuto=bHeavyFull=false;
    if(bHeavyAttack){
        if(bFalconHeavy&&Pawn()&&Pawn()->IsLocallyControlled()&&!Pawn()->HasAuthority())
            ServerSetKukriHeavyCharge(InstanceId,false,false,bDualHeavy,0.);
        bHeavyAttack=false;FinishHeavy(true);
    }
    bDualHeavy=bFalconHeavy=false;
    // A cancelled sprint attack keeps its paid stamina; hits that already landed still train the skill.
    bDashAttack=bDualDash=false;FinishDashAttack();DashSprintSeconds=0.f;
    // A cancelled quick melee keeps its paid stamina and releases F (only this component's own cast).
    if(bQuickCombat){bQuickCombat=false;FinishQuickCombat();}
    // A cancelled uppercut keeps its paid release and still trains once (the sword's rule).
    if(bUppercut){bUppercut=false;FinishUppercut(true);}
    // A cancelled ShadowStep settles its paid cast and clears any active follow-up window / focus blur.
    if(bShadowStep){bShadowStep=false;FinishShadowStep(true);}
    bAttacking=false;bEquipping=false;bQueued=false;Stage=0;NextStage=0;LastAttackEnd=-1.;CameraCarryAge=bWasCharging?0.f:-1.f;
    bDualSweep=bOffhandSwing=bDualThrust=bDualChop=bChopRight=bChopLeft=false;OffhandHitActors.Reset();
    HitStop=0.f;HitActors.Reset();bHavePreviousBlade=false;
    ResetStrike();StrikeAge=-1.f;StopRift();StopSkillRift();
    if(WasActive&&IsEquipped()&&Viewmodel&&Animations.Num())
        SetClip(LocomotionClip(),true,KukriRhythm::EntryBlendSeconds);
    UpdateOffhandDraw();
}

void UKukriWeaponComponent::ConfirmImpact(const FHitResult& Hit,bool bWorld)
{
    const auto& K=StrikeProfile();
    if(K.At>0.f&&!bStrikeDone)
    {
        // Found before the impact moment (stab: during the drive; slashes: before the blade crosses the centre) --
        // the cue waits for it (ArriveStrike); damage has already been applied.
        if(bWorld){if(!bPendingWall){bPendingWall=true;PendingWallHit=Hit;}}
        else if(!bPendingFlesh){bPendingFlesh=true;PendingFleshHit=Hit;}
        return;
    }
    if(bWorld)
    {
        if(bWallHit||bImpactConfirmed)return;
        bWallHit=true;HitStop=KukriRhythm::WallStopSeconds;ImpactAge=0.f;ImpactKick=.7f;
        if(bFalconHeavy&&bHeavyAttack)HitStop=Shot.MeleeDamagePhase?.065f:.085f;
        if(WallSound)UGameplayStatics::PlaySoundAtLocation(this,WallSound,Hit.ImpactPoint,.55f,1.15f);
        return;
    }
    // One confirmed-hit cue per swing; every target still gets its own damage receipt.
    if(bImpactConfirmed)return;
    // The double thrust lands both blades at once: a harder stop and a bigger jolt than the single stab.
    bImpactConfirmed=true;ImpactAge=0.f;
    HitStop=KukriRhythm::FleshStopSeconds*(IsHatchetDualChop()?HatchetDualChopRhythm::HitStopScale:
        bDualThrust?KukriRhythm::DualThrustHitStopScale:
        bDualHeavy&&bHeavyAttack?KukriRhythm::DualHeavyHitStopScale:SwingProfile().HitStopScale);
    ImpactKick=KukriRhythm::ImpactKick*(IsHatchetDualChop()?HatchetDualChopRhythm::ImpactScale:
        bDualThrust?KukriRhythm::DualThrustImpactScale:SwingProfile().ImpactScale);
    if(bFalconHeavy&&bHeavyAttack)
    {
        HitStop=SwiftFalconHeavy::FleshStop(Shot.MeleeDamagePhase==1,bDualHeavy);
        ImpactKick=KukriRhythm::ImpactKick*SwiftFalconHeavy::ContactStrength(Shot.MeleeDamagePhase==1,bDualHeavy);
    }
    if(HitSound)UGameplayStatics::PlaySoundAtLocation(this,HitSound,Hit.ImpactPoint,.95f,1.04f);
    if(StabThudSounds.Num())
        UGameplayStatics::PlaySoundAtLocation(this,StabThudSounds[FMath::RandRange(0,StabThudSounds.Num()-1)],Hit.ImpactPoint,
            KukriRhythm::StabThudVolume,KukriRhythm::StabThudPitch);
    bPressIn=K.PressX!=0.f||K.PressY!=0.f||K.PressZ!=0.f;PressStop=HitStop;
}

void UKukriWeaponComponent::TraceBlade(const FTransform& From,const FTransform& To,bool UseOffhand)
{
    auto* P=Pawn();
    UWorld* World=GetWorld();
    if(!P||!World)return;
    const bool Left=(bAttacking&&bDualSweep&&bOffhandSwing)||
        (UseOffhand&&((bAttacking&&bDualThrust)||(bHeavyAttack&&bDualHeavy)));
    // The off-hand kukri was put away mid-action: its (hidden) blade cuts nothing for the rest of the clip.
    if(Left&&!IsDual())return;
    const auto& HitShot=Left?OffhandShot:Shot;
    const float Damage=Left?OffhandSwingDamage:SwingDamage;
    const float BladeReach=Left?OffhandReach:Reach;
    const FTransform Aim=P->GetMeleeAimTransform();
    const auto& BladeModules=Left||bLoneOffhand?OffhandModules:MainModules;
    const FVector Probe=To.TransformPosition(bHeavyAttack&&bFalconHeavy?
        .5f*(BladeModules.TraceBase+BladeModules.TraceTip):KukriRhythm::BladeMid);
    TArray<FHitResult,TInlineAllocator<8>> Contacts;
    // Targets: forward area from the blade's current position (cleave, low targets, cover).
    const float Forward=FVector::DotProduct(Probe-Aim.GetLocation(),Aim.GetUnitAxis(EAxis::X));
    const float QueryWidthScale=bAttacking?KukriRhythm::BasicAttackQueryWidthScale:1.f;
    if(Forward>=0.f)
        Contacts.Append(MeleeSmallTargets::QueryQuickAreaContacts(World,P,Aim,Probe,FMath::Max(40.f,BladeReach-Forward),
            KukriRhythm::QueryRadiusCM*QueryWidthScale,MeleeSmallTargets::LowArcDegrees*QueryWidthScale));
    // Scenery: the real edge from root to tip, swept between substeps.
    // Visual length affects scenery contacts only; enemy reach remains BladeReach.
    FFPSAttackQuery Q(SCENE_QUERY_STAT(KukriSwing),false,GetOwner());
    Q.bReturnPhysicalMaterial=true;Q.bReturnFaceIndex=true;
    for(const auto& Actor:HitActors)if(Actor.IsValid())Q.AddIgnoredActor(Actor.Get());
    for(int32 Segment=0;Segment<=3;++Segment)
    {
        const FVector Local=FMath::Lerp(BladeModules.TraceBase,BladeModules.TraceTip,Segment/3.f);
        FHitResult Hit;
        if(World->SweepSingleByChannel(Hit,From.TransformPosition(Local),To.TransformPosition(Local),FQuat::Identity,
            ECC_Visibility,FCollisionShape::MakeSphere(2.5f),Q))
            if(const auto* Actor=Hit.GetActor();Actor&&!Actor->FindComponentByClass<UMonsterCombatComponent>())Contacts.Add(Hit);
    }
    Contacts.Sort([](const FHitResult& A,const FHitResult& B){return A.Time<B.Time;});
    for(const auto& Hit:Contacts)
    {
        auto* Actor=Hit.GetActor();
        if(!Actor||Actor->ActorHasTag(TEXT("Friendly"))||HitActors.Contains(Actor))continue;
        const FVector Direction=(Hit.TraceEnd-Hit.TraceStart).GetSafeNormal();
        auto* Combat=Actor->FindComponentByClass<UMonsterCombatComponent>();
        if(!Combat)
        {
            UWardBreakableGlass::BreakHit(Hit,Direction);
            // Scenery comes back on every substep while the blade rests against it: one cue and one burst per swing.
            const bool bFirstWall=!bWallHit&&!bImpactConfirmed&&!bPendingWall;
            ConfirmImpact(Hit,true);
            if(bFirstWall)QueueContactFX(Hit,true);
            continue;
        }
        // The uppercut is single-target, like the sword and hammer uppercuts.
        if(bUppercut&&!HitActors.IsEmpty())break;
        HitActors.Add(Actor);
        if(Combat->IsDead())continue;
        FHitResult EdgeHit=Hit;
        const FVector MidEdge=(BladeModules.TraceBase+BladeModules.TraceTip)*.5f;
        EdgeHit.TraceStart=From.TransformPosition(MidEdge);EdgeHit.TraceEnd=To.TransformPosition(MidEdge);
        if(bHeavyAttack&&bDualHeavy)
        {
            auto& Pair=PairedHeavyContacts.FindOrAdd(Actor);
            const int32 Hand=Left?1:0;
            Pair.Blades[Hand]={Hit,Direction,Damage,HitShot};Pair.Mask|=1<<Hand;
            if(bFalconHeavy&&!Pair.bContactPresented)
            {
                // Present the confirmed blade collision on its authored strike beat, even if only one blade hits.
                // Keep the paired damage receipt pending so a later second blade still contributes exactly once.
                Pair.bContactPresented=true;ConfirmImpact(Hit,false);
                if(P->HasAuthority())QueueContactFX(EdgeHit,false);
            }
            continue;
        }
        const bool bHeavyVictim=bHeavyAttack&&bHeavyTrainingPending&&ColdSteelSkills::IsMasteryTrainingTarget(P,Actor);
        FWeaponDamageResult Receipt;
        const float Applied=ColdSteelSkills::ApplyHit(GetOwner(),Hit,Damage,Direction,HitShot,&Receipt);
        // Hit cue: damage was dealt, or this hit killed the target.
        if(Applied>0.f||Combat->IsDead())
        {
            ConfirmImpact(Hit,false);
            if(P->HasAuthority())QueueContactFX(EdgeHit,false);
            P->NotifyConfirmedWeaponHit(Actor,Applied,&Receipt,false);
            // The dual X cuts each target with both blades: a victim trains the heavy strike once (the other blade's set).
            if(bHeavyVictim)CountHeavyVictim(Actor,Combat->IsDead());
            // The double thrust drives the target back (the reference's dummy flies off); authority-side push.
            if(bDualThrust&&!Combat->IsDead())Combat->ReceiveMeleeKnockback(P,KukriRhythm::DualThrustKnockbackCM);
        }
    }
}

void UKukriWeaponComponent::AdvanceAttack(float Delta)
{
    float Remaining=Delta;
    int32 Guard=0;
    while(Remaining>UE_SMALL_NUMBER&&bAttacking&&++Guard<64)
    {
        if(HitStop>0.f)
        {
            const float Pause=FMath::Min(Remaining,HitStop);
            HitStop-=Pause;Remaining-=Pause;
            continue;
        }
        const float Length=bDualThrust?KukriRhythm::DualThrustSeconds:
            CurrentAnimation?CurrentAnimation->GetPlayLength():KukriRhythm::AttackSeconds;
        // Author-time substeps (<= 1/120 s) that land exactly on every phase boundary.
        const KukriRhythm::FSwing& S0=SwingProfile();
        // Dual sweep: the left blade's swing is the same stage again, its DualSweepOffset later (author_dual_attack.py).
        const float Off=bOffhandSwing?KukriRhythm::DualSweepOffset(Stage):0.f;
        KukriRhythm::FSwing S=S0;
        S.SwingSound+=Off;S.ContactStart+=Off;S.ContactEnd+=Off;
        if(bDualThrust)
        {
            // The double thrust runs on its own authored phases (KukriRhythm::DualThrust*: no tempo curve, no rift).
            S.SwingSound=KukriRhythm::DualThrustSwingSound;
            S.ContactStart=KukriRhythm::DualThrustContactStart;S.ContactEnd=KukriRhythm::DualThrustContactEnd;
            // The dual chop's whoosh comes with its heads over the top (a local cue; the windows stay the thrust's) -- also
            // when only one hand of a hatchet + kukri pair chops.
            if(IsHatchetDualChop())S.SwingSound=HatchetDualChopRhythm::SwingSound;
        }
        // V12b: the stab slows its visible phases on a smooth tempo curve (KukriRhythm::StageTempo); substeps are
        // <= 1/120 author s, so the rate is sampled finely enough for the SmoothStep blends between knots.
        const float Rate=PlayRate*(bDualThrust?1.f:bDualSweep?KukriRhythm::DualSweepTempo(Stage,Elapsed):KukriRhythm::StageTempo(Stage,Elapsed));
        float Step=FMath::Min(Remaining*Rate,1.f/120.f);
        const float StrikeAt=bDualThrust?KukriRhythm::DualThrustStrikeAt:StrikeProfile().At+Off;
        const float RiftAt=bDualThrust?(IsHatchetDualChop()?HatchetDualChopRhythm::Rift.Start:Length+1.f):RiftProfile().Start+Off;
        const float HandOver=bDualSweep&&!bOffhandSwing?KukriRhythm::DualSweepOffset(Stage):Length;
        for(const float Boundary:{S.SwingSound,S.ContactStart,S.ContactEnd,StrikeAt,RiftAt,HandOver,Length})
            if(Elapsed<Boundary-UE_KINDA_SMALL_NUMBER)Step=FMath::Min(Step,Boundary-Elapsed);
        Step=FMath::Max(Step,1e-4f);
        const float Before=Elapsed;
        Elapsed=FMath::Min(Length,Elapsed+Step);
        Remaining=FMath::Max(0.f,Remaining-(Elapsed-Before)/Rate);
        SamplePose(Elapsed);
        // The right swing is done (contact, strike and rift all behind it): the cues, the contact set and the traced blade
        // go over to the left kukri.  The next boundaries of this step use the left phases.
        if(bDualSweep&&!bOffhandSwing&&Elapsed>=HandOver-UE_KINDA_SMALL_NUMBER){BeginOffhandSwing();continue;}
        const FTransform Now=bOffhandSwing?OffhandBladeFrame():BladeFrame();
        if(!bSwingPlayed&&Elapsed>=S.SwingSound-UE_KINDA_SMALL_NUMBER)
        {
            bSwingPlayed=true;
            // The stab plays a short sharp whoosh on its drive instead of the item swing sound.
            const bool bWhoosh=StrikeProfile().bWhoosh&&StabWhooshSound;
            USoundBase* Cue=bWhoosh?StabWhooshSound.Get():SwingSound.Get();
            if(Cue)UGameplayStatics::PlaySound2D(this,Cue,bWhoosh?KukriRhythm::StabWhooshVolume:.55f,
                S.SwingPitch*FMath::Clamp(PlayRate,.85f,1.3f));
        }
        const bool bInContact=Before>=S.ContactStart-UE_KINDA_SMALL_NUMBER&&Before<S.ContactEnd;
        if(bHavePreviousBlade&&bInContact)TraceBlade(PreviousBlade,Now);
        if(bDualThrust)
        {
            // The left blade drives in the same window with its own contact set: each blade cuts each target once.
            const FTransform NowLeft=OffhandBladeFrame();
            if(bInContact){Swap(HitActors,OffhandHitActors);TraceBlade(PreviousOffhandBlade,NowLeft,true);Swap(HitActors,OffhandHitActors);}
            PreviousOffhandBlade=NowLeft;
            AdvanceDualThrustLunge(Before,Elapsed);
        }
        if(StrikeAt>0.f&&!bStrikeDone&&Elapsed>=StrikeAt-UE_KINDA_SMALL_NUMBER)ArriveStrike();
        if(!bRiftStarted&&Elapsed>=RiftAt-UE_KINDA_SMALL_NUMBER){bRiftStarted=true;StartRift();}
        PreviousBlade=Now;bHavePreviousBlade=true;
        if(Elapsed>=Length-UE_KINDA_SMALL_NUMBER)
        {
            // Back on the stance: the full recovery was this stage's attack interval.  A buffered click starts
            // the next stage now (3 -> 1); otherwise the next click within ComboResetSeconds still continues.
            const bool bNext=bQueued;
            FinishNetworkAttack();
            bAttacking=false;HitActors.Reset();bDualSweep=bOffhandSwing=bDualThrust=bDualChop=bChopRight=bChopLeft=false;
            OffhandHitActors.Reset();
            NextStage=(Stage+1)%KukriRhythm::SwingCount;
            LastAttackEnd=GetWorld()?GetWorld()->GetTimeSeconds():0.;
            if(bNext){StartAttack(NextStage);if(bAttacking)continue;}
            SetClip(LocomotionClip(),true,KukriRhythm::EntryBlendSeconds);
        }
    }
}

void UKukriWeaponComponent::TickComponent(float Delta,ELevelTick Type,FActorComponentTickFunction* Tick)
{
    Super::TickComponent(Delta,Type,Tick);
    // Authority of a remote owner: keep its heavy charge honest (the stamina bill stops with the charge).
    if(bServerHeavyCharging&&GetOwner()&&GetOwner()->HasAuthority())TickServerHeavyCharge();
    auto* P=Pawn();
    if(bStaffOffhandWhirlwind&&P&&P->IsLocallyControlled())
    {
        if(!CanUse(true)){CancelAction();return;}
        TickSkillRift(Delta);TickWhirlwind(Delta);return;
    }
    if(!P||!Viewmodel||!IsEquipped()||!P->IsLocallyControlled())return;
    if(ImpactAge>=0.f){ImpactAge+=Delta;if(ImpactAge>.6f)ImpactAge=-1.f;}
    if(StrikeAge>=0.f){StrikeAge+=Delta;if(StrikeAge>.4f)StrikeAge=-1.f;}
    TickRift(Delta);TickSkillRift(Delta);
    if(CameraCarryAge>=0.f){CameraCarryAge+=Delta*PlayRate;if(CameraCarryAge>KukriRhythm::CameraCarrySeconds)CameraCarryAge=-1.f;}
    if(JumpRoot)
    {
        // Impact kick is a camera-aligned rotation of the presentation parent only.
        const FTransform Kick(ViewmodelKick(),StrikeViewmodelOffset());
        FTransform Presentation=Kick*P->GetWeaponJumpTransform(EFirstPersonJumpRig::Sword);
        if(bLoneOffhand)
        {
            // The lone off-hand blade's mirrored moveset: every kick, press and jump sway mirrors about the view's vertical
            // plane (camera Y), like the arms (mesh X = camera Y).
            const FQuat Q=Presentation.GetRotation();const FVector L=Presentation.GetLocation();
            Presentation.SetRotation(FQuat(-Q.X,Q.Y,-Q.Z,Q.W));Presentation.SetLocation(FVector(L.X,-L.Y,L.Z));
        }
        JumpRoot->SetRelativeTransform(Presentation);
    }
    const bool Present=CanPresent();
    FPSComponentVisibility::SetVisibilityTree(Viewmodel,Present&&Viewmodel->GetSkeletalMeshAsset());
    if(!Present){if(IsBusy())CancelAction();return;}
    if(bPendingOffhandDraw&&!IsBusy()&&!P->IsCastBlockingLeftHandAction())
    {
        const auto* Potion=P->FindComponentByClass<UFPSPotionUseComponent>();
        if(!Potion||!Potion->IsStowingOffhand())
        {
            bPendingOffhandDraw=false;bEquipping=true;
            bTossPlayed=bCatchPlayed=true;bOffhandTossPlayed=bOffhandCatchPlayed=false;
            SetClip(bOffhandHatchet?OffhandBladeDraw::Hatchet:OffhandBladeDraw::Kukri,false,.075f);UpdateOffhandDraw();
        }
    }
    UpdateOffhandBlade();
    UpdateDualFlip(Delta);
    Viewmodel->AdvanceEntry(Delta);
    if((bAttacking||bDashAttack||bQuickCombat||bUppercut||bHeavyCharging||bHeavyAttack||bWhirlwind||bShadowStep)&&!CanUse(true))CancelAction();
    TickDashReadiness(Delta);
    if(bShadowStep){AdvanceShadowStep(Delta);return;}
    if(bDashAttack){AdvanceDashAttack(Delta);return;}
    if(bQuickCombat){AdvanceQuickCombat(Delta);return;}
    if(bWhirlwind){TickWhirlwind(Delta);return;}
    if(bUppercut){AdvanceUppercut(Delta);return;}
    if(bHeavyCharging){AdvanceHeavyCharge(Delta);return;}
    if(bHeavyAttack){AdvanceHeavy(Delta);return;}
    const float Speed=LightningHaste::ActionSpeed(P);
    if(bEquipping)
    {
        Elapsed+=Delta*Speed;
        // Flick whoosh as the knife leaves the hand, a short grip slap as the handle lands in the palm (the hatchet's
        // vertical toss on its own clock, also as the right hand of a pair's draw).
        const bool bHatchetDraw=IsRightHatchetDraw(CurrentClip);
        if(!bTossPlayed&&Elapsed>=(bHatchetDraw?HatchetDrawRhythm::TossAt:KukriDrawRhythm::TossAt))
        {
            bTossPlayed=true;
            if(TossSound)UGameplayStatics::PlaySound2D(this,TossSound,bHatchetDraw?HatchetDrawRhythm::TossVolume:KukriDrawRhythm::TossVolume,
                bHatchetDraw?HatchetDrawRhythm::TossPitch:KukriDrawRhythm::TossPitch);
        }
        if(!bCatchPlayed&&Elapsed>=(bHatchetDraw?HatchetDrawRhythm::CatchAt:KukriDrawRhythm::CatchAt))
        {
            bCatchPlayed=true;
            if(CatchSound)UGameplayStatics::PlaySound2D(this,CatchSound,bHatchetDraw?HatchetDrawRhythm::CatchVolume:KukriDrawRhythm::CatchVolume,
                bHatchetDraw?HatchetDrawRhythm::CatchPitch:KukriDrawRhythm::CatchPitch);
        }
        if(IsDualEquipClip(CurrentClip))
        {
            // The left hand's toss and catch, a beat after the right's (a touch softer and lower, so the pair reads as two),
            // on its own weapon's clock.
            const bool bLeftHatchet=IsLeftHatchetDraw(CurrentClip);
            const float Left=Elapsed-(bLeftHatchet?HatchetPairRhythm::LeftDelay:KukriDualEquipBlade::LeftDelay);
            if(!bOffhandTossPlayed&&Left>=(bLeftHatchet?HatchetDrawRhythm::TossAt:KukriDrawRhythm::TossAt))
            {
                bOffhandTossPlayed=true;
                if(TossSound)UGameplayStatics::PlaySound2D(this,TossSound,
                    (bLeftHatchet?HatchetDrawRhythm::TossVolume:KukriDrawRhythm::TossVolume)*KukriDrawRhythm::OffhandVolume,
                    (bLeftHatchet?HatchetDrawRhythm::TossPitch:KukriDrawRhythm::TossPitch)*KukriDrawRhythm::OffhandPitch);
            }
            if(!bOffhandCatchPlayed&&Left>=(bLeftHatchet?HatchetDrawRhythm::CatchAt:KukriDrawRhythm::CatchAt))
            {
                bOffhandCatchPlayed=true;
                if(CatchSound)UGameplayStatics::PlaySound2D(this,CatchSound,
                    (bLeftHatchet?HatchetDrawRhythm::CatchVolume:KukriDrawRhythm::CatchVolume)*KukriDrawRhythm::OffhandVolume,
                    (bLeftHatchet?HatchetDrawRhythm::CatchPitch:KukriDrawRhythm::CatchPitch)*KukriDrawRhythm::OffhandPitch);
            }
        }
        const float Length=CurrentAnimation?CurrentAnimation->GetPlayLength():KukriDrawRhythm::Seconds;
        if(Elapsed>=Length){bEquipping=false;SetClip(LocomotionClip(),true,KukriRhythm::EntryBlendSeconds);}
        else SamplePose(Elapsed);
        UpdateOffhandDraw();
        return;
    }
    if(bAttacking){AdvanceAttack(Delta);return;}
    // Dual hatchets' sprint-ready run set (enter / raised loop / exit) owns the locomotion while it plays.
    if(TickReadyRun(Delta))return;
    const FName Want=LocomotionClip();
    if(Want!=CurrentClip)
        SetClip(Want,true,(Want==KukriDualRun||CurrentClip==KukriDualRun)?KukriDualRunBlendSeconds:
            (IsRunClip(Want)||IsRunClip(CurrentClip))?KukriRhythm::SprintBlendSeconds:KukriRhythm::EntryBlendSeconds);
    if(!CurrentAnimation)return;
    float Rate=1.f;
    if(IsWalkClip(CurrentClip))Rate=FMath::Clamp(P->GetVelocity().Size2D()/KukriWalkReferenceSpeed,.6f,1.4f);
    Elapsed=FMath::Fmod(Elapsed+Delta*Rate,FMath::Max(.01f,CurrentAnimation->GetPlayLength()));
    SamplePose(Elapsed);
}
