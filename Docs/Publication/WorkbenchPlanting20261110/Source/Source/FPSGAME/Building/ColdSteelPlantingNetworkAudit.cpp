#include "ColdSteelPlantingAuditCommandlet.h"
#include "ColdSteelPlantingSystem.h"
#include "VoxelBuildWorld.h"
#include "VoxelBuildPrefabActor.h"
#include "../Multiplayer/ColdSteelSharedInventorySubsystem.h"
#include "../Multiplayer/ColdSteelInventoryRequestTypes.h"
#include "../UI/ColdSteelStatusModel.h"
#include "../FPSGAMECharacter.h"
#include "Engine/Engine.h"
#include "Engine/GameInstance.h"
#include "Engine/World.h"
#include "GameFramework/PlayerController.h"
#include "HAL/FileManager.h"
#include "Kismet/GameplayStatics.h"
#include "Misc/CommandLine.h"
#include "Misc/FileHelper.h"
#include "Misc/Parse.h"
#include "Misc/Paths.h"
#include "Misc/ScopeExit.h"
#include "Dom/JsonObject.h"
#include "Dom/JsonValue.h"
#include "Serialization/JsonSerializer.h"

// Deterministic network-branch regression. No socket, map, PIE, or production save.
// The same real snapshot consumer receives both reply and delayed world payloads.
int32 UColdSteelPlantingAuditCommandlet::RunNetworkAudit(const FString& Params)
{
    FString Root;
    if(!FParse::Value(*Params,TEXT("PlantingAuditRoot="),Root)||Root.IsEmpty())return 2;
    Root=FPaths::ConvertRelativePathToFull(Root);FPaths::NormalizeDirectoryName(Root);
    FString Saved=FPaths::ConvertRelativePathToFull(FPaths::ProjectSavedDir());FPaths::NormalizeDirectoryName(Saved);
    FString Allowed=FPaths::ConvertRelativePathToFull(FPaths::ProjectDir()/TEXT("SourceAssets/PlantingMultiplayer20261022/TestRuns"));
    FPaths::NormalizeDirectoryName(Allowed);
    if(!Root.StartsWith(Allowed+TEXT("/"))||!Saved.StartsWith(Root+TEXT("/")))return 2;
    const FString Original=FCommandLine::Get();
    const FString Profile=TEXT("PlantingNetworkAudit_")+FGuid::NewGuid().ToString(EGuidFormats::Digits);
    FCommandLine::Set(*(Original+TEXT(" -ColdSteelProfile=")+Profile));
    auto* GI=NewObject<UGameInstance>(GEngine);GI->AddToRoot();GI->InitializeStandalone(TEXT("PlantingNetworkAuditWorld"));
    auto* World=GI->GetWorld();
    ON_SCOPE_EXIT
    {
        World->NextURL.Reset();GI->Shutdown();GEngine->DestroyWorldContext(World);World->DestroyWorld(false);
        GI->RemoveFromRoot();FCommandLine::Set(*Original);
    };
    auto* Model=GI->GetSubsystem<UColdSteelStatusModel>();auto* System=GI->GetSubsystem<UColdSteelPlantingSystem>();
    if(!Model||!System||!Model->IsAudit()||Model->ProfileSlot()!=TEXT("ColdSteel_")+Profile||World->GetNetDriver())return 2;
    int32 Failures=0;TArray<TSharedPtr<FJsonValue>> Rows;FString Reason;
    auto Check=[&](bool Pass,const FString& Name)
    {
        if(!Pass)++Failures;
        auto Row=MakeShared<FJsonObject>();Row->SetStringField(TEXT("name"),Name);Row->SetBoolField(TEXT("passed"),Pass);
        if(!Pass)Row->SetStringField(TEXT("reason"),Reason);
        Rows.Add(MakeShared<FJsonValueObject>(Row));
        UE_LOG(LogTemp,Display,TEXT("PLANTING_NETWORK_AUDIT %s %s %s"),Pass?TEXT("PASS"):TEXT("FAIL"),*Name,Pass?TEXT(""):*Reason);
        return Pass;
    };
    ON_SCOPE_EXIT
    {
        auto Result=MakeShared<FJsonObject>();Result->SetNumberField(TEXT("checks"),Rows.Num());Result->SetNumberField(TEXT("failures"),Failures);
        Result->SetArrayField(TEXT("results"),Rows);Result->SetBoolField(TEXT("network_transport_exercised"),false);
        Result->SetBoolField(TEXT("graphical_editor_started"),false);Result->SetBoolField(TEXT("game_or_pie_started"),false);
        Result->SetStringField(TEXT("profile_slot"),Model->ProfileSlot());Result->SetStringField(TEXT("saved_root"),Saved);
        FString Output;FJsonSerializer::Serialize(Result,TJsonWriterFactory<>::Create(&Output));
        FFileHelper::SaveStringToFile(Output,*(Root/TEXT("planting-network-audit.json")));
        UE_LOG(LogTemp,Display,TEXT("PLANTING_NETWORK_AUDIT_COMPLETE checks=%d failures=%d"),Rows.Num(),Failures);
    };
    Check(System->Catalog().Num()==4,TEXT("actual planting catalog available"));
    auto* PC=World->SpawnActor<APlayerController>();PC->SetAsLocalPlayerController();World->AddController(PC);
    auto* Pawn=World->SpawnActor<AFPSGAMECharacter>(FVector(0,0,100),FRotator::ZeroRotator);PC->Possess(Pawn);
    auto Blank=Model->Snapshot();Blank.Items.Reset();Blank.PlantingCrops.Reset();Blank.ActiveProductionTool.Reset();Blank.ActiveWeaponSlot=6;
    Blank.Hotbar.Init(TEXT(""),4);Blank.HotbarDefinitions.Init(TEXT(""),4);for(auto& Binding:Blank.QuickBindings)Binding={};
    Blank.ForgeJob={};Blank.GunAssemblyJob={};Blank.WoodworkingJob={};Blank.EnhancementItem={};
    Model->AdoptNetMirror(Blank);Model->AttachPawn(Pawn);
    auto Seed=Model->Snapshot();
    if(!Check(ColdSteelInventory::Insert(Seed.Items,Model->CreateItem(TEXT("tomato"),2))&&Model->CommitState(Seed),
        TEXT("isolated inventory baseline saved with two planting inputs")))return 3;
    auto* Building=World->SpawnActor<AVoxelBuildWorld>();Building->WorldKey=TEXT("PlantingNetworkAuditWorld");Building->bReady=true;
    ON_SCOPE_EXIT {Building->bReady=false;};
    auto* Bed=World->SpawnActor<AVoxelBuildPrefabActor>();Bed->SetOwner(Building);
    Bed->Configure(UColdSteelPlantingSystem::BedPrefabId(),FIntVector::ZeroValue,0,nullptr,nullptr,nullptr);
    FVoxelBuildPrefabInstance Record;Record.Id=UColdSteelPlantingSystem::BedPrefabId();Record.Cell=FIntVector::ZeroValue;
    Record.InstanceId=FGuid::NewGuid();Record.Footprint=FIntVector(10,10,2);Building->Prefabs.Add(Record);Building->PrefabActors.Add(Record.Cell,Bed);
    System->bAssetsReady=true;
    auto* Peer=NewObject<UColdSteelPlantingSystem>(GI);Peer->AddToRoot();
    ON_SCOPE_EXIT {Peer->RemoveFromRoot();};
    World->NextURL=TEXT("/Engine/Maps/Entry?listen");
    auto* Shared=World->GetSubsystem<UColdSteelSharedInventorySubsystem>();
    if(!Check(World->GetNetMode()==NM_ListenServer&&Shared&&Shared->InitializeAuthority(),TEXT("real listen authority initialized without transport")))return 3;
    auto Initial=Shared->Current;Initial.PlantingSeededWorlds.Add(Building->WorldKey);Initial.PlantingRevision=1;
    if(!Check(Shared->CommitPlantingWorld(Initial,Reason),TEXT("shared planting baseline committed in isolated save root")))return 3;
    const FString Slot=Shared->SaveSlot;
    auto Reload=[&]()
    {
        Shared->Current={};Shared->SaveSlot.Reset();Shared->bInitialized=false;Shared->bBlocked=false;Shared->bCommitting=false;
        return Shared->InitializeAuthority();
    };
    FColdSteelInventoryRequest Request;Request.Action=EColdSteelInventoryAction::Planting;Request.Mode=TEXT("planting.plant");
    Request.Pawn=Pawn;Request.Target=Bed;Request.Anchor=Record.Cell;Request.Cell=0;Request.Definition=TEXT("tomato");Request.PlantingBedId=Record.InstanceId;
    FColdSteelProfile Proposed;auto After=Shared->Current;
    if(!Check(System->PrepareNetwork(Building,Request,Model,Proposed,After.PlantingCrops,Reason),TEXT("authority prepares planting from request identity and owned inventory")))return 3;
    const auto BeforeFailure=System->NetworkState(Building);
    const int64 InventoryBefore=Model->CountMaterial(TEXT("tomato"));
    ++After.PlantingRevision;Model->AuditFailNextSave=true;
    const bool Committed=Shared->Commit(Model,nullptr,Proposed,After,Reason);
    const auto Failed=System->NetworkState(Building);
    if(!Check(!Committed&&!Model->AuditFailNextSave&&Failed.bSaveBlocked&&Failed.Revision==BeforeFailure.Revision
        &&Failed.SnapshotSequence>BeforeFailure.SnapshotSequence&&Model->CountMaterial(TEXT("tomato"))==InventoryBefore&&Shared->Current.PlantingCrops.IsEmpty(),
        TEXT("injected player save failure keeps crops and inputs unchanged but publishes newer lock at same revision")))return 3;
    Check(UGameplayStatics::DoesSaveGameExist(Slot+TEXT("_Transaction"),0),TEXT("failed transaction retains durable recovery journal"));
    World->NextURL=TEXT("127.0.0.1:1");
    if(!Check(World->GetNetMode()==NM_Client,TEXT("real client net-mode branch selected without socket")))return 3;
    auto Deliver=[&](UColdSteelPlantingSystem* Client,const FColdSteelPlantingNetState& State)
    {
        auto* Reply=NewObject<UColdSteelInventoryReply>();Reply->bPlantingView=true;Reply->Planting=State;TArray<uint8> Bytes;
        if(!UGameplayStatics::SaveGameToMemory(Reply,Bytes))return false;
        const auto* Loaded=Cast<UColdSteelInventoryReply>(UGameplayStatics::LoadGameFromMemory(Bytes));
        return Loaded&&Loaded->Planting.SnapshotSequence==State.SnapshotSequence&&Client->ApplyNetworkState(World,Loaded->Planting);
    };
    Check(Deliver(System,BeforeFailure)&&Deliver(Peer,BeforeFailure),TEXT("two independent client mirrors decode the serialized initial snapshot"));
    Check(Deliver(System,Failed)&&Deliver(Peer,Failed)&&System->Mirror.bSaveBlocked&&Peer->Mirror.bSaveBlocked,TEXT("both client mirrors accept same-revision save lock"));
    const uint64 LockedSerial=System->StateSerial();
    Check(Deliver(System,BeforeFailure)&&Deliver(Peer,BeforeFailure)&&System->Mirror.bSaveBlocked&&Peer->Mirror.bSaveBlocked&&System->StateSerial()==LockedSerial,
        TEXT("delayed pre-failure world snapshot cannot unlock either client or dirty its UI"));
    Check(!System->CanAct(Building,Record.Cell,0,TEXT("tomato"),Reason),TEXT("locked client preview rejects planting after stale snapshot delivery"));
    Check(Deliver(System,Failed)&&System->StateSerial()==LockedSerial,TEXT("duplicate snapshot is idempotent"));
    World->NextURL=TEXT("/Engine/Maps/Entry?listen");
    if(!Check(Reload()&&!Shared->IsPlantingSaveBlocked()&&Shared->Current.PlantingRevision==BeforeFailure.Revision
        &&Shared->Current.PlantingCrops.IsEmpty()&&!UGameplayStatics::DoesSaveGameExist(Slot+TEXT("_Transaction"),0),
        TEXT("real journal recovery discards unpaid proposal and reopens unchanged revision")))return 3;
    const auto Recovered=System->NetworkState(Building);
    World->NextURL=TEXT("127.0.0.1:1");
    Check(Deliver(System,Recovered)&&Deliver(Peer,Recovered)&&!System->Mirror.bSaveBlocked&&!Peer->Mirror.bSaveBlocked,
        TEXT("newer same-revision recovery snapshot unlocks both mirrors"));
    Check(Deliver(System,Failed)&&Deliver(Peer,Failed)&&!System->Mirror.bSaveBlocked&&!Peer->Mirror.bSaveBlocked,
        TEXT("delayed failure reply cannot relock clients after recovery"));
    Check(System->CanAct(Building,Record.Cell,0,TEXT("tomato"),Reason),TEXT("recovered client can preview planting again"));
    World->NextURL=TEXT("/Engine/Maps/Entry?listen");
    After=Shared->Current;
    if(!Check(System->PrepareNetwork(Building,Request,Model,Proposed,After.PlantingCrops,Reason),TEXT("winning empty-slot intent still validates after recovery")))return 3;
    ++After.PlantingRevision;
    if(!Check(Shared->Commit(Model,nullptr,Proposed,After,Reason)&&Shared->Current.PlantingCrops.Num()==1&&Model->CountMaterial(TEXT("tomato"))==InventoryBefore-1,
        TEXT("winning planting intent commits exactly one crop and one input")))return 3;
    auto LosingAfter=Shared->Current;const auto RevisionAfter=Shared->Current.PlantingRevision;
    Check(!System->PrepareNetwork(Building,Request,Model,Proposed,LosingAfter.PlantingCrops,Reason)
        &&Model->CountMaterial(TEXT("tomato"))==InventoryBefore-1&&Shared->Current.PlantingRevision==RevisionAfter,
        TEXT("serialized competing empty-slot intent loses without charging or overwriting winner"));
    const FGuid PlantId=Shared->Current.PlantingCrops[0].PlantId;
    Request.PlantingBedId=FGuid::NewGuid();Request.Cell=2;
    Check(!System->PrepareNetwork(Building,Request,Model,Proposed,LosingAfter.PlantingCrops,Reason),TEXT("stale bed replacement identity rejected"));
    Request.PlantingBedId=Record.InstanceId;Request.Cell=0;Request.Mode=TEXT("planting.harvest");Request.ExpectedPlantId=FGuid::NewGuid();
    Check(!System->PrepareNetwork(Building,Request,Model,Proposed,LosingAfter.PlantingCrops,Reason),TEXT("stale harvest identity cannot take current crop"));
    auto Mature=Shared->Current;Mature.PlantingCrops[0].PlantedUtcTicks=FDateTime::UtcNow().GetTicks()-int64((Mature.PlantingCrops[0].GrowthSeconds+1)*ETimespan::TicksPerSecond);
    ++Mature.PlantingRevision;
    if(!Check(Shared->CommitPlantingWorld(Mature,Reason),TEXT("isolated maturity checkpoint saved")))return 3;
    Request.ExpectedPlantId=PlantId;After=Shared->Current;
    if(!Check(System->PrepareNetwork(Building,Request,Model,Proposed,After.PlantingCrops,Reason),TEXT("correct mature harvest identity prepares configured yield")))return 3;
    const int64 BeforeHarvest=Model->CountMaterial(TEXT("tomato"));const int64 Yield=Shared->Current.PlantingCrops[0].OutputCount;
    ++After.PlantingRevision;
    if(!Check(Shared->Commit(Model,nullptr,Proposed,After,Reason)&&Shared->Current.PlantingCrops.IsEmpty()&&Model->CountMaterial(TEXT("tomato"))==BeforeHarvest+Yield,
        TEXT("winning harvest removes crop and grants configured yield once")))return 3;
    LosingAfter=Shared->Current;
    Check(!System->PrepareNetwork(Building,Request,Model,Proposed,LosingAfter.PlantingCrops,Reason)&&Model->CountMaterial(TEXT("tomato"))==BeforeHarvest+Yield,
        TEXT("competing harvest of same identity cannot pay twice"));
    Check(Reload()&&Shared->Current.PlantingCrops.IsEmpty(),TEXT("shared disk reload does not resurrect harvested crop"));
    const auto Latest=System->NetworkState(Building);World->NextURL=TEXT("127.0.0.1:1");
    Check(Deliver(System,Latest)&&Deliver(Peer,Latest)&&System->Mirror.Plants.IsEmpty()&&Peer->Mirror.Plants.IsEmpty(),TEXT("both mirrors receive final harvested state"));
    auto Older=BeforeFailure;Older.SnapshotSequence=Latest.SnapshotSequence+100;
    Check(Deliver(System,Older)&&System->Mirror.Revision==Latest.Revision,TEXT("older crop revision is rejected even with larger publication sequence"));
    Peer->NetworkEnded();
    Check(Deliver(Peer,Latest)&&Peer->Mirror.Revision==Latest.Revision,TEXT("late/reconnected mirror acquires complete current snapshot"));
    Peer->NetworkEnded();
    Check(Deliver(Peer,BeforeFailure)&&Peer->Mirror.SnapshotSequence==BeforeFailure.SnapshotSequence,TEXT("new connection can accept a restarted server sequence after context reset"));
    auto Invalid=Latest;Invalid.WorldKey.Reset();Check(!System->ApplyNetworkState(World,Invalid),TEXT("invalid world snapshot is rejected"));
    World->NextURL=TEXT("/Engine/Maps/Entry?listen");
    Check(!System->ApplyNetworkState(World,Latest),TEXT("authority cannot adopt a client mirror snapshot"));
    return Failures?1:0;
}