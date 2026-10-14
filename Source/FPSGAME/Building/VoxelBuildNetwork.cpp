#include "VoxelBuildWorld.h"
#include "VoxelBuildPersistence.h"
#include "VoxelBuildRuntime.h"
#include "VoxelBuildPalette.h"
#include "VoxelBuildPrefabActor.h"
#include "VoxelCollapseFragment.h"
#include "../Multiplayer/ColdSteelInventoryRequestTypes.h"
#include "../UI/ColdSteelStatusModel.h"
#include "../FPSGAMECharacter.h"
#include "../Development/DevelopmentTuningSubsystem.h"
#include "Components/DynamicMeshComponent.h"
#include "EngineUtils.h"
#include "GameFramework/PlayerState.h"

bool AVoxelBuildWorld::MakeNetworkSnapshot(TArray<uint8>& Out) const
{return bReady&&VoxelPersistence::Encode(VoxelPersistence::Take(MakeSnapshot()),Out);}

bool AVoxelBuildWorld::ApplyNetworkSnapshot(const TArray<uint8>& Bytes)
{
    auto* Data=VoxelPersistence::Decode(Bytes);if(!Data||Data->CellSizeCm!=20)return false;
    if(!bReady)
    {
        auto* Asset=LoadObject<UVoxelBuildPalette>(nullptr,TEXT("/Game/Building/Voxels/Rounded/DA_VoxelBuildPalette.DA_VoxelBuildPalette"));
        if(!Initialize(Data->WorldKey,Asset))return false;
    }
    if(WorldKey!=Data->WorldKey)return false;
    TArray<FVoxelEditCell> Changed;
    TMap<FIntVector,FName> Incoming;for(const auto& C:Data->Cells)Incoming.Add(C.Position,C.Material);
    for(const auto& E:Cells)if(Incoming.FindRef(E.Key)!=E.Value)Changed.Add({E.Key,E.Value,Incoming.FindRef(E.Key),{}});
    for(const auto& E:Incoming)if(!Cells.Contains(E.Key))Changed.Add({E.Key,NAME_None,E.Value,{}});
    for(const auto& V:FreeVolumes)for(const auto& E:V.Value.Cells)Changed.Add({E.Key,E.Value,NAME_None,V.Key});
    RebuildAffected(Changed);
    Cells=MoveTemp(Incoming);FreeVolumes.Reset();
    for(const auto& V:Data->FreeVolumes){FreeVolumes.Add(V.Id,V);for(const auto& E:V.Cells)Changed.Add({E.Key,NAME_None,E.Value,V.Id});}
    if(HasAuthority())
    {
        for(auto It=PrefabActors.CreateIterator();It;++It)
        {const auto* Desired=Data->Prefabs.FindByPredicate([&](const auto& P){return P.Cell==It.Key();});
         auto* Piece=Cast<AVoxelBuildPrefabActor>(It.Value().Get());
         if(!Desired||!Piece||Piece->PrefabId()!=Desired->Id||Piece->Yaw()!=Desired->Yaw)
         {if(Piece){if(auto* Logic=Piece->Logic())Logic->Destroy();Piece->Destroy();}It.RemoveCurrent();}}
        for(const auto& P:Data->Prefabs)if(!PrefabActors.Contains(P.Cell))SpawnPrefab(P);
    }
    Prefabs=Data->Prefabs;SmeltingJobs=Data->Smelting;Fuels=Data->Fuel;
    CellDamage=Data->Damage;LegacyProtected=Data->LegacyProtected;
    RefreshPrefabOccupancy();
    RefreshSupportGraph();RebuildAffected(Changed);
    PrefabActors.Reset();for(TActorIterator<AVoxelBuildPrefabActor> It(GetWorld());It;++It)
        if(It->GetOwner()==this&&!It->IsFalling())PrefabActors.Add(It->AnchorCell(),*It);
    if(!HasAuthority())
    {
        TSet<FGuid> Wanted;for(const auto& F:Data->Fragments)
        {
            Wanted.Add(F.Id);AVoxelCollapseFragment* Actor=Fragments.FindRef(F.Id);
            if(IsValid(Actor))Actor->UpdateCellDamage(F.Cells);
            else if(!Runtime->PendingFragments.Contains(F.Id))EnqueueFragment(F);
        }
        // Replicated destruction/movement own the live actors; an older bulk snapshot
        // must not destroy a newer replica or teleport its physics back in time.
        for(auto It=Fragments.CreateIterator();It;++It)if(!Wanted.Contains(It.Key())||!IsValid(It.Value()))It.RemoveCurrent();
        for(auto It=Runtime->PendingFragments.CreateIterator();It;++It)if(!Wanted.Contains(It.Key()))It.RemoveCurrent();
    }
    ++Revision;return true;
}

bool AVoxelBuildWorld::ExecuteNetworkEdit(const FColdSteelInventoryRequest& R,UColdSteelStatusModel* M,FString& Reason)
{
    if(!HasAuthority()||!bReady||!M||!M->RuntimePawn())return false;
    if(R.Cells.Num()>4096){Reason=TEXT("单次建造范围过大");return false;}
    TSet<FIntVector> Seen;TArray<FIntVector> UniqueCells;
    for(const auto& Cell:R.Cells)if(!Seen.Contains(Cell)){Seen.Add(Cell);UniqueCells.Add(Cell);}
    APawn* Pawn=M->RuntimePawn();const FVector Eye=Pawn->GetPawnViewLocation();
    const FVector Origin=R.Mode==TEXT("free")?FVector(R.Origin):VolumeOrigin(R.Volume);
    auto Reach=[&](FVector P){return !P.ContainsNaN()&&FVector::DistSquared(Eye,P)<FMath::Square(1800.f);};
    for(const auto& C:UniqueCells)if(!Reach(Origin+CellCenter(C))){Reason=TEXT("建造位置超出范围");return false;}
    if(R.Mode==TEXT("prefab")&&!Reach(CellCenter(R.Anchor)))return false;
    if((R.Mode==TEXT("removePrefab")||R.Mode==TEXT("debris"))&&(!IsValid(R.Target)||!Reach(R.Target->GetActorLocation())))return false;
    auto* HistoryOwner=Pawn->GetPlayerState();if(!HistoryOwner)return false;
    for(auto It=PlayerHistory.CreateIterator();It;++It)if(!It.Key().IsValid())It.RemoveCurrent();
    TGuardValue<TArray<TArray<FVoxelEditCell>>> PersonalUndo(History,PlayerHistory.FindOrAdd(HistoryOwner));
    TMap<FName,int32> Removed;bool Success=false;
    if(R.Mode==TEXT("place")||R.Mode==TEXT("free"))
    {
        if(UniqueCells.IsEmpty()||R.Definition.IsNone()||!Palette->Find(R.Definition))return false;
        const FString Definition=TEXT("voxel_block_")+R.Definition.ToString();
        if(!UDevelopmentTuningSubsystem::IsPlayerOptionEnabled(Pawn,EDevelopmentTuningOption::FreeBuilding)&&!M->ConsumeItem(Definition,UniqueCells.Num(),Reason))return false;
        Success=R.Mode==TEXT("free")?PlaceFree(R.Origin,UniqueCells,R.Definition):EditVolumeCells(R.Volume,UniqueCells,R.Definition);
    }
    else if(R.Mode==TEXT("remove"))
    {
        for(const auto& C:UniqueCells){const FName Mat=VolumeMaterialAt(R.Volume,C);if(!Mat.IsNone())Removed.FindOrAdd(Mat)++;}
        Success=EditVolumeCells(R.Volume,UniqueCells,NAME_None);
    }
    else if(R.Mode==TEXT("undo"))Success=Undo(&Removed);
    else if(R.Mode==TEXT("prefab"))Success=PlacePrefab(R.Definition,R.Anchor,R.Orientation);
    else if(R.Mode==TEXT("removePrefab"))Success=RemovePrefab(R.Target);
    else if(R.Mode==TEXT("debris"))
    {
        if(auto* F=Cast<AVoxelCollapseFragment>(R.Target);F&&F->GetOwner()==this&&!F->IsMoving())
        {for(const auto& C:F->Data().Cells)Removed.FindOrAdd(C.Material)++;RemoveFragment(F);Success=true;}
    }
    Reason=Message;
    // Undo can consume a stale empty batch without changing geometry; persist that cleanup too.
    PlayerHistory.Add(HistoryOwner,History);
    if(!Success)return false;
    for(const auto& E:Removed)
    {
        const FString Definition=TEXT("voxel_block_")+E.Key.ToString();
        if(!M->AddItem(Definition,E.Value))M->GrantWorldBlocks({{Definition,E.Value}},Pawn->GetActorLocation());
    }
    return true;
}
