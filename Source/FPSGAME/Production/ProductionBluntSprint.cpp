#include "ProductionToolComponent.h"
#include "../FPSGAMECharacter.h"
#include "../Multiplayer/ColdSteelAuthorityContext.h"
#include "../UI/ColdSteelStatusModel.h"
#include "../Monsters/FPSCombatHealthComponent.h"
#include "../Movement/FPSCharacterMovementComponent.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "GameFramework/Controller.h"
#include "Engine/GameInstance.h"
#include "Engine/World.h"
#include "HAL/IConsoleManager.h"

namespace
{
TAutoConsoleVariable<int32> BluntSprintTrace(TEXT("fps.Tool.SprintTrace"),0,
    TEXT("Log held hammer sprint readiness gates while Shift is held. 0 disables."));
float ReadySeconds(const UColdSteelStatusModel* Profile)
{
    const auto& D=Profile->MasteryDefinition(TEXT("dashAttack"));
    const int32 Level=FMath::Clamp(Profile->MasteryProgress(D.Id).Level,1,D.MaxLevel);
    return FMath::Max(.01f,D.DashAttack.ReadySeconds*(1.f-(Level-1)*D.DashAttack.ReadyReductionPerLevel));
}
}

void UProductionToolComponent::AdvanceBluntSprintReadiness(float Delta)
{
    auto* Pawn=Character.Get();auto* World=GetWorld();if(!Pawn||!World)return;
    auto* Profile=Pawn->HasAuthority()?ColdSteelAuthority::ForPawn(Pawn):World->GetGameInstance()->GetSubsystem<UColdSteelStatusModel>();
    const auto* Item=Profile?Profile->ActiveProductionTool():nullptr;
    const auto* Health=Pawn->FindComponentByClass<UFPSCombatHealthComponent>();
    const bool Local=Pawn->IsLocallyControlled();
    const bool Eligible=Item&&ColdSteelInventory::IsTwoHandedBlunt(*Item)&&!Pawn->IsTraversing()&&
        !Pawn->IsDodging()&&!Pawn->IsCastBlockingLeftHandAction()&&(!Health||!Health->IsDead())&&
        (Local?(!IsBusy()&&CanUse()):(!bBluntServerCharging&&World->GetTimeSeconds()>=BluntServerReadyAt));
    if(Local&&Kind==TEXT("warhammer")&&BluntSprintTrace.GetValueOnGameThread()!=0&&Pawn->bSprintHeld)
    {
        static double LastLogAt=-100.;const double Now=World->GetTimeSeconds();
        if(Now<LastLogAt||Now-LastLogAt>=.4)
        {
            LastLogAt=Now;
            UE_LOG(LogTemp,Display,TEXT("[WarhammerSprint] eligible=%d seconds=%.3f ready=%.3f sprint=%d ground=%d speed=%.1f busy=%d equip=%.3f attack=%.3f charge=%d return=%d whirl=%d uppercut=%d canUse=%d cast=%d canSprint=%d aim=%d fire=%d locked=%d forward=%.2f"),
                Eligible,BluntSprintSeconds,DashReadyFraction(),Pawn->IsSprinting(),Pawn->GetCharacterMovement()->IsMovingOnGround(),
                Pawn->GetVelocity().Size2D(),IsBusy(),EquipElapsed,Elapsed,bBluntCharging,bBluntReturningCharge,bBluntWhirlwind,bBluntUppercut,
                CanUse(),Pawn->IsCastBlockingLeftHandAction(),Profile&&Profile->CanSprint(),Pawn->bIsAiming,Pawn->bFireHeld,
                Pawn->IsMeleeSkillMovementLocked(),Pawn->MoveInput.Y);
        }
    }
    if(!Eligible||BluntSprintInstance!=Item->InstanceId)
    {
        BluntSprintSeconds=0.f;BluntSprintReadyAt=-100.;
        BluntSprintInstance=Eligible?Item->InstanceId:FString();
        if(!Eligible)return;
    }
    const float Required=ReadySeconds(Profile);
    const auto* Move=CastChecked<UFPSCharacterMovementComponent>(Pawn->GetCharacterMovement());
    const bool SprintIntent=Local?(Pawn->bSprintHeld&&Pawn->IsSprinting()):Move->bWantsToSprint;
    const bool GroundSprint=SprintIntent&&!Pawn->IsSliding()&&
        Move->IsMovingOnGround()&&Pawn->GetVelocity().SizeSquared2D()>2500.f;
    // CMC transmits actual sprint locomotion, not the local Shift key. Airborne
    // moves clear that flag, so retain only a previously earned readiness there.
    const bool Carry=(!Local||Pawn->bSprintHeld)&&BluntSprintSeconds>=Required&&
        (Pawn->IsSliding()||Move->IsFalling()||Pawn->bWeaponJumpAirborne||!Move->PendingLaunchVelocity.IsZero());
    if(GroundSprint)BluntSprintSeconds=FMath::Min(Required,BluntSprintSeconds+Delta);
    else if(!Carry)BluntSprintSeconds=0.f;
    if(BluntSprintSeconds>=Required)BluntSprintReadyAt=World->GetTimeSeconds();
}

float UProductionToolComponent::DashReadyFraction() const
{
    const auto* Pawn=Character.Get();
    if(Kind!=TEXT("warhammer")||!IsEquipped()||IsBusy()||!Pawn||!Pawn->bSprintHeld||!CanUse()||
        Pawn->IsDodging()||Pawn->IsCastBlockingLeftHandAction())return 0.f;
    const auto* Profile=GetWorld()->GetGameInstance()->GetSubsystem<UColdSteelStatusModel>();
    if(!Profile)return 0.f;
    const auto* Move=Pawn->GetCharacterMovement();const float Required=ReadySeconds(Profile);
    const bool Carry=BluntSprintSeconds>=Required&&(Pawn->IsSliding()||Move->IsFalling()||
        Pawn->bWeaponJumpAirborne||!Move->PendingLaunchVelocity.IsZero());
    if(!Carry&&(!Pawn->IsSprinting()||!Move->IsMovingOnGround()||Pawn->GetVelocity().SizeSquared2D()<=2500.f))return 0.f;
    return FMath::Clamp(BluntSprintSeconds/Required,0.f,1.f);
}

bool UProductionToolComponent::TryBeginSprintAttack()
{
    if(DashReadyFraction()<1.f-UE_SMALL_NUMBER||!HasReadyPresentation())return false;
    auto* Pawn=Character.Get();
    auto* Move=Pawn?Cast<UFPSCharacterMovementComponent>(Pawn->GetCharacterMovement()):nullptr;
    const auto* Profile=Pawn?ColdSteelAuthority::ForPawn(Pawn):nullptr;
    if(!Move||!Profile)return false;
    const bool PendingJump=!Move->PendingLaunchVelocity.IsZero();
    const bool CarryMomentum=Move->IsFalling()||PendingJump;
    const FVector Carry=PendingJump?Move->PendingLaunchVelocity:Move->Velocity;
    const float Distance=Profile->DashAttackStats().DistanceCM;
    bBluntSprintAttack=true;NextBluntStage=2;
    BeginUse();
    if(Elapsed<0.f){bBluntSprintAttack=bBluntHeavy=false;return false;}
    if(Pawn->IsSliding())Pawn->StopSlide(true);
    Pawn->ExitSprintForWeapon();
    BluntSprintDirection=BluntSlamRotation.GetForwardVector().GetSafeNormal2D();
    BluntSprintLungeDistance=Distance;
    bBluntSprintLungeBlocked=CarryMomentum&&Move->BeginMeleeDashMomentum(Carry,BluntAttackId);
    if(!bBluntSprintLungeBlocked)
    {
        Move->PendingLaunchVelocity.X=0.;Move->PendingLaunchVelocity.Y=0.;
        Move->BeginMeleeLungeRequest(EFPSMeleeMove::Dash,BluntSprintDirection,BluntAttackId);
    }
    UpdateBluntSprintAnchor(true);
    BluntSprintSeconds=0.f;BluntSprintReadyAt=-100.;
    return true;
}

bool UProductionToolComponent::GetCommittedSprintMovement(uint32 AttackId,FVector& Direction,float& DistanceCM,float& LimitCM,float& RecoverySeconds) const
{
    const auto* Pawn=Character.Get();const auto* World=GetWorld();
    if(!Pawn||!Pawn->HasAuthority()||!World||!bBluntServerSprintAttack||AttackId!=BluntServerAttackId||
        World->GetTimeSeconds()>BluntServerSprintMoveUntil)return false;
    const auto* Profile=ColdSteelAuthority::ForPawn(Pawn);
    const auto* Item=Profile?Profile->ActiveProductionTool():nullptr;
    if(!Item||!ColdSteelInventory::IsTwoHandedBlunt(*Item)||Item->InstanceId!=BluntServerInstance)return false;
    DistanceCM=BluntSprintLungeDistance;
    Direction=BluntSprintDirection;
    LimitCM=DistanceCM*FMath::SmoothStep(0.f,WarhammerSprint::LiftSeconds/HasteActionRate,
        float(World->GetTimeSeconds()-BluntServerSprintStartedAt)+.05f);
    RecoverySeconds=FMath::Max(.01f,float(BluntServerReadyAt-World->GetTimeSeconds()));
    return true;
}

void UProductionToolComponent::AdvanceBluntSprintLunge(float FromTime,float ToTime)
{
    if(!bBluntSprintAttack)return;
    const float Lift=BluntLiftSeconds();
    const float Distance=BluntSprintLungeDistance*(FMath::SmoothStep(0.f,Lift,ToTime)-FMath::SmoothStep(0.f,Lift,FromTime));
    auto* Pawn=Character.Get();auto* Move=Pawn?Cast<UFPSCharacterMovementComponent>(Pawn->GetCharacterMovement()):nullptr;
    if(!bBluntSprintLungeBlocked&&Distance>0.f)
    {
        if(!Move||Pawn->IsSliding()||Pawn->IsTraversing()||Move->IsDodging()||
            (!Move->IsMovingOnGround()&&!Move->IsFalling())||Move->IsMeleeLungeRejected())bBluntSprintLungeBlocked=true;
        else
        {
            FVector Moved=FVector::ZeroVector;
            if(Move->IsFalling())
            {
                const auto* Controller=Pawn->GetController();
                if(!Controller||Controller->IsMoveInputIgnored())bBluntSprintLungeBlocked=true;
                else
                {
                    const FVector Before=Pawn->GetActorLocation();FHitResult Hit;
                    Move->SafeMoveUpdatedComponent(BluntSprintDirection*Distance,Pawn->GetActorQuat(),true,Hit);
                    Moved=Pawn->GetActorLocation()-Before;
                    if(Hit.bBlockingHit)bBluntSprintLungeBlocked=true;
                }
            }
            else Moved=Move->ApplyMeleeLungeStep(BluntSprintDirection,Distance);
            const float Forward=float(FVector::DotProduct(Moved,BluntSprintDirection));
            Move->RecordMeleeLungeStep(FMath::Max(0.f,Forward));
            if(Forward+.01f<Distance)bBluntSprintLungeBlocked=true;
        }
    }
    // Include native airborne momentum and network corrections, not just the
    // explicit step. The planted floor stops following once contact occurs.
    UpdateBluntSprintAnchor(!bContacted);
}

void UProductionToolComponent::UpdateBluntSprintAnchor(bool bUpdateFloor)
{
    auto* Pawn=Character.Get();if(!Pawn)return;
    const FVector Location=Pawn->GetActorLocation(),Delta=Location-BluntSprintAnchorLocation;
    BluntSprintAnchorLocation=Location;
    if(Delta.IsNearlyZero())return;
    BluntSlamEye+=Delta;
    if(!bUpdateFloor)return;
    if(bBluntFloorTarget)BluntFloorPoint+=Delta;
    FHitResult Floor;bBluntFloorTarget=FindBluntGround(Floor);
    if(bBluntFloorTarget){BluntFloorPoint=Floor.ImpactPoint;BluntFloorNormal=Floor.ImpactNormal;}
}
