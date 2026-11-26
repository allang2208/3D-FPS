#include "VoxelBuildWorld.h"
#include "../WorldGeneration/VillageMechanicalWorkshop.h"
#include "TimerManager.h"
#include "VillageBuildDefense.h"
#include "VillageDefenseFootprint.h"
#include "VillageWallStairs.h"
#include "VillageGateReplacement.h"
#include "../WorldGeneration/HighVillageDefense.h"
#include "../WorldGeneration/TemperateHillsWorld.h"
#include "../WorldGeneration/VillageDefenseSection.h"
#include "../WorldGeneration/VillageDefenseStairs.h"
#include "../WorldGeneration/VillageDefenseState.h"
#include "ColdSteelCampfire.h"
#include "../UI/ColdSteelIncineratorStorage.h"
#include "../UI/ColdSteelStatusModel.h"
#include "Engine/GameInstance.h"
#include "VoxelBuildRuntime.h"
#include "VoxelBuildPalette.h"
#include "VoxelBuildPrefabActor.h"
#include "VoxelBuildGrounding.h"
#include "VoxelCollapseFragment.h"
#include "SmeltingSystem.h"
#include "ColdSteelDoor.h"
#include "ColdSteelWindow.h"
#include "ColdSteelSlidingDoor.h"
#include "ColdSteelRevolvingDoor.h"
#include "ColdSteelFountain.h"
#include "Components/PrimitiveComponent.h"
#include "Engine/StaticMesh.h"
#include "EngineUtils.h"
#include "../Multiplayer/ColdSteelAuthorityContext.h"
#include "../Multiplayer/ColdSteelPlayerState.h"
#include "GameFramework/PlayerController.h"

void AVoxelBuildWorld::FillPrefabCells(const FVoxelBuildPrefabInstance& Instance,TArray<FIntVector>& Out) const
{
    Out.Reset();
    const FVector2D* Cut=Instance.InstanceId.IsValid()?CutPlacedWalls.Find(Instance.InstanceId):nullptr;
    if(Cut && Cut->Y-Cut->X<=.01)return;
    if(Cut && Instance.Id==VillageBuildDefense::StoneWall)
    {
        const auto* Definition=Palette->FindComponent(Instance.Id);
        if(!Definition)return;
        FTransform Pose=VillageGateReplacement::Trim(VillageWallStairs::Placement(Instance),*Cut);
        Pose.SetScale3D(FVector(Pose.GetScale3D().X,1.,1.));
        const FVector Half=FVector(Definition->Footprint)*10.;
        VillageDefenseFootprint::FShape Shape;
        Shape.Boxes.Add(FBox(FVector(-Half.X,-Half.Y,0.),FVector(Half.X,Half.Y,Half.Z*2.)));
        VillageDefenseFootprint::Rasterize(Shape,Pose,Out);
        return;
    }
    if(VillageBuildDefense::IsSiegeEngine(Instance.Id))
    {
        VillageDefenseFootprint::Rasterize(VillageDefenseFootprint::Siege(Instance.Id),VillageWallStairs::Placement(Instance),Out);
        return;
    }
    if(VillageBuildDefense::IsBasicWallOrGate(Instance.Id)&&Instance.WallDockPose.IsSet())
    {
        // Free ground placement keeps the native footprint and uses an exact yaw about its centre.
        const FIntVector Native=AVoxelBuildPrefabActor::RotatedFootprint(Instance.Footprint,Instance.Yaw);
        VillageDefenseFootprint::RasterizeGridEnvelope(Native,Instance.WallDockPose.GetValue(),Out);
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
                const FTransform Pose=VillageWallStairs::Placement(Instance);
                VillageDefenseFootprint::Rasterize(Shape,Cut?VillageGateReplacement::Trim(Pose,*Cut):Pose,Out);
                return;
            }
        }
    }
    const FIntVector Size=Instance.Footprint.ComponentMax(FIntVector(1,1,1));
    for(int32 Z=0;Z<Size.Z;++Z)for(int32 Y=0;Y<Size.Y;++Y)for(int32 X=0;X<Size.X;++X)
        Out.Add(Instance.Cell+FIntVector(X,Y,Z));
}

namespace
{
    // 支撑判定只看六个正对面（与体素的连接键同一套邻接口径）。
    const FIntVector SupportFaces[]={FIntVector(1,0,0),FIntVector(-1,0,0),FIntVector(0,1,0),
        FIntVector(0,-1,0),FIntVector(0,0,1),FIntVector(0,0,-1)};
    // 超大构件（凉亭 48×48×38 ≈ 8.7 万格）不逐格扫：抽样上限内找一个接触就够。
    constexpr int32 MaxSupportSamples=4096;

    // Placed floors provide a link to another piece. Terrain and authored world structures are roots.
    bool HasFixedFloor(const VoxelGrounding::FFootprint& Floor,const AVoxelBuildWorld* World,TSet<FIntVector>* SupportingPieces)
    {
        if(!SupportingPieces)return true;
        for(const auto& Surface:Floor.Surfaces)
        {
            const AActor* Node=Surface.IsValid()?Surface->GetOwner():nullptr;
            while(Node&&!Node->IsA<AVoxelBuildPrefabActor>())Node=Node->GetAttachParentActor();
            const auto* Carrier=Cast<AVoxelBuildPrefabActor>(Node);
            if(!Carrier||Carrier->GetOwner()!=World)return true;
            if(!Carrier->IsFalling())SupportingPieces->Add(Carrier->AnchorCell());
        }
        return false;
    }
    bool SiegeFooting(const AVoxelBuildWorld& World,FName Id,const FTransform& Pose,
        const AVoxelBuildPrefabActor* Self,double& FloorZ,TSet<FIntVector>* Parents=nullptr,
        const UPrimitiveComponent** OutRoof=nullptr)
    {
        // Sample load-bearing feet in their rotated positions, including authored tower decks.
        FCollisionQueryParams Params(SCENE_QUERY_STAT(VillageSiegeFooting),true);
        if(Self){Params.AddIgnoredActor(Self);Params.AddIgnoredActor(Self->Logic());}
        static const FVector2D Pedestal[]={{-62,-37},{-62,37},{62,-37},{62,37},{0,0}};
        // Sample the ends and the middle of both longitudinal supports, in mesh space.
        static const FVector2D Chassis[]={{-219,-128},{-219,128},{-10,-128},{-10,128},{199,-128},{199,128}};
        const bool bTrebuchet=Id==VillageBuildDefense::Trebuchet;
        static const FVector2D OilFeet[]={{-66,-65},{-66,65},{66,-65},{66,65},{0,0}};
        const TConstArrayView<FVector2D> Pads=bTrebuchet?MakeArrayView(Chassis):
            Id==VillageBuildDefense::OilPot?MakeArrayView(OilFeet):MakeArrayView(Pedestal);
        double Low=MAX_dbl,High=-MAX_dbl;
        bool AllFixed=true;
        TSet<FIntVector> Supports;
        const UPrimitiveComponent* CommonRoof=nullptr;
        const UPrimitiveComponent* SampledRoof=nullptr;
        for(int32 Index=0;Index<Pads.Num();++Index)
        {
            const FVector P=Pose.TransformPosition(FVector(Pads[Index],0.));
            const FVector Top=P+FVector(0,0,19.),Bottom=P-FVector(0,0,29.);
            FHitResult Hit;
            const VillageDefenseFootprint::FShape* Deck=nullptr;
            Params.bTraceComplex=false;
            if(World.GetWorld()->LineTraceSingleByChannel(Hit,Top,Bottom,ECC_Visibility,Params))
                Deck=VillageDefenseFootprint::SiegeRoof(Hit.GetComponent());
            if(!Deck)
            {
                Params.bTraceComplex=true;
                if(!World.GetWorld()->LineTraceSingleByChannel(Hit,Top,Bottom,ECC_Visibility,Params))return false;
            }
            if(!VoxelGrounding::IsFixedBuildingSurface(Hit) || Hit.ImpactNormal.Z<.85
                || Cast<AVoxelCollapseFragment>(Hit.GetActor()))return false;
            const auto* Surface=Hit.GetComponent();
            const bool OnRoof=Deck && FMath::Abs(Surface->GetComponentTransform().InverseTransformPosition(Hit.ImpactPoint).Z-Deck->Bounds.Max.Z)<1.;
            if(bTrebuchet && OnRoof && SampledRoof!=Surface)
            {
                if(!VillageDefenseFootprint::TrebuchetFitsDeck(*Deck,Surface->GetComponentTransform(),Pose))return false;
                SampledRoof=Surface;
            }
            if(Index==0 && OnRoof)CommonRoof=Surface;
            else if(!OnRoof || CommonRoof!=Surface)CommonRoof=nullptr;
            Low=FMath::Min(Low,Hit.ImpactPoint.Z);High=FMath::Max(High,Hit.ImpactPoint.Z);
            VoxelGrounding::FFootprint Floor;
            Floor.Surfaces.Add(Hit.GetComponent());
            if(Parents && !HasFixedFloor(Floor,&World,&Supports))AllFixed=false;
        }
        if(High-Low>16.)return false;
        FloorZ=(Low+High)*.5;
        if(OutRoof)*OutRoof=CommonRoof;
        if(Parents)Parents->Append(Supports);
        return AllFixed;
    }
}

void AVoxelBuildWorld::ApplyGateCutToWall(AVillageDefenseSection& Wall) const
{
    if((!Wall.IsA<AHighVillageWall>()&&!Wall.IsRepairedCurtain())||Wall.GetOwner()!=FindVillageConstructionWorld())return;
    const FVector2D* Cut=Wall.GetPlacedId().IsValid()?CutPlacedWalls.Find(Wall.GetPlacedId()):CutVillageWalls.Find(Wall.GetSectionId());
    FVector2D Interval(-150.,150.);
    if(Cut)Interval=*Cut;
    else if(!CutVillageWalls.IsEmpty() && Wall.IsA<AHighVillageWall>() && !Wall.GetPlacedId().IsValid())
        for(const auto& Gate:Prefabs)
            if(!Gate.GateCuts.IsEmpty() && VillageGateReplacement::IntervalFor(Wall,Gate,Interval))break;
    Wall.SetWallInterval(Interval);
}

void AVoxelBuildWorld::RefreshPrefabOccupancy()
{
    const bool HadCuts=!CutPlacedWalls.IsEmpty()||!CutVillageWalls.IsEmpty();
    CutPlacedWalls.Reset();CutVillageWalls.Reset();
    for(const auto& Gate:Prefabs)for(const auto& Cut:Gate.GateCuts)
    {
        if(Cut.PlacedId.IsValid())CutPlacedWalls.Add(Cut.PlacedId,Cut.Remaining);
        else CutVillageWalls.Add(Cut.Section,Cut.Remaining);
    }
    if(HasAuthority() && (HadCuts||!CutPlacedWalls.IsEmpty()||!CutVillageWalls.IsEmpty()))
        for(TActorIterator<AVillageDefenseSection> It(GetWorld());It;++It)ApplyGateCutToWall(**It);
    CachedGridRecipe=NAME_None;
    PrefabCellOwners.Reset();
    TArray<FIntVector> Occupied;
    for(const FVoxelBuildPrefabInstance& Entry:Prefabs)
        AddPrefabOccupancy(Entry,Occupied);
}

void AVoxelBuildWorld::AddPrefabOccupancy(const FVoxelBuildPrefabInstance& Instance,TArray<FIntVector>& Scratch)
{
    FillPrefabCells(Instance,Scratch);
    for(const FIntVector& Cell:Scratch)PrefabCellOwners.Add(Cell,Instance.Cell);
    CachedGridRecipe=NAME_None;
}

void AVoxelBuildWorld::RemovePrefabOccupancy(FIntVector Anchor,const TArray<FIntVector>& Occupied)
{
    for(const FIntVector& Cell:Occupied)PrefabCellOwners.RemoveSingle(Cell,Anchor);
    CachedGridRecipe=NAME_None;
}

bool AVoxelBuildWorld::ResolvePrefabSurfaceCell(const FHitResult& Hit,FVoxelBuildKey& Key) const
{
    // 命中面必须属于一件已放置构件：占位 Actor 自己，或挂在它下面的逻辑构件（门／窗的组件沿
    // 挂载链一路上溯到 AVoxelBuildPrefabActor）。
    const AVoxelBuildPrefabActor* Piece=nullptr;
    for(AActor* Node=Hit.GetComponent()?Hit.GetComponent()->GetOwner():nullptr;
        Node;Node=Node->GetAttachParentActor())
        if((Piece=Cast<AVoxelBuildPrefabActor>(Node)))break;
    if(!Piece||Piece->IsFalling()||Piece->GetOwner()!=this)return false;
    if(VillageBuildDefense::IsVillageRecipe(Piece->PrefabId())&&!VoxelGrounding::IsFixedBuildingSurface(Hit))return false;
    // 与体素 ResolveHit 同一口径：取面内半厘米处的格子，命中面贴边才不会落到邻格。
    const FIntVector Cell=ToCell(Hit.ImpactPoint-Hit.ImpactNormal*.5);
    // 占格表是唯一的权威：摆动出来的门／窗扇打在占格体积之外，这里自然拒绝（落回贴地分支）。
    if(!PrefabCellOwners.FindPair(Cell,Piece->AnchorCell()))return false;
    Key=FVoxelBuildKey{{},Cell};return true;
}

bool AVoxelBuildWorld::HitBelongsToPlacedPrefab(const FHitResult& Hit) const
{
    // 与 ResolvePrefabSurfaceCell 同一条上溯链，但不验占格：占格外的摆开扇面也算"构件自己的网格"。
    for(AActor* Node=Hit.GetComponent()?Hit.GetComponent()->GetOwner():nullptr;
        Node;Node=Node->GetAttachParentActor())
        if(Cast<AVoxelBuildPrefabActor>(Node))return true;
    return false;
}

bool AVoxelBuildWorld::IsPrefabCell(FGuid Volume,FIntVector Cell) const
{
    if(Volume.IsValid())
    {
        // 自由体积的格是本地坐标、原点可以在任意连续位置（自由放置不取整）：
        // 换算成真实世界格再查（历史缺陷：直接拿本地格查世界占格表）。
        const auto* Data=FreeVolumes.Find(Volume);if(!Data)return false;
        Cell=ToCell(Data->Origin+CellMin(Cell));
    }
    return PrefabCellOwners.Contains(Cell);
}

bool AVoxelBuildWorld::PrefabSupportAt(FVector WorldMin) const
{
    const FIntVector C=ToCell(WorldMin);
    for(const FIntVector& Face:SupportFaces)
    {
        const FIntVector Neighbor=C+Face;
        for(auto Holder=PrefabCellOwners.CreateConstKeyIterator(Neighbor);Holder;++Holder)
            if(CanBearLoadAt(Holder.Value(),Neighbor))return true;
    }
    return false;
}

bool AVoxelBuildWorld::PrefabColumnTop(FIntVector Cell,FIntVector& OutTopCell) const
{
    const auto BearsWeight=[&](FIntVector At)
    {
        for(auto Holder=PrefabCellOwners.CreateConstKeyIterator(At);Holder;++Holder)
            if(CanBearLoadAt(Holder.Value(),At))return true;
        return false;
    };
    if(!BearsWeight(Cell))return false;
    OutTopCell=Cell;
    do {++OutTopCell.Z;} while(BearsWeight(OutTopCell));
    return true;
}

void AVoxelBuildWorld::ReanchorVoxelsAround(const TArray<FIntVector>& VacatedCells,bool bIncludeInterior,bool bRestored)
{
    if(!SupportGraph||SupportGraph->Nodes.IsEmpty()||!Runtime||VacatedCells.IsEmpty())return;
    // 只重判"腾出格外壳一圈"的体素，且只处理**原本有锚、如今既不贴地面也不贴别的构件**的节点——
    // 重锚发生在拆除／脱落之后，锚只可能变没、不会新增，所以绝大多数节点一次查表就跳过。
    TSet<FIntVector> VacatedSet;for(const FIntVector& Cell:VacatedCells)VacatedSet.Add(Cell);
    TSet<FIntVector> Boundary;
    if(bIncludeInterior)Boundary=VacatedSet;
    for(const FIntVector& Cell:VacatedCells)for(const FIntVector& Face:SupportFaces)
    {
        const FIntVector Neighbor=Cell+Face;
        if(VacatedSet.Contains(Neighbor))continue;
        Boundary.Add(Neighbor);
    }
    TSet<FVoxelBuildKey> Done;bool bChanged=false;
    // 审计 W1（2026-09-23）：重锚整轮共用一次查询参数（每个边界节点原本都要内部 Query 一遍）。
    const FCollisionQueryParams GroundParams=VoxelGrounding::Query(GetWorld(),this);
    for(const FIntVector& Cell:Boundary)
    {
        for(const FVoxelBuildKey& Key:SupportGraph->Near(CellMin(Cell)))
        {
            if(Done.Contains(Key))continue;Done.Add(Key);
            FVoxelSupportNode* Node=SupportGraph->Nodes.Find(Key);
            if(!Node||Node->bAnchor==bRestored)continue;
            const bool bSupported=HasVoxelFoundation(Key,GroundParams);
            if(bSupported==Node->bAnchor)continue;
            Node->bAnchor=bSupported;
            Runtime->DirtySupport.Add(Key);Runtime->NodeEpoch.Add(Key,Revision+1);
            bChanged=true;
        }
    }
    if(!bChanged)return;
    ++Revision;SupportGraph->SolveConnectivity();
    Runtime->StructureAt=GetWorld()->GetTimeSeconds()+.08;MarkSaveDirty();
}


bool AVoxelBuildWorld::IsPrefabOnGround(FIntVector AnchorCell,FIntVector Footprint,TSet<FIntVector>* SupportingPieces) const
{
    // 地面探测点：中心 + 四角（起伏地形上只测中心会误判"没着地"）。
    const int32 LastX=FMath::Max(0,Footprint.X-1),LastY=FMath::Max(0,Footprint.Y-1);
    const FIntVector Points[]={FIntVector(LastX/2,LastY/2,0),FIntVector(0,0,0),FIntVector(LastX,0,0),
        FIntVector(0,LastY,0),FIntVector(LastX,LastY,0)};
    // 2026-09-18 根因（用户报"拆掉支撑后窗仍然悬空"）：探针带是"底面 +40.5 cm"，而构件自己的
    // 网格正好在这条带里。不排除它时，任何构件都会把自己的碰撞当成"底下有地面"，于是拆光周围
    // 也不会掉。这里只排除这一件自己的占位 Actor 与逻辑构件：其他构件、场景实体照旧算表面，
    // 体素放置用的 IsGroundAnchor 口径不变。
    FCollisionQueryParams Params=VoxelGrounding::Query(GetWorld(),this);
    if(const TWeakObjectPtr<AActor>* Placed=PrefabActors.Find(AnchorCell))
        if(AActor* Piece=Placed->Get())
        {
            Params.AddIgnoredActor(Piece);
            if(auto* Prefab=Cast<AVoxelBuildPrefabActor>(Piece))
                if(AActor* Logic=Prefab->Logic())Params.AddIgnoredActor(Logic);
        }
    for(const FIntVector& Offset:Points)
    {
        VoxelGrounding::FFootprint Ground;
        const FVector Min=CellMin(AnchorCell+Offset);
        if(VoxelGrounding::Sample(GetWorld(),Min,Min.Z+VoxelGrounding::AnchorProbeRiseCm,
            Min.Z-VoxelGrounding::ContactToleranceCm,Params,Ground)&&HasFixedFloor(Ground,this,SupportingPieces))return true;
    }
    return false;
}

bool AVoxelBuildWorld::IsPrefabSupported(const FVoxelBuildPrefabInstance& Instance,FIntVector* OutContact,
    TSet<FIntVector>* SupportingPieces) const
{
    if(CutPlacedWalls.Contains(Instance.InstanceId))return true;
    const FVoxelBuildPrefab* Definition=Palette?Palette->FindComponent(Instance.Id):nullptr;
    if(!Definition)return true;   // 定义缺失时不在这里判死，交给生成路径报错
    if(VillageBuildDefense::IsSiegeEngine(Instance.Id))
    {
        double FloorZ;
        return SiegeFooting(*this,Instance.Id,VillageWallStairs::Placement(Instance),
            Cast<AVoxelBuildPrefabActor>(PrefabActors.FindRef(Instance.Cell).Get()),FloorZ,SupportingPieces);
    }
    if(Definition->Mount==EVoxelPrefabMount::Wall)
    {
        FHitResult Surface;
        if(!FindWallBacking(Instance,Surface))return false;
        VoxelGrounding::FFootprint Backing;
        Backing.Surfaces.Add(Surface.GetComponent());
        return HasFixedFloor(Backing,this,SupportingPieces);
    }
    const FIntVector Footprint=AVoxelBuildPrefabActor::RotatedFootprint(Definition->Footprint,Instance.Yaw);
    // ① 地形：先试这一条，站在地上的大件（凉亭、喷泉）在这里就短路了。
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
        if(!Instance.GateCuts.IsEmpty())
        {
            const auto* Hills=FindVillageConstructionWorld();
            FVector2D Interval;
            for(TActorIterator<AVillageDefenseSection> It(GetWorld());It;++It)
                if(It->GetOwner()==Hills && VillageGateReplacement::IntervalFor(**It,Instance,Interval))
                {
                    Params.AddIgnoredActor(*It);
                    Params.AddIgnoredActor(It->GetAttachParentActor());
                }
        }
        const FTransform Pose=VillageWallStairs::Placement(Instance);
        const FVector StairFeet[]={{-80.,-90.,0.},{80.,-245.,0.},{0.,220.,0.}};
        const FVector WallFeet[]={{0.,0.,0.},{-133.,0.,0.},{133.,0.,0.}};
        const FVector TowerFeet[]={{-425.,-425.,0.},{425.,-425.,0.},{-425.,425.,0.},{425.,425.,0.},{0.,0.,0.}};
        const FVector GateFeet[]={{-382.,-70.,0.},{-382.,94.,0.},{382.,-70.,0.},{382.,94.,0.}};
        const FVector TimberFeet[]={AVillageDefenseGate::PlacedPostTransform(false).GetLocation(),
            AVillageDefenseGate::PlacedPostTransform(true).GetLocation()};
        const double WallX=(Definition->Footprint.X-1)*10., WallY=(Definition->Footprint.Y-1)*10.;
        const FVector BasicWallFeet[]={{0.,0.,0.},{-WallX,-WallY,0.},{WallX,-WallY,0.},
            {-WallX,WallY,0.},{WallX,WallY,0.}};
        const TConstArrayView<FVector> Samples=Instance.Id==VillageWallStairs::Id?MakeArrayView(StairFeet):
            Instance.Id==VillageBuildDefense::HighTower?MakeArrayView(TowerFeet):
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
    if(!Instance.GateCuts.IsEmpty())return false;
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
        }
    }
    if(PrefabCellOwners.IsEmpty()&&Cells.IsEmpty()&&FreeVolumeWorldCells.IsEmpty())return false;
    // ②／③ 与体素或另一件构件面对面相邻。
    const bool bCacheSupport=!SupportingPieces&&CachedGridRecipe==Instance.Id&&CachedGridRevision==Revision&&
        VillageWallStairs::Placement(Instance).Equals(CachedGridPose,.001);
    if(bCacheSupport&&CachedGridSupport.IsSet())
    {
        if(CachedGridSupport.GetValue()&&OutContact)*OutContact=CachedSupportContact;
        return CachedGridSupport.GetValue();
    }
    TArray<FIntVector> Occupied;
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
    for(int32 Index=0;Index<Occupied.Num();Index+=Stride)
    {
        const FIntVector& Cell=Occupied[Index];
        for(const FIntVector& Face:SupportFaces)
        {
            const FIntVector Neighbor=Cell+Face;
            bool bContact=Cells.Contains(Neighbor);
            for(auto Holder=PrefabCellOwners.CreateConstKeyIterator(Neighbor);Holder&&!bContact;++Holder)
                if(Holder.Value()!=Instance.Cell&&CanBearLoadAt(Holder.Value(),Neighbor))
                {
                    if(SupportingPieces)SupportingPieces->Add(Holder.Value());
                    else bContact=true;
                }
            if(!bContact&&FreeVolumeWorldCells.Contains(Neighbor))
            {
                // Free voxel origins are continuous. Require the same real face contact as the voxel graph.
                const FVector Min=CellMin(Cell);
                FVoxelContact Contact;
                for(const FVoxelBuildKey& Key:SupportGraph->Near(Min))
                    if(Key.Volume.IsValid()&&FVoxelSupportGraph::Contact(Min,VolumeOrigin(Key.Volume)+CellMin(Key.Cell),Contact))
                    {bContact=true;break;}
            }
            if(bContact)
            {
                if(OutContact)*OutContact=Neighbor;
                if(bCacheSupport){CachedGridSupport=true;CachedSupportContact=Neighbor;}
                return true;
            }
        }
    }
    if(bCacheSupport)CachedGridSupport=false;
    return false;
}

void AVoxelBuildWorld::AddNearbyPrefabOwners(FIntVector Cell,TSet<FIntVector>& Out) const
{
    const auto AddOwners=[&](FIntVector At)
    {
        for(auto Holder=PrefabCellOwners.CreateConstKeyIterator(At);Holder;++Holder)Out.Add(Holder.Value());
    };
    AddOwners(Cell);
    for(const FIntVector& Face:SupportFaces)AddOwners(Cell+Face);
}

void AVoxelBuildWorld::VerifyPrefabSupport(const TArray<FVoxelEditCell>& Edit)
{
    if(Prefabs.IsEmpty()||Edit.IsEmpty())return;
    // 只看"改动点及一圈邻居"命中的占格：不这样筛，每批编辑都要扫全场构件（凉亭一件 8.7 万格）。
    TSet<FIntVector> Candidates;
    for(const FVoxelEditCell& E:Edit)
    {
        if(E.Before.IsNone())continue; // Adding support cannot detach an existing piece.
        // 2026-10-13 审计修复（中危#4）：自由体积编辑的 E.Position 是体积本地格，查世界占格表
        // 前必须换算（与 IsPrefabCell 同口径）——原实现直接拿本地格查 PrefabCellOwner，只有体积
        // 原点恰在原点附近才碰巧命中，自由建筑内拆格子会漏判/误判邻接构件的支撑重判。
        const FIntVector World=E.Volume.IsValid()?ToCell(VolumeOrigin(E.Volume)+CellMin(E.Position)):E.Position;
        AddNearbyPrefabOwners(World,Candidates);
    }
    DropUnsupportedPrefabs(Candidates);
}

void AVoxelBuildWorld::DropUnsupportedPrefabs(const TSet<FIntVector>& Candidates)
{
    if(Candidates.IsEmpty())return;
    // 审计 W3（2026-09-23）：Drop 从 TArray 换成 TSet——脱落循环里的 Drop.Contains 与
    // RemoveAll 谓词都是线性查找，多件同批脱落时是 O(n²)；TSet 把它降到常数。
    TSet<FIntVector> Drop,Grounded;
    TMap<FIntVector,const FVoxelBuildPrefabInstance*> ByAnchor;
    for(const auto& Piece:Prefabs)ByAnchor.Add(Piece.Cell,&Piece);
    // A mutually touching group must still have a path to an actual foundation.
    // Traverse only groups reached by the edit; a ground-level piece exits at its first footing.
    for(const FIntVector& Seed:Candidates)
    {
        if(Drop.Contains(Seed)||Grounded.Contains(Seed))continue;
        TArray<FIntVector> Pending={Seed};
        TSet<FIntVector> Seen,Adjacent;
        bool bGrounded=false;
        while(!Pending.IsEmpty())
        {
            const FIntVector Current=Pending.Pop(EAllowShrinking::No);
            if(Grounded.Contains(Current)){bGrounded=true;break;}
            if(Seen.Contains(Current)||Drop.Contains(Current))continue;
            const FVoxelBuildPrefabInstance* Piece=ByAnchor.FindRef(Current);
            if(!Piece)continue;
            Seen.Add(Current);
            Adjacent.Reset();
            if(IsPrefabSupported(*Piece,nullptr,&Adjacent)){Grounded.Add(Current);bGrounded=true;break;}
            for(const FIntVector& Next:Adjacent)if(!Seen.Contains(Next))Pending.Add(Next);
        }
        if(bGrounded)Grounded.Add(Seed);
        else Drop.Append(Seen);
    }
    if(Drop.IsEmpty())return;
    FString Names;
    TSet<FIntVector> Retained;
    for(const FIntVector& Anchor:Drop)
    {
        const FVoxelBuildPrefabInstance* Instance=Prefabs.FindByPredicate(
            [Anchor](const FVoxelBuildPrefabInstance& Entry){return Entry.Cell==Anchor;});
        const FVoxelBuildPrefab* Definition=Instance&&Palette?Palette->FindComponent(Instance->Id):nullptr;
        const FString Label=Definition?Definition->DisplayName.ToString():
            (Instance?Instance->Id.ToString():FString(TEXT("构件")));
        // 脱落 = 真的掉下来（2026-09-18）：占位网格补上调色板代表网格后切成刚体自由落体，
        // 逻辑构件挂上去跟随、停止交互，8 秒后一起销毁。没有可用网格／物理体时退回直接移除。
        // 炉内冶炼/存料的高炉脱落：尽力退料（落体无法像手动拆除那样拒绝）；背包放不下则随炉
        // 清任务与存料并在提示栏点名，不留孤儿条目（读档侧同样会丢弃孤儿，双保险）。
        if(Instance && !Instance->GateCuts.IsEmpty())
        {
            FString Reason;
            if(!CanRestoreGateWalls(Anchor,Reason)){Retained.Add(Anchor);continue;}
        }
        if(IsCampfireAt(Anchor)||FindSmelting(Anchor)||FuelAt(Anchor)>0)
        {
            FString RefundReason;
            if(!RefundSmeltingAt(Anchor,RefundReason))
            {
                // Keep campfire escrow intact if a durable transaction or refund is blocked.
                // A later removal can retry; never discard a guest's paid order on save failure.
                if(IsCampfireAt(Anchor)){Retained.Add(Anchor);continue;}
                UE_LOG(LogTemp,Warning,TEXT("PREFAB_DROP %s 炉内冶炼无法退料（%s），任务随炉清理"),*Label,*RefundReason);
                ClearSmelting(Anchor);SetFuel(Anchor,0);
                if(UGameInstance* Game=GetWorld()?GetWorld()->GetGameInstance():nullptr)
                    if(auto* Model=Game->GetSubsystem<UColdSteelStatusModel>())
                        Model->PostNotice(TEXT("构件脱落"),FString::Printf(TEXT("%s 炉内冶炼随炉丢失（背包已满）"),*Label),FString(),3.2f);
            }
        }
        if(IsCampfireAt(Anchor))ClearSmelting(Anchor);
        AActor* Piece=PrefabActors.FindRef(Anchor).Get();
        // 审计 W3（2026-09-23）：记录里还有这件构件、占位 Actor 却已经没了（外部销毁/GC 边界），
        // 原来会**无声**走完"删记录+清占格"——玩家只看到构件凭空消失。现在点名记日志。
        if(!Piece)UE_LOG(LogTemp,Error,TEXT("PREFAB_DROP %s @格(%d,%d,%d) 占位 Actor 已缺失 · 仅清理记录"),
            *Label,Anchor.X,Anchor.Y,Anchor.Z);
        auto* Placed=Piece?Cast<AVoxelBuildPrefabActor>(Piece):nullptr;
        // A village gate consists of two hinged leaves. Let both disappear
        // with their carrier when the foundation goes, including any repair target.
        const bool bVillageDefense=Instance&&VillageBuildDefense::IsVillageRecipe(Instance->Id);
        if(bVillageDefense)RemovedVillageDefenses.Add(Instance->InstanceId);
        const bool bFalling=Placed&&!bVillageDefense&&Placed->BeginFall(Definition?Definition->Mesh.LoadSynchronous():nullptr,8.f);
        if(Piece&&!bFalling)Piece->Destroy();
        PrefabActors.Remove(Anchor);
        Names+=Names.IsEmpty()?Label:FString::Printf(TEXT("、%s"),*Label);
        UE_LOG(LogTemp,Warning,TEXT("PREFAB_DROP %s 失去支撑 @格(%d,%d,%d) %s"),
            *Label,Anchor.X,Anchor.Y,Anchor.Z,bFalling?TEXT("落体"):TEXT("直接移除"));
    }
    for(const auto& Cell:Retained)Drop.Remove(Cell);
    if(Drop.IsEmpty())return;
    // 先记下将被腾空的全部占格（RemoveAll 之后 Footprint 就没处查了）。
    TArray<FIntVector> Vacated;TArray<FIntVector> Scratch;
    for(const FVoxelBuildPrefabInstance& Entry:Prefabs)
        if(Drop.Contains(Entry.Cell))
        {
            FillPrefabCells(Entry,Scratch);
            RemovePrefabOccupancy(Entry.Cell,Scratch);
            Vacated.Append(Scratch);
        }
    const bool RestoreWalls=Prefabs.ContainsByPredicate([&Drop](const auto& P){return Drop.Contains(P.Cell)&&!P.GateCuts.IsEmpty();});
    Prefabs.RemoveAll([&Drop](const FVoxelBuildPrefabInstance& Entry){return Drop.Contains(Entry.Cell);});
    // 脱落的高炉连燃料记录一起清（2026-09-24 回头审查）：SetFuel(0) 遇已升级记录会保留等级（为"烧空不丢升级"，
    // 炉子还在才对），但炉子本体脱落掉出后那条等级记录就成了无主残留——同格重建新炉会白捡旧等级。
    // 上面退料段已按格退过，这里无差别清掉脱落格的燃料记录；下一行 MarkSaveDirty 顺带落盘。
    if(RestoreWalls)RefreshPrefabOccupancy();
    Fuels.RemoveAll([&Drop](const FVoxelFurnaceFuel& E){return Drop.Contains(E.Cell);});
    // 腾出的格：原本只锚在这件构件上的体素要重判锚定，否则它会继续被当"有地基"撑着（2026-09-19）。
    ReanchorVoxelsAround(Vacated);
    MarkSaveDirty();
    Message=FString::Printf(TEXT("%s 失去支撑已脱落"),*Names);
    if(UGameInstance* Game=GetWorld()?GetWorld()->GetGameInstance():nullptr)
        if(auto* Model=Game->GetSubsystem<UColdSteelStatusModel>())
            Model->PostNotice(TEXT("构件脱落"),Message,FString(),3.2f);
}

bool AVoxelBuildWorld::CanPlacePrefab(FName Id,FIntVector Cell,int32 Yaw,FString& Reason,bool bSurfaceBacked,bool bDocked,
    const AActor* DockTarget,FTransform* OutPlacementPose,int32 GroundYawDegrees,bool bReplaceWall,TArray<FVillageGateCut>* OutCuts,TArray<FTransform>* PreviewBars) const
{
    if(!bReady||!Palette){Reason=Message;return false;}
    const FVoxelBuildPrefab* Definition=Palette->FindComponent(Id);
    if(!Definition){Reason=TEXT("缺少该构件定义");return false;}
    const bool bFortification=VillageWallStairs::CanDock(Id);
    const bool bVillage=VillageBuildDefense::IsVillageRecipe(Id);
    if(GroundYawDegrees!=INDEX_NONE&&(!bVillage||bDocked||Yaw!=0||GroundYawDegrees<0||GroundYawDegrees>=360))
    {Reason=TEXT("城防地面朝向无效");return false;}
    if(bVillage)
    {
        const auto* Hills=FindVillageConstructionWorld();
        const auto Required=VillageBuildDefense::RequiredTier(Id);
        if(VillageBuildDefense::UnlockedTier(Hills)<Required)
        {Reason=VillageBuildDefense::LockReason(Required);return false;}
    }
    const bool bWallMount=Definition->Mount==EVoxelPrefabMount::Wall;
    // 逻辑构件（门）只要求 Actor 类；普通构件仍然要求网格。
    if(Definition->ActorClass.IsNull()&&!Definition->Mesh.LoadSynchronous())
    {Reason=TEXT("构件网格尚未导入");return false;}
    const FIntVector Footprint=AVoxelBuildPrefabActor::RotatedFootprint(Definition->Footprint,Yaw);
    if(PrefabActors.FindRef(Cell).IsValid()||HasPrefabAt(Cell))
    {Reason=TEXT("该建造位置已被占用");return false;}
    FVoxelBuildPrefabInstance Probe;
    Probe.Id=Id;Probe.Cell=Cell;Probe.Yaw=Yaw;Probe.Footprint=Footprint;
    VillageWallStairs::FDock Dock;
    VillageGateReplacement::FOpening Opening;
    if(bReplaceWall)
    {
        FTransform GatePose;
        FIntVector Address;
        int32 Facing;
        if(!bDocked || !VillageGateReplacement::Layout(Id,DockTarget,Definition->Footprint,GatePose,Address,Facing)
            || Address!=Cell || Facing!=Yaw
            || !VillageGateReplacement::Collect(*this,*FindVillageConstructionWorld(),Id,DockTarget,GatePose,Opening,PreviewBars))
        {Reason=TEXT("替换位置已变化，请重新瞄准同一直线上的城墙");return false;}
        Probe.WallDockPose=GatePose;
        Probe.GateCuts=Opening.Cuts;
    }
    else if(bDocked)
    {
        if(!VillageWallStairs::FindDock(GetWorld(),Id,Definition->Footprint,Cell,Yaw,Dock,DockTarget))
        {Reason=TEXT("未找到匹配的城防接口，请重新瞄准");return false;}
        Probe.WallDockPose=Dock.Pose;
    }
    else if(GroundYawDegrees!=INDEX_NONE)
        Probe.WallDockPose=VillageBuildDefense::Placement(Id,Cell,Footprint,Yaw,GroundYawDegrees);
    FTransform Pose=bVillage?VillageWallStairs::Placement(Probe):FTransform::Identity;
    const UPrimitiveComponent* BearingRoof=nullptr;
    if(VillageBuildDefense::IsSiegeEngine(Id))
    {
        double FloorZ=0.;
        if(!SiegeFooting(*this,Id,Pose,nullptr,FloorZ,nullptr,&BearingRoof))
        {Reason=Id==VillageBuildDefense::Trebuchet?TEXT("投石机底架需要连续平面 · 避开楼梯口和平台边缘"):
            TEXT("器械底座需要完整、平缓的平台或地面");return false;}
        FVector Foot=Pose.GetLocation();Foot.Z=FloorZ;
        Pose.SetLocation(Foot);
        Probe.WallDockPose=Pose;
    }
    if(bVillage&&OutPlacementPose)*OutPlacementPose=Pose;
    if(VillageBuildDefense::IsSiegeEngine(Id))
    {
        if(!VillageDefenseFootprint::IsClear(*GetWorld(),VillageDefenseFootprint::Siege(Id),Pose,this,{},BearingRoof?2.:16.))
        {
            Reason=Id==VillageBuildDefense::Trebuchet?TEXT("机架或投臂摆动范围受阻 · 移动或旋转投石机"):
                Id==VillageBuildDefense::OilPot?TEXT("热油锅底座或锅柄被挡住，请避开垛口和楼梯口"):TEXT("弩炮机架被挡住 · 请避开垛口、楼梯栏杆或其他物体");
            return false;
        }
    }
    else if(bFortification)
    {
        const auto& Shape=VillageDefenseFootprint::Get(Id,Definition->Mesh.LoadSynchronous());
        if(!VillageDefenseFootprint::IsClear(*GetWorld(),Shape,Pose,this,Opening.Walls))
        {Reason=TEXT("城防构件与人物、建筑或地形重叠，请更换位置");return false;}
        if(bDocked && Id==VillageWallStairs::Id && !VillageWallStairs::HasClearStairEntrance(*GetWorld(),Pose))
        {Reason=TEXT("楼梯入口被挡住 · 用滚轮换向或选择另一段城墙");return false;}
    }
    else if(bVillage)
    {
        const FVector HalfSize=FVector(Definition->Footprint)*(CellSizeCm*.5);
        const FVector Center=Pose.GetLocation()+FVector(0.,0.,HalfSize.Z);
        FCollisionQueryParams Query(SCENE_QUERY_STAT(VillageBuildClearance),false,this);
        for(const AActor* Wall:Opening.Walls)Query.AddIgnoredActor(Wall);
        if(GetWorld()->OverlapAnyTestByObjectType(Center,Pose.GetRotation(),FCollisionObjectQueryParams(ECC_Pawn),
            FCollisionShape::MakeBox(HalfSize-FVector(1.)),Query))
        {
            Reason=TEXT("建造位置有人或动物，请让开后放置");
            return false;
        }
        // The snapped bottom cell can sit up to 20 cm below the sampled soil.
        // Space above it must be free of blocking scenery.
        const FVector Min=Center-HalfSize+FVector(1.,1.,20.);
        const FVector Max=Center+HalfSize-FVector(1.);
        if(GetWorld()->OverlapBlockingTestByChannel((Min+Max)*.5,Pose.GetRotation(),ECC_Pawn,
            FCollisionShape::MakeBox((Max-Min)*.5),Query))
        {Reason=TEXT("请移开构件，避开建筑或凸起的地面");return false;}
    }
    TOptional<FIntVector> Mate;
    const AActor* Support=Dock.Target?static_cast<const AActor*>(Dock.Target):BearingRoof?BearingRoof->GetOwner():nullptr;
    if(Support)
        if(const auto* Carrier=Cast<AVoxelBuildPrefabActor>(Support->GetAttachParentActor()))
            Mate=Carrier->AnchorCell();
    // On a proved roof, the floor and the pedestal may share a partially filled grid cell.
    // Its parapets and rails were still checked against each individual part above.
    // A gate spans thousands of cells. Moving actors and terrain are queried above
    // every time; repeat the discrete occupancy scan only when the preview or grid changes.
    if(!bVillage || bReplaceWall!=bCachedWallReplacement ||
        (bReplaceWall && !Opening.WallAnchors.Includes(CachedGridWallAnchors)) ||
        (bReplaceWall && Opening.WallAnchors.Num()!=CachedGridWallAnchors.Num()) || CachedGridRecipe!=Id || CachedGridRevision!=Revision || CachedGridMate!=Mate
        || !Pose.Equals(CachedGridPose,.001))
    {
        FString Conflict;
        if(!PrefabCellOwners.IsEmpty()||!Cells.IsEmpty()||!FreeVolumeWorldCells.IsEmpty())
        {
            TArray<FIntVector> Occupied;
            FillPrefabCells(Probe,Occupied);
            for(const FIntVector& Entry:Occupied)
            {
                for(auto Holder=PrefabCellOwners.CreateConstKeyIterator(Entry);Holder;++Holder)
                    if((!Mate.IsSet()||Holder.Value()!=Mate.GetValue())&&!Opening.WallAnchors.Contains(Holder.Value()))
                    {Conflict=TEXT("该位置已有构件");break;}
                if(!Conflict.IsEmpty())break;
                if(Cells.Contains(Entry)||FreeVolumeWorldCells.Contains(Entry))
                {Conflict=TEXT("该位置已有体素方块");break;}
            }
        }
        if(bVillage)
        {
            bCachedWallReplacement=bReplaceWall;
            CachedGridWallAnchors=Opening.WallAnchors;
            CachedGridRecipe=Id;
            CachedGridPose=Pose;
            CachedGridRevision=Revision;
            CachedGridMate=Mate;
            CachedGridConflict=Conflict;
            CachedGridSupport.Reset();
        }
        if(!Conflict.IsEmpty()){Reason=Conflict;return false;}
    }
    else if(!CachedGridConflict.IsEmpty()){Reason=CachedGridConflict;return false;}
    if(bWallMount)
    {
        if(!bSurfaceBacked){Reason=TEXT("必须贴在墙面或结构表面才能放置");return false;}
        FHitResult Surface;
        if(!FindWallBacking(Probe,Surface))
        {Reason=TEXT("需要可固定壁挂件的竖直表面");return false;}
    }
    else
    {
        // 悬空的构件不能放（2026-09-18 用户口径：构件要挂在结构上，不然拆掉周围就剩它浮着）。
        if(!Dock.Target&&!VillageBuildDefense::IsSiegeEngine(Id)&&!IsPrefabSupported(Probe))
        {Reason=TEXT("该位置悬空 · 构件要与体素、别的构件或地面接触");return false;}
    }
    if(bReplaceWall)
    {
        if(OutCuts)*OutCuts=Opening.Cuts;
        Reason=FString::Printf(TEXT("替换 %d 段城墙 · 保留门洞两端余墙 · 左键确认"),Opening.Cuts.Num());
        return true;
    }
    Reason=FString::Printf(TEXT("可放置 %s · %d × %d × %d cm · 左键确认"),
        *Definition->DisplayName.ToString(),Footprint.X*CellSizeCm,Footprint.Y*CellSizeCm,Footprint.Z*CellSizeCm);
    return true;
}

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

AVoxelBuildPrefabActor* AVoxelBuildWorld::SpawnPrefab(const FVoxelBuildPrefabInstance& Instance)
{
    const FVoxelBuildPrefab* Definition=Palette?Palette->FindComponent(Instance.Id):nullptr;
    if(!Definition||!GetWorld())return nullptr;
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
    UClass* LogicClass=Definition->ActorClass.LoadSynchronous();
    UStaticMesh* Mesh=LogicClass?nullptr:Definition->Mesh.LoadSynchronous();
    if(!LogicClass&&!Mesh)return nullptr;
    // The saved footprint is normalized from the palette so edits to the asset stay authoritative.
    const FIntVector Footprint=AVoxelBuildPrefabActor::RotatedFootprint(Definition->Footprint,Instance.Yaw);
    // 摆放口径按“是不是逻辑构件”分流，而不是看有没有网格：
    //   普通构件：网格包围盒居中于占格体积（ComputeTransform，历史口径）；
    //   逻辑构件（门等）：锚点 = 占格底面中心，构件自己从锚点往上搭。
    // 逻辑构件也带 Mesh（只用于抽屉缩略图），若照普通构件居中，门会被抬升半个身高、与预览不一致。
    const FTransform Transform=LogicClass
        ?FTransform(FRotator(0.f,Instance.Yaw*90.f,0.f),
            FVector(Instance.Cell)*20.f+FVector(Footprint.X*10.f,Footprint.Y*10.f,0.f))
        :AVoxelBuildPrefabActor::ComputeTransform(*Definition,Mesh,Instance.Cell,Instance.Yaw);
    FActorSpawnParameters Spawn;
    Spawn.Owner=this;Spawn.SpawnCollisionHandlingOverride=ESpawnActorCollisionHandlingMethod::AlwaysSpawn;
    auto* Piece=GetWorld()->SpawnActor<AVoxelBuildPrefabActor>(AVoxelBuildPrefabActor::StaticClass(),Transform,Spawn);
    if(!Piece)return nullptr;
    if(LogicClass&&LogicClass->IsChildOf(AColdSteelCampfire::StaticClass()))
    {
        // This new replicated child needs a replicated attachment anchor. Other prefab families
        // retain their current network path; client construction remains outside this feature.
        Piece->SetReplicates(true);
        Piece->SetReplicateMovement(true);
    }
    Piece->Configure(Instance.Id,Instance.Cell,Instance.Yaw,Mesh,Definition->Surface.LoadSynchronous(),StructuralContact);
    if(LogicClass)
    {
        // 门等自带逻辑的构件：挂成占位 Actor 的子件，占格/存档仍由 Instance 记录。
        FActorSpawnParameters LogicSpawn;
        LogicSpawn.Owner=this;
        LogicSpawn.SpawnCollisionHandlingOverride=ESpawnActorCollisionHandlingMethod::AlwaysSpawn;
        FTransform LogicTransform=Transform;
        LogicTransform.SetLocation(Transform.GetLocation()+Transform.GetRotation().RotateVector(Definition->ActorOffsetCm));
        if(AActor* Logic=GetWorld()->SpawnActor<AActor>(LogicClass,LogicTransform,LogicSpawn))
        {
            Logic->SetReplicates(true);Logic->SetReplicateMovement(true);
            // 逻辑构件自己接管外观：门／窗按调色板条目的材质整体替换（框与扇同一材质）。
            if(auto* Door=Cast<AColdSteelDoor>(Logic))Door->Configure(Definition->Surface.LoadSynchronous());
            else if(auto* Window=Cast<AColdSteelWindow>(Logic))Window->Configure(Definition->Surface.LoadSynchronous());
            else if(auto* Slide=Cast<AColdSteelSlidingDoor>(Logic))Slide->Configure(Definition->Surface.LoadSynchronous());
            else if(auto* Revolving=Cast<AColdSteelRevolvingDoor>(Logic))Revolving->Configure(Definition->Surface.LoadSynchronous());
            else if(auto* Fountain=Cast<AColdSteelFountain>(Logic))Fountain->Configure(Definition->Surface.LoadSynchronous());
            Logic->AttachToActor(Piece,FAttachmentTransformRules::KeepWorldTransform);
            Piece->AttachLogicActor(Logic);
        }
    }
    PrefabActors.Add(Instance.Cell,Piece);
    return Piece;
}

void AVoxelBuildWorld::TryGrantWorkshopTower()
{
    if(!HasAuthority() || !bReady || bClosing || bWorkshopTowerGranted)return;
    auto* Hills=FindVillageConstructionWorld();
    if(!Hills || !Hills->GetVillageSite().bPlaced ||
        !WorldKey.EndsWith(TEXT("|")+Hills->WorldId.ToString(EGuidFormats::Digits)) ||
        !Hills->IsVillagePlanUnlocked(TEXT("village_construction")))return;
    const auto& Site=Hills->GetVillageSite();
    for(const auto& Entry:Prefabs)
    {
        if(Entry.Id==VillageBuildDefense::HighTower && Site.IsWorkshopTowerPosition(VillageWallStairs::Placement(Entry).GetLocation()))
        {
            bWorkshopTowerGranted=true;
            MarkSaveDirty();
            return;
        }
    }

    const auto* Definition=Palette->FindComponent(VillageBuildDefense::HighTower);
    if(!Definition)return;
    FVoxelBuildPrefabInstance Tower;
    Tower.Id=VillageBuildDefense::HighTower;
    const FTransform SitePose=Site.WorkshopTowerPose();
    Tower.WallDockPose=SitePose;
    Tower.Yaw=(FMath::RoundToInt(SitePose.Rotator().Yaw/90.)+4)%4;
    Tower.Footprint=AVoxelBuildPrefabActor::RotatedFootprint(Definition->Footprint,Tower.Yaw);
    Tower.Cell=ToCell(SitePose.GetLocation())-FIntVector(Tower.Footprint.X/2,Tower.Footprint.Y/2,0);
    Tower.InstanceId=FGuid::NewGuid();

    // The two surveyed buildings share an eave. Only this workshop is exempt from clearance.
    TArray<AActor*> Neighbours;
    for(TActorIterator<AVillageMechanicalWorkshop> It(GetWorld());It;++It)
        if(It->GetOwner()==Hills)Neighbours.Add(*It);
    const auto& Shape=VillageDefenseFootprint::Get(Tower.Id,Definition->Mesh.LoadSynchronous());
    bool bClear=!bNetworkTransaction && !HasPrefabAt(Tower.Cell) &&
        VillageDefenseFootprint::IsClear(*GetWorld(),Shape,SitePose,this,Neighbours) && IsPrefabSupported(Tower);
    TArray<FIntVector> Occupied;
    if(bClear)
    {
        FillPrefabCells(Tower,Occupied);
        // A matching wall socket can share contact cells along the landing.
        VillageWallStairs::FDock Join;
        TOptional<FIntVector> WallAnchor;
        if(VillageWallStairs::FindDock(GetWorld(),Tower.Id,Definition->Footprint,Tower.Cell,Tower.Yaw,Join) &&
            Join.Pose.Equals(SitePose,.1) && Join.Target)
            if(auto* Carrier=Cast<AVoxelBuildPrefabActor>(Join.Target->GetAttachParentActor()))WallAnchor=Carrier->AnchorCell();
        for(const FIntVector& Cell:Occupied)
        {
            if(Cells.Contains(Cell) || FreeVolumeWorldCells.Contains(Cell)){bClear=false;break;}
            for(auto It=PrefabCellOwners.CreateConstKeyIterator(Cell);It;++It)
                if(!WallAnchor.IsSet() || It.Value()!=WallAnchor.GetValue()){bClear=false;break;}
            if(!bClear)break;
        }
    }
    if(!bClear || !SpawnPrefab(Tower))
    {
        GetWorldTimerManager().SetTimer(WorkshopTowerRetry,this,&AVoxelBuildWorld::TryGrantWorkshopTower,5.f,false);
        return;
    }
    Prefabs.Add(Tower);
    for(const FIntVector& Cell:Occupied)PrefabCellOwners.Add(Cell,Tower.Cell);
    CachedGridRecipe=NAME_None;
    bWorkshopTowerGranted=true;
    MarkSaveDirty();
}

bool AVoxelBuildWorld::PlacePrefab(FName Id,FIntVector Cell,int32 Yaw,bool bDocked,AActor* DockTarget,int32 GroundYawDegrees,bool bReplaceWall,int64 ExpectedWallSelection)
{
    if(!bReady||GetNetMode()==NM_Client)return false;
    const FVoxelBuildPrefab* Looking=Palette?Palette->FindComponent(Id):nullptr;
    // 壁挂件在组件侧已经确认过"瞄准的是竖直表面"，这里复检时要把这一点带进来，
    // 否则同一件会被自己的"必须贴墙"规则挡掉。
    const bool bSurfaceBacked=Looking&&Looking->Mount==EVoxelPrefabMount::Wall;
    FTransform PlacementPose;
    FVoxelBuildPrefabInstance Instance;
    if(!CanPlacePrefab(Id,Cell,Yaw,Message,bSurfaceBacked,bDocked,DockTarget,&PlacementPose,GroundYawDegrees,bReplaceWall,&Instance.GateCuts))return false;
    if(bReplaceWall && ExpectedWallSelection>=0 && ExpectedWallSelection!=VillageGateReplacement::WallSelection(Instance.GateCuts))
    {Message=TEXT("墙线已变化，请按更新后的预览重新放置");return false;}
    const FVoxelBuildPrefab* Definition=Looking;
    Instance.Id=Id;Instance.Cell=Cell;Instance.Yaw=((Yaw%4)+4)%4;
    Instance.Footprint=AVoxelBuildPrefabActor::RotatedFootprint(Definition->Footprint,Instance.Yaw);
    if(bDocked||GroundYawDegrees!=INDEX_NONE||VillageBuildDefense::IsSiegeEngine(Id))Instance.WallDockPose=PlacementPose;
    Instance.InstanceId=FGuid::NewGuid();
    if(!SpawnPrefab(Instance)){Message=TEXT("构件网格生成失败");return false;}
    Prefabs.Add(Instance);
    TArray<FIntVector> Occupied;
    if(bReplaceWall)
    {
        GateWallCells(Instance,Occupied);
        RefreshPrefabOccupancy();
        ReanchorVoxelsAround(Occupied,true);
        TSet<FIntVector> Dependents;
        for(const FIntVector& Changed:Occupied)AddNearbyPrefabOwners(Changed,Dependents);
        Dependents.Remove(Cell);
        DropUnsupportedPrefabs(Dependents);
    }
    else AddPrefabOccupancy(Instance,Occupied);
    MarkSaveDirty();
    UndoHistory.Remember(UndoPlayer,{nullptr,Instance.InstanceId,Instance.Cell});
    if(Id==TEXT("campfire"))if(const auto* Piece=PrefabActorAt(Cell))
        if(auto* Fire=Cast<AColdSteelCampfire>(Piece->Logic()))Fire->PublishSharedState(true);
    Message=FString::Printf(TEXT("已放置构件 · 共 %d 件 · 正在保存"),Prefabs.Num());
    return true;
}

// Use the original wall solids intersected with the gate opening. The new gate and its
// surviving neighbours need no support update outside this region.
void AVoxelBuildWorld::GateWallCells(const FVoxelBuildPrefabInstance& Gate,TArray<FIntVector>& Changed,TArray<TPair<FBox,FTransform>>* RestoredBoxes) const
{
    const auto* Hills=FindVillageConstructionWorld();
    for(TActorIterator<AVillageDefenseSection> It(GetWorld());It;++It)
    {
        if(It->GetOwner()!=Hills || (!It->IsA<AHighVillageWall>() && !It->IsRepairedCurtain()))continue;
        FVector2D Remaining;
        if(!VillageGateReplacement::IntervalFor(**It,Gate,Remaining))continue;
        const auto* Body=It->GetMasonry();
        UStaticMesh* Mesh=Body?Body->GetStaticMesh():nullptr;
        if(!Mesh || It->GetHealth()<=0.f)continue;
        const double Min=Remaining.X<=-149.999?Remaining.Y:-150.;
        const double Max=Remaining.Y>=149.999?Remaining.X:150.;
        VillageDefenseFootprint::FShape Region;
        const auto& Original=VillageDefenseFootprint::Get(It->IsA<AHighVillageWall>()?VillageBuildDefense::HighWall:VillageBuildDefense::StoneWall,Mesh);
        auto Intersect=[&](FBox Box)
        {
            Box.Min.X=FMath::Max(Min,Box.Min.X);
            Box.Max.X=FMath::Min(Max,Box.Max.X);
            Box.Min.Z=FMath::Max(0.,Box.Min.Z);
            if(Box.Max.X>Box.Min.X && Box.Max.Z>Box.Min.Z)
            {
                Region.Boxes.Add(Box);
                if(RestoredBoxes)RestoredBoxes->Emplace(Box,It->GetActorTransform());
            }
        };
        if(Original.Boxes.IsEmpty())Intersect(Mesh->GetBoundingBox());
        else for(const FBox& Box:Original.Boxes)Intersect(Box);
        TArray<FIntVector> Part;
        VillageDefenseFootprint::Rasterize(Region,It->GetActorTransform(),Part);
        Changed.Append(Part);
    }
}

bool AVoxelBuildWorld::CanRestoreGateWalls(FIntVector GateCell,FString& Reason) const
{
    const auto* Gate=Prefabs.FindByPredicate([GateCell](const auto& P){return P.Cell==GateCell;});
    if(!Gate || Gate->GateCuts.IsEmpty())return true;
    TArray<FIntVector> Changed;
    TArray<TPair<FBox,FTransform>> RestoredBoxes;
    GateWallCells(*Gate,Changed,&RestoredBoxes);
    TSet<FIntVector> Participants={GateCell};
    FCollisionQueryParams Query(SCENE_QUERY_STAT(GateWallRestore),false,this);
    if(const auto* Carrier=PrefabActorAt(GateCell))
    {
        Query.AddIgnoredActor(Carrier);
        Query.AddIgnoredActor(Carrier->Logic());
    }
    for(const auto& Wall:Prefabs)
        if(Wall.InstanceId.IsValid() && Gate->GateCuts.ContainsByPredicate([&Wall](const auto& Cut){return Cut.PlacedId==Wall.InstanceId;}))
            Participants.Add(Wall.Cell);
    // Original terrain and permanent scenery already coexisted with this wall.
    // Refuse to close the passage on a pawn or on construction added while the gate was open.
    for(const FIntVector& Cell:Changed)
    {
        if(Cells.Contains(Cell)||FreeVolumeWorldCells.Contains(Cell))
        {Reason=TEXT("门洞内已有方块，请先清空再恢复墙段");return false;}
        for(auto It=PrefabCellOwners.CreateConstKeyIterator(Cell);It;++It)
            if(!Participants.Contains(It.Value()))
            {Reason=TEXT("门洞内已有构件，请先移开再恢复墙段");return false;}
    }
    const FCollisionObjectQueryParams Pawns(ECC_Pawn);
    for(const auto& Part:RestoredBoxes)
    {
        const FTransform& Pose=Part.Value;
        const FVector Half=(Part.Key.GetExtent()*Pose.GetScale3D().GetAbs()-FVector(.01)).ComponentMax(FVector(.01));
        if(GetWorld()->OverlapAnyTestByObjectType(Pose.TransformPosition(Part.Key.GetCenter()),Pose.GetRotation(),
            Pawns,FCollisionShape::MakeBox(Half),Query))
        {Reason=TEXT("门洞内有人或动物，暂时无法恢复墙段");return false;}
    }
    return true;
}

bool AVoxelBuildWorld::RemovePrefab(AActor* Piece)
{
    return DismantlePrefab(Piece,true);
}

bool AVoxelBuildWorld::DismantlePrefab(AActor* Piece,bool bManual)
{
    AVoxelBuildPrefabActor* Target=Cast<AVoxelBuildPrefabActor>(Piece);
    // 传进来的可能是逻辑构件（门）本身：向上找承载它的占位记录。
    if(!Target)for(AActor* Parent=Piece?Piece->GetAttachParentActor():nullptr;Parent;Parent=Parent->GetAttachParentActor())
        if(auto* Found=Cast<AVoxelBuildPrefabActor>(Parent)){Target=Found;break;}
    if(!bReady||GetNetMode()==NM_Client||!IsValid(Target)||Target->GetOwner()!=this||Target->IsSceneStation())
    {Message=TEXT("只能拆除自己放置的构件");return false;}
    // 正在下落的构件（失去支撑后脱落）已经不在 Prefabs 记录里，但 Actor 还要飞一段时间。
    // 不特判的话会走到下面的 RemoveAll，提示"不在建筑记录中"——玩家清不掉它；
    // 更糟的是若同一格已经放了**新**构件，用 AnchorCell 查记录会命中新构件并把它销毁。
    // 落体件只销毁自己：不碰记录、不重判锚定（脱落时已经 Reanchor 过了）、不退还材料
    // （与手动拆除一致，构件本就免料）。
    if(Target->IsFalling())
    {
        if(AActor* Logic=Target->Logic())Logic->Destroy();
        Target->Destroy();
        Message=TEXT("已清除正在坠落的构件");
        return true;
    }
    const FIntVector Cell=Target->AnchorCell();
    if(PrefabActorAt(Cell)!=Target){Message=TEXT("构件已被替换，请重新选择");return false;}
    if(CutPlacedWalls.Contains(PrefabInstanceIdentity(Cell)))
    {Message=TEXT("这段墙已并入城门，请先拆除城门");return false;}
    const bool RestoreWall=Prefabs.ContainsByPredicate([Cell](const auto& P){return P.Cell==Cell&&!P.GateCuts.IsEmpty();});
    if(RestoreWall && !CanRestoreGateWalls(Cell,Message))return false;
    if(Target->PrefabId()==VoxelIncineratorId)
    {
        const FString Container=IncineratorContainerAt(Cell);
        const auto Occupied=[&](const UColdSteelStatusModel* Model)
        {return Model&&!Container.IsEmpty()&&ColdSteelIncineratorStorage::HasInputs(Model->Snapshot(),Container);};
        bool HasInputs=Occupied(ColdSteelAuthority::Model(this));
        // Each connected player's staged inputs belong to that player's profile.
        for(auto It=GetWorld()->GetPlayerControllerIterator();It&&!HasInputs;++It)
            if(const auto* PC=It->Get())
            {
                const auto* State=PC->GetPlayerState<AColdSteelPlayerState>();
                const auto* Model=PC->IsLocalController()?GetGameInstance()->GetSubsystem<UColdSteelStatusModel>():(State?State->GetShadowModel():nullptr);
                HasInputs=Occupied(Model);
            }
        if(HasInputs){Message=TEXT("焚化炉仍有暂存物品，请先取回再拆除");return false;}
    }
    if(Target->PrefabId()==VoxelCastingStationId)
    {
        FIntVector Furnace;
        if(FindCastingFurnace(Cell,Furnace))
            if(const auto* Job=FindSmelting(Furnace);Job&&(!Job->Recipe.IsNone()||!Job->Queue.IsEmpty()||!Job->Products.IsEmpty()))
            {Message=TEXT("铸造台仍有任务或成品，请先取出并处理炉内物料");return false;}
    }
    // 高炉拆除特判（2026-09-23 冶炼）：炉内有矿料或存料先退料（完成退产物、未完退原料、燃料折木材）；
    // 背包放不下就拒绝拆除——与放置"先扣料再提交"同一口径，不静默吞料也不凭空产锭。
    if(IsCampfireAt(Cell)||FindSmelting(Cell)||FuelAt(Cell)>0)
    {
        FString RefundReason;
        if(!RefundSmeltingAt(Cell,RefundReason)){Message=RefundReason;return false;}
    }
    if(IsCampfireAt(Cell))ClearSmelting(Cell);
    // 先记下这件构件的占格（RemoveAll 之后 Footprint 就没处查了）：拆除后贴着它的体素要重判锚定。
    TArray<FIntVector> Vacated,RestoredWallCells;
    if(const FVoxelBuildPrefabInstance* Entry=Prefabs.FindByPredicate(
            [Cell](const FVoxelBuildPrefabInstance& E){return E.Cell==Cell;}))
    {
        if(VillageBuildDefense::IsVillageRecipe(Entry->Id))RemovedVillageDefenses.Add(Entry->InstanceId);
        FillPrefabCells(*Entry,Vacated);
        if(RestoreWall)GateWallCells(*Entry,RestoredWallCells);
    }
    if(Prefabs.RemoveAll([Cell](const FVoxelBuildPrefabInstance& Entry){return Entry.Cell==Cell;})<=0)
    {Message=TEXT("该构件不在建筑记录中");return false;}
    if(auto* Found=PrefabActors.Find(Cell))
    {
        // 占位记录是 AActor：逻辑构件（门）挂在上面，拆除时先销毁它再销毁占位。
        if(auto* Placed=Cast<AVoxelBuildPrefabActor>(Found->Get()))
        {
            if(AActor* Logic=Placed->Logic())Logic->Destroy();
            Placed->Destroy();
        }
        else if(AActor* Actor=Found->Get())Actor->Destroy();
        PrefabActors.Remove(Cell);
    }
    if(IsValid(Target))Target->Destroy();
    // 拆除高炉＝这座炉连同它的升级与存料一起作废：清掉燃料记录（含只升过级、存料已烧空/为零的残留记录）。
    // 退料在上面已按格退过；非炉格的拆除这里 RemoveAll 命中 0，无副作用。
    Fuels.RemoveAll([Cell](const FVoxelFurnaceFuel& E){return E.Cell==Cell;});
    if(RestoreWall)RefreshPrefabOccupancy();
    else RemovePrefabOccupancy(Cell,Vacated);
    ReanchorVoxelsAround(Vacated);
    if(RestoreWall)ReanchorVoxelsAround(RestoredWallCells,true,true);
    TSet<FIntVector> Neighbors;
    if(!PrefabCellOwners.IsEmpty())
        for(const FIntVector& Freed:Vacated)AddNearbyPrefabOwners(Freed,Neighbors);
    DropUnsupportedPrefabs(Neighbors);
    MarkSaveDirty();
    // 手动拆除后本次建筑不再可撤销（2026-10-13 中危#5）：与体素"任何拆除清空撤销历史"同口径。
    if(bManual)UndoHistory.For(UndoPlayer).Reset();
    Message=Prefabs.IsEmpty()?TEXT("已拆除构件 · 正在保存"):FString::Printf(TEXT("已拆除构件 · 余 %d 件 · 正在保存"),Prefabs.Num());
    return true;
}

// —— 炉内冶炼（VBX v6）：任务与存料都按高炉锚格存，与构件记录同一份存档、同一生命周期。
// 进度＝已积累秒数＋当前燃烧段（UTC ticks，关闭游戏也计入，但受燃料封顶）；
// 结算/续燃/添燃料在 UColdSteelSmeltingSystem，这里只存状态。

const FVoxelSmeltingJob* AVoxelBuildWorld::FindSmelting(FIntVector Cell) const
{
    const FVoxelSmeltingJob* Job=SmeltingJobs.FindByPredicate([Cell](const FVoxelSmeltingJob& E){return E.Cell==Cell;});
    return Job&&(!Job->Recipe.IsNone()||Job->bCasting||IsCampfireAt(Cell))?Job:nullptr;
}

FVoxelSmeltingJob* AVoxelBuildWorld::FindSmeltingMutable(FIntVector Cell)
{
    FVoxelSmeltingJob* Job=SmeltingJobs.FindByPredicate([Cell](const FVoxelSmeltingJob& E){return E.Cell==Cell;});
    return Job&&(!Job->Recipe.IsNone()||Job->bCasting||IsCampfireAt(Cell))?Job:nullptr;
}

bool AVoxelBuildWorld::BeginSmelting(FIntVector Cell,FName Recipe,FString& Reason,int64 Batch)
{
    if(!bReady||GetNetMode()==NM_Client){Reason=TEXT("建筑世界未就绪");return false;}
    if(!IsFuelStationAt(Cell)){Reason=TEXT("目标不是已放置的燃料工作台");return false;}
    if(FindSmelting(Cell)){Reason=TEXT("这座高炉正在冶炼");return false;}
    if(Recipe.IsNone()){Reason=TEXT("冶炼任务无效");return false;}
    // 以"待燃"落账：是否立刻起燃由系统层 EnsureBurning 按存料决定。
    FVoxelSmeltingJob& Job=SmeltingJobs.AddDefaulted_GetRef();
    Job.Cell=Cell;Job.Recipe=Recipe;Job.ProgressSeconds=0;Job.BurnStartTicks=0;
    Job.BatchCount=FMath::Max<int64>(1,Batch);
    if(IsCampfireAt(Cell)&&FuelAt(Cell)>0)Job.BurnStartTicks=FDateTime::UtcNow().GetTicks();
    MarkSaveDirty();
    return true;
}

int32 AVoxelBuildWorld::FurnaceLevel(FIntVector Cell) const
{   return FurnaceUpgradeLevel(Cell,VoxelFurnaceAxisSpeed);   }

namespace { int32 FVoxelFurnaceFuel::* FurnaceLevelField(int32 Axis)
{   switch(Axis){case VoxelFurnaceAxisFuelCapacity:return &FVoxelFurnaceFuel::FuelLevel;
    case VoxelFurnaceAxisBatch:return &FVoxelFurnaceFuel::BatchLevel;default:return &FVoxelFurnaceFuel::Level;}   }   }

int32 AVoxelBuildWorld::FurnaceUpgradeLevel(FIntVector Cell,int32 Axis) const
{
    const FVoxelFurnaceFuel* Fuel=Fuels.FindByPredicate([Cell](const FVoxelFurnaceFuel& E){return E.Cell==Cell;});
    return Fuel?FMath::Clamp(Fuel->*FurnaceLevelField(Axis),1,VoxelFurnaceAxisMax(Axis)):1;
}

void AVoxelBuildWorld::SetFurnaceUpgradeLevel(FIntVector Cell,int32 Axis,int32 Level)
{
    if(Axis==VoxelFurnaceAxisSpeed)
        if(const auto* Job=FindSmelting(Cell);Job&&Job->bCasting)
            if(auto* Game=GetGameInstance())
                if(auto* System=Game->GetSubsystem<UColdSteelSmeltingSystem>())System->SettleFurnace(this,Cell);
    Level=FMath::Clamp(Level,1,VoxelFurnaceAxisMax(Axis));   // 燃料仓 6 档、其余 5 档（2026-09-24 数值调参）
    FVoxelFurnaceFuel* Fuel=Fuels.FindByPredicate([Cell](const FVoxelFurnaceFuel& E){return E.Cell==Cell;});
    if(!Fuel)
    {   // 升级可以发生在零存料时：建一条 0 秒记录承载等级（读档过滤认任一轴>1 的记录，不会丢）。
        FVoxelFurnaceFuel& Created=Fuels.AddDefaulted_GetRef();Created.Cell=Cell;Fuel=&Created;
    }
    int32 FVoxelFurnaceFuel::* Field=FurnaceLevelField(Axis);
    if(Fuel->*Field==Level)return;
    if(Axis==VoxelFurnaceAxisSpeed)
        if(auto* Job=FindSmeltingMutable(Cell);Job&&Job->bCasting)
            Job->ProgressSeconds*=UColdSteelSmeltingSystem::SpeedMultiplier(Fuel->*Field)
                /UColdSteelSmeltingSystem::SpeedMultiplier(Level);
    Fuel->*Field=Level;MarkSaveDirty();
}

void AVoxelBuildWorld::SetFurnaceLevel(FIntVector Cell,int32 Level)
{   SetFurnaceUpgradeLevel(Cell,VoxelFurnaceAxisSpeed,Level);   }

bool AVoxelBuildWorld::ClearSmelting(FIntVector Cell)
{
    const int32 Removed=SmeltingJobs.RemoveAll([Cell](const FVoxelSmeltingJob& E){return E.Cell==Cell;});
    if(Removed>0)MarkSaveDirty();
    return Removed>0;
}

double AVoxelBuildWorld::FuelAt(FIntVector Cell) const
{
    const FVoxelFurnaceFuel* Fuel=Fuels.FindByPredicate([Cell](const FVoxelFurnaceFuel& E){return E.Cell==Cell;});
    return Fuel?Fuel->FuelSeconds:0.;
}

void AVoxelBuildWorld::SetFuel(FIntVector Cell,double Seconds)
{
    if(auto* Piece=PrefabActorAt(Cell))if(auto* Campfire=Cast<AColdSteelCampfire>(Piece->Logic()))
        Campfire->SetFuelSeconds(Seconds);
    const int32 Index=Fuels.IndexOfByPredicate([Cell](const FVoxelFurnaceFuel& E){return E.Cell==Cell;});
    if(Seconds<=0)
    {
        // 零存料但已升级的炉子：记录要留着承载等级（否则升级随烧空丢失，2026-09-24 排查发现）。
        // v9 三轴：任一轴升过级都要保记录，不然烧空一次就把那条轴的等级洗掉。
        if(Index!=INDEX_NONE)
        {
            const FVoxelFurnaceFuel& E=Fuels[Index];
            if(E.Level>1||E.FuelLevel>1||E.BatchLevel>1)
            {   if(!FMath::IsNearlyEqual(E.FuelSeconds,0.0)){Fuels[Index].FuelSeconds=0;MarkSaveDirty();} return; }
            Fuels.RemoveAt(Index);MarkSaveDirty();
        }
        return;
    }
    if(Index!=INDEX_NONE)
    {
        if(FMath::IsNearlyEqual(Fuels[Index].FuelSeconds,Seconds))return;   // 值没变就不标脏
        Fuels[Index].FuelSeconds=Seconds;
    }
    else
    {
        FVoxelFurnaceFuel& Fuel=Fuels.AddDefaulted_GetRef();
        Fuel.Cell=Cell;Fuel.FuelSeconds=Seconds;
    }
    MarkSaveDirty();
}

void AVoxelBuildWorld::SetFurnaceFireTicks(FIntVector Cell,int64 Ticks)
{
    if(FVoxelFurnaceFuel* Fuel=Fuels.FindByPredicate([Cell](const FVoxelFurnaceFuel& E){return E.Cell==Cell;}))
        if(Fuel->FireStartTicks!=Ticks){Fuel->FireStartTicks=Ticks;MarkSaveDirty();}
}

int64 AVoxelBuildWorld::FurnaceFireTicks(FIntVector Cell) const
{
    const FVoxelFurnaceFuel* Fuel=Fuels.FindByPredicate([Cell](const FVoxelFurnaceFuel& E){return E.Cell==Cell;});
    return Fuel?Fuel->FireStartTicks:0;
}

bool AVoxelBuildWorld::RefundSmeltingAt(FIntVector Cell,FString& Reason)
{
    if(!FindSmelting(Cell)&&FuelAt(Cell)<=0)return true;   // 炉内本就没有矿料和存料。
    UGameInstance* Game=GetWorld()?GetWorld()->GetGameInstance():nullptr;
    auto* System=Game?Game->GetSubsystem<UColdSteelSmeltingSystem>():nullptr;
    if(!System){Reason=TEXT("冶炼系统未就绪");return false;}
    return System->RefundForTeardown(this,Cell,Reason);
}

FString AVoxelBuildWorld::IncineratorContainerAt(FIntVector Cell) const
{
    const auto* Piece=Prefabs.FindByPredicate([&](const auto& P){return P.Cell==Cell&&P.Id==VoxelIncineratorId;});
    return bReady&&Piece&&Piece->InstanceId.IsValid()?TEXT("incinerator.")+SaveSlot+TEXT(".")+Piece->InstanceId.ToString(EGuidFormats::Digits):FString();
}
