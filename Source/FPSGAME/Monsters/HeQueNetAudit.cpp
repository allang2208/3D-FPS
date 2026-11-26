#include "HeQueNetAudit.h"
#include "../FPSGAMECharacter.h"
#include "HeQueMonster.h"
#include "MonsterAIController.h"
#include "../Movement/FPSCharacterMovementComponent.h"
#include "../Combat/CombatStatusFormula.h"
#include "Components/BoxComponent.h"
#include "Engine/World.h"
#include "EngineUtils.h"
#include "GameFramework/GameStateBase.h"
#include "Kismet/GameplayStatics.h"
#include "Misc/CommandLine.h"
#include "Misc/Parse.h"
#include "Misc/FileHelper.h"
#include "Net/UnrealNetwork.h"

namespace HeQueNetAudit
{
bool Enabled(){return FParse::Param(FCommandLine::Get(),TEXT("HeQueNetAudit"));}
void Finish(bool Passed,const FString& Reason)
{
    const FString Result=FString::Printf(TEXT("{\"passed\":%s,\"reason\":\"%s\",\"scope\":\"real sockets: shared payload, monster status, owner push and late join; empty map\"}"),Passed?TEXT("true"):TEXT("false"),*Reason);
    FString Path;if(FParse::Value(FCommandLine::Get(),TEXT("HeQueAuditOutput="),Path))FFileHelper::SaveStringToFile(Result,*Path);
    UE_LOG(LogTemp,Display,TEXT("HEQUE_NET_RESULT %s"),*Result);FPlatformMisc::RequestExit(false);
}
}
AHeQueNetAuditProbe::AHeQueNetAuditProbe()
{
    bReplicates=true;bAlwaysRelevant=true;SetNetUpdateFrequency(30.f);
    // The same network-addressable floor component must exist on every peer;
    // a server-only temporary box cannot be resolved as a movement base.
    auto* Floor=CreateDefaultSubobject<UBoxComponent>(TEXT("AuditFloor"));RootComponent=Floor;
    Floor->InitBoxExtent(FVector(6000,6000,50));Floor->SetCollisionProfileName(TEXT("BlockAll"));
}
void AHeQueNetAuditProbe::GetLifetimeReplicatedProps(TArray<FLifetimeProperty>& OutLifetimeProps) const
{
    Super::GetLifetimeReplicatedProps(OutLifetimeProps);
    DOREPLIFETIME(AHeQueNetAuditProbe,Progress);DOREPLIFETIME(AHeQueNetAuditProbe,Phase);
    DOREPLIFETIME(AHeQueNetAuditProbe,Boss);DOREPLIFETIME(AHeQueNetAuditProbe,PushedPawn);DOREPLIFETIME(AHeQueNetAuditProbe,ExpectedEnd);
}
void AHeQueNetAuditController::BeginPlay()
{
    Super::BeginPlay();if(!HeQueNetAudit::Enabled()||!IsLocalController())return;
    FParse::Value(FCommandLine::Get(),TEXT("HeQueAuditLabel="),Label);ServerHello(Label);
}
void AHeQueNetAuditController::ServerHello_Implementation(const FString& InLabel)
{if(HeQueNetAudit::Enabled()){Label=InLabel;UE_LOG(LogTemp,Display,TEXT("HEQUE_NET_HELLO %s"),*Label);}}
void AHeQueNetAuditController::ServerReport_Implementation(int32 Phase,bool Pass,float Error,bool SawPush)
{
    if(!HeQueNetAudit::Enabled())return;
    ReportedPhase=Phase;Failed|=!Pass;
    UE_LOG(LogTemp,Display,TEXT("HEQUE_NET_REPORT role=%s phase=%d pass=%d error_cm=%.3f saw_push=%d"),*Label,Phase,Pass,Error,SawPush);
}
void AHeQueNetAuditController::Tick(float Dt)
{
    Super::Tick(Dt);if(!HeQueNetAudit::Enabled()||!IsLocalController())return;
    if(const auto* ControlledPawn=Cast<AFPSGAMECharacter>(GetPawn()))
        bSawPush|=CastChecked<UFPSCharacterMovementComponent>(ControlledPawn->GetCharacterMovement())->HasImpactPush();
    for(TActorIterator<AHeQueNetAuditProbe> It(GetWorld());It;++It)
    {
        const auto* P=*It;if(P->Phase<=SentPhase||P->Progress.RunId.IsEmpty()||!P->Boss)return;
        const double Now=GetWorld()->GetRealTimeSeconds();
        if(ObservedPhase!=P->Phase){ObservedPhase=P->Phase;PhaseAt=Now;}
        Mirror.ApplyNewer(P->Progress,P->Phase==4?TEXT("heque.audit.2"):TEXT("heque.audit.1"));
        bool Pass=Mirror.RunId==(P->Phase==4?TEXT("heque.audit.2"):TEXT("heque.audit.1"))&&!Mirror.bCompleted;
        Pass&=Mirror.bFinalBossDefeated==(P->Phase==2||P->Phase==3)&&Mirror.bFinalTreasureLooted==(P->Phase==3);
        float Error=0.f;
        if(P->Phase>=2)
        {
            const auto* Status=P->Boss->FindComponentByClass<UCombatStatusFormula>();
            Pass&=Status&&FMath::IsNearlyEqual(Status->MovementMultiplier(),.5f);
            Error=P->PushedPawn?FVector::Dist2D(P->PushedPawn->GetActorLocation(),P->ExpectedEnd):10000.f;
            Pass&=Error<3.f&&(Label!=TEXT("early")||bSawPush);
        }
        if(Pass||Now-PhaseAt>15.){SentPhase=P->Phase;ServerReport(P->Phase,Pass,Error,bSawPush);}
        return;
    }
}
AHeQueNetAuditGameMode::AHeQueNetAuditGameMode()
{
    PrimaryActorTick.bCanEverTick=true;PlayerControllerClass=AHeQueNetAuditController::StaticClass();
    DefaultPawnClass=AFPSGAMECharacter::StaticClass();GameStateClass=AGameStateBase::StaticClass();
}
void AHeQueNetAuditGameMode::BeginPlay()
{
    Super::BeginPlay();if(!HeQueNetAudit::Enabled())return;
    StartedAt=GetWorld()->GetRealTimeSeconds();
    Probe=GetWorld()->SpawnActor<AHeQueNetAuditProbe>(FVector(0,0,-50),FRotator::ZeroRotator);
    Probe->Progress.RunId=TEXT("heque.audit.1");Probe->Progress.Revision=1;
    UClass* BossClass=LoadClass<AHeQueMonster>(nullptr,TEXT("/Game/Monsters/HeQue/BP_HeQue.BP_HeQue_C"));
    if(!BossClass){HeQueNetAudit::Finish(false,TEXT("missing boss class"));return;}
    Probe->Boss=GetWorld()->SpawnActor<AHeQueMonster>(BossClass,FVector(3000,3000,228),FRotator::ZeroRotator);
    if(!Probe->Boss){HeQueNetAudit::Finish(false,TEXT("boss spawn failed"));return;}
    if(auto* AI=Cast<AMonsterAIController>(Probe->Boss->GetController()))AI->SetDecisionEnabled(false);
    UE_LOG(LogTemp,Display,TEXT("HEQUE_NET_HOST_READY"));
}
void AHeQueNetAuditGameMode::Tick(float Dt)
{
    Super::Tick(Dt);if(!HeQueNetAudit::Enabled()||Done||!Probe)return;
    const double Now=GetWorld()->GetRealTimeSeconds();
    AHeQueNetAuditController* Host=nullptr;AHeQueNetAuditController* Early=nullptr;AHeQueNetAuditController* Late=nullptr;
    for(auto It=GetWorld()->GetPlayerControllerIterator();It;++It)
        if(auto* PC=Cast<AHeQueNetAuditController>(It->Get()))
        {
            if(PC->Failed){Done=true;HeQueNetAudit::Finish(false,TEXT("client assertion failed"));return;}
            if(PC->Label==TEXT("host"))Host=PC;else if(PC->Label==TEXT("early"))Early=PC;else if(PC->Label==TEXT("late"))Late=PC;
        }
    if(Now-StartedAt>300.){Done=true;HeQueNetAudit::Finish(false,TEXT("peer timeout"));return;}
    if(!Host||!Early)return;
    if(PushAt<0.&&Host->ReportedPhase==1&&Early->ReportedPhase==1)
    {
        Probe->PushedPawn=Cast<AFPSGAMECharacter>(Early->GetPawn());if(!Probe->PushedPawn)return;
        Probe->PushedPawn->SetActorLocation(FVector(0,1500,98),false,nullptr,ETeleportType::TeleportPhysics);
        // Let the relocation settle before the displacement probe.
        PushAt=Now;Probe->ForceNetUpdate();
    }
    if(Probe->Phase==1&&PushAt>=0.&&Now-PushAt>1.)
    {
        auto* Move=CastChecked<UFPSCharacterMovementComponent>(Probe->PushedPawn->GetCharacterMovement());
        UCombatStatusFormula::GetOrAdd(Probe->Boss)->AddSlow(180.f,.5f);
        Probe->ExpectedEnd=Probe->PushedPawn->GetActorLocation()+FVector(1000,0,0);Move->ApplyImpactPush(FVector::ForwardVector,1000.f);
        Probe->Phase=2;Probe->Progress.bFinalBossDefeated=true;++Probe->Progress.Revision;Probe->ForceNetUpdate();
    }
    if(Probe->Phase==2&&Host->ReportedPhase==2&&Early->ReportedPhase==2)
    {
        Probe->Phase=3;Probe->Progress.bFinalTreasureLooted=true;++Probe->Progress.Revision;Probe->ForceNetUpdate();
        UE_LOG(LogTemp,Display,TEXT("HEQUE_NET_LATE_READY"));
    }
    if(Probe->Phase==3&&Late&&Host->ReportedPhase==3&&Early->ReportedPhase==3&&Late->ReportedPhase==3)
    {Probe->Phase=4;Probe->Progress={};Probe->Progress.RunId=TEXT("heque.audit.2");Probe->Progress.Revision=1;Probe->ForceNetUpdate();}
    if(Probe->Phase==4&&Late&&Host->ReportedPhase==4&&Early->ReportedPhase==4&&Late->ReportedPhase==4)
    {Done=true;HeQueNetAudit::Finish(true,TEXT("host early and late peers completed all phases"));}
}
