#include "RuneSwordComponent.h"
#include "RuneSwordGuardTuning.h"
#include "../FPSGAMECharacter.h"
#include "../FPSGAMEPlayerController.h"
#include "../UI/ColdSteelStatusModel.h"
#include "../Movement/PlayerGuardBreakComponent.h"
#include "../Monsters/FPSCombatHealthComponent.h"
#include "../Monsters/MonsterCombatComponent.h"
#include "../Monsters/PoisonMaggotMonster.h"
#include "../Skills/CorrosivePusDamage.h"
#include "../Skills/EnemyAttackDamage.h"
#include "Animation/AnimSequence.h"
#include "Components/SkeletalMeshComponent.h"
#include "Engine/GameInstance.h"
#include "Engine/World.h"
#include "GameFramework/PlayerController.h"
#include "Kismet/GameplayStatics.h"
#include "Sound/SoundBase.h"

void URuneSwordComponent::BeginGuard()
{
    if(bWhirlwind||bDashAttack)return;
    if(!IsEquipped() || !CanUse() || !Animations.FindRef(TEXT("Guard")))return;
    if(bInspecting)CancelAction();
    bGuardHeld=true;bQueuedAttack=false;
    if(bCharging)ReturnFromCharge();
    TryBeginGuard();
}
void URuneSwordComponent::TryBeginGuard()
{
    if(bWhirlwind || !bGuardHeld || bGuarding || bGuardBreakPose || bGuardReacting ||
        bAttacking || bEquipping || bInspecting || bCharging || bReturningCharge || !CanUse())return;
    auto* Pawn=Character.Get();
    if(Pawn->IsCastBlockingLeftHandAction() || Pawn->IsDodging() || Pawn->IsSliding())return;
    auto* Profile=GetWorld()->GetGameInstance()->GetSubsystem<UColdSteelStatusModel>();
    if(!Profile || Profile->Stamina()<=0.f)return;
    const float Entry=bReturningGuard?GuardPoseTime:0.f;
    bGuarding=true;bReturningGuard=false;GuardStartedAt=GetWorld()->GetTimeSeconds();
    GuardPoseTime=Entry;StopRift();SetClip(TEXT("Guard"),false);Elapsed=Entry;SamplePose(Entry);
    Viewmodel->SetRelativeLocation(FVector::ZeroVector);Viewmodel->SetRelativeRotation(FRotator(0,90,0));
    Profile->DelayStaminaRecovery();
}
void URuneSwordComponent::ReleaseGuard()
{
    bGuardHeld=false;
    if(!bGuarding)return;
    bGuarding=false;bReturningGuard=true;
    if(auto* Profile=GetWorld()->GetGameInstance()->GetSubsystem<UColdSteelStatusModel>())Profile->DelayStaminaRecovery();
}
void URuneSwordComponent::ClearGuard()
{
    bGuardHeld=bGuarding=bReturningGuard=bGuardReacting=bGuardBreakPose=false;
    GuardPoseTime=0.f;GuardFeedbackStrength=0.f;GuardFeedbackAt=-100.;
}
bool URuneSwordComponent::TickGuard(float Delta)
{
    if(bGuarding && (Character->IsCastBlockingLeftHandAction() || Character->IsDodging() || Character->IsSliding()))
    {CancelAction();return true;}
    TryBeginGuard();
    if(bGuardReacting)
    {
        Elapsed=FMath::Min(CurrentAnimation->GetPlayLength(),Elapsed+Delta*GuardReactionRate);SamplePose(Elapsed);
        if(Elapsed>=CurrentAnimation->GetPlayLength())
        {
            bGuardReacting=false;SetClip(TEXT("Guard"),false);
            GuardPoseTime=RuneSwordGuardTuning::RaiseSeconds;Elapsed=GuardPoseTime;SamplePose(Elapsed);
        }
        return true;
    }
    if(bGuarding)
    {
        GuardPoseTime=FMath::Min(RuneSwordGuardTuning::RaiseSeconds,GuardPoseTime+Delta);
        Elapsed=GuardPoseTime;SamplePose(Elapsed);return true;
    }
    if(bReturningGuard)
    {
        GuardPoseTime=FMath::Max(0.f,GuardPoseTime-Delta*RuneSwordGuardTuning::RaiseSeconds/RuneSwordGuardTuning::LowerSeconds);
        Elapsed=GuardPoseTime;SamplePose(Elapsed);
        if(GuardPoseTime<=0.f){bReturningGuard=false;SetClip(TEXT("Idle"),true);}
        return true;
    }
    return false;
}
bool URuneSwordComponent::TickGuardBreak(float Delta)
{
    if(!bGuardBreakPose)return false;
    auto* Pawn=Character.Get();auto* PC=Pawn?Cast<APlayerController>(Pawn->GetController()):nullptr;
    const auto* Health=Pawn?Pawn->FindComponentByClass<UFPSCombatHealthComponent>():nullptr;
    if(AFPSGAMEPlayerController::BlocksOngoingActions(PC) || (Health && Health->IsDead())){CancelAction();return false;}
    Viewmodel->SetVisibility(true);
    if(CurrentAnimation){Elapsed=FMath::Min(CurrentAnimation->GetPlayLength(),Elapsed+Delta);SamplePose(Elapsed);}
    const auto* Broken=Pawn->FindComponentByClass<UPlayerGuardBreakComponent>();
    if(!Broken || !Broken->IsActive()){bGuardBreakPose=false;SetClip(TEXT("Idle"),true);}
    return true;
}
void URuneSwordComponent::GuardFeedback(bool Parried)
{
    GuardFeedbackAt=GetWorld()->GetTimeSeconds();GuardFeedbackStrength=Parried?1.45f:1.f;
    if(auto* Sound=Parried?ParrySound.Get():BlockSound.Get())UGameplayStatics::PlaySound2D(this,Sound,.85f,Parried?1.15f:1.f);
    // Early-window parries can happen during the lift. Keep that entry continuous.
    if(GuardPoseTime>=RuneSwordGuardTuning::RaiseSeconds && !bGuardReacting && Animations.FindRef(TEXT("GuardHit")))
    {
        bGuardReacting=true;GuardReactionRate=Parried?1.25f:1.f;SetClip(TEXT("GuardHit"),false);
    }
}
float URuneSwordComponent::ResolveGuardDamage(float IncomingDamage,const UDamageType* Type,AController* Instigator,AActor* Causer)
{
    if(IncomingDamage<=0.f || !bGuarding)return IncomingDamage;
    auto* Pawn=Character.Get();auto* Profile=GetWorld()->GetGameInstance()->GetSubsystem<UColdSteelStatusModel>();
    const auto* Item=Profile?Profile->Equipped():nullptr;
    if(!CanUse() || !Item || Item->InstanceId!=InstanceId || Pawn->IsCastBlockingLeftHandAction() || Pawn->IsDodging() || Pawn->IsSliding())
    {CancelAction();return IncomingDamage;}
    if(Type && (Type->IsA<UMaggotPoisonDamage>() || Type->IsA<UCorrosivePusDamage>()))return IncomingDamage;
    AActor* Source=Instigator?Instigator->GetPawn():Causer;
    if(Causer && (!Source || Source==Causer))
    {
        if(auto* SourcePawn=Causer->GetInstigator())Source=SourcePawn;
        else if(auto* SourceOwner=Causer->GetOwner();SourceOwner && SourceOwner!=Pawn)Source=SourceOwner;
    }
    if(IsValid(Source) && Source!=Pawn && GetWorld()->GetTimeSeconds()-GuardStartedAt<=RuneSwordGuardTuning::ParrySeconds)
    {
        const FVector Toward=(Source->GetActorLocation()-Pawn->GetActorLocation()).GetSafeNormal2D();
        const FVector Facing=FRotationMatrix(FRotator(0,Pawn->GetControlRotation().Yaw,0)).GetUnitAxis(EAxis::X);
        if(!Toward.IsNearlyZero() && FVector::DotProduct(Facing,Toward)>=FMath::Cos(FMath::DegreesToRadians(RuneSwordGuardTuning::ParryHalfAngleDegrees)))
        {
            GuardFeedback(true);
            GrantClovenCounter();
            if(Type && Type->IsA<UEnemyMeleeDamage>() && !Source->ActorHasTag(TEXT("ParryImmune")))
                if(auto* Combat=Source->FindComponentByClass<UMonsterCombatComponent>())
                    Combat->ReceiveParry(Pawn,RuneSwordGuardTuning::ParryStunSeconds,RuneSwordGuardTuning::ParryKnockbackCM);
            return 0.f;
        }
    }
    GuardFeedback(false);
    const float BlockCost=static_cast<float>(ColdSteelMelee::BlockStamina(MeleeModifiers));
    const bool Broken=Profile->Stamina()<BlockCost;
    Profile->SpendStamina(Broken?Profile->Stamina():BlockCost);
    if(Broken)
    {
        auto* Stun=Pawn->FindComponentByClass<UPlayerGuardBreakComponent>();
        if(!Stun){Stun=NewObject<UPlayerGuardBreakComponent>(Pawn);Pawn->AddInstanceComponent(Stun);Stun->RegisterComponent();}
        Stun->Apply(RuneSwordGuardTuning::BreakStunSeconds);
        // Apply owns the gameplay lock; this component only presents the broken guard.
        bGuardBreakPose=true;GuardFeedbackAt=GetWorld()->GetTimeSeconds();GuardFeedbackStrength=1.8f;
        SetClip(Animations.FindRef(TEXT("GuardBreak"))?TEXT("GuardBreak"):TEXT("Idle"),false);
    }
    return IncomingDamage*RuneSwordGuardTuning::DamageTakenRatio;
}
bool URuneSwordComponent::GetGuardCameraMotion(FVector& Location,FRotator& Rotation) const
{
    if(!bGuarding && !bReturningGuard && !bGuardReacting && !bGuardBreakPose)return false;
    const float Held=bGuardBreakPose?0.f:FMath::SmoothStep(0.f,RuneSwordGuardTuning::RaiseSeconds,GuardPoseTime);
    Location=FVector(-2.f,0.f,-1.2f)*Held;Rotation=FRotator(1.2f,0.f,0.f)*Held;
    const float Age=float(GetWorld()->GetTimeSeconds()-GuardFeedbackAt);
    if(Age>=0.f && Age<.25f)
    {
        const float Pulse=FMath::Sin(FMath::Clamp(Age/.25f,0.f,1.f)*PI)*FMath::Exp(-10.f*Age)*GuardFeedbackStrength;
        Location+=FVector(-11.f,0.f,-2.f)*Pulse;Rotation+=FRotator(6.f,1.f,-1.5f)*Pulse;
    }
    Location*=1.5f;Rotation*=1.5f;return true;
}
