#include "RuneSwordComponent.h"
#include "../Characters/FPSComponentVisibility.h"
#include "../Skills/LightningHasteSpeed.h"
#include "RuneSwordGuardTuning.h"
#include "../Production/ProductionToolComponent.h"
#include "../Production/WarhammerGuardMotion.h"
#include "../Multiplayer/ColdSteelAuthorityContext.h"
#include "TangDaoGuardComponent.h"
#include "EagleTalonGuardComponent.h"
#include "PanChiGuardComponent.h"
#include "../Combat/CombatStatusFormula.h"
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
#include "RuneSwordMeshComponent.h"

namespace
{
bool IsBreathingGuardClip(const UAnimSequenceBase* Clip)
{
    return Clip&&Clip->GetPlayLength()>=RuneSwordGuardTuning::ViewHoldStartSeconds+RuneSwordGuardTuning::ViewBreathSeconds-.02f;
}
// Clip time where the raise ends and the hold begins.
float GuardHoldStart(const UAnimSequenceBase* Clip)
{
    if(IsBreathingGuardClip(Clip))return RuneSwordGuardTuning::ViewHoldStartSeconds;
    return Clip?FMath::Min(Clip->GetPlayLength(),RuneSwordGuardTuning::RaiseSeconds):RuneSwordGuardTuning::RaiseSeconds;
}
// Haste speeds the raise only; the breathing loop keeps the reference rhythm and wraps one breath back.
float AdvanceGuardView(const UAnimSequenceBase* Clip,float Time,float Delta,float Speed)
{
    const float Hold=GuardHoldStart(Clip);
    if(!IsBreathingGuardClip(Clip))return FMath::Min(Hold,Time+Delta*Speed);
    Time+=Time<Hold?Delta*Speed:Delta;
    const float Length=Clip->GetPlayLength();
    while(Time>=Length)Time-=RuneSwordGuardTuning::ViewBreathSeconds;
    return Time;
}
}

void URuneSwordComponent::BeginGuard()
{
    if(!ToolGuardInstance.IsEmpty())
    {
        auto* Tool=Character.IsValid()?Character->FindComponentByClass<UProductionToolComponent>():nullptr;
        if(!Tool||!Tool->CanQueueGuard())return;
        Tool->PrepareGuard();bGuardHeld=true;TryBeginGuard();return;
    }
    if(bChainSlash||bUppercut||bWhirlwind||bDashAttack)return;
    if(!IsEquipped() || !CanUse() || !Animations.FindRef(TEXT("Guard")))return;
    if(bInspecting)CancelAction();
    bGuardHeld=true;bQueuedAttack=false;RingPrimaryDownAt=-1.;
    if(bCharging)ReturnFromCharge();
    TryBeginGuard();
}
void URuneSwordComponent::TryBeginGuard()
{
    if(bChainSlash || bUppercut || bWhirlwind || !bGuardHeld || bGuarding || bGuardBreakPose || bGuardReacting ||
        bAttacking || bEquipping || bInspecting || bCharging || bReturningCharge || !CanUse())return;
    auto* Pawn=Character.Get();
    if(Pawn->IsCastBlockingLeftHandAction() || Pawn->IsDodging() || Pawn->IsSliding())return;
    auto* Profile=GetWorld()->GetGameInstance()->GetSubsystem<UColdSteelStatusModel>();
    if(!Profile || Profile->Stamina()<=0.f)return;
    if(!ToolGuardInstance.IsEmpty())
    {
        const auto* Tool=Pawn->FindComponentByClass<UProductionToolComponent>();
        const auto* Broken=Pawn->FindComponentByClass<UPlayerGuardBreakComponent>();
        if(!Tool||!Tool->CanStartGuard()||(Broken&&Broken->IsActive()))return;
    }
    const double Now=GetWorld()->GetTimeSeconds();
    if(!bGuarding&&Now-GuardReleasedAt<RuneSwordGuardTuning::RaiseSeconds+RuneSwordGuardTuning::LowerSeconds)return;
    const float Entry=bReturningGuard?GuardPoseTime:0.f;
    // Re-raising while lowering resumes the clip where the lowering has reached.
    const float ViewEntry=bReturningGuard&&CurrentClip==TEXT("Guard")?FMath::Min(Elapsed,GuardHoldStart(CurrentAnimation)):0.f;
    bGuarding=true;bReturningGuard=false;GuardStartedAt=Now;bNetworkGuardParried=false;
    SendGuardIntent(true);
    if(!ToolGuardInstance.IsEmpty())
    {
        GuardPoseTime=Entry;ToolGuardAge=Entry;ToolGuardClip=TEXT("GuardEnter");
        Profile->DelayStaminaRecovery();return;
    }
    GuardPoseTime=Entry;StopRift();SetClip(TEXT("Guard"),false);Elapsed=ViewEntry;SamplePose(ViewEntry);
    Viewmodel->SetRelativeLocation(FVector::ZeroVector);Viewmodel->SetRelativeRotation(FRotator(0,90,0));
    Profile->DelayStaminaRecovery();
}
void URuneSwordComponent::ReleaseGuard()
{
    SendGuardIntent(false);
    bGuardHeld=false;
    GuardReleasedAt=GetWorld()->GetTimeSeconds();
    if(!bGuarding)return;
    bGuarding=false;bReturningGuard=true;
    if(ToolGuardInstance.IsEmpty())
    {
        // The lowering is the raise played back from the hold start. Released mid-breath, or during the 0.75 s V24
        // hit reaction (which must not delay the counterattack), blend from the shown pose to that start.
        const bool bMidReaction=bGuardReacting&&CurrentClip==TEXT("GuardHit");
        if(bMidReaction||(!bGuardReacting&&CurrentClip==TEXT("Guard")&&Elapsed>GuardHoldStart(CurrentAnimation)))
        {
            if(auto* Arms=Cast<URuneSwordMeshComponent>(Viewmodel))Arms->CaptureLocomotionEntry(.12f);
            if(bMidReaction){bGuardReacting=false;SetClip(TEXT("Guard"),false);GuardPoseTime=RuneSwordGuardTuning::RaiseSeconds;}
            Elapsed=GuardHoldStart(CurrentAnimation);
        }
    }
    if(!ToolGuardInstance.IsEmpty())
    {
        bGuardReacting=false;
        // Releasing during the lift unwinds that partial lift continuously;
        // the full exit clip starts only after the brace has been reached.
        if(ToolGuardClip!=TEXT("GuardEnter"))
        {ToolGuardAge=0.f;ToolGuardClip=TEXT("GuardExit");}
    }
    if(auto* Profile=GetWorld()->GetGameInstance()->GetSubsystem<UColdSteelStatusModel>())Profile->DelayStaminaRecovery();
}
void URuneSwordComponent::ClearGuard()
{
    if(bGuardHeld||bGuarding)SendGuardIntent(false);
    bGuardHeld=bGuarding=bReturningGuard=bGuardReacting=bGuardBreakPose=false;
    GuardPoseTime=0.f;GuardFeedbackStrength=0.f;GuardFeedbackAt=-100.;
    ToolGuardClip=NAME_None;ToolGuardAge=0.f;
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
            // GuardHit ends on the hold-start pose of the Guard clip.
            bGuardReacting=false;SetClip(TEXT("Guard"),false);
            GuardPoseTime=RuneSwordGuardTuning::RaiseSeconds;Elapsed=GuardHoldStart(CurrentAnimation);SamplePose(Elapsed);
        }
        return true;
    }
    const float Speed=LightningHaste::ActionSpeed(GetOwner());
    if(bGuarding)
    {
        GuardPoseTime=FMath::Min(RuneSwordGuardTuning::RaiseSeconds,GuardPoseTime+Delta*Speed);
        Elapsed=AdvanceGuardView(CurrentAnimation,Elapsed,Delta,Speed);SamplePose(Elapsed);return true;
    }
    if(bReturningGuard)
    {
        GuardPoseTime=FMath::Max(0.f,GuardPoseTime-Delta*Speed*RuneSwordGuardTuning::RaiseSeconds/RuneSwordGuardTuning::LowerSeconds);
        // The raise played back from the hold start in LowerSeconds, like the earlier 0.20 s clips.
        const float Hold=GuardHoldStart(CurrentAnimation);
        Elapsed=FMath::Max(0.f,FMath::Min(Elapsed,Hold)-Delta*Speed*Hold/RuneSwordGuardTuning::LowerSeconds);SamplePose(Elapsed);
        if(Elapsed<=0.f){bReturningGuard=false;GuardPoseTime=0.f;SetClip(TEXT("Idle"),true);}
        return true;
    }
    return false;
}
bool URuneSwordComponent::TickGuardBreak(float Delta)
{
    if(!bGuardBreakPose)return false;
    auto* Pawn=Character.Get();auto* PC=Pawn?Cast<APlayerController>(Pawn->GetController()):nullptr;
    const auto* Health=Pawn?Pawn->FindComponentByClass<UFPSCombatHealthComponent>():nullptr;
    // The break's own input lock is expected; only presentation loss/death or
    // an actual modal UI may cancel its animation.
    if(!CanPresent()||AFPSGAMEPlayerController::BlocksActionContinuation(PC) || (Health && Health->IsDead())){CancelAction();return false;}
    FPSComponentVisibility::SetVisibilityTree(Viewmodel,true);
    if(CurrentAnimation){Elapsed=FMath::Min(CurrentAnimation->GetPlayLength(),Elapsed+Delta);SamplePose(Elapsed);}
    const auto* Broken=Pawn->FindComponentByClass<UPlayerGuardBreakComponent>();
    if(!Broken || !Broken->IsActive())
    {
        bGuardBreakPose=false;SetClip(TEXT("Idle"),true);
        // V24 break holds the beaten-down pose for the stun; recover to idle over 0.32 s instead of the 0.10 s handoff.
        if(auto* Arms=Cast<URuneSwordMeshComponent>(Viewmodel))Arms->CaptureLocomotionEntry(.32f);
    }
    return true;
}
void URuneSwordComponent::GuardFeedback(bool Parried)
{
    GuardFeedbackAt=GetWorld()->GetTimeSeconds();GuardFeedbackStrength=Parried?1.45f:1.f;
    if(!ToolGuardInstance.IsEmpty())
    {
        if(auto* Tool=Character->FindComponentByClass<UProductionToolComponent>())Tool->PlayGuardSound(Parried);
        if(bGuarding&&GuardPoseTime>=WarhammerGuard::EnterSeconds&&!bGuardReacting)
        {bGuardReacting=true;GuardReactionRate=Parried?1.25f:1.f;ToolGuardClip=TEXT("GuardHit");ToolGuardAge=0.f;}
        return;
    }
    USoundBase* ImpactSound=Parried?ParrySound.Get():(FMath::RandBool()?BlockSound.Get():BlockSoundAlternate.Get());
    if(ImpactSound)UGameplayStatics::PlaySound2D(this,ImpactSound,.85f,Parried?1.15f:1.f);
    // Early-window parries can happen during the lift. Keep that entry continuous.
    if(bGuarding && GuardPoseTime>=RuneSwordGuardTuning::RaiseSeconds && !bGuardReacting && Animations.FindRef(TEXT("GuardHit")))
    {
        bGuardReacting=true;GuardReactionRate=Parried?1.25f:1.f;SetClip(TEXT("GuardHit"),false);
    }
}
float URuneSwordComponent::ResolveGuardDamage(float IncomingDamage,const UDamageType* Type,AController* Instigator,AActor* Causer)
{
    if(IncomingDamage<=0.f || !bGuarding)return IncomingDamage;
    auto* Pawn=Character.Get();auto* Profile=ColdSteelAuthority::ForPawn(Pawn);
    const auto* Item=GuardItem(Profile);
    const auto& Mods=GuardModifiers();
    if(!Pawn||!Pawn->HasAuthority()||!CanMaintainNetworkGuard()||!Item||Item->InstanceId!=GuardWeaponInstance())
    {CancelAction();return IncomingDamage;}
    if(Type && (Type->IsA<UMaggotPoisonDamage>() || Type->IsA<UCorrosivePusDamage>()))return IncomingDamage;
    AActor* Source=Instigator?Instigator->GetPawn():Causer;
    if(Causer && (!Source || Source==Causer))
    {
        if(auto* SourcePawn=Causer->GetInstigator())Source=SourcePawn;
        else if(auto* SourceOwner=Causer->GetOwner();SourceOwner && SourceOwner!=Pawn)Source=SourceOwner;
    }
    if(IsValid(Source) && Source!=Pawn && !bNetworkGuardParried
        && GetWorld()->GetTimeSeconds()-GuardStartedAt<=RuneSwordGuardTuning::ParrySeconds*Mods.ParryWindow)
    {
        const FVector Toward=(Source->GetActorLocation()-Pawn->GetActorLocation()).GetSafeNormal2D();
        const FVector Facing=FRotationMatrix(FRotator(0,Pawn->GetControlRotation().Yaw,0)).GetUnitAxis(EAxis::X);
        if(!Toward.IsNearlyZero() && FVector::DotProduct(Facing,Toward)>=FMath::Cos(FMath::DegreesToRadians(RuneSwordGuardTuning::ParryHalfAngleDegrees)))
        {
            bNetworkGuardParried=true;
            if(auto* Eagle=Pawn->FindComponentByClass<UEagleTalonGuardComponent>())Eagle->Defended(Item->InstanceId,Source,true);
            if(Pawn->IsLocallyControlled())GuardFeedback(true);
            if(auto* Guard=Pawn->FindComponentByClass<UTangDaoGuardComponent>())Guard->GrantDragon();
            if(auto* Guard=Pawn->FindComponentByClass<UPanChiGuardComponent>())Guard->ConfirmGuard(true);
            if(ToolGuardInstance.IsEmpty())GrantClovenCounter();
            if(Mods.RiposteSeconds>0)
                UCombatStatusFormula::GetOrAdd(Pawn)->GrantRiposteGuard(Mods.RiposteSeconds,Mods.RiposteSpeed,Mods.RiposteStamina);
            if(Type && Type->IsA<UEnemyMeleeDamage>() && !Source->ActorHasTag(TEXT("ParryImmune")))
                if(auto* Combat=Source->FindComponentByClass<UMonsterCombatComponent>())
                    Combat->ReceiveParry(Pawn,RuneSwordGuardTuning::ParryStunSeconds,RuneSwordGuardTuning::ParryKnockbackCM);
            if(!Pawn->IsLocallyControlled())ClientSwordGuardResult(GuardWeaponInstance(),1,0.f,GetWorld()->GetTimeSeconds(),ServerGuardIntentSerial);
            return 0.f;
        }
    }
    if(Pawn->IsLocallyControlled())GuardFeedback(false);
    const float BlockCost=static_cast<float>(ColdSteelMelee::BlockStamina(Mods,Profile));
    const float Available=Profile->Stamina();
    const float Spent=FMath::Min(Available,BlockCost);
    const bool Broken=Available<BlockCost;
    Profile->SpendStamina(Spent);
    if(!Broken)
    {
        if(auto* Eagle=Pawn->FindComponentByClass<UEagleTalonGuardComponent>())Eagle->Defended(GuardWeaponInstance(),Source,false);
        if(auto* Guard=Pawn->FindComponentByClass<UPanChiGuardComponent>())Guard->ConfirmGuard(false);
    }
    if(Broken)
    {
        auto* Stun=Pawn->FindComponentByClass<UPlayerGuardBreakComponent>();
        if(!Stun){Stun=NewObject<UPlayerGuardBreakComponent>(Pawn);Pawn->AddInstanceComponent(Stun);Stun->RegisterComponent();}
        Stun->Apply(RuneSwordGuardTuning::BreakStunSeconds);
        bGuarding=bGuardHeld=false;
        if(Pawn->IsLocallyControlled())PresentGuardBreak();
    }
    if(!Pawn->IsLocallyControlled())ClientSwordGuardResult(GuardWeaponInstance(),Broken?2:0,Spent,GetWorld()->GetTimeSeconds(),ServerGuardIntentSerial);
    const double Reduction=FMath::Clamp((1.-RuneSwordGuardTuning::DamageTakenRatio)*Mods.BlockReduction,0.,1.);
    return IncomingDamage*(1.-Reduction);
}
bool URuneSwordComponent::GetGuardCameraMotion(FVector& Location,FRotator& Rotation) const
{
    if(!bGuarding && !bReturningGuard && !bGuardReacting && !bGuardBreakPose)return false;
    // The V24 sword clip is matched to a still reference camera, so only the hammer keeps the static hold offset;
    // both keep the impact pulse below.
    const float Held=bGuardBreakPose||ToolGuardInstance.IsEmpty()?0.f:FMath::SmoothStep(0.f,GuardRaiseSeconds(),GuardPoseTime);
    Location=FVector(-2.f,0.f,-1.2f)*Held;Rotation=FRotator(1.2f,0.f,0.f)*Held;
    const float Age=float(GetWorld()->GetTimeSeconds()-GuardFeedbackAt);
    if(Age>=0.f && Age<.25f)
    {
        const float Pulse=FMath::Sin(FMath::Clamp(Age/.25f,0.f,1.f)*PI)*FMath::Exp(-10.f*Age)*GuardFeedbackStrength;
        Location+=FVector(-11.f,0.f,-2.f)*Pulse;Rotation+=FRotator(6.f,1.f,-1.5f)*Pulse;
    }
    Location*=1.5f;Rotation*=1.5f;return true;
}
