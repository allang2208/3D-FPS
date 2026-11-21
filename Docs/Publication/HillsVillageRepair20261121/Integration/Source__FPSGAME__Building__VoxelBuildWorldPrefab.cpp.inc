// Source/FPSGAME/Building/VoxelBuildWorldPrefab.cpp
// Merge each excerpt at the named target and scope. Line numbers locate the 2026-11-21 production source.

// Lines 4-4 | file scope
#include "VillageWallStairs.h"

// Lines 33-52 | void AVoxelBuildWorld::FillPrefabCells(const FVoxelBuildPrefabInstance& Instance,TArray<FIntVector>& Out) const
    if(VillageBuildDefense::IsBasicWallOrGate(Instance.Id)&&Instance.WallDockPose.IsSet())
    {
        // Free ground placement keeps the native footprint and uses an exact yaw about its centre.
        VillageDefenseFootprint::RasterizeGridEnvelope(Instance.Footprint,Instance.WallDockPose.GetValue(),Out);
        return;
    }
    if(VillageWallStairs::CanDock(Instance.Id))
    {
        const auto* Definition=Palette?Palette->FindComponent(Instance.Id):nullptr;
        if(Definition)
        {
            const auto& Shape=VillageDefenseFootprint::Get(Instance.Id,Definition->Mesh.LoadSynchronous());
            if(!Shape.Boxes.IsEmpty())
            {
                VillageDefenseFootprint::Rasterize(Shape,VillageWallStairs::Placement(Instance),Out);
                return;
            }
        }
    }
    const FIntVector Size=Instance.Footprint.ComponentMax(FIntVector(1,1,1));

// Lines 112-112 | bool AVoxelBuildWorld::ResolvePrefabSurfaceCell(const FHitResult& Hit,FVoxelBuildKey& Key) const
    if(VillageBuildDefense::IsVillageRecipe(Piece->PrefabId())&&!VoxelGrounding::IsFixedBuildingSurface(Hit))return false;

// Lines 144-149 | bool AVoxelBuildWorld::PrefabSupportAt(FVector WorldMin) const
    for(const FIntVector& Face:SupportFaces)
    {
        const FIntVector Neighbor=C+Face;
        for(auto Holder=PrefabCellOwners.CreateConstKeyIterator(Neighbor);Holder;++Holder)
            if(CanBearLoadAt(Holder.Value(),Neighbor))return true;
    }

// Lines 157-158 | bool AVoxelBuildWorld::PrefabColumnTop(FIntVector Cell,FIntVector& OutTopCell) const
        for(auto Holder=PrefabCellOwners.CreateConstKeyIterator(At);Holder;++Holder)
            if(CanBearLoadAt(Holder.Value(),At))return true;

// Lines 247-288 | bool AVoxelBuildWorld::IsPrefabSupported(const FVoxelBuildPrefabInstance& Instance,FIntVector* OutContact,
    if(VillageWallStairs::CanDock(Instance.Id)||
        (VillageBuildDefense::IsBasicWallOrGate(Instance.Id)&&Instance.WallDockPose.IsSet()))
    {
        // Sample actual footings. An arch opening and the empty stair forecourt do not bear weight.
        auto Params=VoxelGrounding::Query(GetWorld(),this);
        if(const auto* Self=Cast<AVoxelBuildPrefabActor>(PrefabActors.FindRef(Instance.Cell).Get()))
        {
            Params.AddIgnoredActor(Self);
            Params.AddIgnoredActor(Self->Logic());
        }
        const FTransform Pose=VillageWallStairs::Placement(Instance);
        const FVector StairFeet[]={{-80.,-90.,0.},{80.,-245.,0.},{0.,220.,0.}};
        const FVector WallFeet[]={{0.,0.,0.},{-133.,0.,0.},{133.,0.,0.}};
        const FVector GateFeet[]={{-382.,-70.,0.},{-382.,94.,0.},{382.,-70.,0.},{382.,94.,0.}};
        const FVector TimberFeet[]={AVillageDefenseGate::PlacedPostTransform(false).GetLocation(),
            AVillageDefenseGate::PlacedPostTransform(true).GetLocation()};
        const double WallX=(Definition->Footprint.X-1)*10., WallY=(Definition->Footprint.Y-1)*10.;
        const FVector BasicWallFeet[]={{0.,0.,0.},{-WallX,-WallY,0.},{WallX,-WallY,0.},
            {-WallX,WallY,0.},{WallX,WallY,0.}};
        const TConstArrayView<FVector> Samples=Instance.Id==VillageWallStairs::Id?MakeArrayView(StairFeet):
            Instance.Id==VillageBuildDefense::StoneGate?MakeArrayView(GateFeet):
            Instance.Id==VillageBuildDefense::WoodGate?MakeArrayView(TimberFeet):
            Instance.Id==VillageBuildDefense::StoneWall?MakeArrayView(BasicWallFeet):MakeArrayView(WallFeet);
        for(const FVector& Sample:Samples)
        {
            const FVector P=Pose.TransformPosition(Sample);
            VoxelGrounding::FFootprint Ground;
            if(VoxelGrounding::Sample(GetWorld(),P-FVector(10.,10.,0.),P.Z+VoxelGrounding::AnchorProbeRiseCm,
                P.Z-18.,Params,Ground)&&HasFixedFloor(Ground,this,SupportingPieces))return true;
        }
    }
    else if(IsPrefabOnGround(Instance.Cell,Footprint,SupportingPieces))return true;
    if(Instance.WallDockPose.IsSet()&&VillageWallStairs::CanDock(Instance.Id))
    {
        // A generated wall supplies real structural support but has no voxel cells.
        VillageWallStairs::FDock Join;
        if(VillageWallStairs::FindDock(GetWorld(),Instance.Id,Definition->Footprint,Instance.Cell,Instance.Yaw,Join)
            &&Join.Pose.Equals(Instance.WallDockPose.GetValue(),.02))
        {
            const auto* Carrier=Cast<AVoxelBuildPrefabActor>(Join.Target->GetAttachParentActor());
            if(!SupportingPieces||!Carrier)return true;
            SupportingPieces->Add(Carrier->AnchorCell());

// Lines 301-318 | bool AVoxelBuildWorld::IsPrefabSupported(const FVoxelBuildPrefabInstance& Instance,FIntVector* OutContact,
    if(Instance.Id==VillageBuildDefense::WoodGate&&Instance.WallDockPose.IsSet())
    {
        // The leaves reserve the closed gate's span. Only the two fixed piers can attach to
        // nearby voxels or prefabs, just as only those piers can carry another piece.
        const auto* Pier=Cast<UStaticMesh>(AVillageDefenseGate::PlacedPostMeshPath().TryLoad());
        if(!Pier)return false;
        VillageDefenseFootprint::FShape Piers;
        for(bool bRight:{false,true})
        {
            FBox Bounds=Pier->GetBoundingBox().TransformBy(AVillageDefenseGate::PlacedPostTransform(bRight));
            Bounds.Min.Z=FMath::Max(0.,Bounds.Min.Z);
            Piers.Boxes.Add(Bounds);
        }
        VillageDefenseFootprint::Rasterize(Piers,Instance.WallDockPose.GetValue(),Occupied);
    }
    else FillPrefabCells(Instance,Occupied);
    const int32 Stride=VillageBuildDefense::IsVillageRecipe(Instance.Id)?1:
        FMath::Max(1,FMath::DivideAndRoundUp(Occupied.Num(),MaxSupportSamples));

// Lines 326-329 | bool AVoxelBuildWorld::IsPrefabSupported(const FVoxelBuildPrefabInstance& Instance,FIntVector* OutContact,
            for(auto Holder=PrefabCellOwners.CreateConstKeyIterator(Neighbor);Holder&&!bContact;++Holder)
                if(Holder.Value()!=Instance.Cell&&CanBearLoadAt(Holder.Value(),Neighbor))
                {
                    if(SupportingPieces)SupportingPieces->Add(Holder.Value());

// Lines 357-357 | void AVoxelBuildWorld::AddNearbyPrefabOwners(FIntVector Cell,TSet<FIntVector>& Out) const
        for(auto Holder=PrefabCellOwners.CreateConstKeyIterator(At);Holder;++Holder)Out.Add(Holder.Value());

// Lines 447-452 | void AVoxelBuildWorld::DropUnsupportedPrefabs(const TSet<FIntVector>& Candidates)
        // A village gate consists of two hinged leaves. Let both disappear
        // with their carrier when the foundation goes, including any repair target.
        const bool bVillageDefense=Instance&&VillageBuildDefense::IsVillageRecipe(Instance->Id);
        if(bVillageDefense)RemovedVillageDefenses.Add(Instance->InstanceId);
        const bool bFalling=Placed&&!bVillageDefense&&Placed->BeginFall(Definition?Definition->Mesh.LoadSynchronous():nullptr,8.f);
        if(Piece&&!bFalling)Piece->Destroy();

// Lines 489-498 | bool AVoxelBuildWorld::CanPlacePrefab(FName Id,FIntVector Cell,int32 Yaw,FString& Reason,bool bSurfaceBacked,bool bDocked,
    const bool bFortification=VillageWallStairs::CanDock(Id);
    const bool bVillage=VillageBuildDefense::IsVillageRecipe(Id);
    if(GroundYawDegrees!=INDEX_NONE&&(!bVillage||bDocked||Yaw!=0||GroundYawDegrees<0||GroundYawDegrees>=360))
    {Reason=TEXT("城防地面朝向无效");return false;}
    if(bVillage)
    {
        const auto* Hills=FindVillageConstructionWorld();
        if(!Hills||!Hills->IsVillagePlanUnlocked(TEXT("village_construction")))
        {Reason=TEXT("请先在修女处解锁村庄修建");return false;}
    }

// Lines 505-528 | bool AVoxelBuildWorld::CanPlacePrefab(FName Id,FIntVector Cell,int32 Yaw,FString& Reason,bool bSurfaceBacked,bool bDocked,
    {Reason=TEXT("该建造位置已被占用");return false;}
    FVoxelBuildPrefabInstance Probe;
    Probe.Id=Id;Probe.Cell=Cell;Probe.Yaw=Yaw;Probe.Footprint=Footprint;
    VillageWallStairs::FDock Dock;
    if(bDocked)
    {
        if(!VillageWallStairs::FindDock(GetWorld(),Id,Definition->Footprint,Cell,Yaw,Dock,DockTarget))
        {Reason=TEXT("未找到匹配的城防接口，请重新瞄准");return false;}
        Probe.WallDockPose=Dock.Pose;
    }
    else if(GroundYawDegrees!=INDEX_NONE)
        Probe.WallDockPose=VillageBuildDefense::Placement(Id,Cell,Footprint,Yaw,GroundYawDegrees);
    const FTransform Pose=bVillage?VillageWallStairs::Placement(Probe):FTransform::Identity;
    if(bVillage&&OutPlacementPose)*OutPlacementPose=Pose;
    if(bFortification)
    {
        const auto& Shape=VillageDefenseFootprint::Get(Id,Definition->Mesh.LoadSynchronous());
        if(!VillageDefenseFootprint::IsClear(*GetWorld(),Shape,Pose,this))
        {Reason=TEXT("城防构件与人物、建筑或地形重叠，请更换位置");return false;}
        if(bDocked && Id==VillageWallStairs::Id && !VillageWallStairs::HasClearStairEntrance(*GetWorld(),Pose))
        {Reason=TEXT("楼梯入口被挡住 · 用滚轮换向或选择另一段城墙");return false;}
    }
    else if(bVillage)
    {

// Lines 532-536 | bool AVoxelBuildWorld::CanPlacePrefab(FName Id,FIntVector Cell,int32 Yaw,FString& Reason,bool bSurfaceBacked,bool bDocked,
            FCollisionShape::MakeBox(HalfSize-FVector(1.))))
        {
            Reason=TEXT("建造位置有人或动物，请让开后放置");
            return false;
        }

// Lines 586-586 | bool AVoxelBuildWorld::CanPlacePrefab(FName Id,FIntVector Cell,int32 Yaw,FString& Reason,bool bSurfaceBacked,bool bDocked,
        {Reason=TEXT("需要可固定壁挂件的竖直表面");return false;}

// Lines 599-617 | ATemperateHillsWorld* AVoxelBuildWorld::FindVillageConstructionWorld() const
ATemperateHillsWorld* AVoxelBuildWorld::FindVillageConstructionWorld() const
{
    if(auto* Cached=VillageConstructionWorld.Get())return Cached;
    for(TActorIterator<ATemperateHillsWorld> It(GetWorld());It;++It)
        if(It->WorldId.IsValid()){VillageConstructionWorld=*It;return *It;}
    return nullptr;
}

void AVoxelBuildWorld::ForgetSavedDefenseRemovals()
{
    if(RemovedVillageDefenses.IsEmpty())return;
    auto* Hills=FindVillageConstructionWorld();
    if(!Hills)return;
    // The network inventory transaction can roll a removal back before the
    // voxel save commits. Its restored GUID must keep the original health.
    for(const auto& Entry:Prefabs)RemovedVillageDefenses.Remove(Entry.InstanceId);
    GetWorld()->GetSubsystem<UVillageDefenseState>()->ForgetPlaced(Hills->WorldId,RemovedVillageDefenses);
    RemovedVillageDefenses.Reset();
}

// Lines 623-645 | AVoxelBuildPrefabActor* AVoxelBuildWorld::SpawnPrefab(const FVoxelBuildPrefabInstance& Instance)
    if(VillageBuildDefense::IsVillageRecipe(Instance.Id))
    {
        if(!HasAuthority()||!Instance.InstanceId.IsValid())return nullptr;
        auto* Hills=FindVillageConstructionWorld();
        if(!Hills)return nullptr;
        const FTransform Transform=VillageWallStairs::Placement(Instance);
        FActorSpawnParameters Spawn;
        Spawn.Owner=this;
        Spawn.SpawnCollisionHandlingOverride=ESpawnActorCollisionHandlingMethod::AlwaysSpawn;
        auto* Piece=GetWorld()->SpawnActor<AVoxelBuildPrefabActor>(AVoxelBuildPrefabActor::StaticClass(),Transform,Spawn);
        if(!Piece)return nullptr;
        // The attached defense is always relevant. Its transform parent must reach the same clients.
        Piece->bAlwaysRelevant=true;
        Piece->Configure(Instance.Id,Instance.Cell,Instance.Yaw,nullptr,nullptr,nullptr);
        auto* Defense=VillageBuildDefense::SpawnPlaced(*Definition,*Hills,Instance.InstanceId,Transform);
        if(!Defense){Piece->Destroy();return nullptr;}
        Defense->AttachToActor(Piece,FAttachmentTransformRules::KeepWorldTransform);
        Defense->SetReplicateMovement(true);
        Piece->AttachLogicActor(Defense);
        Piece->SetNetDormancy(DORM_DormantAll);
        PrefabActors.Add(Instance.Cell,Piece);
        return Piece;
    }

// Lines 734-734 | bool AVoxelBuildWorld::DismantlePrefab(AActor* Piece,bool bManual)
    if(!bReady||GetNetMode()==NM_Client||!IsValid(Target)||Target->GetOwner()!=this||Target->IsSceneStation())

// Lines 786-787 | bool AVoxelBuildWorld::DismantlePrefab(AActor* Piece,bool bManual)
        if(VillageBuildDefense::IsVillageRecipe(Entry->Id))RemovedVillageDefenses.Add(Entry->InstanceId);
        FillPrefabCells(*Entry,Vacated);
