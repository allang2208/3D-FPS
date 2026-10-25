#include "KukriWeaponComponent.h"
#include "KukriArmsMeshComponent.h"
#include "KukriRhythm.h"
#include "KukriQuickRhythm.h"
#include "../MeleeSmallTargetQuery.h"
#include "../MeleeWeaponStats.h"
#include "../../Combat/CombatStatusFormula.h"
#include "../../Combat/WeaponDamageTypes.h"
#include "../../Dungeons/WardBreakableGlass.h"
#include "../../Skills/ColdSteelSkillRules.h"
#include "../../Skills/LightningHasteSpeed.h"
#include "../../Skills/QuickCombatPistolMotion.h"
#include "../../Skills/QuickCombatImpactShake.h"
#include "../../FPSGAMECharacter.h"
#include "../../UI/ColdSteelStatusModel.h"
#include "../../Monsters/MonsterCombatComponent.h"
#include "../../Monsters/BoundCongregateCaptureComponent.h"
#include "Animation/AnimSequence.h"
#include "Engine/GameInstance.h"
#include "Engine/World.h"
#include "Kismet/GameplayStatics.h"
#include "Sound/SoundBase.h"

// Quick melee (F) for the kukri: the reference pommel strike (KukriQuickRhythm.h).  Same skill contract as the other
// quick-melee weapons (RuneSwordComponent::StartQuickCombatStrike, WarhammerQuickCombat.cpp): QuickCombatStats damage /
// range / knockback / toughness / bleed / area, CommitQuickCombatCast pays the skill stamina once and reserves F for the
// whole strike, one deterministic query at the contact frame (blunt form), the camera impulse also on a miss, use and
// kill experience.  Martial-skill clock: only Lightning Haste scales it.

namespace
{
const FName KukriQuickClip(KukriQuickRhythm::Clip);

UColdSteelStatusModel* KukriQuickProfile(const UWorld* World)
{
    return World&&World->GetGameInstance()?World->GetGameInstance()->GetSubsystem<UColdSteelStatusModel>():nullptr;
}
}

bool UKukriWeaponComponent::BeginQuickCombat()
{
    auto* P=Pawn();
    if(!P||!P->CanStartQuickCombatPriority())return false;
    if(!IsEquipped()||!Viewmodel||!Viewmodel->GetSkeletalMeshAsset()||!Animations.FindRef(KukriQuickClip))return false;
    // A swing or sprint attack in progress yields to F (priority interrupt), the draw does not (CanStartQuickCombatPriority).
    P->InterruptActionsForPriority(false);
    if(!CanUse()||IsBusy())return false;
    auto* Profile=KukriQuickProfile(GetWorld());
    const auto* Item=Profile?Profile->Equipped():nullptr;
    if(!Item||Item->InstanceId!=InstanceId||Profile->ActiveProductionTool())return false;
    const float Rate=FMath::Max(.05f,LightningHaste::ActionSpeed(P));
    // The skill cost replaces the swing cost and is paid once; F stays reserved until the strike is back on the stance.
    if(!Profile->CommitQuickCombatCast(Animations.FindRef(KukriQuickClip)->GetPlayLength()/Rate))return false;
    QuickCast=Profile->QuickCombatStats();
    SwingDamage=QuickCast.Damage;
    Shot=ColdSteelSkills::Snapshot(P,Item);
    Shot.bRifle=false;Shot.bPistol=false;Shot.WeakpointPercent=0;
    // The pommel is a blunt blow: blunt toughness conversion; the authority recomputes it from QuickCombatStats.
    Shot.AttackForm=EMonsterAttackForm::Blunt;Shot.bMeleeStrike=true;
    Shot.AttackMeta|=0x80;
    Shot.ToughnessDamageMultiplier=QuickCast.ToughnessMultiplier;
    bQuickCombat=true;bQuickContactDone=false;bQuickKillPending=false;
    bSwingPlayed=bImpactConfirmed=bWallHit=false;HitActors.Reset();HitStop=0.f;ImpactAge=-1.f;
    ResetStrike();StrikeAge=-1.f;CameraCarryAge=-1.f;
    // The swing combo starts over after the quick melee.
    NextStage=0;LastAttackEnd=-1.;
    SetClip(KukriQuickClip,false,KukriRhythm::EntryBlendSeconds);
    Profile->TrainQuickCombat(Profile->QuickCombatDefinition().UseExperience);
    return true;
}

void UKukriWeaponComponent::AdvanceQuickCombat(float Delta)
{
    auto* P=Pawn();
    const float Rate=FMath::Max(.05f,LightningHaste::ActionSpeed(P));
    float Remaining=Delta;
    int32 Guard=0;
    while(Remaining>UE_SMALL_NUMBER&&bQuickCombat&&++Guard<64)
    {
        if(HitStop>0.f)
        {
            const float Pause=FMath::Min(Remaining,HitStop);
            HitStop-=Pause;Remaining-=Pause;
            continue;
        }
        const float Length=CurrentAnimation?CurrentAnimation->GetPlayLength():KukriQuickRhythm::Seconds;
        float Step=FMath::Min(Remaining*Rate,1.f/120.f);
        for(const float Boundary:{KukriQuickRhythm::SwingSound,KukriQuickRhythm::ContactAt,Length})
            if(Elapsed<Boundary-UE_KINDA_SMALL_NUMBER)Step=FMath::Min(Step,Boundary-Elapsed);
        Step=FMath::Max(Step,1e-4f);
        const float Before=Elapsed;
        Elapsed=FMath::Min(Length,Elapsed+Step);
        Remaining=FMath::Max(0.f,Remaining-(Elapsed-Before)/Rate);
        SamplePose(Elapsed);
        if(!bSwingPlayed&&Elapsed>=KukriQuickRhythm::SwingSound-UE_KINDA_SMALL_NUMBER)
        {
            bSwingPlayed=true;
            if(SwingSound)UGameplayStatics::PlaySound2D(this,SwingSound,KukriQuickRhythm::SwingVolume,KukriQuickRhythm::SwingPitch);
        }
        // The pose is on the contact frame here: the pommel point is read from it.
        if(!bQuickContactDone&&Elapsed>=KukriQuickRhythm::ContactAt-UE_KINDA_SMALL_NUMBER){bQuickContactDone=true;QuickContact();}
        if(Elapsed>=Length-UE_KINDA_SMALL_NUMBER)
        {
            bQuickCombat=false;HitActors.Reset();
            FinishQuickCombat();
            SetClip(LocomotionClip(),true,KukriRhythm::EntryBlendSeconds);
        }
    }
    if(!bQuickCombat)return;
    if(auto* Profile=KukriQuickProfile(GetWorld()))
    {
        const float Length=CurrentAnimation?CurrentAnimation->GetPlayLength():KukriQuickRhythm::Seconds;
        Profile->UpdateQuickCombatAction((Length-Elapsed)/Rate+HitStop,Length/Rate);
    }
}

void UKukriWeaponComponent::QuickContact()
{
    auto* P=Pawn();
    UWorld* World=GetWorld();
    auto* Profile=KukriQuickProfile(World);
    if(!P||!World||!Profile)return;
    if(auto* Capture=P->FindComponentByClass<UBoundCongregateCaptureComponent>();Capture&&Capture->HitRestraintWithQuickMelee())
    {
        ImpactAge=0.f;StrikeAge=0.f;ImpactKick=KukriRhythm::ImpactKick*KukriQuickRhythm::ImpactScale;
        P->RefreshQuickCombatCamera();
        if(PommelHitSound)UGameplayStatics::PlaySound2D(this,PommelHitSound,1.f,1.f);
        return;
    }
    const FTransform Aim=P->GetMeleeAimTransform();
    const FVector Direction=Aim.GetUnitAxis(EAxis::X);
    // The pommel's lane (height and side on the contact frame), swept from the eye plane: starting at the pommel would
    // skip close blockers and add the arm's reach to the skill's rangeCM (WarhammerQuickCombat rule).
    const FVector Pommel=BladeFrame().TransformPosition(KukriQuickRhythm::Pommel);
    const FVector Origin=Pommel-Direction*FMath::Max(0.f,FVector::DotProduct(Pommel-Aim.GetLocation(),Direction));
    const float Radius=QuickCombatPistolMotion::QueryRadiusCM*float(ColdSteelMelee::EquippedModifiers(Profile).MartialRange);
    TArray<FHitResult> Hits;
    if(QuickCast.bAreaHit)Hits=MeleeSmallTargets::QueryQuickAreaContacts(World,P,Aim,Origin,QuickCast.RangeCM,Radius);
    else
    {
        FHitResult Hit;
        if(MeleeSmallTargets::QueryQuickContact(World,P,Aim,Origin,QuickCast.RangeCM,Radius,Hit))Hits.Add(Hit);
    }
    // The quick-melee shake belongs to this one query, a miss included (lighter); the hit-stop and the hit cue need damage.
    // StrikeAge drives the real-time contact accent and the scaled shared impulse (hit or miss).
    ImpactAge=0.f;StrikeAge=0.f;ImpactKick=KukriRhythm::ImpactKick*KukriQuickRhythm::ImpactScale*KukriQuickRhythm::MissKick;
    UE_LOG(LogTemp,Log,TEXT("[QuickCombat] 接触 武器=弯刀 射线=刀把端 起点=%s 方向=%s 距离=%.0f AOE=%d 接触数=%d"),
        *Origin.ToCompactString(),*Direction.ToCompactString(),QuickCast.RangeCM,QuickCast.bAreaHit?1:0,Hits.Num());
    int32 MasteryHits=0;
    for(const FHitResult& Hit:Hits)
    {
        AActor* Target=Hit.GetActor();
        if(!IsValid(Target)||Target->ActorHasTag(TEXT("Friendly"))||HitActors.Contains(Target))continue;
        HitActors.Add(Target);
        if(UWardBreakableGlass::BreakHit(Hit,Direction)){ConfirmQuickImpact(Hit,true);continue;}
        auto* Combat=Target->FindComponentByClass<UMonsterCombatComponent>();
        if(!Combat||Combat->IsDead())continue;
        const bool Eligible=ColdSteelSkills::IsMasteryTrainingTarget(P,Target);
        auto HitShot=Shot;
        HitShot.ExtraMasteryExperience=Eligible&&MasteryHits==1?Profile->MasteryDefinition(Shot.MasteryId).MultiHitExperience:0;
        FWeaponDamageResult Receipt;
        const float Applied=ColdSteelSkills::ApplyHit(P,Hit,SwingDamage,Direction,HitShot,&Receipt);
        const bool bKilled=Combat->IsDead();
        if(Applied<=0.f&&!bKilled)continue;
        if(Eligible)++MasteryHits;
        ConfirmQuickImpact(Hit,false);
        P->NotifyConfirmedWeaponHit(Target,Applied,&Receipt,false);
        // Pure push after the damage, no stun reaction (the skill's knockback).
        Combat->ReceiveMeleeKnockback(P,QuickCast.KnockbackCM);
        if(P->HasAuthority()&&!bKilled&&QuickCast.BleedChance>0.f&&FMath::FRand()<QuickCast.BleedChance)
            if(auto* Status=UCombatStatusFormula::GetOrAdd(Target))Status->AddBleeding(P,1);
        if(Eligible&&bKilled)bQuickKillPending=true;
    }
    // A miss still stops dead on the contact frame, briefly.
    if(!bImpactConfirmed&&!bWallHit)HitStop=FMath::Max(HitStop,KukriQuickRhythm::MissStop);
    // Resample the camera now so the impulse shows on this frame even after the character's camera update.
    P->RefreshQuickCombatCamera();
}

void UKukriWeaponComponent::ConfirmQuickImpact(const FHitResult& Hit,bool bWorld)
{
    // One cue per strike; every target still gets its own damage receipt.  Flesh replaces an earlier glass cue.
    if(bImpactConfirmed||(bWorld&&bWallHit))return;
    if(bWorld)
    {
        bWallHit=true;HitStop=KukriRhythm::WallStopSeconds;ImpactAge=0.f;
        ImpactKick=KukriRhythm::ImpactKick*KukriQuickRhythm::ImpactScale*.6f;
        if(WallSound)UGameplayStatics::PlaySoundAtLocation(this,WallSound,Hit.ImpactPoint,.55f,1.15f);
        SpawnContactFX(Hit,true);
        return;
    }
    bImpactConfirmed=true;ImpactAge=0.f;
    HitStop=KukriRhythm::FleshStopSeconds*KukriQuickRhythm::HitStopScale;
    ImpactKick=KukriRhythm::ImpactKick*KukriQuickRhythm::ImpactScale;
    if(PommelHitSound)UGameplayStatics::PlaySoundAtLocation(this,PommelHitSound,Hit.ImpactPoint,1.f,.9f);
    if(StabThudSounds.Num())
        UGameplayStatics::PlaySoundAtLocation(this,StabThudSounds[FMath::RandRange(0,StabThudSounds.Num()-1)],Hit.ImpactPoint,
            KukriRhythm::StabThudVolume,KukriRhythm::StabThudPitch*KukriQuickRhythm::ThudPitchScale);
    SpawnContactFX(Hit,false);
}

void UKukriWeaponComponent::FinishQuickCombat()
{
    // Only called for this component's own cast (it releases the shared F reservation).
    auto* Profile=KukriQuickProfile(GetWorld());
    if(Profile)
    {
        Profile->FinishQuickCombatCast();
        if(bQuickKillPending)Profile->TrainQuickCombat(Profile->QuickCombatDefinition().KillExperience);
    }
    bQuickKillPending=false;bQuickContactDone=false;
}

void UKukriWeaponComponent::GetQuickCameraMotion(FVector& Location,FRotator& Rotation,float& FovDelta) const
{
    // Same author clock as the clip: the hit-stop freezes the curve with the arm.
    KukriQuickRhythm::Camera(Elapsed,Rotation,FovDelta);
    Location=FVector::ZeroVector;
    if(ImpactAge>=0.f)
    {
        const float Shake=KukriRhythm::HitShake(ImpactAge)*ImpactKick;
        Rotation+=FRotator(Shake*.9f,Shake*.35f,Shake*1.4f*KukriQuickRhythm::HitRoll);
        Location+=FVector(0.f,Shake*.25f,Shake*.15f);
        FovDelta+=KukriRhythm::ImpactEnvelope(ImpactAge)*ImpactKick*KukriQuickRhythm::HitFov;
    }
    if(StrikeAge>=0.f)
    {
        // Contact accent (real time, hit or miss): the view nods into the blow, pushes forward and widens for a beat,
        // plus a share of the shared quick-melee impulse (QuickCombatImpactShake, full strength on the other weapons).
        const float E=KukriRhythm::StrikeEnvelope(StrikeAge);
        Rotation.Pitch+=KukriQuickRhythm::AccentPitch*E;Location.X+=KukriQuickRhythm::AccentPushCM*E;
        FovDelta+=KukriQuickRhythm::AccentFov*E;
        FVector ImpulseLocation=FVector::ZeroVector;FRotator ImpulseRotation=FRotator::ZeroRotator;
        QuickCombatImpactShake::Add(StrikeAge,ImpulseLocation,ImpulseRotation);
        Location+=ImpulseLocation*KukriQuickRhythm::ImpulseScale;Rotation+=ImpulseRotation*KukriQuickRhythm::ImpulseScale;
    }
}

FRotator UKukriWeaponComponent::QuickViewmodelKick() const
{
    if(ImpactAge<0.f)return FRotator::ZeroRotator;
    // The pommel lands forward and down-left: the contact pushes the arm back up and to the right.
    const float E=KukriRhythm::ImpactEnvelope(ImpactAge)*ImpactKick;
    const float Shake=KukriRhythm::HitShake(ImpactAge)*ImpactKick;
    return FRotator(E*.6f*KukriQuickRhythm::KickPitch+Shake*.5f,E*.8f*KukriQuickRhythm::KickYaw,Shake*.8f);
}
