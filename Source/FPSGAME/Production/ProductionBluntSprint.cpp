#include "ProductionToolComponent.h"
#include "../FPSGAMECharacter.h"
#include "../Multiplayer/ColdSteelAuthorityContext.h"
#include "../UI/ColdSteelStatusModel.h"
#include "../Monsters/FPSCombatHealthComponent.h"
#include "GameFramework/CharacterMovementComponent.h"
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
    const auto* Move=Pawn->GetCharacterMovement();
    const bool GroundSprint=Pawn->bSprintHeld&&Pawn->IsSprinting()&&!Pawn->IsSliding()&&
        Move->IsMovingOnGround()&&Pawn->GetVelocity().SizeSquared2D()>2500.f;
    const bool Carry=Pawn->bSprintHeld&&BluntSprintSeconds>=Required&&
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
    bBluntSprintAttack=true;NextBluntStage=2;
    BeginUse();
    if(Elapsed<0.f){bBluntSprintAttack=bBluntHeavy=false;return false;}
    Character->ExitSprintForWeapon();
    BluntSprintSeconds=0.f;BluntSprintReadyAt=-100.;
    return true;
}
