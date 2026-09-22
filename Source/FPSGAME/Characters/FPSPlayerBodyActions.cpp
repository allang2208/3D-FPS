#include "FPSPlayerBodyComponent.h"
#include "../FPSGAMECharacter.h"
#include "../Weapons/RuneSwordComponent.h"
#include "../Weapons/RuneSwordGuardTuning.h"
#include "../Weapons/PistolDualWieldComponent.h"
#include "../Production/ProductionToolComponent.h"
#include "../Production/ProductionPickaxeImpactMotion.h"
#include "../Movement/FPSCharacterMovementComponent.h"
#include "../Movement/FPSTraversalComponent.h"
#include "../Skills/FPSFireballComponent.h"
#include "../Skills/FPSQuickCombatComponent.h"
#include "../Weapons/DualPistolQuickCombatMotion.h"
#include "../Monsters/FPSCombatHealthComponent.h"
#include "Animation/AnimSequence.h"
#include "Components/SkeletalMeshComponent.h"
#include "Engine/World.h"

FFPSBodyState UFPSPlayerBodyComponent::SampleLocalState() const
{
    const auto* Pawn=Character.Get();FFPSBodyState State;
    const float Now=ServerClock(),LocalNow=GetWorld()->GetTimeSeconds();
    const auto Timed=[&](EFPSBodyAction Action,float SourceAge,float SourceLength,float Rate=1.f)
    {
        State.Action=Action;State.bHasActionProgress=true;
        State.ActionDuration=SourceLength/FMath::Max(.01f,Rate);
        State.ActionStartedAt=Now-SourceAge/FMath::Max(.01f,Rate);
        State.ActionProgress=FMath::Clamp(SourceAge/FMath::Max(.01f,SourceLength),0.f,1.f);
    };
    State.Weapon=FName(*Pawn->ActiveInventoryWeaponDefinition);
    State.Family=Pawn->HasInventoryWeapon()?(Pawn->IsPistolWeapon()?TEXT("Pistol"):TEXT("Rifle")):TEXT("Unarmed");
    State.bAiming=Pawn->IsAiming();State.bSprinting=Pawn->IsSprinting();
    State.bCrouched=Pawn->bIsCrouched;State.bSliding=Pawn->IsSliding();State.bDual=Pawn->IsDualWieldingPistols();
    State.AimPitch=FMath::RoundToFloat(FRotator::NormalizeAxis(Pawn->GetBaseAimRotation().Pitch));
    State.LastShotAt=Pawn->LastShotWorldTime>=0.?Now-(LocalNow-Pawn->LastShotWorldTime):-100.f;
    if(Pawn->HasInventoryWeapon())
    {
        EFPSBodyAction Action=EFPSBodyAction::None;
        switch(Pawn->WeaponState)
        {
        case EAKMWeaponState::Equipping:Action=EFPSBodyAction::Equip;break;
        case EAKMWeaponState::Reloading:Action=EFPSBodyAction::Reload;break;
        case EAKMWeaponState::ReloadingEmpty:Action=EFPSBodyAction::ReloadEmpty;break;
        case EAKMWeaponState::Inspecting:Action=EFPSBodyAction::Inspect;break;
        default:break;
        }
        Timed(Action,Pawn->WeaponStateElapsed,Pawn->WeaponStateDuration);
    }
    if(State.bDual&&Pawn->DualPistols)
    {
        State.Family=TEXT("Pistol");
        for(int32 I=0;I<2;++I)
        {
            const auto& Hand=Pawn->DualPistols->Hand(I);
            auto& BodyHand=I==0?State.RightHand:State.LeftHand;
            BodyHand.LastShotAt=Now-static_cast<float>(LocalNow-Hand.LastShot);
            BodyHand.bReloading=Hand.Reloading;
            BodyHand.bEquipping=Hand.Action&&Hand.Action==Hand.Clips.FindRef(TEXT("equip"));
            BodyHand.Progress=Hand.Action?FMath::Clamp(Hand.ActionTime/FMath::Max(.01f,Hand.Action->GetPlayLength()),0.f,1.f):0.f;
            State.LastShotAt=FMath::Max(State.LastShotAt,BodyHand.LastShotAt);
        }
        // The two hands are evaluated independently; never play a two-handed reload.
        if(State.Action==EFPSBodyAction::Reload||State.Action==EFPSBodyAction::ReloadEmpty)State.Action=EFPSBodyAction::None;
    }
    if(const auto* Sword=Pawn->FindComponentByClass<URuneSwordComponent>();Sword&&Sword->IsEquipped())
    {
        State.Family=TEXT("Melee");State.Action=EFPSBodyAction::None;State.ActionVariant=Sword->CurrentClip;
        const float Length=Sword->CurrentAnimation?Sword->CurrentAnimation->GetPlayLength():1.f;
        if(Sword->bWhirlwind)
        {
            const auto& W=Sword->WhirlwindTuning;const float End=W.ReadySeconds+W.SpinSeconds+W.RecoverSeconds;
            Timed(EFPSBodyAction::Whirlwind,Sword->Elapsed,End);
            State.ContactFraction=W.ReadySeconds/End;State.ReleaseFraction=(W.ReadySeconds+W.SpinSeconds)/End;
        }
        else if(Sword->bGuardBreakPose)Timed(EFPSBodyAction::GuardBreak,Sword->Elapsed,Length);
        else if(Sword->bGuardReacting)Timed(EFPSBodyAction::GuardHit,Sword->Elapsed,Length,Sword->GuardReactionRate);
        else if(Sword->bGuarding||Sword->bReturningGuard)
        {
            Timed(EFPSBodyAction::Guard,Sword->GuardPoseTime,RuneSwordGuardTuning::RaiseSeconds);
            State.ActionWeight=State.ActionProgress;
        }
        else if(Sword->bCharging||Sword->bReturningCharge)
        {
            Timed(EFPSBodyAction::Charge,Sword->Elapsed,RuneSwordHeavyRhythm::ChargeSeconds);
            if(Sword->bReturningCharge)
            {
                State.ActionProgress=FMath::Clamp(Sword->CancelChargeFrom/RuneSwordHeavyRhythm::ChargeSeconds,0.f,1.f);
                State.ActionWeight=1.f-FMath::SmoothStep(0.f,Sword->CancelChargeDuration,Sword->CancelChargeAge);
            }
        }
        else if(Sword->bAttacking)
        {
            const auto Action=Sword->bPommelAttack?EFPSBodyAction::Pommel:Sword->bThrustAttack?EFPSBodyAction::Thrust:
                (Sword->bHeavyAttack||Sword->bOverheadAttack?EFPSBodyAction::HeavyStrike:EFPSBodyAction::Strike);
            // The sword executor ends at CurrentAnimation length and compares
            // contact against Elapsed before sampling its authored pose.
            Timed(Action,Sword->Elapsed,Length,Sword->SwingRate);
            State.ContactFraction=Sword->ContactStart/Length;State.ReleaseFraction=Sword->ContactEnd/Length;
            if(Sword->bDashAttack)State.ActionVariant=TEXT("DashOverhead");
        }
        else if(Sword->bEquipping)Timed(EFPSBodyAction::Equip,Sword->Elapsed,Length);
        else if(Sword->bInspecting)Timed(EFPSBodyAction::Inspect,Sword->Elapsed,Length);
    }
    if(const auto* Tool=Pawn->FindComponentByClass<UProductionToolComponent>();Tool&&Tool->IsEquipped())
    {
        State.Family=TEXT("Tool");State.Weapon=FName(*Tool->Kind);State.ActionVariant=State.Weapon;State.Action=EFPSBodyAction::None;
        if(Tool->EquipElapsed>=0.f)
        {
            UAnimSequence* Clip=Tool->Motions.FindRef(TEXT("Equip"));
            Timed(EFPSBodyAction::Equip,Tool->EquipElapsed,Clip?Clip->GetPlayLength():.6f);
        }
        else if(Tool->Elapsed>=0.f)
        {
            Timed(EFPSBodyAction::HeavyStrike,Tool->Elapsed,Tool->SwingSeconds);
            State.ContactFraction=Tool->ContactSeconds/FMath::Max(.01f,Tool->SwingSeconds);
            if(Tool->bHitConfirmed)
            {
                const float Recover=Tool->Kind==TEXT("axe")?Tool->AxeMotion.HitRecoverSeconds:
                    Tool->Kind==TEXT("pickaxe")?ProductionPickaxeImpact::HitRecoverSeconds:Tool->SwingSeconds-Tool->ContactSeconds;
                Timed(EFPSBodyAction::ToolRecover,Tool->Elapsed-Tool->ContactSeconds,Recover);
            }
        }
    }
    if(const auto* Bash=Pawn->FindComponentByClass<UFPSQuickCombatComponent>();Bash&&Bash->IsOccupyingLeftHand())
    {
        Timed(EFPSBodyAction::GunBash,Bash->GetActionAge(),Bash->GetSourceLength());
        State.ContactFraction=Bash->GetContactFraction();
        State.ActionVariant=State.Family==TEXT("Rifle")?TEXT("RifleBash"):TEXT("PistolBash");
        if(State.bDual)State.ActionVariant=DualPistolQuickCombatMotion::StrikingHand(Bash->GetActionSerial())==1?TEXT("PistolBashLeft"):TEXT("PistolBashRight");
    }
    // IsCastingWithLeftHand intentionally includes gun bash for input arbitration.
    // Presentation must ask the spell owner, not reinterpret that shared busy flag.
    if(const auto* Magic=Pawn->FindComponentByClass<UFPSFireballComponent>();Magic&&Magic->IsOccupyingLeftHand())
    {
        State.Action=EFPSBodyAction::Cast;State.bHasActionProgress=true;State.ActionDuration=0.f;
        State.ActionProgress=Magic->HandPhaseFraction();State.ReleaseFraction=Magic->HandReleaseFraction();
        switch(Magic->GetHandPhase())
        {
        case EFireballHandPhase::Raising:State.ActionVariant=TEXT("Gather");break;
        case EFireballHandPhase::ReadyingRelease:State.ActionVariant=TEXT("Ready");break;
        case EFireballHandPhase::Releasing:State.ActionVariant=TEXT("Release");break;
        case EFireballHandPhase::Recovering:State.ActionVariant=TEXT("Recover");break;
        default:State.ActionVariant=TEXT("Hold");break;
        }
    }
    if(State.bSliding)
    {
        State.Motion=EFPSBodyMotion::Slide;
        State.MotionProgress=FMath::Clamp(Pawn->SlideAge/FMath::Max(.1f,Pawn->SlideMaximumTime),0.f,1.f);
        const FVector V=Pawn->GetActorQuat().UnrotateVector(Pawn->GetVelocity()).GetSafeNormal2D();
        State.MotionDirection=V.IsNearlyZero()?FVector(0,1,0):FVector(-V.Y,V.X,0);
    }
    if(const auto* Move=Cast<UFPSCharacterMovementComponent>(Pawn->GetCharacterMovement());Move&&Move->IsDodging())
    {
        State.Motion=EFPSBodyMotion::Dodge;State.MotionProgress=Move->GetDodgeProgress();
        const FVector D=Pawn->GetActorQuat().UnrotateVector(Move->GetDodgeDirection());
        State.MotionDirection=FVector(-D.Y,D.X,0);
    }
    if(const auto* Traversal=Pawn->FindComponentByClass<UFPSTraversalComponent>();Traversal&&Traversal->IsTraversing())
    {
        const auto& Target=Traversal->LastJumpTarget;
        State.Motion=Target.Action==EFPSTraversalAction::Vault?EFPSBodyMotion::Vault:EFPSBodyMotion::Mantle;
        State.MotionProgress=Traversal->GetPresentationProgress();State.MotionContact=Traversal->GetContactFraction();
        State.MotionRelease=Traversal->GetReleaseFraction();State.Action=EFPSBodyAction::Traverse;
        State.MotionHandContact=Traversal->GetHandContactWeight();
        State.ActionProgress=State.MotionProgress;State.bHasActionProgress=true;
        const FVector Across=FVector::CrossProduct(FVector::UpVector,-Target.WallNormal).GetSafeNormal();
        State.RightHandhold=Target.FrontEdge+Across*22.f;State.LeftHandhold=Target.FrontEdge-Across*22.f;
        if(Target.Handholds.Num()>=2)
        {
            State.RightHandhold=Target.Handholds[0].Position;State.LeftHandhold=Target.Handholds[1].Position;
            if(FVector::DotProduct(State.RightHandhold-State.LeftHandhold,Across)<0.f)Swap(State.RightHandhold,State.LeftHandhold);
        }
        State.bHasHandholds=true;
    }
    if(const auto* Health=Pawn->FindComponentByClass<UFPSCombatHealthComponent>();Health&&Health->IsDead())
    {State.Action=EFPSBodyAction::Dead;State.ActionDuration=0.f;State.bHasActionProgress=false;State.Motion=EFPSBodyMotion::Ground;}
    return State;
}
