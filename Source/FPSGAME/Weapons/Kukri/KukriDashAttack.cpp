#include "KukriWeaponComponent.h"
#include "KukriArmsMeshComponent.h"
#include "KukriRhythm.h"
#include "KukriDashRhythm.h"
#include "../RuneSwordHitQuery.h"
#include "../../Combat/WeaponDamageTypes.h"
#include "../../Skills/ColdSteelSkillRules.h"
#include "../../Skills/LightningHasteSpeed.h"
#include "../../FPSGAMECharacter.h"
#include "../../UI/ColdSteelStatusModel.h"
#include "../../Monsters/MonsterCombatComponent.h"
#include "../../Monsters/BoundCongregateCaptureComponent.h"
#include "Animation/AnimSequence.h"
#include "Engine/GameInstance.h"
#include "Engine/World.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "Kismet/GameplayStatics.h"
#include "Sound/SoundBase.h"

// Sprint attack (passive skill dashAttack, Docs/Skills/dash-attack-migration-20260920.md) for the kukri: same readiness,
// cost, damage, sector, knockback and training contract as the sword's (RuneSwordDashAttack.cpp); the motion is the
// reference two-handed jump chop (KukriDashRhythm.h).  The character owns the movement hand-over (FirePressed).

namespace
{
const FName KukriDashClip(TEXT("SprintAttack"));

UColdSteelStatusModel* KukriDashProfile(const UWorld* World)
{
    return World&&World->GetGameInstance()?World->GetGameInstance()->GetSubsystem<UColdSteelStatusModel>():nullptr;
}

float KukriDashReadySeconds(const UColdSteelStatusModel* Profile)
{
    const auto& D=Profile->MasteryDefinition(TEXT("dashAttack"));
    const int32 Level=FMath::Clamp(Profile->MasteryProgress(D.Id).Level,1,D.MaxLevel);
    // Readiness depends on the skill level only; no per-frame weapon formula evaluation.
    return FMath::Max(.01f,D.DashAttack.ReadySeconds*(1.f-(Level-1)*D.DashAttack.ReadyReductionPerLevel));
}
}

void UKukriWeaponComponent::TickDashReadiness(float Delta)
{
    const auto* P=Pawn();
    const auto* Profile=KukriDashProfile(GetWorld());
    // Shift release resets the charge (AFPSGAMECharacter::SprintReleased -> ResetDashReadiness).
    const bool Eligible=P&&IsEquipped()&&!IsBusy()&&CanUse()&&Animations.FindRef(KukriDashClip)&&
        !P->IsCastBlockingLeftHandAction()&&!P->IsDodging()&&
        Profile&&!Profile->ActiveProductionTool()&&Profile->MasteryProgress(TEXT("dashAttack")).Level>0;
    if(!Eligible){ResetDashReadiness();return;}
    const float ReadySeconds=KukriDashReadySeconds(Profile);
    const auto* Movement=P->GetCharacterMovement();
    const bool bGroundSprint=P->IsSprinting()&&!P->IsSliding()&&Movement->IsMovingOnGround()&&
        P->GetVelocity().SizeSquared2D()>2500.f;
    // An earned charge survives a slide or slide-jump (including the pending LaunchCharacter frame).
    const bool bSlideOrJump=P->IsSliding()||Movement->IsFalling()||P->bWeaponJumpAirborne||
        !Movement->PendingLaunchVelocity.IsZero();
    if(DashSprintSeconds>=ReadySeconds&&bSlideOrJump){DashSprintSeconds=ReadySeconds;return;}
    DashSprintSeconds=bGroundSprint?FMath::Min(DashSprintSeconds+Delta,ReadySeconds):0.f;
}

float UKukriWeaponComponent::DashReadyFraction() const
{
    const auto* P=Pawn();
    if(DashSprintSeconds<=0.f||!P||IsBusy())return 0.f;
    const auto* Profile=KukriDashProfile(GetWorld());
    if(!Profile)return 0.f;
    const float ReadySeconds=KukriDashReadySeconds(Profile);
    const auto* Movement=P->GetCharacterMovement();
    const bool bRetainedReady=DashSprintSeconds>=ReadySeconds&&
        (P->IsSliding()||Movement->IsFalling()||P->bWeaponJumpAirborne||!Movement->PendingLaunchVelocity.IsZero());
    if(!bRetainedReady&&(!P->IsSprinting()||!Movement->IsMovingOnGround()||P->GetVelocity().SizeSquared2D()<=2500.f))return 0.f;
    return FMath::Clamp(DashSprintSeconds/ReadySeconds,0.f,1.f);
}

bool UKukriWeaponComponent::TryBeginDashAttack()
{
    auto* P=Pawn();
    if(!P||UBoundCongregateCaptureComponent::IsCaptured(P))return false;
    if(!IsEquipped()||IsBusy()||!CanUse()||!Viewmodel||!Animations.FindRef(KukriDashClip)||
        P->IsCastBlockingLeftHandAction()||P->IsDodging()||P->IsSpellGestureBlocking())return false;
    auto* Profile=KukriDashProfile(GetWorld());
    const auto* Item=Profile?Profile->Equipped():nullptr;
    if(!Item||Item->InstanceId!=InstanceId||Profile->ActiveProductionTool()||Profile->MasteryProgress(TEXT("dashAttack")).Level<1)return false;
    if(DashReadyFraction()<1.f-UE_SMALL_NUMBER)return false;
    const FDashAttackCast Cast=Profile->DashAttackStats();
    // The skill cost replaces this swing's ordinary cost and is paid once; without it nothing starts (a ready click
    // never falls back to an ordinary swing).
    if(!Profile->SpendStamina(Cast.StaminaCost))return false;
    Shot=ColdSteelSkills::Snapshot(P,Item);
    Shot.bRifle=false;Shot.bPistol=false;Shot.WeakpointPercent=0;
    Shot.AttackForm=KukriRhythm::Form;Shot.bMeleeStrike=true;
    Shot.AttackMeta=0x16;            // active dash skill (authority uses DashAttackStats for range and damage)
    SwingDamage=Cast.Damage;DashRangeCM=Cast.RangeCM;DashArcDegrees=Cast.ArcDegrees;DashKnockbackCM=Cast.KnockbackCM;
    DashDirection=P->GetMeleeAimTransform().GetUnitAxis(EAxis::X).GetSafeNormal2D();
    bDashAttack=bDashTrainingPending=true;DashHits=DashKills=0;DashSprintSeconds=0.f;
    bSwingPlayed=bImpactConfirmed=bWallHit=false;HitActors.Reset();HitStop=0.f;
    // The swing combo starts over after the sprint attack.
    NextStage=0;LastAttackEnd=-1.;
    // From the sprint carry (or idle/walk) into the clip's stance start.
    SetClip(KukriDashClip,false,KukriRhythm::SprintBlendSeconds);
    return true;
}

void UKukriWeaponComponent::AdvanceDashAttack(float Delta)
{
    auto* P=Pawn();
    // Martial-skill clock: independent of weapon attack speed, only Lightning Haste scales it.
    const float Rate=FMath::Max(.05f,LightningHaste::ActionSpeed(P));
    float Remaining=Delta;
    int32 Guard=0;
    while(Remaining>UE_SMALL_NUMBER&&bDashAttack&&++Guard<64)
    {
        if(HitStop>0.f)
        {
            const float Pause=FMath::Min(Remaining,HitStop);
            HitStop-=Pause;Remaining-=Pause;
            continue;
        }
        const float Length=CurrentAnimation?CurrentAnimation->GetPlayLength():KukriDashRhythm::Seconds;
        float Step=FMath::Min(Remaining*Rate,1.f/120.f);
        for(const float Boundary:{KukriDashRhythm::SwingSound,KukriDashRhythm::RiftStart,KukriDashRhythm::ContactStart,KukriDashRhythm::ContactEnd,Length})
            if(Elapsed<Boundary-UE_KINDA_SMALL_NUMBER)Step=FMath::Min(Step,Boundary-Elapsed);
        Step=FMath::Max(Step,1e-4f);
        const float Before=Elapsed;
        Elapsed=FMath::Min(Length,Elapsed+Step);
        Remaining=FMath::Max(0.f,Remaining-(Elapsed-Before)/Rate);
        SamplePose(Elapsed);
        if(!bSwingPlayed&&Elapsed>=KukriDashRhythm::SwingSound-UE_KINDA_SMALL_NUMBER)
        {
            bSwingPlayed=true;
            if(SwingSound)UGameplayStatics::PlaySound2D(this,SwingSound,.62f,KukriDashRhythm::SwingPitch);
        }
        // The chop's space distortion, hit or miss, when the blade comes over the top (KukriSkillRift.cpp).
        if(Before<KukriDashRhythm::RiftStart-UE_KINDA_SMALL_NUMBER&&Elapsed>=KukriDashRhythm::RiftStart-UE_KINDA_SMALL_NUMBER)StartDashRift();
        if(Before>=KukriDashRhythm::ContactStart-UE_KINDA_SMALL_NUMBER&&Before<KukriDashRhythm::ContactEnd)DashContact();
        if(Elapsed>=Length-UE_KINDA_SMALL_NUMBER)
        {
            bDashAttack=false;HitActors.Reset();
            FinishDashAttack();
            SetClip(LocomotionClip(),true,KukriRhythm::EntryBlendSeconds);
        }
    }
}

void UKukriWeaponComponent::DashContact()
{
    auto* P=Pawn();
    UWorld* World=GetWorld();
    if(!P||!World)return;
    // Forward sector from the player's current position (the carried momentum moves the player during the chop).
    const auto Hits=RuneSwordCombat::QuerySector(World,P,P->GetActorLocation(),DashDirection,DashRangeCM,DashArcDegrees,HitActors);
    for(const FHitResult& Hit:Hits)
    {
        AActor* Target=Hit.GetActor();
        if(!IsValid(Target)||Target->ActorHasTag(TEXT("Friendly"))||HitActors.Contains(Target))continue;
        auto* Combat=Target->FindComponentByClass<UMonsterCombatComponent>();
        if(Combat&&Combat->IsDead())continue;
        HitActors.Add(Target);
        const bool Eligible=ColdSteelSkills::IsMasteryTrainingTarget(P,Target);
        FWeaponDamageResult Receipt;
        const float Applied=ColdSteelSkills::ApplyHit(P,Hit,SwingDamage,DashDirection,Shot,&Receipt);
        const bool bKilled=Combat&&Combat->IsDead();
        if(Applied<=0.f&&!bKilled)continue;
        // Hit cue and training: damage was dealt, or this blow killed the target.
        ConfirmDashImpact(Hit);
        P->NotifyConfirmedWeaponHit(Target,Applied,&Receipt,false);
        if(Eligible){++DashHits;if(bKilled)++DashKills;}
        if(Combat)Combat->ReceiveMeleeKnockback(P,DashKnockbackCM);
    }
}

void UKukriWeaponComponent::ConfirmDashImpact(const FHitResult& Hit)
{
    // One confirmed-hit cue per chop; every target still gets its own damage receipt.
    if(bImpactConfirmed)return;
    bImpactConfirmed=true;ImpactAge=0.f;
    HitStop=KukriRhythm::FleshStopSeconds*KukriDashRhythm::HitStopScale;
    ImpactKick=KukriRhythm::ImpactKick*KukriDashRhythm::ImpactScale;
    if(HitSound)UGameplayStatics::PlaySoundAtLocation(this,HitSound,Hit.ImpactPoint,.95f,.9f);
}

void UKukriWeaponComponent::FinishDashAttack()
{
    // Training is committed once per cast, also when the chop is cancelled after it has hit.
    if(!bDashTrainingPending)return;
    bDashTrainingPending=false;
    if(auto* Profile=KukriDashProfile(GetWorld()))Profile->TrainDashAttack(DashHits,DashKills);
}

void UKukriWeaponComponent::GetDashCameraMotion(FVector& Location,FRotator& Rotation,float& FovDelta) const
{
    // Same author clock as the clip: the hit-stop freezes the curve with the arms.
    KukriDashRhythm::Camera(Elapsed,Rotation,FovDelta);
    Location=FVector::ZeroVector;
    if(ImpactAge>=0.f)
    {
        const float Shake=KukriRhythm::HitShake(ImpactAge)*ImpactKick;
        Rotation+=FRotator(Shake*.9f,Shake*.35f,Shake*1.4f*KukriDashRhythm::HitRoll);
        Location+=FVector(0.f,Shake*.25f,Shake*.15f);
        FovDelta+=KukriRhythm::ImpactEnvelope(ImpactAge)*ImpactKick*1.4f;
    }
}

FRotator UKukriWeaponComponent::DashViewmodelKick() const
{
    if(ImpactAge<0.f)return FRotator::ZeroRotator;
    // The chop lands downwards: the contact pushes the arms back up.
    const float E=KukriRhythm::ImpactEnvelope(ImpactAge)*ImpactKick;
    const float Shake=KukriRhythm::HitShake(ImpactAge)*ImpactKick;
    return FRotator(E*.6f*KukriDashRhythm::KickPitch+Shake*.5f,E*.8f*KukriDashRhythm::KickYaw,Shake*.8f);
}
