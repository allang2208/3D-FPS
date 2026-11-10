#include "EnhancementEscrowWireAudit.h"
#include "../UI/ColdSteelStatusModel.h"
#include "../UI/ColdSteelEnhancementSystem.h"
#include "../Multiplayer/ColdSteelProfileTransfer.h"
#include "../Multiplayer/ColdSteelSharedInventorySubsystem.h"
#include "../Building/VoxelBuildWorld.h"
#include "../Building/VoxelBuildPrefabActor.h"
#include "../Building/ColdSteelPlantingSystem.h"
#include "../FPSGAMECharacter.h"
#include "Components/StaticMeshComponent.h"
#include "Engine/GameInstance.h"
#include "Engine/World.h"
#include "Engine/StaticMesh.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "GameFramework/GameStateBase.h"
#include "Kismet/GameplayStatics.h"
#include "Misc/CommandLine.h"
#include "Misc/FileHelper.h"
#include "Misc/Parse.h"
#include "Net/UnrealNetwork.h"
#include "Serialization/JsonSerializer.h"

namespace EscrowWire
{
bool Enabled(){return FParse::Param(FCommandLine::Get(),TEXT("EnhancementEscrowWireAudit"));}
const FString Gun=TEXT("escrow-wire-m1911"),Other=TEXT("escrow-wire-m4");
void Freeze(AFPSGAMECharacter* Pawn,FVector Location)
{
    if(!Pawn)return;Pawn->SetActorLocation(Location);Pawn->SetActorHiddenInGame(true);Pawn->SetActorEnableCollision(false);Pawn->SetActorTickEnabled(false);
    Pawn->GetCharacterMovement()->StopMovementImmediately();Pawn->GetCharacterMovement()->DisableMovement();
    for(auto* Component:Pawn->GetComponents())Component->SetComponentTickEnabled(false);
}
FColdSteelProfile Seed(UColdSteelStatusModel* M,bool Host)
{
    auto P=M->Snapshot();P.Items.Reset();P.EnhancementItem={};P.ForgeJob={};P.GunAssemblyJob={};P.WoodworkingJob={};P.AlchemyJob={};
    P.QuickBindings.Init(FColdSteelQuickBinding(),ColdSteelQuickBar::Count);P.QuickBarVersion=ColdSteelQuickBar::Version;P.Hotbar.Init(TEXT(""),4);P.HotbarDefinitions.Init(TEXT(""),4);P.ActiveProductionTool.Reset();P.ActiveWeaponSlot=6;
    P.CampfireInventoryRevision=0;P.CampfireWorldReceipts.Reset();P.ServerSoulCredits=P.ServerSoulDebits=0;P.Souls=100000;
    FString Session;FParse::Value(FCommandLine::Get(),TEXT("EscrowWireSession="),Session);FGuid::Parse(Session,P.NetworkProfileId);
    if(Host)P.NetworkProfileId=FGuid::NewGuid();
    auto I=M->CreateItem(TEXT("ue_m1911"));I.InstanceId=Host?TEXT("escrow-wire-host"):Gun;I.Magazine=5;ColdSteelInventory::ApplyOrientation(I,1);
    I.Cell=-1;P.EnhancementItem=I;
    auto O=M->CreateItem(TEXT("ue_m4a1"));O.InstanceId=Other;ColdSteelInventory::Insert(P.Items,O);
    ColdSteelInventory::Insert(P.Items,M->CreateItem(TEXT("enhancement_stone"),10));
    // BowWeaponComponent grants a missing starter bow at pawn initialization.
    // Keep it in the fixture so reconnect does not introduce a local-only item.
    auto Bow=M->CreateItem(TEXT("bow_dark"));Bow.InstanceId=TEXT("escrow-wire-starter-bow");
    ColdSteelInventory::Insert(P.Items,Bow);return P;
}
int64 Revision(int32 P){return P==0?1:P<=2?2:P==3?3:P==4?4:P==5?5:P<=10?6:7;}
bool ExpectedSuccess(int32 P){return P!=2&&P!=7&&P!=8&&P!=9;}
bool State(UColdSteelStatusModel* M,int32 P)
{
    if(!M)return false;const auto S=M->Snapshot();
    const FString Expected=(P==0||P==4||P==11)?FString():P==3?Other:Gun;
    if(S.EnhancementItem.InstanceId!=Expected||S.CampfireInventoryRevision!=Revision(P))return false;
    const FColdSteelItem* I=Expected==Gun?&S.EnhancementItem:M->FindItem(Gun);
    if(!I||I->Width!=2||I->Height!=3||!I->bRotated||I->Magazine!=5||ColdSteelInventory::Number(*I,TEXT("enhanceLevel"))!=(P>=6?1:0))return false;
    int32 Copies=S.EnhancementItem.InstanceId==Gun?1:0;for(const auto& V:S.Items)Copies+=V.InstanceId==Gun;
    return Copies==1;
}
void Save(const TArray<TSharedPtr<FJsonValue>>& Rows,bool Passed,const TCHAR* Role)
{
    auto O=MakeShared<FJsonObject>();O->SetBoolField(TEXT("passed"),Passed);O->SetStringField(TEXT("role"),Role);O->SetArrayField(TEXT("checks"),Rows);
    O->SetBoolField(TEXT("real_udp_inventory_rpc"),true);O->SetBoolField(TEXT("visuals_tested"),false);
    O->SetStringField(TEXT("planting_scope"),TEXT("snapshot transport and ApplyNetworkState ordering only; no planting action RPC"));
    FString Text,Path;FJsonSerializer::Serialize(O,TJsonWriterFactory<>::Create(&Text));
    if(FParse::Value(FCommandLine::Get(),TEXT("EscrowWireOutput="),Path))FFileHelper::SaveStringToFile(Text,*Path);
    UE_LOG(LogTemp,Display,TEXT("ENHANCEMENT_WIRE_RESULT %s"),*Text);
}
}
void AEnhancementEscrowWirePlayerState::Tick(float Delta)
{
    if(!EscrowWire::Enabled()){Super::Tick(Delta);return;}
    APlayerState::Tick(Delta);
    if(HasAuthority())TickInventoryReply();else if(bInventoryWaitingUpload)TickUpload(Delta);
}
void AEnhancementEscrowWireController::GetLifetimeReplicatedProps(TArray<FLifetimeProperty>& OutLifetimeProps) const
{Super::GetLifetimeReplicatedProps(OutLifetimeProps);DOREPLIFETIME(AEnhancementEscrowWireController,Bench);}
void AEnhancementEscrowWireController::Receipt(bool Success,const FString& Message)
{++Receipts;ReceiptSuccess=Success;Notice=Message; if(auto* M=GetGameInstance()->GetSubsystem<UColdSteelStatusModel>())UE_LOG(LogTemp,Display,TEXT("ENHANCEMENT_WIRE_OWNER phase=%d success=%d model_reason=%s"),Current,Success,*M->ResultMessage());}
void AEnhancementEscrowWireController::ClientPhase_Implementation(int32 Phase,const TArray<uint8>& Seed)
{if(!EscrowWire::Enabled()||Phase==Requested)return;Requested=Phase;Fixture=Seed;}
void AEnhancementEscrowWireController::Tick(float Delta)
{
    Super::Tick(Delta);if(!EscrowWire::Enabled()||!IsLocalController()||HasAuthority())return;
    const double Now=GetWorld()->GetRealTimeSeconds();if(ExitAt>=0){if(Now>=ExitAt)FPlatformMisc::RequestExit(false);return;}
    auto* M=GetGameInstance()->GetSubsystem<UColdSteelStatusModel>();auto* E=GetGameInstance()->GetSubsystem<UColdSteelEnhancementSystem>();
    auto* PS=GetPlayerState<AColdSteelPlayerState>();auto* OwnerPawn=Cast<AFPSGAMECharacter>(GetPawn());
    if(!M||!M->IsAudit()||!E||!PS||PS->GetPawn()!=OwnerPawn||!OwnerPawn||!Bench||Requested<0)return;
    if(!Bound){E->OnNetworkResult.AddUObject(this,&ThisClass::Receipt);Bound=true;M->AttachPawn(OwnerPawn);}
    EscrowWire::Freeze(OwnerPawn,FVector(0,0,100));
    if(Current!=Requested)
    {
        Current=Requested;Sent=Reported=false;Receipts=0;Started=Now;Notice.Reset();
        if(Current==0&&!M->CommitState(EscrowWire::Seed(M,false))){ServerResult(Current,false,-1,M->ResultMessage());Reported=true;return;}
        if(!Fixture.IsEmpty())
        {
            auto* Save=ColdSteelProfileTransfer::BlobToSave(Fixture);Fixture.Reset();
            if(!Save){ServerResult(Current,false,-1,TEXT("fixture decode failed"));Reported=true;return;}
            M->AdoptNetMirror(Save->Profile);M->SaveNow();
            // Explicit fixture edits on both peers are not production transactions.
            PS->AcknowledgedInventoryBaseline=PS->InventoryBaseline(M->Snapshot());
            PS->bHasUploadedAppearance=true;PS->UploadedHeadId=M->Snapshot().PlayerHeadId;PS->UploadedHairId=M->Snapshot().PlayerHairId;
        }
    }
    if(Reported)return;
    if(Current==10){M->SaveNow();Reported=true;ServerResult(Current,EscrowWire::State(M,Current),M->Snapshot().CampfireInventoryRevision,TEXT("saved escrow before reconnect"));return;}
    if(!Sent&&!PS->InventoryRequestPending())
    {
        FColdSteelInventoryRequest R;R.Action=EColdSteelInventoryAction::Workstation;R.Target=Bench;
        if(Current==0||Current==4||Current==8||Current==11){R.Mode=TEXT("enhancement.retrieve");R.Item=Current==4?EscrowWire::Other:EscrowWire::Gun;R.ExpectedBenchId=R.Item;}
        else if(Current==6||Current==7){R.Mode=TEXT("enhancement.apply");R.Item=EscrowWire::Gun;R.Count=0;}
        else {R.Mode=TEXT("enhancement.place");R.Item=(Current==2||Current==3||Current==9)?EscrowWire::Other:EscrowWire::Gun;R.ExpectedBenchId=(Current==3||Current==9)?EscrowWire::Gun:FString();}
        Sent=PS->RequestInventoryAction(R);
    }
    if((Sent&&Receipts>0&&!PS->InventoryRequestPending())||Now-Started>60.)
    {
        const bool OK=Sent&&Receipts==1&&ReceiptSuccess==EscrowWire::ExpectedSuccess(Current)&&EscrowWire::State(M,Current);
        Reported=true;ServerResult(Current,OK,M->Snapshot().CampfireInventoryRevision,Notice);
    }
}
void AEnhancementEscrowWireController::ServerResult_Implementation(int32 Phase,bool OwnerPass,int64 OwnerRevision,const FString& Detail)
{
    if(!EscrowWire::Enabled()||Phase<=Finished)return;auto* PS=GetPlayerState<AColdSteelPlayerState>();auto* M=PS?PS->ShadowModel.Get():nullptr;
    const auto* Saved=PS?Cast<UColdSteelProfileSave>(UGameplayStatics::LoadGameFromSlot(PS->CampfireGuestSlot(),0)):nullptr;
    const bool Durable=Saved&&M&&Saved->Profile.CampfireInventoryRevision==M->Snapshot().CampfireInventoryRevision
        &&Saved->Profile.EnhancementItem.InstanceId==M->EnhancementItem().InstanceId;
    const auto* Host=GetGameInstance()->GetSubsystem<UColdSteelStatusModel>();
    auto* Shared=GetWorld()->GetSubsystem<UColdSteelSharedInventorySubsystem>();
    UE_LOG(LogTemp,Display,TEXT("ENHANCEMENT_WIRE_DIAG phase=%d shared=%d initialized=%d harvest=%d model=%d runtime=%s pawn=%s reach=%d escrow=%s"),Phase,Shared!=nullptr,Shared&&Shared->InitializeAuthority(),UColdSteelSharedInventorySubsystem::HarvestModel(this)!=nullptr,M!=nullptr,M?*GetNameSafe(M->RuntimePawn()):TEXT("none"),*GetNameSafe(GetPawn()),PS&&PS->StationReach(TEXT("enhancement"),Bench),M?*M->EnhancementItem().InstanceId:TEXT("none"));
    const bool OK=OwnerPass&&EscrowWire::State(M,Phase)&&Durable&&Host&&Host->EnhancementItem().InstanceId==TEXT("escrow-wire-host")
        &&Host->Snapshot().CampfireInventoryRevision==0;
    Passed&=OK;Finished=Phase;
    if(auto* GM=GetWorld()->GetAuthGameMode<AEnhancementEscrowWireGameMode>())GM->Record(Phase,OK,OwnerPass,OwnerRevision,Detail);
}
void AEnhancementEscrowWireController::ClientPlantState_Implementation(int32 Index,const FColdSteelPlantingNetState& State,bool Changed)
{
    if(!EscrowWire::Enabled())return;auto* P=GetGameInstance()->GetSubsystem<UColdSteelPlantingSystem>();const uint64 Before=P->StateSerial();
    const bool OK=P->ApplyNetworkState(GetWorld(),State)&&P->StateSerial()==Before+(Changed?1:0);ServerPlantResult(Index,OK);
}
void AEnhancementEscrowWireController::ServerPlantResult_Implementation(int32 Index,bool OK)
{if(EscrowWire::Enabled()){PlantFinished=FMath::Max(PlantFinished,Index);Passed&=OK;UE_LOG(LogTemp,Display,TEXT("ENHANCEMENT_WIRE_PLANT_ORDER index=%d pass=%d"),Index,OK);}}
void AEnhancementEscrowWireController::ClientFinish_Implementation(bool OK)
{if(EscrowWire::Enabled()){EscrowWire::Save({},OK,TEXT("client"));ExitAt=GetWorld()->GetRealTimeSeconds()+.5;}}
AEnhancementEscrowWireGameMode::AEnhancementEscrowWireGameMode()
{
    PlayerControllerClass=AEnhancementEscrowWireController::StaticClass();PlayerStateClass=AEnhancementEscrowWirePlayerState::StaticClass();
    DefaultPawnClass=AFPSGAMECharacter::StaticClass();GameStateClass=AGameStateBase::StaticClass();PrimaryActorTick.bCanEverTick=true;
}
void AEnhancementEscrowWireGameMode::BeginPlay()
{
    Super::BeginPlay();if(!EscrowWire::Enabled())return;Started=GetWorld()->GetRealTimeSeconds();
    Building=GetWorld()->SpawnActor<AVoxelBuildWorld>();Building->SetActorTickEnabled(false);
    FActorSpawnParameters Spawn;Spawn.Owner=Building;Bench=GetWorld()->SpawnActor<AVoxelBuildPrefabActor>(FVector(200,0,100),FRotator::ZeroRotator,Spawn);
    Bench->bAlwaysRelevant=true;Bench->Configure(TEXT("arcane_workbench"),FIntVector::ZeroValue,0,LoadObject<UStaticMesh>(nullptr,TEXT("/Engine/BasicShapes/Cube.Cube")),nullptr,nullptr);
    FVoxelBuildPrefabInstance Entry;Entry.Id=TEXT("arcane_workbench");Entry.Cell=FIntVector::ZeroValue;Entry.InstanceId=FGuid::NewGuid();
    Building->Prefabs.Add(Entry);Building->PrefabActors.Add(Entry.Cell,Bench.Get());
    UE_LOG(LogTemp,Display,TEXT("ENHANCEMENT_WIRE_HOST_READY"));
}
void AEnhancementEscrowWireGameMode::PostLogin(APlayerController* PC)
{Super::PostLogin(PC);if(EscrowWire::Enabled()&&!PC->IsLocalController()){Guest=Cast<AEnhancementEscrowWireController>(PC);++Connections;Prepared=Connections==1?-1:10;AwaitingReconnect=false;}}
void AEnhancementEscrowWireGameMode::Logout(AController* PC)
{
    const bool WasGuest=PC==Guest;Super::Logout(PC);
    if(EscrowWire::Enabled()&&WasGuest){Guest=nullptr;if(AwaitingReconnect)UE_LOG(LogTemp,Display,TEXT("ENHANCEMENT_WIRE_RECONNECT_READY"));}
}
void AEnhancementEscrowWireGameMode::Record(int32 Phase,bool OK,bool OwnerPass,int64 OwnerRevision,const FString& Detail)
{
    auto R=MakeShared<FJsonObject>();R->SetNumberField(TEXT("phase"),Phase);R->SetBoolField(TEXT("passed"),OK);R->SetBoolField(TEXT("owner_passed"),OwnerPass);
    R->SetNumberField(TEXT("owner_revision"),OwnerRevision);R->SetStringField(TEXT("notice"),Detail);Rows.Add(MakeShared<FJsonValueObject>(R));Passed&=OK;
    FString Json;FJsonSerializer::Serialize(R,TJsonWriterFactory<>::Create(&Json));UE_LOG(LogTemp,Display,TEXT("ENHANCEMENT_WIRE_CASE %s"),*Json);
}
void AEnhancementEscrowWireGameMode::BeginPhase(int32 Phase)
{
    Prepared=Phase;TArray<uint8> Bytes;auto* PS=Guest->GetPlayerState<AColdSteelPlayerState>();auto* M=PS?PS->ShadowModel.Get():nullptr;
    if(Phase==8&&M)
    {
        WithSpace=M->Snapshot();auto Full=WithSpace;Full.Items.Reset();const int32 Cells=ColdSteelInventory::BagRows(Full.Items)*18;
        for(int32 Cell=0;Cell<Cells;++Cell){auto I=M->CreateItem(TEXT("enhancement_stone"),1);I.Cell=Cell;I.InstanceId=FString::Printf(TEXT("wire-full-%d"),Cell);Full.Items.Add(I);}
        auto Other=M->CreateItem(TEXT("ue_m4a1"));Other.InstanceId=EscrowWire::Other;Other.Place=1;Other.Cell=6;Full.Items.Add(Other);M->AdoptNetMirror(Full);
    }
    if(Phase==10&&M)M->AdoptNetMirror(WithSpace);
    if((Phase==8||Phase==10)&&M){auto* S=NewObject<UColdSteelProfileSave>();S->Profile=M->Snapshot();ColdSteelProfileTransfer::SaveToBlob(S,Bytes);}
    Guest->Bench=Bench;Guest->ForceNetUpdate();Guest->ClientPhase(Phase,Bytes);
}
void AEnhancementEscrowWireGameMode::Tick(float Delta)
{
    Super::Tick(Delta);if(!EscrowWire::Enabled()||Done)return;const double Now=GetWorld()->GetRealTimeSeconds();
    if(ExitAt>=0){if(Now>=ExitAt){Done=true;FPlatformMisc::RequestExit(false);}return;}
    auto* Host=GetGameInstance()->GetSubsystem<UColdSteelStatusModel>();
    if(!HostSeeded)
    {
        auto* PC=GetWorld()->GetFirstPlayerController();auto* Pawn=PC&&PC->IsLocalController()?Cast<AFPSGAMECharacter>(PC->GetPawn()):nullptr;
        if(!Host||!Host->IsAudit()||!Pawn)return;Host->AdoptNetMirror(EscrowWire::Seed(Host,true));Host->AttachPawn(Pawn);
        EscrowWire::Freeze(Pawn,FVector(-1500,0,100));HostSeeded=true;
    }
    if(Now-Started>420.||!Passed||(Guest&&!Guest->Passed))
    {EscrowWire::Save(Rows,false,TEXT("listen-host"));if(Guest)Guest->ClientFinish(false);ExitAt=Now+2.;return;}
    if(!Guest||!Guest->GetPawn())return;EscrowWire::Freeze(Cast<AFPSGAMECharacter>(Guest->GetPawn()),FVector(0,0,100));
    if(Guest->Finished==11)
    {EscrowWire::Save(Rows,true,TEXT("listen-host"));Guest->ClientFinish(true);ExitAt=Now+2.;return;}
    if(AwaitingReconnect)return;
    if(Guest->Finished==10)
    {
        if(Guest->PlantFinished==0)
        {
            FColdSteelPlantingNetState S;S.WorldKey=TEXT("EnhancementEscrowWire_PlantOrder");S.Revision=7;S.bReady=true;
            const uint64 Sequence[]={1,2,1,3,2};const bool Blocked[]={false,true,false,false,true};
            for(int32 I=0;I<5;++I){S.SnapshotSequence=Sequence[I];S.bSaveBlocked=Blocked[I];Guest->ClientPlantState(I+1,S,I!=2&&I!=4);}Guest->PlantFinished=-1;
        }
        else if(Guest->PlantFinished==5){Record(12,Guest->Passed,true,6,TEXT("five ordered/stale planting snapshots traversed UDP; no planting action coverage"));AwaitingReconnect=true;Guest->ClientFinish(true);}
        return;
    }
    const int32 Next=Connections==1?Guest->Finished+1:11;
    if(Prepared!=Next)BeginPhase(Next);
}
