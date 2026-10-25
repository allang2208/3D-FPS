#include "RuneboundReviewFixture.h"
#include "../Production/ProductionToolComponent.h"
#include "../Movement/FPSCharacterMovementComponent.h"
#include "../Skills/SkillWireAudit.h"
#include "Components/BoxComponent.h"
#include "Engine/GameInstance.h"
#include "Engine/World.h"

namespace
{
void PrepareSprintPawn(AFPSGAMECharacter* AuditPawn)
{
    RuneboundReview::Freeze(AuditPawn);
    auto* Actor=AuditPawn->GetWorld()->SpawnActor<AActor>();auto* Floor=NewObject<UBoxComponent>(Actor);
    Actor->AddInstanceComponent(Floor);Actor->SetRootComponent(Floor);Floor->SetBoxExtent(FVector(100000,100000,10));
    Floor->SetCollisionEnabled(ECollisionEnabled::QueryAndPhysics);Floor->SetCollisionObjectType(ECC_WorldStatic);
    Floor->SetCollisionResponseToAllChannels(ECR_Block);Floor->RegisterComponent();Floor->SetWorldLocation(FVector(0,0,-10));
    AuditPawn->GetCapsuleComponent()->SetCollisionEnabled(ECollisionEnabled::QueryAndPhysics);
    AuditPawn->SetActorLocationAndRotation(FVector(0,0,AuditPawn->GetCapsuleComponent()->GetScaledCapsuleHalfHeight()+2),FRotator::ZeroRotator);
    AuditPawn->GetCharacterMovement()->SetMovementMode(MOVE_Walking);AuditPawn->GetCharacterMovement()->SetComponentTickEnabled(true);
}
}
void ARuneboundReviewController::SetupSprint(const FString& Instance)
{
    if(!RuneboundReview::WireEnabled()||HasAuthority()||Started>=0)return;
    auto* AuditPawn=Cast<AFPSGAMECharacter>(GetPawn());auto* Model=GetGameInstance()->GetSubsystem<UColdSteelStatusModel>();
    if(!AuditPawn||!Model||!Model->IsAudit())return;
    Model->AdoptNetMirror(RuneboundReview::Seed(Model,Instance,TEXT("")));Model->AttachPawn(AuditPawn);
    PrepareSprintPawn(AuditPawn);SetControlRotation(FRotator::ZeroRotator);
    auto* Tool=AuditPawn->FindComponentByClass<UProductionToolComponent>();Tool->Character=AuditPawn;Tool->Kind=TEXT("warhammer");
    Tool->EquippedId=Instance;Tool->ApplyToolStats(Model->ActiveProductionTool(),Model);Tool->Elapsed=Tool->EquipElapsed=-1.f;
    Weapon=Instance;Started=GetWorld()->GetRealTimeSeconds();Stage=0;
}
void ARuneboundReviewController::TickSprint(float Delta)
{
    if(!RuneboundReview::WireEnabled()||HasAuthority())return;
    const double Now=GetWorld()->GetRealTimeSeconds();
    if(ExitAt>=0){if(Now>=ExitAt)FPlatformMisc::RequestExit(false);return;}
    if(Started<0)return;
    auto* AuditPawn=Cast<AFPSGAMECharacter>(GetPawn());auto* Model=GetGameInstance()->GetSubsystem<UColdSteelStatusModel>();
    if(!AuditPawn||!Model)return;
    auto* Move=CastChecked<UFPSCharacterMovementComponent>(AuditPawn->GetCharacterMovement());
    auto* Tool=AuditPawn->FindComponentByClass<UProductionToolComponent>();
    if(Stage==0)
    {
        Move->bWantsToSprint=true;Move->MaxWalkSpeed=AuditPawn->SprintSpeed;AuditPawn->AddMovementInput(FVector::ForwardVector);
        if(Now-Started<4.)return;
        ServerPhase(1,Move->Velocity.Size2D()>50.f&&AuditPawn->GetActorLocation().X>300.f);
        AuditPawn->ConsumeMovementInputVector();Move->StopMovementImmediately();Move->bWantsToSprint=false;
        Tool->BluntAttackId=8101;Tool->bBluntHeavy=Tool->bBluntSprintAttack=true;Tool->Elapsed=0.f;
        Tool->ServerBeginBluntAttack(8101,false,true);Tool->ServerBeginBluntAttack(8101,false,true);
        Move->BeginMeleeLungeRequest(EFPSMeleeMove::Dash,FVector::ForwardVector,8101);
        SprintOrigin=AuditPawn->GetActorLocation();SprintAge=0.f;Started=Now;Stage=1;return;
    }
    if(Stage==1)
    {
        const float Next=SprintAge+Delta;
        const float Step=Model->DashAttackStats().DistanceCM*(FMath::SmoothStep(0.f,.25f,Next)-FMath::SmoothStep(0.f,.25f,SprintAge));
        if(Step>0.f&&!Move->IsMeleeLungeRejected())
        {
            const FVector Moved=Move->ApplyMeleeLungeStep(FVector::ForwardVector,Step);Move->RecordMeleeLungeStep(FMath::Max(0.f,float(Moved.X)));
        }
        SprintAge=Next;Tool->Elapsed=Next;
        if(Now-Started<2.)return;
        Tool->Elapsed=-1.f;
        const bool Receipt=FMath::IsNearlyEqual(Model->Stamina(),100.f-float(Tool->ToolStats.StaminaCost),.01f);
        ServerPhase(2,Receipt&&!Move->IsMeleeLungeRejected()&&FMath::IsNearlyEqual(Move->MeleeRequest.Distance,Model->DashAttackStats().DistanceCM,.2f));
        UE_LOG(LogTemp,Display,TEXT("HAMMER_SPRINT_WIRE_OWNER x=%.3f cumulative=%.3f rejected=%d stamina=%.3f"),
            AuditPawn->GetActorLocation().X,Move->MeleeRequest.Distance,Move->IsMeleeLungeRejected(),Model->Stamina());
        Stage=2;
    }
}
void ARuneboundReviewController::ClientSprintResult_Implementation(float ServerX,bool Passed)
{
    if(!RuneboundReview::WireEnabled()||!FParse::Param(FCommandLine::Get(),TEXT("HammerSprintWire")))return;
    auto* AuditPawn=Cast<AFPSGAMECharacter>(GetPawn());if(!AuditPawn)return;
    TArray<TSharedPtr<FJsonValue>> Rows;bool OK=Passed;
    RuneboundReview::Check(Rows,OK,Passed,TEXT("server accepted actual UDP sprint RPC and native CMC packets"));
    const float Error=FMath::Abs(float(AuditPawn->GetActorLocation().X)-ServerX);
    RuneboundReview::Check(Rows,OK,Error<5.f,TEXT("owner and authority settle within five centimetres"));
    UE_LOG(LogTemp,Display,TEXT("HAMMER_SPRINT_WIRE_CORRECTION error_cm=%.3f"),Error);
    FString Path;FParse::Value(FCommandLine::Get(),TEXT("RuneboundReviewOutput="),Path);
    RuneboundReview::Save(Rows,OK,TEXT("hammer sprint UDP owner"),Path);ServerPhase(3,OK);ExitAt=GetWorld()->GetRealTimeSeconds()+1.;
}
void ARuneboundReviewGameMode::TickSprint(float Delta)
{
    if(!RuneboundReview::WireEnabled())return;
    const double Now=GetWorld()->GetRealTimeSeconds();if(ExitAt>=0){if(Now>=ExitAt)FPlatformMisc::RequestExit(false);return;}
    auto* Host=GetGameInstance()->GetSubsystem<UColdSteelStatusModel>();if(!Host||!Host->IsAudit())return;
    if(!HostPawn)for(FConstPlayerControllerIterator It=GetWorld()->GetPlayerControllerIterator();It;++It)
        if(It->IsValid()&&It->Get()->IsLocalController())if(auto* AuditPawn=Cast<AFPSGAMECharacter>(It->Get()->GetPawn()))
        {HostPawn=AuditPawn;RuneboundReview::Freeze(AuditPawn);AuditPawn->SetActorLocation(FVector(0,1000,500));}
    if(!Guest||!HostPawn)return;
    auto* AuditPawn=Cast<AFPSGAMECharacter>(Guest->GetPawn());auto* PS=Guest->GetPlayerState<AColdSteelPlayerState>();if(!AuditPawn||!PS)return;
    auto* Tool=AuditPawn->FindComponentByClass<UProductionToolComponent>();auto* Move=CastChecked<UFPSCharacterMovementComponent>(AuditPawn->GetCharacterMovement());
    if(!GuestModel)
    {
        Weapon=TEXT("HammerSprintWireGuest");GuestModel=Host->CreateShadowModel(RuneboundReview::Seed(Host,Weapon,TEXT("")));
        PS->ShadowModel=GuestModel;AuditPawn->NetShadowProfile=GuestModel;GuestModel->AttachPawn(AuditPawn);PS->SetActorTickEnabled(false);
        PrepareSprintPawn(AuditPawn);Guest->SetControlRotation(FRotator::ZeroRotator);
        Tool->Character=AuditPawn;Tool->Kind=TEXT("warhammer");Tool->EquippedId=Weapon;Tool->ApplyToolStats(GuestModel->ActiveProductionTool(),GuestModel);
        InitialHostStamina=Host->Stamina();InitialGuestStamina=GuestModel->Stamina();Stage=1;PhaseAt=Now;
    }
    Tool->AdvanceBluntSprintReadiness(Delta);Tool->TickAuthorityBluntCharge();
    if(Stage==1&&Now-PhaseAt>1.){Guest->ClientSetup(Weapon,nullptr,HostPawn);PhaseAt=Now;}
    if(Stage==1&&Guest->Reported>=2)
    {
        bool OK=Guest->AllPassed;
        RuneboundReview::Check(Results,OK,Tool->BluntServerAttackId==8101&&Tool->bBluntServerSprintAttack,TEXT("remote sprint readiness commits through reliable RPC"));
        RuneboundReview::Check(Results,OK,Move->ServerHammerAttackId==8101&&!Move->bServerMeleeBlocked&&
            FMath::IsNearlyEqual(Move->ServerMeleeDistance,GuestModel->DashAttackStats().DistanceCM,.2f),TEXT("native movement channel applies one complete bounded stride"));
        RuneboundReview::Check(Results,OK,FMath::IsNearlyEqual(GuestModel->Stamina(),float(InitialGuestStamina-Tool->ToolStats.StaminaCost),.01f),TEXT("duplicated sprint RPC charges guest exactly once"));
        RuneboundReview::Check(Results,OK,Host->Stamina()==InitialHostStamina,TEXT("guest sprint does not debit listen host"));
        Guest->AllPassed&=OK;Guest->ClientSprintResult(float(AuditPawn->GetActorLocation().X),OK);Stage=2;
    }
    if(Guest->Reported>=3||Now-Joined>40.)
    {
        bool OK=Guest->Reported==3&&Guest->AllPassed;
        RuneboundReview::Check(Results,OK,Guest->Reported==3&&Guest->AllPassed,TEXT("UDP owner receipt and final position acknowledged"));
        FString Path;FParse::Value(FCommandLine::Get(),TEXT("RuneboundReviewOutput="),Path);
        RuneboundReview::Save(Results,OK,TEXT("hammer sprint UDP listen host"),Path);ExitAt=Now+2.;
    }
}
