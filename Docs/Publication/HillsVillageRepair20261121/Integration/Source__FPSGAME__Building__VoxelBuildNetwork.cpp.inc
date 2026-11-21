// Source/FPSGAME/Building/VoxelBuildNetwork.cpp
// Merge each excerpt at the named target and scope. Line numbers locate the 2026-11-21 production source.

// Lines 7-7 | file scope
#include "VillageBuildDefense.h"

// Lines 48-51 | bool AVoxelBuildWorld::ApplyNetworkSnapshot(const TArray<uint8>& Bytes)
         if(!Desired||!Piece||Piece->PrefabId()!=Desired->Id||Piece->Yaw()!=Desired->Yaw||
             (VillageBuildDefense::IsVillageRecipe(Desired->Id)&&PrefabInstanceIdentity(It.Key())!=Desired->InstanceId)||
             (VillageBuildDefense::IsVillageRecipe(Desired->Id)&&!Piece->GetActorTransform().Equals(VillageWallStairs::Placement(*Desired))))
         {if(Piece){if(auto* Logic=Piece->Logic())Logic->Destroy();Piece->Destroy();}It.RemoveCurrent();}}

// Lines 69-79 | bool AVoxelBuildWorld::ApplyNetworkSnapshot(const TArray<uint8>& Bytes)
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

// Lines 107-125 | bool AVoxelBuildWorld::ExecuteNetworkEdit(const FColdSteelInventoryRequest& R,UColdSteelStatusModel* M,FString& Reason)
    const bool bWallDock=R.Mode==TEXT("wallDockPrefab");
    const bool bGroundDefense=R.Mode==TEXT("groundDefensePrefab");
    const bool bPlacePrefab=bWallDock||bGroundDefense||R.Mode==TEXT("prefab");
    if(bWallDock&&(!IsValid(R.Target.Get())||R.Target->GetWorld()!=GetWorld()||!VillageWallStairs::CanDock(R.Definition)))
    {Reason=TEXT("该城防接口已失效，请重新瞄准");return false;}
    FIntVector Anchor=R.Anchor;
    int32 Yaw=R.Orientation;
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
    if(bPlacePrefab&&(Yaw<0||Yaw>(bGroundDefense?359:3)||!Reach(CellCenter(Anchor))))
    {Reason=TEXT("建造位置或方向超出范围");return false;}

// Lines 127-129 | bool AVoxelBuildWorld::ExecuteNetworkEdit(const FColdSteelInventoryRequest& R,UColdSteelStatusModel* M,FString& Reason)
    auto* HistoryOwner=Pawn->GetPlayerState();if(!HistoryOwner)return false;
    UndoHistory.ForgetDisconnected();
    TGuardValue<APlayerState*> EditingPlayer(UndoPlayer,HistoryOwner);

// Lines 147-148 | bool AVoxelBuildWorld::ExecuteNetworkEdit(const FColdSteelInventoryRequest& R,UColdSteelStatusModel* M,FString& Reason)
    else if(bGroundDefense)Success=PlacePrefab(R.Definition,R.Anchor,0,false,nullptr,R.Orientation);
    else if(bPlacePrefab)Success=PlacePrefab(R.Definition,Anchor,Yaw,bWallDock,bWallDock?R.Target.Get():nullptr);
