#include "ColdSteelPlayerState.h"
#include "../Building/ColdSteelDoor.h"
#include "../UI/ColdSteelSceneContainer.h"
#include "../Dungeons/AuthoredDungeonGenerator.h"
#include "../Dungeons/WardBreakableGlass.h"
#include "ColdSteelWorldSnapshot.h"
#include "../WorldGeneration/ForestVillageMap.h"
#include "../WorldGeneration/TemperateHillsWorld.h"
#include "ColdSteelSharedInventorySubsystem.h"
#include "ColdSteelProfileTransfer.h"
#include "../Building/VoxelBuildWorld.h"
#include "../Building/ColdSteelPlantingSystem.h"
#include "../Dungeons/DungeonRunSubsystem.h"
#include "../Dungeons/DungeonRoomSubsystem.h"
#include "Engine/World.h"
#include "Engine/NetConnection.h"
#include "Misc/CommandLine.h"
#include "Misc/Parse.h"
#include "EngineUtils.h"
#include "GameFramework/PlayerController.h"
#include "Kismet/GameplayStatics.h"

void AColdSteelPlayerState::EnsureWorldStreamContext()
{
    if(WorldStreamWorld.Get()==GetWorld())return;
    WorldStreamWorld=GetWorld();
    PlantingClockPublishAt=0.;
    WorldOutgoing.Reset();WorldIncoming.Reset();WorldLastSent.Reset();
    LastDungeonLayoutSentRunId.Reset();
    PendingWorldState=nullptr;LastBuildingSentWorld.Reset();LastBuildingSentRevision=0;
    WorldChunk=WorldReceiveTotal=0;WorldSendAt=WorldSnapshotAt=WorldApplyAt=0.;bWorldHarvestApplied=false;
}

void AColdSteelPlayerState::TickWorldNetwork(float Delta)
{
    EnsureWorldStreamContext();
    auto* PC=Cast<APlayerController>(GetOwner());if(!PC)return;
    if(!HasAuthority()){ApplyWorldState();return;}
    // Exactly one authority controller drives the shared clock, including
    // dedicated servers where no controller is local.
    if(PC==GetWorld()->GetFirstPlayerController())
        if(auto* Shared=GetWorld()->GetSubsystem<UColdSteelSharedInventorySubsystem>())Shared->AdvanceHarvest(Delta);
    if(PC->IsLocalController())return;
    // Small owner-only UTC sample advances by local monotonic elapsed time on
    // clients. Pauses/time dilation/local wall-clock changes cannot alter crop age.
    if(GetWorld()->GetRealTimeSeconds()>=PlantingClockPublishAt)
    {PlantingUtcTicks=FDateTime::UtcNow().GetTicks();PlantingClockPublishAt=GetWorld()->GetRealTimeSeconds()+2.;}
    // Inventory receipts and the profile stream take priority over bulk geometry.
    if(!InventoryReplyOutgoing.IsEmpty())return;
    auto* Connection=PC->GetNetConnection();if(!Connection||!Connection->IsNetReady())return;
    const double Now=GetWorld()->GetRealTimeSeconds();
    if(WorldOutgoing.IsEmpty()&&Now>=WorldSnapshotAt)
    {
        WorldSnapshotAt=Now+2.;auto* State=NewObject<UColdSteelWorldSnapshot>();
        State->Map=UGameplayStatics::GetCurrentLevelName(this,true);
        AVoxelBuildWorld* BuildingSent=nullptr;
        if(auto* Shared=GetWorld()->GetSubsystem<UColdSteelSharedInventorySubsystem>();Shared&&Shared->InitializeAuthority()){State->Harvest=Shared->Data().Harvest;State->HarvestRemovals=Shared->Data().HarvestRemovals;}
        if (ForestVillageMap::Is(GetWorld())) State->Harvest.TreeGrowthDay=0.;
        for(TActorIterator<AVoxelBuildWorld> It(GetWorld());It;++It)if(It->IsReady())
        {
            if(auto* Planting=GetGameInstance()->GetSubsystem<UColdSteelPlantingSystem>())State->Planting=Planting->NetworkState(*It);
            if((LastBuildingSentWorld.Get()!=*It||LastBuildingSentRevision!=It->NetworkRevision)&&It->MakeNetworkSnapshot(State->Building))BuildingSent=*It;
            break;
        }
        if(auto* Run=UDungeonRunSubsystem::Get(GetWorld())){if(!UDungeonRoomSubsystem::Supports(GetWorld())||bInDungeonRoom)Run->EnsurePlayerRun(ShadowModel);Run->FillNetworkState(State);}
        for(TActorIterator<AAuthoredDungeonGenerator> It(GetWorld());It;++It)
            if(!It->IsPreparationPending()&&It->ActorHasTag(TEXT("DungeonAssembly.Ready"))
                &&!It->NetworkRunId.IsEmpty()&&It->NetworkRunId!=LastDungeonLayoutSentRunId)
            {
                State->DungeonLayoutRunId=It->NetworkRunId;State->DungeonLayoutSeed=It->GeneratedSeed;
                const FString& Layout=It->LayoutManifestJson;
                for(int32 Offset=0;Offset<Layout.Len();Offset+=32768)State->DungeonLayoutParts.Add(Layout.Mid(Offset,32768));
                break;
            }
        // Planting uses a fresh ordering token for each observation, including polls with
        // identical contents. Keep the token on the wire, outside the forest change key.
        const auto Sequence=State->Planting.SnapshotSequence;
        const bool Forest=ForestVillageMap::Is(GetWorld());
        if(Forest) State->Planting.SnapshotSequence=0;
        TArray<uint8> Blob;
        const bool Encoded=ColdSteelProfileTransfer::SaveToBlob(State,Blob);
        const bool Send=Encoded && (BuildingSent || Blob!=WorldLastSent);
#if !UE_BUILD_SHIPPING
        static const bool TraceForestTransport=FParse::Param(FCommandLine::Get(),TEXT("HillsSceneryNetworkProbe"));
        if(TraceForestTransport && ForestVillageMap::Is(GetWorld()) && Encoded)
            UE_LOG(LogTemp,Display,TEXT("FOREST_WORLD_PAYLOAD enqueue=%d compressed_bytes=%d"),Send,Blob.Num());
#endif
        if(Send)
        {
            if (Forest)
            {
                State->Planting.SnapshotSequence=Sequence;
                if(!ColdSteelProfileTransfer::SaveToBlob(State,WorldOutgoing))return;
                WorldLastSent=MoveTemp(Blob);
            }
            else WorldOutgoing=MoveTemp(Blob);WorldChunk=0;++WorldSerial;
            if(!State->DungeonLayoutParts.IsEmpty())LastDungeonLayoutSentRunId=State->DungeonLayoutRunId;
            // Failed serialization leaves the revision dirty for the next attempt.
            if(BuildingSent){LastBuildingSentWorld=BuildingSent;LastBuildingSentRevision=BuildingSent->NetworkRevision;}
        }
    }
    if(WorldOutgoing.IsEmpty())return;
    const double Rate=FMath::Min(8192.,double(Connection->CurrentNetSpeed)*.1);
    if(Rate<=0||Now<WorldSendAt)return;
    const int32 Total=FMath::DivideAndRoundUp(WorldOutgoing.Num(),1024),Offset=WorldChunk*1024;
    TArray<uint8> Bytes;Bytes.Append(WorldOutgoing.GetData()+Offset,FMath::Min(1024,WorldOutgoing.Num()-Offset));
    ClientWorldChunk(WorldSerial,WorldChunk,Total,Bytes);WorldSendAt=Now+1280./Rate;
    if(++WorldChunk==Total)
    {
        if(!ForestVillageMap::Is(GetWorld()))WorldLastSent=MoveTemp(WorldOutgoing);
        WorldOutgoing.Reset();
    }
}
void AColdSteelPlayerState::OnRep_PlantingClock()
{
    const auto* PC=Cast<APlayerController>(GetOwner());
    if(PC&&PC->IsLocalController()&&!HasAuthority())
        if(auto* Planting=GetGameInstance()->GetSubsystem<UColdSteelPlantingSystem>())Planting->ObserveServerClock(GetWorld(),PlantingUtcTicks);
}
void AColdSteelPlayerState::ClientWorldChunk_Implementation(int32 Serial,int32 Index,int32 Total,const TArray<uint8>& Bytes)
{
    EnsureWorldStreamContext();
    if(Total<=0||Total>ColdSteelProfileTransfer::MaxChunks||Index<0||Index>=Total||Bytes.Num()<=0||Bytes.Num()>1024)return;
    if(Index==0){WorldReceiveSerial=Serial;WorldReceiveTotal=Total;WorldIncoming.Reset();}
    if(Serial!=WorldReceiveSerial||Total!=WorldReceiveTotal||WorldIncoming.Num()!=Index*1024)return;
    WorldIncoming.Append(Bytes);if(Index+1!=Total)return;
    auto* State=NewObject<UColdSteelWorldSnapshot>();
    if(ColdSteelProfileTransfer::BlobToSaveObject(WorldIncoming,State)&&State->Map==UGameplayStatics::GetCurrentLevelName(this,true))
    {
        if(PendingWorldState&&PendingWorldState->Map==State->Map&&!PendingWorldState->Building.IsEmpty()&&State->Building.IsEmpty())State->Building=MoveTemp(PendingWorldState->Building);
        if(PendingWorldState&&PendingWorldState->Map==State->Map&&State->DungeonLayoutParts.IsEmpty()
            &&State->RunId==PendingWorldState->DungeonLayoutRunId)
        {
            State->DungeonLayoutRunId=PendingWorldState->DungeonLayoutRunId;
            State->DungeonLayoutSeed=PendingWorldState->DungeonLayoutSeed;
            State->DungeonLayoutParts=MoveTemp(PendingWorldState->DungeonLayoutParts);
        }
        PendingWorldState=State;WorldApplyAt=0.;bWorldHarvestApplied=false;ApplyWorldState();
    }
    WorldIncoming.Reset();
}

bool AColdSteelPlayerState::ApplyWorldState()
{
    if(!PendingWorldState)return true;
    const double Now=GetWorld()->GetRealTimeSeconds();
    if(Now<WorldApplyAt)return false;
    WorldApplyAt=Now+.2;
    if(PendingWorldState->Map!=UGameplayStatics::GetCurrentLevelName(this,true)){PendingWorldState=nullptr;return true;}
    if(!bWorldHarvestApplied)
        if(auto* Shared=GetWorld()->GetSubsystem<UColdSteelSharedInventorySubsystem>())
        {
            if(ForestVillageMap::Is(GetWorld()))
            {
                TActorIterator<ATemperateHillsWorld> H(GetWorld());
                if(!H || H->ForestGrowthDay<0.) return false;
                PendingWorldState->Harvest.TreeGrowthDay=H->ForestGrowthDay;
            }
            Shared->ApplyHarvestMirror(PendingWorldState->Harvest,PendingWorldState->HarvestRemovals);bWorldHarvestApplied=true;
        }
    // The layout must be consumed BEFORE waiting for local assembly. Waiting
    // first would deadlock clients which are correctly waiting for this stream.
    if(!PendingWorldState->DungeonLayoutParts.IsEmpty())
    {
        bool Accepted=false;
        for(TActorIterator<AAuthoredDungeonGenerator> It(GetWorld());It;++It)
            if(It->AcceptNetworkLayout(PendingWorldState->DungeonLayoutRunId,PendingWorldState->DungeonLayoutSeed,PendingWorldState->DungeonLayoutParts))
            {Accepted=true;break;}
        if(!Accepted)return false;
        PendingWorldState->DungeonLayoutParts.Reset();
    }
    // Do not consume a one-shot snapshot while deterministic actors are still assembling.
    for(TActorIterator<AAuthoredDungeonGenerator> It(GetWorld());It;++It)
        if(It->IsPreparationPending())return false;
    if(!PendingWorldState->Building.IsEmpty())
    {bool Applied=false;for(TActorIterator<AVoxelBuildWorld> It(GetWorld());It;++It){Applied=It->ApplyNetworkSnapshot(PendingWorldState->Building);break;}if(!Applied)return false;PendingWorldState->Building.Reset();}
    if(!PendingWorldState->Planting.WorldKey.IsEmpty())
    {
        if(auto* Planting=GetGameInstance()->GetSubsystem<UColdSteelPlantingSystem>())
            if(!Planting->ApplyNetworkState(GetWorld(),PendingWorldState->Planting))return false;
        PendingWorldState->Planting={};
    }
    auto* Run=UDungeonRunSubsystem::Get(GetWorld());
    if(!PendingWorldState->RunId.IsEmpty()&&(!Run||Run->RunId()!=PendingWorldState->RunId))return false;
    const bool SceneApplied=Run&&Run->ApplyNetworkState(PendingWorldState);
    if(!SceneApplied)return false;
    PendingWorldState=nullptr;return true;
}

void AColdSteelPlayerState::ClientGeneratedDoorSwing_Implementation(const FString& ActorName,const FColdSteelDoorNetState& State)
{
    if(GetNetMode()!=NM_Client)return;
    for(TActorIterator<AColdSteelDoor> It(GetWorld());It;++It)
        if(UDungeonRoomSubsystem::SceneActorKey(*It)==ActorName){It->ApplyNetworkSwing(State,true);break;}
    // A door still being assembled catches up from the periodic world snapshot.
}

void AColdSteelPlayerState::ClientGeneratedContainerOpened_Implementation(const FString& ActorName)
{
    if(GetNetMode()!=NM_Client)return;
    for(TActorIterator<AColdSteelSceneContainer> It(GetWorld());It;++It)
        if(UDungeonRoomSubsystem::SceneActorKey(*It)==ActorName){It->OpenSharedVisual();break;}
}

void AColdSteelPlayerState::ClientGlassBroken_Implementation(const FString& ActorName,FVector_NetQuantize Point,FVector_NetQuantizeNormal Direction)
{
    if(GetNetMode()!=NM_Client)return;
    for(TActorIterator<AActor> It(GetWorld());It;++It)if(UDungeonRoomSubsystem::SceneActorKey(*It)==ActorName)
    {
        if(auto* G=It->FindComponentByClass<UWardBreakableGlass>();G&&!G->bBroken)
        {G->BreakPoint=Point;G->BreakDirection=Direction;G->bBroken=true;G->OnRep_Broken();}
        break;
    }
}
