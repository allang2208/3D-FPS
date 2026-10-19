#include "RuneSwordComponent.h"
#include "RuneSwordChixiaoRhythm.h"
#include "ModularSwordVisual.h"
#include "MeleeSmallTargetQuery.h"
#include "../FPSGAMECharacter.h"
#include "Animation/AnimSequence.h"
#include "Engine/AssetManager.h"
#include "Engine/StreamableManager.h"
#include "Engine/World.h"
#include "Kismet/GameplayStatics.h"
#include "Sound/SoundBase.h"

void URuneSwordComponent::RefreshChixiao(const FColdSteelItem* Item)
{
    const bool Enabled=Item&&ColdSteelModularSword::UsesChixiaoDoubleHeavy(*Item);
    if(!Enabled&&bChixiaoHeavy)CancelAction();
    bChixiaoEquipped=Enabled;
    if(!Enabled||ChixiaoLoad)return;
    const FSoftObjectPath Standard(TEXT("/Game/Weapons/Zhanmadao20261018/ChixiaoDoubleHeavyV1/A_Chixiao_DoubleHeavy_Standard.A_Chixiao_DoubleHeavy_Standard"));
    const FSoftObjectPath LongGrip(TEXT("/Game/Weapons/Zhanmadao20261018/ChixiaoDoubleHeavyV1/A_Chixiao_DoubleHeavy_LongGrip.A_Chixiao_DoubleHeavy_LongGrip"));
    ChixiaoLoad=UAssetManager::GetStreamableManager().RequestAsyncLoad(TArray<FSoftObjectPath>{Standard,LongGrip},
        FStreamableDelegate::CreateWeakLambda(this,[this,Standard,LongGrip]()
        {
            ChixiaoStandard=Cast<UAnimSequence>(Standard.ResolveObject());
            ChixiaoLongGrip=Cast<UAnimSequence>(LongGrip.ResolveObject());
        }));
}

UAnimSequence* URuneSwordComponent::ChixiaoAnimation() const
{
    return EquippedAnimationFolder==TEXT("/Game/Weapons/FrostCrystalSword20260915/Grips20260919/LongGripAnimations")
        ?ChixiaoLongGrip.Get():ChixiaoStandard.Get();
}

void URuneSwordComponent::TickChixiaoHeavy(float Delta)
{
    namespace R=RuneSwordChixiaoRhythm;
    const float Next=FMath::Min(CurrentAnimation->GetPlayLength(),Elapsed+Delta);
    const FTransform AimNow=Character->GetMeleeAimTransform();
    const auto FrameAt=[&](float Time)
    {
        FTransform Frame;Frame.Blend(PreviousAimFrame,AimNow,FMath::Clamp((Time-Elapsed)/FMath::Max(UE_SMALL_NUMBER,Delta),0.f,1.f));
        return Frame;
    };
    // Process both windows, in order, even when a frame spans the entire pair.
    // HitActors belongs to a blade pass: each target may take one full heavy hit per cut.
    for(int32 Cut=0;Cut<2;++Cut)
    {
        const float Start=Cut==0?R::FirstStart:R::SecondStart;
        const float Finish=Cut==0?R::FirstEnd:R::SecondEnd;
        if(Next<Start||Elapsed>=Finish)continue;
        if(ChixiaoStrikeIndex!=Cut)
        {
            ChixiaoStrikeIndex=Cut;HitActors.Reset();SwingTrainingHits=0;
            bImpactFeedbackPlayed=false;bSwingCooldownReduced=false;
            ContactStart=Start;ContactEnd=Finish;bSwingCuePlayed=true;
            if(Cut==1)
            {
                // Preserve the captured full-heavy damage/poise/skill snapshot.
                // Only the per-cut identity changes; no second stamina or cast commit.
                if(++NetworkBladeSerial==0)++NetworkBladeSerial;
                SwingSkills.GuardAttackSerial=NetworkBladeSerial;
                StopRift();
            }
            if(AttackLayerSound)UGameplayStatics::PlaySound2D(this,AttackLayerSound,1.f,1.f);
            if(SwingSound)UGameplayStatics::PlaySound2D(this,SwingSound,.95f,Cut==0?.95f:1.05f);
            if(Cut==0){StartRift(Next-Start);ReleaseSlashWave(FrameAt(Start));}
        }
        const float HitStart=FMath::Max(Elapsed,Start),HitEnd=FMath::Min(Next,Finish);
        if(HitEnd<=HitStart)continue;
        const FTransform First=FrameAt(HitStart),Last=FrameAt(HitEnd);
        const float Travel=FVector::Distance(First.GetLocation(),Last.GetLocation())+
            SwingReach*First.GetRotation().AngularDistance(Last.GetRotation());
        const int32 Steps=FMath::Max3(1,FMath::CeilToInt((HitEnd-HitStart)*R::SampleRate),
            FMath::CeilToInt(Travel/FMath::Max(.1f,RuneSwordCombat::BladeRadius*SwingRangeMultiplier)));
        SamplePose(HitStart);auto Previous=ReadBlade(First);
        for(int32 I=1;I<=Steps;++I)
        {
            const float Time=FMath::Lerp(HitStart,HitEnd,float(I)/Steps);
            SamplePose(Time);const auto Current=ReadBlade(FrameAt(Time));
            SweepBlade(Previous,Current);Previous=Current;
            if(!bChixiaoHeavy||!bAttacking)return;
        }
        ApplySwingHits(MeleeSmallTargets::QueryLowSector(GetWorld(),Character.Get(),Last,
            AzureDragonSwingRange(SwingReach),HitActors,true,MeleeSmallTargets::LowArcDegrees,
            AzureDragonSwingRange(MeleeSmallTargets::LowReachCM*MeleeModifiers.MartialRange)),Last.GetUnitAxis(EAxis::X));
        if(!bChixiaoHeavy||!bAttacking)return;
    }
    SamplePose(Next);PreviousAimFrame=AimNow;Elapsed=Next;
    if(Next>=R::SecondEnd)FinishHeavyTraining();
    if(!bChixiaoHeavy||!bAttacking)return;
    if(Elapsed>=CurrentAnimation->GetPlayLength())
    {
        const bool Queued=bQueuedAttack,QueuedSkill=bQueuedQuickCombat;
        bChixiaoHeavy=bAttacking=bHeavyAttack=bQueuedAttack=bQueuedQuickCombat=false;
        ChixiaoStrikeIndex=-1;LastAttackEnd=GetWorld()->GetTimeSeconds();
        SetClip(TEXT("Idle"),true);
        if(QueuedSkill)BeginQuickCombatStrike();else if(Queued)BeginAttack();
    }
}

void URuneSwordComponent::ChixiaoCameraMotion(FVector& Location,FRotator& Rotation) const
{
    namespace R=RuneSwordChixiaoRhythm;
    const FVector Load(-13.f,7.8f,3.12f),Down(24.f,-16.5f,-13.5f),Up(20.f,12.f,7.f);
    const FRotator LoadR(7.8f,9.1f,6.5f),DownR(-13.5f,-18.f,-15.f),UpR(10.f,13.f,9.f);
    if(Elapsed<=R::FirstEnd)
    {
        const float U=FMath::Clamp(Elapsed/R::FirstEnd,0.f,1.f),A=U*U*(2.f-U);
        Location=FMath::Lerp(Load,Down,A);Rotation=FMath::Lerp(LoadR,DownR,A);
    }
    else if(Elapsed<R::SecondStart){Location=Down;Rotation=DownR;}
    else if(Elapsed<=R::SecondEnd)
    {
        const float A=FMath::SmoothStep(R::SecondStart,R::SecondEnd,Elapsed);
        Location=FMath::Lerp(Down,Up,A);Rotation=FMath::Lerp(DownR,UpR,A);
    }
    else
    {
        const float Weight=1.f-FMath::SmoothStep(R::FollowEnd,R::End,Elapsed);
        Location=Up*Weight;Rotation=UpR*Weight;
    }
}
