#include "VoxelBuildWorld.h"
#include "../Dungeons/DungeonRoomSubsystem.h"
#include "VoxelBuildPersistence.h"
#include "VoxelBuildRuntime.h"
#include "VoxelBuildPalette.h"
#include "VoxelBuildPrefabActor.h"
#include "VillageBuildDefense.h"
#include "VillageGateReplacement.h"
#include "../WorldGeneration/TemperateHillsWorld.h"
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
    // 楔形切割整表替换（与 Cells 同口径；形状只会随放置产生，材质不变形状变的差分不存在）。
    // 形状差异也要进 Changed 触发重网格——差分条目只喂 RebuildAffected（读 Position/Volume）。
    for(const auto& E:Data->CellShapes)
        if(CellShapes.FindRef(E.Key)!=E.Value)Changed.Add({E.Key,NAME_None,NAME_None,{}});
    for(const auto& E:CellShapes)
        if(!Data->CellShapes.Contains(E.Key))Changed.Add({E.Key,NAME_None,NAME_None,{}});
    RebuildAffected(Changed);
    Cells=MoveTemp(Incoming);CellShapes=Data->CellShapes;FreeVolumes.Reset();
    for(const auto& V:Data->FreeVolumes){FreeVolumes.Add(V.Id,V);for(const auto& E:V.Cells)Changed.Add({E.Key,NAME_None,E.Value,V.Id});}
    if(HasAuthority())
    {
        for(auto It=PrefabActors.CreateIterator();It;++It)
        {const auto* Desired=Data->Prefabs.FindByPredicate([&](const auto& P){return P.Cell==It.Key();});
         auto* Piece=Cast<AVoxelBuildPrefabActor>(It.Value().Get());
         if(!Desired||!Piece||Piece->PrefabId()!=Desired->Id||Piece->Yaw()!=Desired->Yaw||
             (VillageBuildDefense::IsVillageRecipe(Desired->Id)&&PrefabInstanceIdentity(It.Key())!=Desired->InstanceId)||
             (VillageBuildDefense::IsVillageRecipe(Desired->Id)&&!Piece->GetActorTransform().Equals(VillageWallStairs::Placement(*Desired))))
         {if(Piece){if(auto* Logic=Piece->Logic())Logic->Destroy();Piece->Destroy();}It.RemoveCurrent();}}
        for(const auto& P:Data->Prefabs)if(!PrefabActors.Contains(P.Cell))SpawnPrefab(P);
    }
    bWorkshopTowerGranted=Data->bWorkshopTowerGranted;
    Prefabs=Data->Prefabs;SmeltingJobs=Data->Smelting;Fuels=Data->Fuel;
    CellDamage=Data->Damage;LegacyProtected=Data->LegacyProtected;
    // 自由体积整表替换后重建世界格反查表（2026-10-13 中危#3，与 Initialize 同口径）。
    FreeVolumeWorldCells.Reset();
    for(const auto& V:FreeVolumes)for(const auto& E:V.Value.Cells)
        FreeVolumeWorldCells.Add(ToCell(V.Value.Origin+CellMin(E.Key)));
    // 2026-10-13 联机审计 B1：快照应用（含服务端失败回滚）整图重建——丢弃在飞的应力解算
    // 与半途收集。否则结果按回滚前的图落地：Supported/LoadRatios 写进野键，Detached 会给
    // 已回滚掉的格生成幽灵残骸。（NodeEpoch 不随回滚变化，既有 stale 检测拦不住这条路。）
    if(Runtime->Stress.IsValid())Runtime->Stress=TFuture<FVoxelStressResult>();
    Runtime->JobKeys.Reset();Runtime->JobEpoch.Reset();Runtime->DirtySupport.Reset();
    Runtime->GatherQueue.Reset();Runtime->GatherSeen.Reset();Runtime->GatherHops.Reset();Runtime->Gather={};
    // 2026-10-13 联机审计 B1：快照里的断键必须随图重建继承。该函数不只服务客户端——
    // 服务端在请求失败回滚（ColdSteelHarvestAuthority WorldAction）与恢复回灌
    // （RestoreBuilding）时也会把快照应用回自己，丢断键会污染权威图并把断键写丢进存档。
    // The authority already reconciled player-built actors above. A village station
    // has the same owner, but a rollback must never destroy it as a removed prefab.
    if(!HasAuthority())
    {
        PrefabActors.Reset();
        for(TActorIterator<AVoxelBuildPrefabActor> It(GetWorld());It;++It)
            if(It->GetOwner()==this&&!It->IsSceneStation()&&!It->PrefabId().IsNone()&&!It->IsFalling())
                PrefabActors.Add(It->AnchorCell(),*It);
    }
    RefreshPrefabOccupancy();
    RefreshSupportGraph(&Data->BrokenBonds);RebuildAffected(Changed);
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
    if(UDungeonRoomSubsystem::IsDungeonPawn(M->RuntimePawn())){Reason=TEXT("地牢内不能建造");return false;}
    if(R.Cells.Num()>4096){Reason=TEXT("单次建造范围过大");return false;}
    TSet<FIntVector> Seen;TArray<FIntVector> UniqueCells;
    for(const auto& Cell:R.Cells)if(!Seen.Contains(Cell)){Seen.Add(Cell);UniqueCells.Add(Cell);}
    APawn* Pawn=M->RuntimePawn();const FVector Eye=Pawn->GetPawnViewLocation();
    const FVector Origin=R.Mode==TEXT("free")?FVector(R.Origin):VolumeOrigin(R.Volume);
    auto Reach=[&](FVector P){return !P.ContainsNaN()&&FVector::DistSquared(Eye,P)<FMath::Square(1800.f);};
    for(const auto& C:UniqueCells)if(!Reach(Origin+CellCenter(C))){Reason=TEXT("建造位置超出范围");return false;}
    const bool bWallDock=R.Mode==TEXT("wallDockPrefab");
    const bool bGroundDefense=R.Mode==TEXT("groundDefensePrefab");
    const bool bReplaceWall=R.Mode==TEXT("replaceWallGate");
    const bool bPlacePrefab=bReplaceWall||bWallDock||bGroundDefense||R.Mode==TEXT("prefab");
    if(bWallDock&&(!IsValid(R.Target.Get())||R.Target->GetWorld()!=GetWorld()||!VillageWallStairs::CanDock(R.Definition)))
    {Reason=TEXT("该城防接口已失效，请重新瞄准");return false;}
    FIntVector Anchor=R.Anchor;
    int32 Yaw=R.Orientation;
    if(bReplaceWall)
    {
        const auto* Definition=Palette->FindComponent(R.Definition);
        FTransform Pose;
        if(!Definition || R.Count<0 || R.Count>MAX_uint32 || R.Cell!=VillageGateReplacement::ReplacementSocket || !IsValid(R.Target.Get()) ||
            R.Target->GetWorld()!=GetWorld() || !VillageGateReplacement::Layout(R.Definition,R.Target.Get(),Definition->Footprint,Pose,Anchor,Yaw))
        {Reason=TEXT("目标墙段已变化，请重新瞄准");return false;}
    }
    if(bWallDock&&R.Cell!=INDEX_NONE)
    {
        // A quantized replica can put the same socket on the other side of a 20 cm cell edge.
        const auto* Definition=Palette->FindComponent(R.Definition);
        VillageWallStairs::FDock Dock;
        if(!Definition||!VillageWallStairs::MakeDockAtSocket(R.Definition,Definition->Footprint,R.Target.Get(),R.Cell,Dock))
        {Reason=TEXT("该城防接口已失效，请重新瞄准");return false;}
        Anchor=Dock.Anchor;
        Yaw=Dock.Yaw;
    }
    if(bPlacePrefab)
    {
        const FVector Point=CellCenter(Anchor);
        const bool InRange=VillageBuildDefense::IsVillageRecipe(R.Definition)?VillageBuildDefense::InSurveyRange(Eye,Point):Reach(Point);
        if(Yaw<0||Yaw>(bGroundDefense?359:3)||!InRange){Reason=TEXT("建造位置或方向超出范围");return false;}
    }
    if(R.Mode==TEXT("removePrefab")||R.Mode==TEXT("debris"))
    {
        if(!IsValid(R.Target))return false;
        const auto* Piece=Cast<AVoxelBuildPrefabActor>(R.Target.Get());
        const bool IsVillagePiece=R.Mode==TEXT("removePrefab")&&Piece&&Piece->GetOwner()==this&&VillageBuildDefense::IsVillageRecipe(Piece->PrefabId());
        const FVector Point=R.Target->GetActorLocation();
        if(IsVillagePiece && !Reach(Point))
        {
            const auto* Hills=FindVillageConstructionWorld();
            if(!Hills||!Hills->IsVillageWallRepaired()||!VillageBuildDefense::InSurveyRange(Eye,Point))
            {Reason=TEXT("超出村庄施工范围");return false;}
        }
        else if(!Reach(Point))return false;
    }
    auto* HistoryOwner=Pawn->GetPlayerState();if(!HistoryOwner)return false;
    UndoHistory.ForgetDisconnected();
    TGuardValue<APlayerState*> EditingPlayer(UndoPlayer,HistoryOwner);
    TMap<FName,int32> Removed;bool Success=false;
    if(R.Mode==TEXT("place")||R.Mode==TEXT("free"))
    {
        if(UniqueCells.IsEmpty()||R.Definition.IsNone()||!Palette->Find(R.Definition))return false;
        const FString Definition=TEXT("voxel_block_")+R.Definition.ToString();
        if(!UDevelopmentTuningSubsystem::IsPlayerOptionEnabled(Pawn,EDevelopmentTuningOption::FreeBuilding)&&!M->ConsumeItem(Definition,UniqueCells.Num(),Reason))return false;
        if(R.Mode==TEXT("free"))Success=PlaceFree(R.Origin,UniqueCells,R.Definition);
        // 2026-10-17：事务带切割时走带形状的重放（UniqueCells 保持请求序，与 CellShapes 对齐）。
        else if(!R.Volume.IsValid()&&!R.CellShapes.IsEmpty())Success=EditCellsShaped(UniqueCells,R.Definition,R.CellShapes);
        else Success=EditVolumeCells(R.Volume,UniqueCells,R.Definition);
    }
    else if(R.Mode==TEXT("remove"))
    {
        for(const auto& C:UniqueCells){const FName Mat=VolumeMaterialAt(R.Volume,C);if(!Mat.IsNone())Removed.FindOrAdd(Mat)++;}
        Success=EditVolumeCells(R.Volume,UniqueCells,NAME_None);
    }
    else if(R.Mode==TEXT("undo"))Success=Undo(&Removed);
    else if(bGroundDefense)Success=PlacePrefab(R.Definition,R.Anchor,0,false,nullptr,R.Orientation);
    else if(bPlacePrefab)Success=PlacePrefab(R.Definition,Anchor,Yaw,bWallDock||bReplaceWall,R.Target.Get(),INDEX_NONE,bReplaceWall,bReplaceWall?R.Count:-1);
    else if(R.Mode==TEXT("removePrefab"))Success=RemovePrefab(R.Target);
    else if(R.Mode==TEXT("debris"))
    {
        if(auto* F=Cast<AVoxelCollapseFragment>(R.Target);F&&F->GetOwner()==this&&!F->IsMoving())
        {for(const auto& C:F->Data().Cells)Removed.FindOrAdd(C.Material)++;RemoveFragment(F);Success=true;}
    }
    Reason=Message;
    if(!Success)return false;
    for(const auto& E:Removed)
    {
        const FString Definition=TEXT("voxel_block_")+E.Key.ToString();
        if(!M->AddItem(Definition,E.Value))M->GrantWorldBlocks({{Definition,E.Value}},Pawn->GetActorLocation());
    }
    return true;
}
