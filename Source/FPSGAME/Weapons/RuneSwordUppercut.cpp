#include "RuneSwordComponent.h"
#include "RuneSwordUppercutMotion.h"
#include "RuneSwordCombatTuning.h"
#include "MeleeWeaponStats.h"
#include "MeleeSmallTargetQuery.h"
#include "../Skills/SwordUppercutTuning.h"
#include "../Skills/ColdSteelSkillRules.h"
#include "../UI/ColdSteelStatusModel.h"
#include "../Combat/CombatStatusFormula.h"
#include "../FPSGAMECharacter.h"
#include "Animation/AnimSequence.h"
#include "Components/SkeletalMeshComponent.h"
#include "Engine/AssetManager.h"
#include "Engine/StreamableManager.h"
#include "Engine/SkeletalMesh.h"
#include "Engine/GameInstance.h"
#include "Engine/World.h"
#include "Kismet/GameplayStatics.h"
#include "Sound/SoundBase.h"

void URuneSwordComponent::LoadUppercutAnimations()
{
    UppercutLoad=UAssetManager::GetStreamableManager().RequestAsyncLoad(
        TArray<FSoftObjectPath>{UppercutStandard.ToSoftObjectPath(),UppercutLongGrip.ToSoftObjectPath()});
}

UAnimSequence* URuneSwordComponent::UppercutAnimation() const
{
    return EquippedAnimationFolder==TEXT("/Game/Weapons/FrostCrystalSword20260915/Grips20260919/LongGripAnimations")
        ? UppercutLongGrip.Get() : UppercutStandard.Get();
}

FString URuneSwordComponent::UppercutStatusText() const
{
    if(!IsEquipped())return TEXT("需要持剑");
    if(bUppercut)return TEXT("上挑中");
    if(!Character.IsValid()||!CanUse())return TEXT("暂不可用");
    const auto* Profile=GetWorld()->GetGameInstance()->GetSubsystem<UColdSteelStatusModel>();
    if(!Profile)return TEXT("暂不可用");
    if(Profile->SwordUppercutCooldown()>0.f)return TEXT("冷却中");
    if(!Profile->CanSpendStamina(Profile->MasteryDefinition(TEXT("swordUppercut")).UppercutStaminaCost))return TEXT("体力不足");
    if(IsBusy()||bGuardHeld)return TEXT("动作中");
    if(Character->IsCastBlockingLeftHandAction())return TEXT("动作占用");
    const auto* Clip=UppercutAnimation();
    if(!Clip)return UppercutLoad&&!UppercutLoad->HasLoadCompleted()?TEXT("动作准备中"):TEXT("动作未就绪");
    const auto* Mesh=Viewmodel?Viewmodel->GetSkeletalMeshAsset():nullptr;
    if(!Mesh||Clip->GetSkeleton()!=Mesh->GetSkeleton())return TEXT("动作未就绪");
    return FString();
}

bool URuneSwordComponent::CanBeginUppercut() const
{
    return UppercutStatusText().IsEmpty();
}

bool URuneSwordComponent::BeginUppercut()
{
    if(!CanBeginUppercut())return false;
    UAnimSequence* Clip=UppercutAnimation();
    auto* Profile=GetWorld()->GetGameInstance()->GetSubsystem<UColdSteelStatusModel>();
    const auto* Item=Profile?Profile->Equipped():nullptr;
    if(!Item)return false;
    const auto Stats=ColdSteelMelee::Evaluate(*Item,Profile);
    if(bInspecting)CancelAction();
    bUppercut=true;
    bThrustAttack=bPommelAttack=bOverheadAttack=bHeavyAttack=bQuickCombatStrike=false;
    bHeavyTrainingPending=false;HeavyTrainingHits=HeavyTrainingKills=0;
    HitActors.Reset();SwingTrainingHits=0;
    SwingDamage=Stats.Damage*ColdSteelMelee::UppercutMultiplier(Profile,Stats.Modifiers);
    const auto& Definition=Profile->MasteryDefinition(TEXT("swordUppercut"));
    const auto Effect=Profile->MasteryEffect(TEXT("swordUppercut"));
    SwingReach=Stats.ThrustReach*Effect.UppercutReachMultiplier;
    SwingRangeMultiplier=RuneSwordCombatTuning::RangeMultiplier*Stats.Modifiers.Range*Definition.UppercutRangeMultiplier;
    UppercutReachGrowth=Effect.UppercutReachMultiplier/Definition.UppercutRangeMultiplier;
    UppercutLowReachCM=MeleeSmallTargets::LowReachCM*Effect.UppercutReachMultiplier;
    SwingHitReactionMultiplier=Stats.Modifiers.HitReaction;
    SwingKnockbackCM=Stats.KnockbackCM;
    SwingRuneVulnerability=Stats.Modifiers.RuneVulnerability;
    SwingRuneVulnerabilitySeconds=Stats.Modifiers.RuneVulnerabilitySeconds;
    SwingCooldownReduceSeconds=Item->Definition==TEXT("ue_rune_sword")?.5f+Stats.Modifiers.CooldownReduceSecondsPerHit:0.f;
    bSwingCooldownReduced=false;SwingWaveRange=SwingWaveScale=0.f;
    SwingPoison=ColdSteelCombat::Snapshot(Character.Get()).Poison;
    SwingSkills=ColdSteelSkills::Snapshot(Character.Get());
    SwingSkills.bRifle=SwingSkills.bPistol=false;SwingSkills.WeakpointPercent=0.f;
    SwingSkills.AttackMeta=SwordUppercut::AttackMeta;
    SwingSkills.AttackForm=EMonsterAttackForm::Blade;
    SwingSkills.ToughnessDamageMultiplier*=Stats.Modifiers.HeavyToughness;
    // Keep the accepted authored tempo; only gameplay damage/range is snapshotted.
    SwingRate=1.f;bSwingCuePlayed=bImpactFeedbackPlayed=bThrustImpact=false;
    ContactStart=RuneSwordUppercutMotion::ReleaseStart;
    ContactEnd=RuneSwordUppercutMotion::Finish;
    bLungeStarted=bLungeBlocked=false;
    LungeDirection=FVector::ZeroVector;
    bQueuedAttack=bQueuedQuickCombat=false;
    ImpactAge=1.f;
    StopRift();
    ScheduleWalkInspect(true);
    Animations.Add(TEXT("Uppercut"),Clip);
    SetClip(TEXT("Uppercut"),false);
    PreviousAimFrame=Character->GetMeleeAimTransform();
    return true;
}

void URuneSwordComponent::TickUppercut(float Delta)
{
    const float End=CurrentAnimation->GetPlayLength();
    const float Next=FMath::Min(End,Elapsed+Delta);
    if(!bSwingCuePlayed&&Next>=ContactStart)
    {
        auto* Profile=GetWorld()->GetGameInstance()->GetSubsystem<UColdSteelStatusModel>();
        if(!Profile||!Profile->CommitSwordUppercutRelease()){CancelAction();return;}
        if(!bUppercut)return;
    }
    const FTransform AimBeforeLunge=Character->GetMeleeAimTransform();
    const FVector Moved=AdvanceThrustLunge(Elapsed,Next);
    const FTransform AimNow=Character->GetMeleeAimTransform();
    if(bRiftActive){RiftOrigin.AddToTranslation(Moved);TickRift(0.f);}
    if(!bSwingCuePlayed&&Next>=ContactStart)
    {
        bSwingCuePlayed=true;bHeavyTrainingPending=true;
        if(AttackLayerSound)UGameplayStatics::PlaySound2D(this,AttackLayerSound,1.f,1.f);
        if(SwingSound)UGameplayStatics::PlaySound2D(this,SwingSound,.72f,1.1f);
        StartRift(Next-ContactStart);
    }
    const auto FrameAt=[&](float Time)
    {
        FTransform Frame;
        const float Played=Time-Elapsed;
        Frame.Blend(PreviousAimFrame,AimBeforeLunge,FMath::Clamp(Played/FMath::Max(SMALL_NUMBER,Delta),0.f,1.f));
        const float Distance=FVector::DotProduct(Moved,LungeDirection);
        if(Distance>SMALL_NUMBER)
        {
            const float Requested=RuneSwordUppercutMotion::LungeDistance*
                (RuneSwordUppercutMotion::LungeAlpha(Time,bUppercut)-RuneSwordUppercutMotion::LungeAlpha(Elapsed,bUppercut));
            Frame.AddToTranslation(Moved*FMath::Clamp(Requested/Distance,0.f,1.f));
        }
        return Frame;
    };
    const float HitStart=FMath::Max(Elapsed,ContactStart),HitEnd=FMath::Min(Next,ContactEnd);
    if(HitEnd>HitStart&&HitActors.IsEmpty())
    {
        const FTransform StartFrame=FrameAt(HitStart),EndFrame=FrameAt(HitEnd);
        const float AimTravel=FVector::Distance(StartFrame.GetLocation(),EndFrame.GetLocation())+
            SwingReach*StartFrame.GetRotation().AngularDistance(EndFrame.GetRotation());
        const float Radius=RuneSwordThrustRhythm::BladeRadius*SwingRangeMultiplier;
        const int32 Steps=FMath::Max3(1,FMath::CeilToInt((HitEnd-HitStart)*RuneSwordThrustRhythm::SampleRate),
            FMath::CeilToInt(AimTravel/FMath::Max(.1f,Radius)));
        SamplePose(HitStart);auto Previous=ReadBlade(StartFrame);
        for(int32 I=1;I<=Steps&&HitActors.IsEmpty();++I)
        {
            const float Time=FMath::Lerp(HitStart,HitEnd,float(I)/Steps);
            SamplePose(Time);const auto Current=ReadBlade(FrameAt(Time));
            SweepBlade(Previous,Current);Previous=Current;
        }
        if(HitActors.IsEmpty())ApplySwingHits(MeleeSmallTargets::QueryLowSector(
            GetWorld(),Character.Get(),EndFrame,SwingReach,HitActors,false,30.f,
            UppercutLowReachCM),EndFrame.GetUnitAxis(EAxis::X));
    }
    SamplePose(Next);PreviousAimFrame=AimNow;Elapsed=Next;
    if(Next>=ContactEnd)FinishHeavyTraining();
    if(!bUppercut)return; // Training/save callbacks may cancel the current action.
    if(Elapsed>=End)
    {
        bUppercut=false;bLungeStarted=bLungeBlocked=false;LungeDirection=FVector::ZeroVector;
        SetClip(TEXT("Idle"),true);
    }
}
