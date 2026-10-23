#include "RuneboundReviewFixture.h"
#include "../Production/ProductionToolComponent.h"
#include "../Skills/SkillWireAudit.h"
#include "../Skills/ColdSteelSkillRules.h"
#include "../Multiplayer/ColdSteelAuthorityContext.h"
#include "Engine/GameInstance.h"
#include "Engine/World.h"

void ARuneboundReviewController::ClientSetup_Implementation(const FString& Instance,ARuneboundReviewTarget* Target,AFPSGAMECharacter* Host)
{
    if(!RuneboundReview::WireEnabled()||HasAuthority()||Started>=0||!Target||!Host)return;
    auto* AuditPawn=Cast<AFPSGAMECharacter>(GetPawn());auto* Model=GetGameInstance()->GetSubsystem<UColdSteelStatusModel>();
    if(!AuditPawn||!Model||!Model->IsAudit())return;
    Model->AdoptNetMirror(RuneboundReview::Seed(Model,Instance,RuneboundHammer::FinalTollHead,TEXT("swift_mana_rune")));Model->AttachPawn(AuditPawn);
    RuneboundReview::Freeze(AuditPawn);AuditPawn->SetActorLocationAndRotation(FVector(0,0,500),FRotator::ZeroRotator);SetControlRotation(FRotator::ZeroRotator);
    auto* Tool=AuditPawn->FindComponentByClass<UProductionToolComponent>();Tool->Character=AuditPawn;Tool->Kind=TEXT("warhammer");Tool->EquippedId=Instance;
    Tool->ApplyToolStats(Model->ActiveProductionTool(),Model);
    Subject=Target;HostSubject=Host;Weapon=Instance;Started=GetWorld()->GetRealTimeSeconds();Stage=0;
}
void ARuneboundReviewController::ServerPhase_Implementation(int32 Phase,bool Passed)
{
    if(!RuneboundReview::WireEnabled()||Phase!=Reported+1)return;
    Reported=Phase;AllPassed&=Passed;UE_LOG(LogTemp,Display,TEXT("RUNEBOUND_WIRE_CLIENT_PHASE phase=%d passed=%d"),Phase,Passed);
}
void ARuneboundReviewController::ClientFinish_Implementation(bool Passed)
{
    if(!RuneboundReview::WireEnabled())return;
    TArray<TSharedPtr<FJsonValue>> Rows;bool OK=Passed;RuneboundReview::Check(Rows,OK,Passed,TEXT("real UDP owner and remote persistent-state phases"));
    FString Path;FParse::Value(FCommandLine::Get(),TEXT("RuneboundReviewOutput="),Path);RuneboundReview::Save(Rows,OK,TEXT("UDP client"),Path);
    ExitAt=GetWorld()->GetRealTimeSeconds()+.5;
}
void ARuneboundReviewController::Tick(float Delta)
{
    Super::Tick(Delta);if(!RuneboundReview::WireEnabled()||HasAuthority())return;
    const double Now=GetWorld()->GetRealTimeSeconds();if(ExitAt>=0){if(Now>=ExitAt)FPlatformMisc::RequestExit(false);return;}
    if(Started<0||!HostSubject||!Subject)return;
    auto* AuditPawn=Cast<AFPSGAMECharacter>(GetPawn());auto* Model=GetGameInstance()->GetSubsystem<UColdSteelStatusModel>();if(!AuditPawn||!Model)return;
    auto* Own=AuditPawn->FindComponentByClass<UProductionToolComponent>();auto* Remote=HostSubject->FindComponentByClass<UProductionToolComponent>();
    if(Stage==0)
    {
        Remote->ReconcileFinalTollSeals(Remote->RuneboundActiveUntil>Remote->RuneboundClock());
        const bool Initial=Remote->FinalTollSealState.Marks.Num()==1&&Remote->FinalTollVisualMarks.Num()==1&&Own->RuneboundCharge==5&&Own->IsRuneboundAwakened(*Model->ActiveProductionTool());
        if(!Initial&&Now-Started<10.)return;
        ServerPhase(1,Initial);Own->ServerBeginBluntCharge(9001);Started=Now;Stage=1;return;
    }
    if(Stage==1&&Now-Started>2.6)
    {
        Own->ServerBeginBluntAttack(9001,true,false);Own->ServerBeginBluntAttack(9001,true,false);
        Started=Now;Stage=2;return;
    }
    if(Stage==2&&Now-Started>2.)
    {
        const bool Receipt=FMath::IsNearlyEqual(Model->Stamina(),100.f-float(Own->ToolStats.HeavyReleaseStaminaCost),.01f);
        ServerPhase(2,Receipt&&Own->FinalTollSealState.Marks.IsEmpty()&&Own->RuneboundActiveUntil>Own->RuneboundClock());
        UE_LOG(LogTemp,Display,TEXT("RUNEBOUND_WIRE_OWNER stamina=%.3f expected=%.3f charge=%d seals=%d"),Model->Stamina(),100.f-float(Own->ToolStats.HeavyReleaseStaminaCost),Own->RuneboundCharge,Own->FinalTollSealState.Marks.Num());
        Started=Now;Stage=3;return;
    }
    if(Stage==3)
    {
        Remote->ReconcileFinalTollSeals(Remote->RuneboundActiveUntil>Remote->RuneboundClock());
        const bool Cleared=Remote->RuneboundActiveUntil==0.&&Remote->FinalTollSealState.Marks.IsEmpty()&&Remote->FinalTollVisualMarks.IsEmpty();
        if(!Cleared&&Now-Started<10.)return;
        ServerPhase(3,Cleared);Stage=4;
    }
}
ARuneboundReviewGameMode::ARuneboundReviewGameMode()
{
    PlayerControllerClass=ARuneboundReviewController::StaticClass();PlayerStateClass=ASkillWireAuditPlayerState::StaticClass();
    DefaultPawnClass=AFPSGAMECharacter::StaticClass();PrimaryActorTick.bCanEverTick=true;
}
void ARuneboundReviewGameMode::BeginPlay()
{
    Super::BeginPlay();if(RuneboundReview::WireEnabled())UE_LOG(LogTemp,Display,TEXT("RUNEBOUND_WIRE_HOST_READY"));
}
void ARuneboundReviewGameMode::PostLogin(APlayerController* Player)
{
    Super::PostLogin(Player);if(RuneboundReview::WireEnabled()&&!Player->IsLocalController())
    {Guest=Cast<ARuneboundReviewController>(Player);Joined=GetWorld()->GetRealTimeSeconds();}
}
void ARuneboundReviewGameMode::Tick(float Delta)
{
    Super::Tick(Delta);if(!RuneboundReview::WireEnabled())return;
    const double Now=GetWorld()->GetRealTimeSeconds();
    if(ExitAt>=0){if(Now>=ExitAt)FPlatformMisc::RequestExit(false);return;}
    auto* Host=GetGameInstance()->GetSubsystem<UColdSteelStatusModel>();if(!Host||!Host->IsAudit())return;
    if(!HostPawn)for(FConstPlayerControllerIterator It=GetWorld()->GetPlayerControllerIterator();It;++It)
        if(It->IsValid()&&It->Get()->IsLocalController())if(auto* AuditPawn=Cast<AFPSGAMECharacter>(It->Get()->GetPawn()))
        {HostPawn=AuditPawn;RuneboundReview::Freeze(AuditPawn);AuditPawn->SetActorLocation(FVector(0,1000,500));AuditPawn->SetReplicates(false);}
    if(!Guest||!HostPawn)return;
    auto* AuditPawn=Cast<AFPSGAMECharacter>(Guest->GetPawn());auto* PS=Guest->GetPlayerState<AColdSteelPlayerState>();if(!AuditPawn||!PS)return;
    if(!GuestModel)
    {
        Weapon=TEXT("RuneboundWireGuest");GuestModel=Host->CreateShadowModel(RuneboundReview::Seed(Host,Weapon,RuneboundHammer::FinalTollHead,TEXT("swift_mana_rune")));
        PS->ShadowModel=GuestModel;AuditPawn->NetShadowProfile=GuestModel;GuestModel->AttachPawn(AuditPawn);PS->SetActorTickEnabled(false);RuneboundReview::Freeze(AuditPawn);
        AuditPawn->SetActorLocationAndRotation(FVector(0,0,500),FRotator::ZeroRotator);Guest->SetControlRotation(FRotator::ZeroRotator);
        auto* Tool=AuditPawn->FindComponentByClass<UProductionToolComponent>();Tool->Character=AuditPawn;Tool->Kind=TEXT("warhammer");Tool->EquippedId=Weapon;
        Tool->ApplyToolStats(GuestModel->ActiveProductionTool(),GuestModel);Tool->TickRunebound(0);Tool->RuneboundCharge=5;Tool->RuneboundActiveUntil=Tool->RuneboundClock()+20.;
        Target=GetWorld()->SpawnActor<ARuneboundReviewTarget>(FVector(150,0,500),FRotator::ZeroRotator);
        Host->AdoptNetMirror(RuneboundReview::Seed(Host,TEXT("RuneboundWireHost"),RuneboundHammer::FinalTollHead));Host->AttachPawn(HostPawn);
        auto* Remote=HostPawn->FindComponentByClass<UProductionToolComponent>();Remote->Character=HostPawn;Remote->TickRunebound(0);Remote->RuneboundActiveUntil=Remote->RuneboundClock()+20.;
        auto Shot=ColdSteelSkills::Snapshot(HostPawn,Host->ActiveProductionTool());Remote->FinalTollHeavySerial=Shot.MasteryAttackSerial;Remote->FinalTollCommitUntil=Remote->RuneboundClock()+2.;
        // This seal exists before the actor gets its first guest channel; no historical multicast can supply it.
        Remote->RecordRuneboundHit(Shot,RuneboundReview::Hit(Target));HostPawn->SetReplicates(true);HostPawn->ForceNetUpdate();AuditPawn->ForceNetUpdate();
        InitialHostStamina=Host->Stamina();InitialGuestStamina=GuestModel->Stamina();PhaseAt=Now;Stage=1;
    }
    if(Stage==1&&Now-PhaseAt>1.){Guest->ClientSetup(Weapon,Target,HostPawn);PhaseAt=Now;}
    if(Stage==1&&Guest->Reported>=2)
    {
        bool OK=true;auto* Tool=AuditPawn->FindComponentByClass<UProductionToolComponent>();
        RuneboundReview::Check(Results,OK,Target->Physical.Num()==2,TEXT("guest native reliable RPC double heavy resolves two physical contacts"));
        const float Expected=GuestModel->Derived(TEXT("matk"))*3.5f;
        RuneboundReview::Check(Results,OK,Target->Magic.Num()==1&&FMath::IsNearlyEqual(Target->Magic[0],Expected,.01f),TEXT("authority finisher exactly 350 percent magic once"));
        RuneboundReview::Check(Results,OK,FMath::IsNearlyEqual(GuestModel->Stamina(),float(InitialGuestStamina-Tool->ToolStats.HeavyReleaseStaminaCost),.01f),TEXT("duplicate release RPC spends guest stamina once"));
        RuneboundReview::Check(Results,OK,Host->Stamina()==InitialHostStamina,TEXT("guest attack leaves listen host profile unchanged"));Guest->AllPassed&=OK;
        auto* Remote=HostPawn->FindComponentByClass<UProductionToolComponent>();Remote->RuneboundActiveUntil=Remote->RuneboundClock()-.01;Remote->TickRunebound(0);HostPawn->ForceNetUpdate();Stage=2;
    }
    if(Guest->Reported>=3||Now-Joined>60.)
    {
        const bool OK=Guest->Reported==3&&Guest->AllPassed;bool All=OK;
        RuneboundReview::Check(Results,All,Guest->Reported>=1&&Guest->AllPassed,TEXT("client recovered pre-channel seal and awake state"));
        RuneboundReview::Check(Results,All,Guest->Reported==3&&Guest->AllPassed,TEXT("client cost receipt and replicated expiry phases"));
        FString Path;FParse::Value(FCommandLine::Get(),TEXT("RuneboundReviewOutput="),Path);RuneboundReview::Save(Results,All,TEXT("real UDP listen host"),Path);
        Guest->ClientFinish(All);ExitAt=Now+2.;
    }
}
