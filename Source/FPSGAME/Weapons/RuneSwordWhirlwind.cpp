#include "RuneSwordComponent.h"
#include "RuneSwordMeshComponent.h"
#include "../FPSGAMECharacter.h"
#include "../UI/ColdSteelStatusModel.h"
#include "../Skills/ColdSteelSkillRules.h"
#include "../Monsters/MonsterCombatComponent.h"
#include "../Combat/CombatStatusFormula.h"
#include "ColdSteelEnchantmentCombat.h"
#include "Animation/AnimSequence.h"
#include "Camera/CameraComponent.h"
#include "Components/SkeletalMeshComponent.h"
#include "Engine/GameInstance.h"
#include "Engine/World.h"
#include "GameFramework/Controller.h"
#include "Kismet/GameplayStatics.h"
#include "Sound/SoundBase.h"

namespace
{
float WhirlwindPhase(float Time,const FWhirlwindTuning& T)
{
    // Cubic acceleration/braking is shared by the camera, damage sweep and blur.
    return FMath::SmoothStep(0.f,1.f,(Time-T.ReadySeconds)/T.SpinSeconds);
}
float WhirlwindEntry(float Time,float Duration)
{
    const float U=FMath::Clamp(Time/Duration,0.f,1.f);
    return U*U*U*(U*(U*6.f-15.f)+10.f);
}
}

bool URuneSwordComponent::BeginWhirlwind()
{
    if(!IsEquipped()||IsBusy()||bGuardHeld||!CanUse()||!Viewmodel||!Camera||
        Character->IsCastBlockingLeftHandAction()||Character->IsDodging()||Character->IsSliding())return false;
    auto* Profile=GetWorld()->GetGameInstance()->GetSubsystem<UColdSteelStatusModel>();
    const auto* Item=Profile?Profile->Equipped():nullptr;
    if(!Item||Profile->ActiveProductionTool()||!ColdSteelInventory::IsMeleeWeapon(*Item))return false;
    if(!Animations.FindRef(TEXT("Whirlwind")))
    {UE_LOG(LogTemp,Warning,TEXT("[Whirlwind] 大旋风动画缺失，未扣除体力或冷却"));return false;}
    const FWhirlwindCast Cast=Profile->WhirlwindStats();
    if(!Profile->CommitWhirlwindCast(Cast))return false;
    WhirlwindCast=Cast;WhirlwindTuning=Profile->MasteryDefinition(TEXT("whirlwind")).Whirlwind;
    bWhirlwind=true;bWhirlwindTrainingPending=true;bSwingCuePlayed=false;
    // World ticks PostPhysics before caching the player camera. Keep the turn,
    // attached arms/weapon and post process in that same rendered frame.
    // The existing owner prerequisite still places us after character movement.
    SetTickGroup(TG_PostPhysics);
    WhirlwindHits=WhirlwindKills=0;WhirlwindPause=WhirlwindPauseSpent=0.f;
    WhirlwindYaw=Character->GetControlRotation().Yaw;
    HitActors.Reset();SwingSkills=ColdSteelSkills::Snapshot(Character.Get());
    SwingSkills.WeakpointPercent=0;SwingPoison=ColdSteelCombat::Snapshot(Character.Get()).Poison;
    SwingHitReactionMultiplier=MeleeModifiers.HitReaction;
    SwingRuneVulnerability=MeleeModifiers.RuneVulnerability;SwingRuneVulnerabilitySeconds=MeleeModifiers.RuneVulnerabilitySeconds;
    StopRift();Character->StopMovementForWhirlwind();
    WhirlwindEntryLocation=Viewmodel->GetRelativeLocation();WhirlwindEntryRotation=Viewmodel->GetRelativeRotation();
    const auto& PP=Camera->PostProcessSettings;
    WhirlwindSavedBlur=PP.MotionBlurAmount;WhirlwindSavedBlurMax=PP.MotionBlurMax;
    bWhirlwindSavedBlurOverride=PP.bOverride_MotionBlurAmount;bWhirlwindSavedBlurMaxOverride=PP.bOverride_MotionBlurMax;
    if(auto* Arms=::Cast<URuneSwordMeshComponent>(Viewmodel))Arms->CaptureWhirlwindEntry();
    SetClip(TEXT("Whirlwind"),false);
    BeginWhirlwindFocus();
    return true;
}

void URuneSwordComponent::FinishWhirlwindTraining()
{
    if(!bWhirlwindTrainingPending)return;
    bWhirlwindTrainingPending=false;
    if(auto* Profile=GetWorld()&&GetWorld()->GetGameInstance()?GetWorld()->GetGameInstance()->GetSubsystem<UColdSteelStatusModel>():nullptr)
        Profile->TrainWhirlwind(WhirlwindHits,WhirlwindKills);
}

void URuneSwordComponent::FinishWhirlwind()
{
    if(!bWhirlwind)return;
    // Clear first: saving training can refresh equipment and re-enter cancellation.
    bWhirlwind=false;
    SetTickGroup(TG_PostUpdateWork);
    if(auto* Arms=Cast<URuneSwordMeshComponent>(Viewmodel))Arms->ClearWhirlwindEntry();
    EndWhirlwindFocus();
    if(Camera)
    {
        auto& PP=Camera->PostProcessSettings;
        PP.MotionBlurAmount=WhirlwindSavedBlur;PP.MotionBlurMax=WhirlwindSavedBlurMax;
        PP.bOverride_MotionBlurAmount=bWhirlwindSavedBlurOverride;
        PP.bOverride_MotionBlurMax=bWhirlwindSavedBlurMaxOverride;
    }
    WhirlwindPause=0.f;FinishWhirlwindTraining();
    HitActors.Reset();LastAttackEnd=GetWorld()?GetWorld()->GetTimeSeconds():0.;
    if(Viewmodel&&Animations.FindRef(TEXT("Idle")))SetClip(TEXT("Idle"),true);
}

void URuneSwordComponent::TickWhirlwind(float Delta)
{
    if(!CurrentAnimation||!Character.IsValid()||!Character->GetController()) {FinishWhirlwind();return;}
    if(Character->IsDodging()||Character->IsTraversing()) {FinishWhirlwind();return;}
    const auto& T=WhirlwindTuning;
    const float Paused=FMath::Min(Delta,WhirlwindPause);
    WhirlwindPause-=Paused;Delta-=Paused;
    if(Delta<=0.f)
    {SetWhirlwindFocus(0.f);Viewmodel->ClearMotionVector();return;}
    // Substeps end at the actual hit sample. A confirmed hit never advances the
    // camera to the frame end while leaving the weapon at the contact pose.
    const float End=T.ReadySeconds+T.SpinSeconds+T.RecoverSeconds;
    float Remaining=FMath::Min(Delta,End-Elapsed);
    while(Remaining>UE_SMALL_NUMBER&&bWhirlwind)
    {
        const float Step=FMath::Min(Remaining,1.f/120.f),Before=Elapsed;
        Elapsed=FMath::Min(End,Elapsed+Step);Remaining-=Step;
        const float BeforePhase=WhirlwindPhase(Before,T),Phase=WhirlwindPhase(Elapsed,T);
        FRotator Aim=Character->GetController()->GetControlRotation();
        Aim.Yaw=WhirlwindYaw+T.TurnDegrees*Phase;
        Character->GetController()->SetControlRotation(Aim);
        Character->RefreshQuickCombatCamera();
        if(!bSwingCuePlayed&&Elapsed>=T.ReadySeconds)
        {
            bSwingCuePlayed=true;
            if(SwingSound)UGameplayStatics::PlaySound2D(this,SwingSound,.9f,.85f);
            if(AttackLayerSound)UGameplayStatics::PlaySound2D(this,AttackLayerSound,.8f,1.f);
        }
        if(Phase>BeforePhase)SweepWhirlwind(T.TurnDegrees*BeforePhase,T.TurnDegrees*Phase);
        if(Elapsed>=T.ReadySeconds+T.SpinSeconds)FinishWhirlwindTraining();
        if(WhirlwindPause>0.f||Elapsed>=End-UE_SMALL_NUMBER)break;
    }
    if(!bWhirlwind)return;
    // Damage retains 120 Hz sampling. Publish only the final visible pose once
    // per frame, after the final camera transform, for coherent skin velocities.
    const float Entry=WhirlwindEntry(Elapsed,T.ReadySeconds);
    Viewmodel->SetRelativeLocation(FMath::Lerp(WhirlwindEntryLocation,FVector::ZeroVector,Entry));
    Viewmodel->SetRelativeRotation(FQuat::Slerp(WhirlwindEntryRotation.Quaternion(),FRotator(0,90,0).Quaternion(),Entry));
    if(auto* Arms=Cast<URuneSwordMeshComponent>(Viewmodel))Arms->SetWhirlwindEntryTime(Elapsed);
    SamplePose(Elapsed/End*CurrentAnimation->GetPlayLength());
    const float Spin=FMath::Clamp((Elapsed-T.ReadySeconds)/T.SpinSeconds,0.f,1.f);
    SetWhirlwindFocus(WhirlwindPause>0.f?0.f:T.MotionBlur*4.f*Spin*(1.f-Spin));
    if(Elapsed>=End-UE_SMALL_NUMBER)FinishWhirlwind();
}

void URuneSwordComponent::SweepWhirlwind(float FromDegrees,float ToDegrees)
{
    auto* Pawn=Character.Get();
    const FVector Origin=Pawn->GetMeleeAimTransform().GetLocation()-FVector(0,0,45.f);
    auto Sample=[&](float Degrees)
    {
        FRuneSwordBladeSample S;
        S.Origin=Origin;S.Forward=FRotator(0,WhirlwindYaw+90.f+Degrees,0).Vector();
        S.Base=Origin+S.Forward*15.f;S.Tip=Origin+S.Forward*WhirlwindCast.RadiusCM;return S;
    };
    FRuneSwordTraceSettings Settings;Settings.Radius=32.f;Settings.bCleavePawns=true;
    const auto Hits=RuneSwordCombat::Query(GetWorld(),Pawn,Sample(FromDegrees),Sample(ToDegrees),WhirlwindCast.RadiusCM,HitActors,Settings);
    bool Confirmed=false;
    for(const FHitResult& Hit:Hits)
    {
        auto* Target=Hit.GetActor();
        if(!IsValid(Target)||HitActors.Contains(Target))continue;
        auto* Combat=Target->FindComponentByClass<UMonsterCombatComponent>();
        if(Combat&&Combat->IsDead())continue;
        HitActors.Add(Target);
        const bool Eligible=Combat&&!Target->ActorHasTag(TEXT("Summoned"))&&!Target->ActorHasTag(TEXT("NoSkillTraining"));
        auto Shot=SwingSkills;
        if(Eligible&&WhirlwindHits==1)
            Shot.ExtraMasteryExperience=GetWorld()->GetGameInstance()->GetSubsystem<UColdSteelStatusModel>()->MasteryDefinition(TEXT("swordMastery")).MultiHitExperience;
        const FVector Direction=(Target->GetActorLocation()-Pawn->GetActorLocation()).GetSafeNormal2D();
        FWeaponDamageResult Result;
        auto Apply=[&] {return ColdSteelSkills::ApplyHit(Pawn,Hit,WhirlwindCast.Damage,Direction,Shot,&Result);};
        const float Applied=Combat?Combat->ApplyHitWithReactionScale(SwingHitReactionMultiplier,Apply):Apply();
        const bool Killed=Combat&&Combat->IsDead();
        if(Applied<=0.f&&!Killed)continue;
        Confirmed=true;
        if(Eligible){++WhirlwindHits;if(Killed)++WhirlwindKills;}
        if(Combat&&!Killed)
        {
            Combat->ReceiveStun(Pawn,WhirlwindCast.StunSeconds,WhirlwindCast.KnockbackCM);
            if(SwingRuneVulnerability>0)
                if(auto* Status=UCombatStatusFormula::GetOrAdd(Target))Status->AddRuneMagicVulnerability(SwingRuneVulnerability,SwingRuneVulnerabilitySeconds);
        }
        Pawn->NotifyConfirmedWeaponHit(Target,Applied,&Result);
        if(!Killed)ColdSteelCombat::OnHit(Target,Pawn,SwingPoison);
    }
    if(Confirmed)
    {
        const float Hold=FMath::Min(WhirlwindTuning.HitStopSeconds,WhirlwindTuning.HitStopBudget-WhirlwindPauseSpent);
        WhirlwindPause=FMath::Max(0.f,Hold);WhirlwindPauseSpent+=WhirlwindPause;
        if(HitSound&&Hold>0.f)UGameplayStatics::PlaySound2D(this,HitSound,.85f,.9f);
    }
}
