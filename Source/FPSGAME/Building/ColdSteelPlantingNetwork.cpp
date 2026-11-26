#include "ColdSteelPlantingSystem.h"
#include "VoxelBuildWorld.h"
#include "VoxelBuildPrefabActor.h"
#include "../Multiplayer/ColdSteelSharedInventorySubsystem.h"
#include "../Multiplayer/ColdSteelInventoryRequestTypes.h"
#include "../Multiplayer/ColdSteelPlayerState.h"
#include "../UI/ColdSteelStatusModel.h"
#include "../FPSGAMECharacter.h"
#include "Engine/GameInstance.h"
#include "Engine/World.h"
#include "GameFramework/GameStateBase.h"
#include "GameFramework/PlayerController.h"

const TArray<FColdSteelCropPlant>& UColdSteelPlantingSystem::Plants(const AVoxelBuildWorld* World) const
{
    static const TArray<FColdSteelCropPlant> Empty;
    if(!World)return Empty;
    if(World->GetNetMode()==NM_Standalone){const auto* M=Model();return M?M->PlantingCrops():Empty;}
    if(World->GetNetMode()==NM_Client)
        return MirrorWorld.Get()==World->GetWorld()&&Mirror.WorldKey==World->BuildingWorldKey()&&Mirror.bReady?Mirror.Plants:Empty;
    const auto* Shared=World->GetWorld()->GetSubsystem<UColdSteelSharedInventorySubsystem>();
    return Shared?Shared->Data().PlantingCrops:Empty;
}
int64 UColdSteelPlantingSystem::NowTicks(const AVoxelBuildWorld* World) const
{
    if(!World||World->GetNetMode()!=NM_Client)return FDateTime::UtcNow().GetTicks();
    if(MirrorWorld.Get()!=World->GetWorld()||!Mirror.bReady)return 0;
    if(ObservedClockWorld.Get()==World->GetWorld()&&ObservedUtcTicks>0)
        return ObservedUtcTicks+int64(FMath::Max(0.,FPlatformTime::Seconds()-ObservedUtcAt)*ETimespan::TicksPerSecond);
    double Elapsed=FMath::Max(0.,FPlatformTime::Seconds()-MirrorReceivedAt);
    if(const auto* State=World->GetWorld()->GetGameState())
        Elapsed=FMath::Max(0.,State->GetServerWorldTimeSeconds()-Mirror.ServerAnchorSeconds);
    return Mirror.UtcAnchorTicks+int64(Elapsed*ETimespan::TicksPerSecond);
}
void UColdSteelPlantingSystem::ObserveServerClock(UWorld* Context,int64 Ticks)
{
    if(!Context||Context->GetNetMode()!=NM_Client||Ticks<=0)return;
    ObservedClockWorld=Context;ObservedUtcTicks=Ticks;ObservedUtcAt=FPlatformTime::Seconds();
}
void UColdSteelPlantingSystem::NetworkEnded()
{
    EndNetworkContext();Mirror={};MirrorWorld.Reset();ObservedClockWorld.Reset();ObservedUtcTicks=0;bVisualDirty=true;
}
FColdSteelPlantingNetState UColdSteelPlantingSystem::NetworkState(AVoxelBuildWorld* World)
{
    FColdSteelPlantingNetState State;
    if(!World||World->GetNetMode()==NM_Client||World->GetNetMode()==NM_Standalone)return State;
    auto* Shared=World->GetWorld()->GetSubsystem<UColdSteelSharedInventorySubsystem>();if(!Shared)return State;
    if(ClockWorld.Get()!=World->GetWorld())
    {ClockWorld=World->GetWorld();ClockUtcTicks=FDateTime::UtcNow().GetTicks();ClockServerSeconds=World->GetWorld()->GetTimeSeconds();PublishedSnapshotSequence=0;}
    State.WorldKey=World->BuildingWorldKey();State.Revision=Shared->Data().PlantingRevision;
    State.SnapshotSequence=++PublishedSnapshotSequence;
    State.bReady=Shared->Data().PlantingSeededWorlds.Contains(State.WorldKey);State.bSaveBlocked=Shared->IsPlantingSaveBlocked();
    for(const auto& Plant:Shared->Data().PlantingCrops)if(Plant.WorldKey==State.WorldKey)State.Plants.Add(Plant);
    State.UtcAnchorTicks=ClockUtcTicks;State.ServerAnchorSeconds=ClockServerSeconds;return State;
}
bool UColdSteelPlantingSystem::ApplyNetworkState(UWorld* Context,const FColdSteelPlantingNetState& State)
{
    if(!Context||Context->GetNetMode()!=NM_Client||State.WorldKey.IsEmpty()||State.Revision<0||State.Plants.Num()>4096)return false;
    // World chunks and inventory replies can finish in a different order. A
    // failed save does not advance PlantingRevision, but its lock must still win
    // over a previously captured unlocked view (and vice versa after recovery).
    if(MirrorWorld.Get()==Context&&Mirror.WorldKey==State.WorldKey
        &&(State.Revision<Mirror.Revision
            ||(State.Revision==Mirror.Revision&&State.SnapshotSequence<=Mirror.SnapshotSequence)))return true;
    MirrorWorld=Context;Mirror=State;MirrorReceivedAt=FPlatformTime::Seconds();bVisualDirty=true;++ChangeSerial;return true;
}
bool UColdSteelPlantingSystem::PrepareNetwork(AVoxelBuildWorld* World,const FColdSteelInventoryRequest& Request,UColdSteelStatusModel* Operator,
    FColdSteelProfile& Profile,TArray<FColdSteelCropPlant>& After,FString& Reason) const
{
    auto* Piece=Bed(World,Request.Anchor);auto* Pawn=Operator?Operator->RuntimePawn():nullptr;
    auto* PC=Pawn?Cast<APlayerController>(Pawn->GetController()):nullptr;
    if(!World||World->GetNetMode()==NM_Client||World->GetNetMode()==NM_Standalone||!World->HasAuthority()||!World->IsReady()
        ||!Piece||Piece!=Request.Target||!Request.PlantingBedId.IsValid()||World->PrefabInstanceIdentity(Request.Anchor)!=Request.PlantingBedId
        ||!PC||PC->GetPawn()!=Request.Pawn||!PC->LineOfSightTo(Piece))
    {Reason=TEXT("种植地已替换、不可见或操作身份无效");return false;}
    const bool Harvest=Request.Mode==TEXT("planting.harvest");
    if((!Harvest&&Request.Mode!=TEXT("planting.plant"))||Harvest!=Request.ExpectedPlantId.IsValid()
        ||Request.Definition.ToString().Len()>32||Request.PlantingSlots.Num()>16
        ||(Harvest&&!Request.PlantingSlots.IsEmpty())
        ||(!Request.PlantingSlots.IsEmpty()&&Request.Cell!=Request.PlantingSlots[0]))
    {Reason=TEXT("种植请求无效");return false;}
    const auto* Existing=Occupant(World,Request.Anchor,Request.Cell);
    if(Harvest?(!Existing||Existing->PlantId!=Request.ExpectedPlantId):Existing!=nullptr)
    {Reason=TEXT("地块或植株已被其他玩家更新，请重新选择");return false;}
    if(!Harvest&&!Request.PlantingSlots.IsEmpty())
        return PrepareSelection(World,Request.Anchor,Request.PlantingSlots,Request.Definition,Operator,Profile,After,Reason);
    return Prepare(World,Request.Anchor,Request.Cell,Request.Definition,Profile,Reason,false,Operator,&After);
}
bool UColdSteelPlantingSystem::RequestNetwork(AVoxelBuildWorld* World,FIntVector Cell,int32 Slot,FName Crop,const FGuid& Expected,FString& Reason,const TArray<int32>& Slots)
{
    auto* PC=World?World->GetWorld()->GetFirstPlayerController():nullptr;
    if(bNetworkPending&&(!World||RequestWorld.Get()!=World->GetWorld()||!RequestPawn.IsValid()||!PC||PC->GetPawn()!=RequestPawn.Get()))EndNetworkContext();
    auto* State=PC?PC->GetPlayerState<AColdSteelPlayerState>():nullptr;auto* Piece=Bed(World,Cell);
    if(!PC||!PC->IsLocalController()||!State||!Piece||bNetworkPending)
    {Reason=TEXT("种植请求仍在同步或交互已失效");return false;}
    FColdSteelInventoryRequest Request;Request.Action=EColdSteelInventoryAction::Planting;
    Request.Mode=Expected.IsValid()?TEXT("planting.harvest"):TEXT("planting.plant");
    Request.Target=Piece;Request.Anchor=Cell;Request.Cell=Slot;Request.Definition=Crop;
    Request.PlantingBedId=World->PrefabInstanceIdentity(Cell);Request.ExpectedPlantId=Expected;Request.PlantingSlots=Slots;
    RequestWorld=World->GetWorld();RequestPawn=PC->GetPawn();RequestBed=Piece;RequestBedId=Request.PlantingBedId;
    bNetworkPending=true;bNetworkFailed=false;Notice=TEXT("正在等待服务端种植结果…");++ChangeSerial;
    if(!State->RequestInventoryAction(Request))
    {bNetworkPending=false;bNetworkFailed=true;Notice=TEXT("库存或房间正在同步，请稍后重试");++ChangeSerial;Reason=Notice;return false;}
    Reason=Notice;return true;
}
void UColdSteelPlantingSystem::NetworkFinished(const FColdSteelInventoryRequest& Request,bool Success,const FString& Reason,APawn* Pawn)
{
    if(!bNetworkPending||Request.Action!=EColdSteelInventoryAction::Planting||Request.PlantingBedId!=RequestBedId
        ||(RequestBed.IsValid()&&Request.Target!=RequestBed.Get()))return;
    const auto* PC=GetGameInstance()->GetFirstLocalPlayerController();
    const bool SamePawn=Pawn&&Pawn==RequestPawn.Get()&&PC&&PC->GetPawn()==Pawn&&Pawn->GetWorld()==RequestWorld.Get();
    bNetworkPending=false;bNetworkFailed=!Success;
    Notice=SamePawn?Reason:FString();RequestPawn.Reset();RequestBed.Reset();RequestWorld.Reset();++ChangeSerial;
}
void UColdSteelPlantingSystem::EndNetworkContext()
{
    bNetworkPending=false;bNetworkFailed=false;RequestPawn.Reset();RequestBed.Reset();RequestWorld.Reset();RequestBedId.Invalidate();Notice.Reset();++ChangeSerial;
}
