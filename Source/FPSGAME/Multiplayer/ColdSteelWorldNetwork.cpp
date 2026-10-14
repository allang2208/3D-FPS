#include "ColdSteelPlayerState.h"
#include "../Building/ColdSteelDoor.h"
#include "../UI/ColdSteelSceneContainer.h"
#include "../Dungeons/AuthoredDungeonGenerator.h"
#include "../Dungeons/WardBreakableGlass.h"
#include "ColdSteelWorldSnapshot.h"
#include "ColdSteelSharedInventorySubsystem.h"
#include "ColdSteelProfileTransfer.h"
#include "../Building/VoxelBuildWorld.h"
#include "../Dungeons/DungeonRunSubsystem.h"
#include "Engine/World.h"
#include "Engine/NetConnection.h"
#include "EngineUtils.h"
#include "GameFramework/PlayerController.h"
#include "Kismet/GameplayStatics.h"

void AColdSteelPlayerState::EnsureWorldStreamContext()
{
    if(WorldStreamWorld.Get()==GetWorld())return;
    WorldStreamWorld=GetWorld();
    WorldOutgoing.Reset();WorldIncoming.Reset();WorldLastSent.Reset();
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
        for(TActorIterator<AVoxelBuildWorld> It(GetWorld());It;++It)if(It->IsReady())
        {
            if((LastBuildingSentWorld.Get()!=*It||LastBuildingSentRevision!=It->NetworkRevision)&&It->MakeNetworkSnapshot(State->Building))BuildingSent=*It;
            break;
        }
        if(auto* Run=UDungeonRunSubsystem::Get(GetWorld())){Run->EnsurePlayerRun(ShadowModel);Run->FillNetworkState(State);}
        TArray<uint8> Blob;if(ColdSteelProfileTransfer::SaveToBlob(State,Blob)&&(BuildingSent||Blob!=WorldLastSent))
        {
            WorldOutgoing=MoveTemp(Blob);WorldChunk=0;++WorldSerial;
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
    if(++WorldChunk==Total){WorldLastSent=MoveTemp(WorldOutgoing);WorldOutgoing.Reset();}
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
    // Do not consume a one-shot snapshot while deterministic actors are still assembling.
    for(TActorIterator<AAuthoredDungeonGenerator> It(GetWorld());It;++It)
        if(It->IsPreparationPending())return false;
    if(!PendingWorldState->Building.IsEmpty())
    {bool Applied=false;for(TActorIterator<AVoxelBuildWorld> It(GetWorld());It;++It){Applied=It->ApplyNetworkSnapshot(PendingWorldState->Building);break;}if(!Applied)return false;PendingWorldState->Building.Reset();}
    auto* Run=UDungeonRunSubsystem::Get(GetWorld());
    if(!PendingWorldState->RunId.IsEmpty()&&(!Run||Run->RunId()!=PendingWorldState->RunId))return false;
    const bool SceneApplied=Run&&Run->ApplyNetworkState(PendingWorldState);
    if(!bWorldHarvestApplied)
        if(auto* Shared=GetWorld()->GetSubsystem<UColdSteelSharedInventorySubsystem>())
        {Shared->ApplyHarvestMirror(PendingWorldState->Harvest,PendingWorldState->HarvestRemovals);bWorldHarvestApplied=true;}
    if(!SceneApplied)return false;
    PendingWorldState=nullptr;return true;
}

void AColdSteelPlayerState::ClientGeneratedDoorSwing_Implementation(const FString& ActorName,const FColdSteelDoorNetState& State)
{
    if(GetNetMode()!=NM_Client)return;
    for(TActorIterator<AColdSteelDoor> It(GetWorld());It;++It)
        if(It->GetName()==ActorName){It->ApplyNetworkSwing(State,true);break;}
    // A door still being assembled catches up from the periodic world snapshot.
}

void AColdSteelPlayerState::ClientGeneratedContainerOpened_Implementation(const FString& ActorName)
{
    if(GetNetMode()!=NM_Client)return;
    for(TActorIterator<AColdSteelSceneContainer> It(GetWorld());It;++It)
        if(It->GetName()==ActorName){It->OpenSharedVisual();break;}
}

void AColdSteelPlayerState::ClientGlassBroken_Implementation(const FString& ActorName,FVector_NetQuantize Point,FVector_NetQuantizeNormal Direction)
{
    if(GetNetMode()!=NM_Client)return;
    for(TActorIterator<AActor> It(GetWorld());It;++It)if(It->GetName()==ActorName)
    {
        if(auto* G=It->FindComponentByClass<UWardBreakableGlass>();G&&!G->bBroken)
        {G->BreakPoint=Point;G->BreakDirection=Direction;G->bBroken=true;G->OnRep_Broken();}
        break;
    }
}
