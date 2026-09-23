#include "RuneSwordComponent.h"
#include "RuneSwordMeshComponent.h"
#include "RuneSwordWhirlwindFeel.h"
#include "ModularSwordVisual.h"
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
    return WhirlwindFeel::Phase(Time,T);
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
    // Existing equipped instances survive Live Coding. Refresh only this clip
    // at the idle-to-skill boundary, before committing stamina or cooldown.
    const FString ClipPath=ColdSteelModularSword::AnimationFolder(*Item)+TEXT("/A_RuneSword_WhirlwindV5");
    const UAnimSequence* Installed=Animations.FindRef(TEXT("Whirlwind")).Get();
    if(!Installed||Installed->GetPathName()!=ClipPath+TEXT(".A_RuneSword_WhirlwindV5"))
        Animations.Add(TEXT("Whirlwind"),LoadObject<UAnimSequence>(nullptr,*ClipPath));
    if(!Animations.FindRef(TEXT("Whirlwind")))
    {UE_LOG(LogTemp,Warning,TEXT("[Whirlwind] 大旋风动画缺失，未扣除体力或冷却"));return false;}
    const FWhirlwindCast Cast=Profile->WhirlwindStats();
    if(!Profile->CommitWhirlwindCast(Cast))return false;
    WhirlwindCast=Cast;WhirlwindTuning=Profile->MasteryDefinition(TEXT("whirlwind")).Whirlwind;
    bWhirlwind=true;bWhirlwindTrainingPending=true;bSwingCuePlayed=false;
    WhirlwindHits=WhirlwindKills=0;WhirlwindPause=WhirlwindPauseSpent=0.f;
    ImpactAge=1.f;ImpactStrength=1.f;
    WhirlwindYaw=Character->GetControlRotation().Yaw;
    HitActors.Reset();SwingSkills=ColdSteelSkills::Snapshot(Character.Get());
    SwingSkills.WeakpointPercent=0;SwingPoison=ColdSteelCombat::Snapshot(Character.Get()).Poison;
    SwingHitReactionMultiplier=MeleeModifiers.HitReaction;
    // 旋风斩属剑刃攻击：导魔符文易伤通道照常挂载；金色强化按确认命中缩减CD（整个旋风只触发一次）。
    SwingRuneVulnerability=MeleeModifiers.RuneVulnerability;SwingRuneVulnerabilitySeconds=MeleeModifiers.RuneVulnerabilitySeconds;
    SwingCooldownReduceSeconds=.5f+static_cast<float>(MeleeModifiers.CooldownReduceSecondsPerHit);bSwingCooldownReduced=false;
    StopRift();Character->StopMovementForMeleeSkill();
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
    if(auto* Arms=Cast<URuneSwordMeshComponent>(Viewmodel))Arms->ClearWhirlwindEntry();
    EndWhirlwindFocus();
    if(Camera)
    {
        auto& PP=Camera->PostProcessSettings;
        PP.MotionBlurAmount=WhirlwindSavedBlur;PP.MotionBlurMax=WhirlwindSavedBlurMax;
        PP.bOverride_MotionBlurAmount=bWhirlwindSavedBlurOverride;
        PP.bOverride_MotionBlurMax=bWhirlwindSavedBlurMaxOverride;
    }
    WhirlwindPause=0.f;ImpactAge=1.f;FinishWhirlwindTraining();
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
    // TickComponent already advanced the contact age. Hold resistance, pose,
    // controller turn and sweep on the same paused clock.
    ImpactAge=FMath::Max(0.f,ImpactAge-Paused);
    if(Delta<=0.f)
    {Character->RefreshQuickCombatCamera();SetWhirlwindFocus(0.f);Viewmodel->ClearMotionVector();return;}
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
        if(!bSwingCuePlayed&&Phase>=.035f)
        {
            bSwingCuePlayed=true;
            if(SwingSound)UGameplayStatics::PlaySound2D(this,SwingSound,.95f,.90f);
            if(AttackLayerSound)UGameplayStatics::PlaySound2D(this,AttackLayerSound,.75f,.94f);
        }
        // A lighter second blade pass makes both turns audible without adding
        // a second windup, damage pulse or wall-clock timer.
        if(BeforePhase<.535f&&Phase>=.535f&&SwingSound)
            UGameplayStatics::PlaySound2D(this,SwingSound,.78f,1.10f);
        if(Phase>BeforePhase)SweepWhirlwind(T.TurnDegrees*BeforePhase,T.TurnDegrees*Phase);
        if(Elapsed>=T.ReadySeconds+T.SpinSeconds)FinishWhirlwindTraining();
        if(WhirlwindPause>0.f||Elapsed>=End-UE_SMALL_NUMBER)break;
    }
    if(!bWhirlwind)return;
    // Contact can change the impulse after the last angular substep. Compose
    // that final feedback before publishing the attached arms and weapon.
    Character->RefreshQuickCombatCamera();
    // Damage retains 120 Hz sampling. Publish only the final visible pose once
    // per frame, after the final camera transform, for coherent skin velocities.
    const float Entry=WhirlwindEntry(Elapsed,T.ReadySeconds);
    Viewmodel->SetRelativeLocation(FMath::Lerp(WhirlwindEntryLocation,FVector::ZeroVector,Entry));
    Viewmodel->SetRelativeRotation(FQuat::Slerp(WhirlwindEntryRotation.Quaternion(),FRotator(0,90,0).Quaternion(),Entry));
    if(auto* Arms=Cast<URuneSwordMeshComponent>(Viewmodel))Arms->SetWhirlwindEntryTime(Elapsed);
    SamplePose(Elapsed/End*CurrentAnimation->GetPlayLength());
    SetWhirlwindFocus(WhirlwindPause>0.f?0.f:T.MotionBlur*WhirlwindFeel::Speed(Elapsed,T));
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
    int32 Confirmed=0;
    bool AnyKilled=false;
    FVector ImpactPoint=FVector::ZeroVector;
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
        ++Confirmed;AnyKilled|=Killed;ImpactPoint+=Hit.ImpactPoint;
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
        // 金色符文强化：旋风斩确认命中同样缩减CD（整个旋风过程只按一次）。
        if(!bSwingCooldownReduced)
        {
            bSwingCooldownReduced=true;
            if(auto* Profile=GetWorld()->GetGameInstance()->GetSubsystem<UColdSteelStatusModel>())Profile->ReduceAllAbilityCooldowns(SwingCooldownReduceSeconds);
        }
        const float Hold=FMath::Min(WhirlwindTuning.HitStopSeconds,WhirlwindTuning.HitStopBudget-WhirlwindPauseSpent);
        WhirlwindPause=FMath::Max(0.f,Hold);WhirlwindPauseSpent+=WhirlwindPause;
        // Contact sound/recoil remain available after the hitstop budget is
        // exhausted. Close contacts merge into one short audible/body accent.
        const float Strength=1.f+.12f*FMath::Min(Confirmed-1,3)+(AnyKilled?.16f:0.f);
        if(ImpactAge>=.065f)
        {
            ImpactAge=0.f;ImpactStrength=Strength;
            if(HitSound)UGameplayStatics::PlaySoundAtLocation(this,HitSound,ImpactPoint/Confirmed,.9f,.88f);
        }
        else ImpactStrength=FMath::Max(ImpactStrength,Strength);
    }
}
