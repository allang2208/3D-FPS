#include "AlchemyManualNetAudit.h"
#include "ColdSteelAlchemyBookWidget.h"
#include "ColdSteelStatusModel.h"
#include "../Building/AlchemySystem.h"
#include "../Building/AlchemyManualComponent.h"
#include "../Building/PotionWorkbenchVisualComponent.h"
#include "../Building/VoxelBuildWorld.h"
#include "../Building/VoxelBuildPrefabActor.h"
#include "../Multiplayer/ColdSteelPlayerState.h"
#include "../Monsters/FPSCombatHealthComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Engine/GameInstance.h"
#include "Engine/StaticMesh.h"
#include "Engine/World.h"
#include "EngineUtils.h"
#include "GameFramework/GameStateBase.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "Misc/CommandLine.h"
#include "Misc/FileHelper.h"
#include "Misc/Parse.h"
#include "Net/UnrealNetwork.h"

namespace ManualWire {
bool Enabled(){return FParse::Param(FCommandLine::Get(),TEXT("AlchemyManualNetAudit"));}
void Finish(bool Pass,const FString& Reason)
{
    const FString Json=FString::Printf(TEXT("{\"passed\":%s,\"reason\":\"%s\",\"scope\":\"real sockets: station RPC, public book presentation, rejection, late join, disconnect and host handover\"}"),Pass?TEXT("true"):TEXT("false"),*Reason);
    FString Path;if(FParse::Value(FCommandLine::Get(),TEXT("ManualNetOutput="),Path))FFileHelper::SaveStringToFile(Json,*Path);
    UE_LOG(LogTemp,Display,TEXT("MANUAL_NET_RESULT %s"),*Json);FPlatformMisc::RequestExit(false);
}
}
AAlchemyManualNetAuditPawn::AAlchemyManualNetAuditPawn()
{
    PrimaryActorTick.bStartWithTickEnabled=false;bAlwaysRelevant=true;
}
void AAlchemyManualNetAuditPawn::BeginPlay()
{
    Super::BeginPlay();if(!ManualWire::Enabled())return;
    SetActorHiddenInGame(true);SetActorEnableCollision(false);SetActorTickEnabled(false);
    GetCharacterMovement()->DisableMovement();
    for(auto* Component:GetComponents())Component->SetComponentTickEnabled(false);
}
AAlchemyManualNetAuditProbe::AAlchemyManualNetAuditProbe(){bReplicates=true;bAlwaysRelevant=true;SetNetUpdateFrequency(20.f);}
void AAlchemyManualNetAuditProbe::GetLifetimeReplicatedProps(TArray<FLifetimeProperty>& OutLifetimeProps) const
{Super::GetLifetimeReplicatedProps(OutLifetimeProps);DOREPLIFETIME(AAlchemyManualNetAuditProbe,Bench);DOREPLIFETIME(AAlchemyManualNetAuditProbe,Phase);DOREPLIFETIME(AAlchemyManualNetAuditProbe,ExpectedPage);DOREPLIFETIME(AAlchemyManualNetAuditProbe,ExpectedOpen);}
void AAlchemyManualNetAuditController::BeginPlay()
{
    Super::BeginPlay();if(!ManualWire::Enabled())return;
    if(auto* PS=GetPlayerState<AColdSteelPlayerState>())PS->SetActorTickEnabled(false);
    if(IsLocalController()){FParse::Value(FCommandLine::Get(),TEXT("ManualNetRole="),Label);ServerHello(Label);}
}
void AAlchemyManualNetAuditController::ServerHello_Implementation(const FString& InRole)
{if(ManualWire::Enabled())Label=InRole;}
void AAlchemyManualNetAuditController::ServerReport_Implementation(int32 Phase,bool Pass)
{
    if(!ManualWire::Enabled())return;ReportedPhase=Phase;Failed|=!Pass;
    UE_LOG(LogTemp,Display,TEXT("MANUAL_NET_REPORT role=%s phase=%d pass=%d"),*Label,Phase,Pass);
}
void AAlchemyManualNetAuditController::ClientLeave_Implementation()
{if(ManualWire::Enabled())FPlatformMisc::RequestExit(false);}
void AAlchemyManualNetAuditController::Tick(float Delta)
{
    Super::Tick(Delta);if(!ManualWire::Enabled()||!IsLocalController())return;
    if(auto* ReaderPawn=Cast<ACharacter>(GetPawn()))
    {
        ReaderPawn->GetCharacterMovement()->DisableMovement();
        ReaderPawn->GetCharacterMovement()->SetComponentTickEnabled(false);
        ReaderPawn->SetActorTickEnabled(false);
    }
    for(TActorIterator<AAlchemyManualNetAuditProbe> It(GetWorld());It;++It)
    {
        auto* Probe=*It;auto* Bench=Probe->Bench.Get();auto* PS=GetPlayerState<AColdSteelPlayerState>();
        // Remote PlayerState can arrive after BeginPlay; keep this fixture's
        // seeded profile independent of the normal client inventory upload.
        if(PS)PS->SetActorTickEnabled(false);
        if(!Bench||!PS||!GetPawn()||Probe->Phase<=SentPhase||!Probe->Phase)return;
        const double Now=GetWorld()->GetRealTimeSeconds();
        if(SeenPhase!=Probe->Phase)
        {
            SeenPhase=Probe->Phase;SeenAt=Now;
            if(Label==TEXT("early"))
            {
                auto Send=[&](APawn* InputPawn,const FString& Job,int32 Page,uint32 Sequence)
                {PS->ServerStationInput(InputPawn,Job,TEXT("alchemy"),uint8(EAlchemyOp::Book),NAME_None,Page,FVector2D::ZeroVector,FVector2D::ZeroVector,Sequence);};
                if(SeenPhase==2)Send(GetPawn(),TEXT("manual.audit.early"),1,1);
                if(SeenPhase==3)
                {
                    Send(nullptr,TEXT("manual.audit.early"),0,2);
                    Send(GetPawn(),TEXT("retired.job"),0,3);
                    Send(GetPawn(),TEXT("manual.audit.early"),0,1);
                    Send(GetPawn(),TEXT("manual.audit.early"),-1,4);
                    Send(GetPawn(),TEXT("manual.audit.early"),MAX_int32,5);
                }
                if(SeenPhase==4)Send(GetPawn(),TEXT("manual.audit.early"),0,6);
                if(SeenPhase==6)Send(GetPawn(),TEXT("manual.audit.early"),1,7);
            }
            if(Label==TEXT("late")&&SeenPhase==10)
                PS->ServerStationInput(GetPawn(),TEXT("manual.audit.late"),TEXT("alchemy"),uint8(EAlchemyOp::Book),NAME_None,0,FVector2D::ZeroVector,FVector2D::ZeroVector,1);
        }
        const auto& State=Bench->AlchemyPresentation();
        auto* Visual=Bench->FindComponentByClass<UPotionWorkbenchVisualComponent>();
        auto* Manual=Visual?Visual->Manual.Get():nullptr;
        bool Pass=State.BookPage==Probe->ExpectedPage&&IsValid(State.Operator)==Probe->ExpectedOpen;
        Pass&=Manual&&Manual->Ready()&&!Manual->Turning()&&Manual->bOpen==Probe->ExpectedOpen;
        if(Probe->ExpectedOpen)Pass&=Manual&&Manual->bHasDisplayedView&&Manual->DisplayedView.Spread==Probe->ExpectedPage&&Manual->Leaves.Num()==3;
        else Pass&=Manual&&Manual->PageTargets.IsEmpty();
        // Allow the test requests to cross their PlayerState channel before
        // observing a stable rejection on the separate controller channel.
        if(Now-SeenAt<1.5)return;
        if(Pass||Now-SeenAt>25.)
        {
            if(!Pass)UE_LOG(LogTemp,Warning,TEXT("MANUAL_NET_STATE role=%s phase=%d expected=%d/%d actual=%d/%d manual=%d ready=%d open=%d turning=%d displayed=%d"),
                *Label,Probe->Phase,Probe->ExpectedPage,Probe->ExpectedOpen,State.BookPage,IsValid(State.Operator),Manual!=nullptr,
                Manual&&Manual->Ready(),Manual&&Manual->bOpen,Manual&&Manual->Turning(),Manual?Manual->DisplayedView.Spread:-1);
            SentPhase=Probe->Phase;ServerReport(Probe->Phase,Pass);
        }
        return;
    }
}
AAlchemyManualNetAuditGameMode::AAlchemyManualNetAuditGameMode()
{
    PrimaryActorTick.bCanEverTick=true;PlayerControllerClass=AAlchemyManualNetAuditController::StaticClass();
    PlayerStateClass=AColdSteelPlayerState::StaticClass();DefaultPawnClass=AAlchemyManualNetAuditPawn::StaticClass();GameStateClass=AGameStateBase::StaticClass();
}
void AAlchemyManualNetAuditGameMode::BeginPlay()
{
    Super::BeginPlay();if(!ManualWire::Enabled())return;
    Started=GetWorld()->GetRealTimeSeconds();
    auto* Model=GetGameInstance()->GetSubsystem<UColdSteelStatusModel>();
    if(!Model||!Model->IsAudit()){Done=true;ManualWire::Finish(false,TEXT("isolated profile required"));return;}
    Probe=GetWorld()->SpawnActor<AAlchemyManualNetAuditProbe>();
    Building=GetWorld()->SpawnActor<AVoxelBuildWorld>();Building->SetActorTickEnabled(false);
    FActorSpawnParameters Spawn;Spawn.Owner=Building;
    Probe->Bench=GetWorld()->SpawnActor<AVoxelBuildPrefabActor>(FVector(200,0,0),FRotator::ZeroRotator,Spawn);
    Probe->Bench->bAlwaysRelevant=true;
    auto* Mesh=LoadObject<UStaticMesh>(nullptr,TEXT("/Engine/BasicShapes/Cube.Cube"));
    Probe->Bench->Configure(TEXT("potion_workbench"),FIntVector::ZeroValue,0,Mesh,nullptr,nullptr);
    FVoxelBuildPrefabInstance Entry;Entry.Id=TEXT("potion_workbench");Entry.Cell=FIntVector::ZeroValue;
    Building->Prefabs.Add(Entry);Building->PrefabActors.Add(Entry.Cell,Probe->Bench.Get());
    UE_LOG(LogTemp,Display,TEXT("MANUAL_NET_HOST_READY"));
}
void AAlchemyManualNetAuditGameMode::Seed(AAlchemyManualNetAuditController* Controller,bool Host)
{
    auto* Base=GetGameInstance()->GetSubsystem<UColdSteelStatusModel>();auto* System=GetGameInstance()->GetSubsystem<UColdSteelAlchemySystem>();
    const FAlchemyRecipe* Recipe=&System->Recipes()[0];
    for(const auto& R:System->Recipes())if(UColdSteelAlchemyBookWidget::Pages(R)>1){Recipe=&R;break;}
    auto Profile=Base->Snapshot();Profile.Items.Reset();Profile.AlchemyJob={};
    auto& Job=Profile.AlchemyJob;Job.Id=Host?TEXT("manual.audit.host"):TEXT("manual.audit.early");
    Job.Recipe=Recipe->Id;Job.Name=Recipe->Name;Job.RecipeSnapshot=Recipe->Raw;Job.Revision=1;Job.Progress.Init(0,Recipe->Steps.Num());
    Job.Product=Base->CreateItem(Recipe->Output,1);
    for(const auto& Ingredient:Recipe->Inputs)
    {
        auto Reserved=Base->CreateItem(Ingredient.Item,Ingredient.Count);
        Reserved.Place=0;Reserved.Cell=-1;Reserved.Container.Reset();Job.Escrow.Add(Reserved);
    }
    auto* PS=Controller->GetPlayerState<AColdSteelPlayerState>();PS->SetActorTickEnabled(false);
    UColdSteelStatusModel* Model=Base;
    if(Host)Base->AdoptNetMirror(Profile);else {PS->ShadowModel=Base->CreateShadowModel(Profile);Model=PS->ShadowModel;}
    if(!Model){Done=true;ManualWire::Finish(false,TEXT("fixture paid batch was rejected by profile validation"));return;}
    auto* Character=CastChecked<AFPSGAMECharacter>(Controller->GetPawn());
    if(!Host)Character->NetShadowProfile=Model;
    Model->AttachPawn(Character);
    Character->GetCharacterMovement()->DisableMovement();
    for(auto* Component:Character->GetComponents())Component->SetComponentTickEnabled(false);
    auto* Session=Host?System:System->CreateNetworkSession(Model,TEXT("ColdSteel_ManualNetAudit_Guest"));
    if(!Host)PS->GuestAlchemy=Session;
    for(TActorIterator<AAlchemyManualNetAuditPawn> It(GetWorld());It;++It)
        if(*It!=Character)It->SetActorLocation(FVector(-1500,500,100));
    Controller->GetPawn()->SetActorLocation(FVector(0,0,100));
    Session->Bench=Probe->Bench.Get();Session->WorkingPawn=Controller->GetPawn();Session->Working=Job;Session->Accepted=*Recipe;Session->RestoredId=Job.Id;
    Session->bActive=true;Session->BookPage=0;Session->NextSaveAt=FPlatformTime::Seconds()+600.;Session->Publish();
    const auto* Health=Character->FindComponentByClass<UFPSCombatHealthComponent>();
    UE_LOG(LogTemp,Display,TEXT("MANUAL_NET_SETUP role=%s reachable=%d pawn=%s eye=%s bench=%s dead=%d controller=%d"),
        *Controller->Label,Session->Reachable(),*Character->GetActorLocation().ToString(),*Character->GetPawnViewLocation().ToString(),
        *Probe->Bench->Body()->Bounds.GetBox().GetClosestPointTo(Character->GetPawnViewLocation()).ToString(),Health&&Health->IsDead(),Character->GetController()==Controller);
}
void AAlchemyManualNetAuditGameMode::Phase(int32 Number,int32 Page,bool Open)
{Probe->Phase=Number;Probe->ExpectedPage=Page;Probe->ExpectedOpen=Open;Probe->ForceNetUpdate();}
void AAlchemyManualNetAuditGameMode::Logout(AController* Controller)
{
    // Let the production NetWorldSubsystem/PlayerState disconnect hooks close
    // the workstation; the fixture must not perform that cleanup itself.
    Super::Logout(Controller);
    if(ManualWire::Enabled())UE_LOG(LogTemp,Display,TEXT("MANUAL_NET_DISCONNECT production logout hook completed"));
}
void AAlchemyManualNetAuditGameMode::Tick(float Delta)
{
    Super::Tick(Delta);if(!ManualWire::Enabled()||Done||!Probe)return;
    AAlchemyManualNetAuditController *Host=nullptr,*Early=nullptr,*Late=nullptr;
    for(auto It=GetWorld()->GetPlayerControllerIterator();It;++It)if(auto* PC=Cast<AAlchemyManualNetAuditController>(It->Get()))
    {
        if(PC->Failed)
        {
            for(auto Other=GetWorld()->GetPlayerControllerIterator();Other;++Other)if(auto* Reader=Cast<AAlchemyManualNetAuditController>(Other->Get()))
                if(auto* PS=Reader->GetPlayerState<AColdSteelPlayerState>();PS&&PS->GuestAlchemy)
                {
                    auto* S=PS->GuestAlchemy.Get();
                    UE_LOG(LogTemp,Warning,TEXT("MANUAL_NET_SESSION role=%s active=%d pending=%d saving=%d reachable=%d sequence=%u modelJob=%s sessionJob=%s page=%d"),
                        *Reader->Label,S->bActive,S->bPending,S->Saving(),S->Reachable(),PS->AlchemyAuthoritySequence,
                        PS->ShadowModel?*PS->ShadowModel->AlchemyJob().Id:TEXT("none"),*S->Job().Id,S->BookPage);
                }
            Done=true;ManualWire::Finish(false,FString::Printf(TEXT("role %s phase %d failed"),*PC->Label,PC->ReportedPhase));return;
        }
        if(PC->Label==TEXT("host"))Host=PC;else if(PC->Label==TEXT("early"))Early=PC;else if(PC->Label==TEXT("late"))Late=PC;
    }
    if(GetWorld()->GetRealTimeSeconds()-Started>600.){Done=true;ManualWire::Finish(false,TEXT("timeout"));return;}
    if(!Host||!Host->GetPawn()||(!Early&&Probe->Phase<8)||(Early&&!Early->GetPawn()))return;
    auto Both=[&](int32 P){return Host->ReportedPhase==P&&Early&&Early->ReportedPhase==P;};
    if(Probe->Phase==0){Seed(Early,false);if(!Done)Phase(1,0);}
    else if(Probe->Phase==1&&Both(1))Phase(2,1);
    else if(Probe->Phase==2&&Both(2))Phase(3,1);
    else if(Probe->Phase==3&&Both(3))Phase(4,0);
    else if(Probe->Phase==4&&Both(4)){Early->GetPlayerState<AColdSteelPlayerState>()->GuestAlchemy->Suspend();Phase(5,0,false);}
    else if(Probe->Phase==5&&Both(5))
    {
        auto* Session=Early->GetPlayerState<AColdSteelPlayerState>()->GuestAlchemy.Get();
        if(!Session->Resume())
        {
            UE_LOG(LogTemp,Warning,TEXT("MANUAL_NET_RESUME saving=%d reachable=%d notice=%s model=%s"),
                Session->Saving(),Session->Reachable(),*Session->Notice,*Session->Model()->ResultMessage());
            Done=true;ManualWire::Finish(false,TEXT("remote session could not resume"));return;
        }
        Phase(6,1);
    }
    else if(Probe->Phase==6&&Both(6))Phase(7,1);
    else if(Probe->Phase==7&&Both(7)){Phase(8,0,false);Early->ClientLeave();}
    else if(Probe->Phase==8&&Host->ReportedPhase==8&&!Early)
    {
        Seed(Host,true);
        if(!Done){GetGameInstance()->GetSubsystem<UColdSteelAlchemySystem>()->Input(EAlchemyOp::Book,1);Phase(9,1);UE_LOG(LogTemp,Display,TEXT("MANUAL_NET_LATE_READY"));}
    }
    else if(Probe->Phase==9&&Host->ReportedPhase==9&&Late&&Late->ReportedPhase==9)
    {
        auto* Base=GetGameInstance()->GetSubsystem<UColdSteelStatusModel>();auto Profile=Base->Snapshot();
        Profile.AlchemyJob.Id=TEXT("manual.audit.late");
        Late->GetPlayerState<AColdSteelPlayerState>()->ShadowModel=Base->CreateShadowModel(Profile);
        if(!Late->GetPlayerState<AColdSteelPlayerState>()->ShadowModel)
        {Done=true;ManualWire::Finish(false,TEXT("fixture observer profile was rejected"));return;}
        Phase(10,1);
    }
    else if(Probe->Phase==10&&Host->ReportedPhase==10&&Late&&Late->ReportedPhase==10)
    {Done=true;ManualWire::Finish(true,TEXT("owner requests, invalid input, observer rejection, late join, disconnect and host handover completed"));}
}
