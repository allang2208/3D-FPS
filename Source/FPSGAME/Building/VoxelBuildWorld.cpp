#include "VoxelBuildWorld.h"
#include "VoxelBuildPalette.h"
#include "VoxelBuildRuntime.h"
#include "VoxelBuildPersistence.h"
#include "VoxelCollapseFragment.h"

#include "Components/DynamicMeshComponent.h"
#include "Components/CapsuleComponent.h"
#include "GameFramework/Character.h"
#include "Kismet/GameplayStatics.h"
#include "Misc/SecureHash.h"
#include "EngineUtils.h"
#include "PhysicalMaterials/PhysicalMaterial.h"

// Keep construction cleanup of the runtime pointer where its type is complete.
AVoxelBuildWorld::AVoxelBuildWorld(FVTableHelper& Helper) : Super(Helper) {}

AVoxelBuildWorld::AVoxelBuildWorld()
{
    PrimaryActorTick.bCanEverTick=true;PrimaryActorTick.TickGroup=TG_PrePhysics;
    SetRootComponent(CreateDefaultSubobject<USceneComponent>(TEXT("VoxelRoot")));
    Runtime=MakeUnique<FVoxelBuildRuntime>();SetCanBeDamaged(true);
}
AVoxelBuildWorld::~AVoxelBuildWorld()=default;
FIntVector AVoxelBuildWorld::ToCell(const FVector& P){return FIntVector(FMath::FloorToInt(P.X/20),FMath::FloorToInt(P.Y/20),FMath::FloorToInt(P.Z/20));}
FVector AVoxelBuildWorld::CellMin(FIntVector P){return FVector(P)*20;}
FVector AVoxelBuildWorld::CellCenter(FIntVector P){return CellMin(P)+FVector(10);}
FIntVector AVoxelBuildWorld::ChunkFor(FIntVector P)
{
    auto Floor=[](int32 N){return N>=0?N/16:-int32((-(int64)N+15)/16);};
    return FIntVector(Floor(P.X),Floor(P.Y),Floor(P.Z));
}
FName AVoxelBuildWorld::MaterialAt(FIntVector P) const {const auto* Value=Cells.Find(P);return Value?*Value:NAME_None;}
bool AVoxelBuildWorld::OwnsSurface(const UPrimitiveComponent* C) const {return C&&C->GetOwner()==this;}

FName AVoxelBuildWorld::VolumeMaterialAt(FGuid Volume,FIntVector Cell) const
{
    if(!Volume.IsValid())return MaterialAt(Cell);
    const auto* Data=FreeVolumes.Find(Volume);const auto* Value=Data?Data->Cells.Find(Cell):nullptr;
    return Value?*Value:NAME_None;
}
FVector AVoxelBuildWorld::VolumeOrigin(FGuid Volume) const
{
    const auto* Data=FreeVolumes.Find(Volume);return Data?Data->Origin:FVector::ZeroVector;
}
int32 AVoxelBuildWorld::BlockCount() const
{
    int32 Count=Cells.Num();for(const auto& Entry:FreeVolumes)Count+=Entry.Value.Cells.Num();return Count;
}
int32 AVoxelBuildWorld::UnsupportedBlockCount() const {return SupportGraph?SupportGraph->Nodes.Num()-SupportGraph->Supported.Num():0;}
bool AVoxelBuildWorld::ResolveHit(const FHitResult& Hit,FVoxelBuildKey& Key) const
{
    if(!OwnsSurface(Hit.GetComponent())||!SupportGraph)return false;
    const FVector Point=Hit.ImpactPoint-Hit.ImpactNormal*.5;
    for(const auto& Candidate:SupportGraph->Near(Point-FVector(10)))
    {
        const FVector Min=SupportGraph->Nodes.FindChecked(Candidate).Min;
        if(FBox(Min-FVector(.01),Min+FVector(20.01)).IsInsideOrOn(Point)){Key=Candidate;return true;}
    }
    return false;
}

bool AVoxelBuildWorld::Initialize(const FString& InWorldKey,UVoxelBuildPalette* InPalette)
{
    if(GetNetMode()!=NM_Standalone||bReady||!InPalette)return false;
    Palette=InPalette;WorldKey=InWorldKey;
    StructuralContact=NewObject<UPhysicalMaterial>(this);
    StructuralContact->Friction=.8f;StructuralContact->Restitution=.03f;
    FTCHARToUTF8 KeyBytes(*WorldKey);FMD5 KeyHash;uint8 Digest[16];
    KeyHash.Update(reinterpret_cast<const uint8*>(KeyBytes.Get()),KeyBytes.Length());KeyHash.Final(Digest);
    SaveSlot=TEXT("Voxel20_")+BytesToHex(Digest,16);
    for(const auto& Entry:Palette->Materials)
    {
        UMaterialInterface* Surface=Entry.Surface.LoadSynchronous();
        if(Entry.Id.IsNone()||!Surface||MaterialSlots.Contains(Entry.Id)){Message=TEXT("建造材质未准备完成");return false;}
        MaterialSlots.Add(Entry.Id,SurfaceMaterials.Add(Surface));
    }
    if(SurfaceMaterials.IsEmpty()){Message=TEXT("没有可用的建造材质");return false;}
    UVoxelBuildSave* LoadedData=nullptr;
    if(UGameplayStatics::DoesSaveGameExist(SaveSlot,0))
    {
        LoadedData=VoxelPersistence::Load(SaveSlot);
        if(!LoadedData||LoadedData->Version<1||LoadedData->Version>3||LoadedData->CellSizeCm!=20||LoadedData->WorldKey!=WorldKey)
        {Message=TEXT("建筑存档版本不兼容，已保留原档");return false;}
        for(const auto& Cell:LoadedData->Cells)
        {
            if(!MaterialSlots.Contains(Cell.Material)){Message=TEXT("建筑存档缺少材料定义，已保留原档");return false;}
            Cells.Add(Cell.Position,Cell.Material);
        }
        for(const auto& Volume:LoadedData->FreeVolumes)
        {
            if(!Volume.Id.IsValid()||Volume.Origin.ContainsNaN()||FreeVolumes.Contains(Volume.Id))
            {Message=TEXT("自由建筑存档无效，已保留原档");return false;}
            for(const auto& Cell:Volume.Cells)if(!MaterialSlots.Contains(Cell.Value))
            {Message=TEXT("自由建筑存档缺少材料定义，已保留原档");return false;}
            FreeVolumes.Add(Volume.Id,Volume);
        }
        TSet<FGuid> FragmentIds;
        for(const auto& F:LoadedData->Fragments)
        {
            if(!F.Id.IsValid()||FragmentIds.Contains(F.Id)||F.Transform.ContainsNaN())
            {Message=TEXT("残骸存档无效，已保留原档");return false;}
            FragmentIds.Add(F.Id);
            for(const auto& C:F.Cells)if(!MaterialSlots.Contains(C.Material)||C.Min.ContainsNaN())
            {Message=TEXT("残骸材料或位置无效，已保留原档");return false;}
        }
        CellDamage=LoadedData->Damage;LegacyProtected=LoadedData->LegacyProtected;
    }
    RefreshSupportGraph();
    if(LoadedData)
    {
        for(const auto& B:LoadedData->BrokenBonds)SupportGraph->Break(B);
        SupportGraph->SolveConnectivity();
        if(LoadedData->Version<3)for(const auto& E:SupportGraph->Nodes)LegacyProtected.Add(E.Key);
    }
    TArray<FVoxelEditCell> Loaded;for(const auto& E:Cells)Loaded.Add({E.Key,NAME_None,E.Value,{}});
    for(const auto& V:FreeVolumes)for(const auto& E:V.Value.Cells)Loaded.Add({E.Key,NAME_None,E.Value,V.Key});
    RebuildAffected(Loaded);bReady=true;
    for(const auto& E:SupportGraph->Nodes)if(!LegacyProtected.Contains(E.Key))Runtime->DirtySupport.Add(E.Key);
    if(LoadedData)for(const auto& F:LoadedData->Fragments)EnqueueFragment(F);
    Message=LegacyProtected.IsEmpty()?TEXT("建筑已载入 · 承重系统已启用"):TEXT("旧建筑已保留 · 编辑相关结构后启用承重");
    return true;
}

bool AVoxelBuildWorld::CanPlace(const TArray<FIntVector>& Positions,FName Material,FString& Reason) const
{return CanPlaceInVolume({},Positions,Material,Reason);}
bool AVoxelBuildWorld::EditCells(const TArray<FIntVector>& Positions,FName Material)
{return EditVolumeCells({},Positions,Material);}

bool AVoxelBuildWorld::CanPlaceInVolume(FGuid Volume,const TArray<FIntVector>& Positions,FName Material,FString& Reason) const
{
    if(Volume.IsValid()&&!FreeVolumes.Contains(Volume)){Reason=TEXT("目标建筑已改变");return false;}
    for(const auto& Cell:Positions)if(!VolumeMaterialAt(Volume,Cell).IsNone()){Reason=TEXT("该位置已有方块");return false;}
    return CanPlaceAt(VolumeOrigin(Volume),Positions,Material,Reason);
}
bool AVoxelBuildWorld::CanPlaceFree(FVector Origin,const TArray<FIntVector>& Positions,FName Material,FString& Reason) const
{
    return CanPlaceAt(Origin,Positions,Material,Reason);
}

void AVoxelBuildWorld::RefreshSupportGraph()
{
    SupportGraph=MakeShared<FVoxelSupportGraph>();
    auto Add=[&](FGuid Volume,FIntVector Cell,FName Material)
    {
        const FVoxelBuildKey Key{Volume,Cell};const FVector Min=VolumeOrigin(Volume)+CellMin(Cell);
        const auto* Definition=Palette->Find(Material);
        SupportGraph->Add({Key,Min,false,Definition&&Definition->bSupportsWeight,Material,Palette->Physical(Material),CellDamage.FindRef(Key)});
    };
    for(const auto& E:Cells)Add({},E.Key,E.Value);
    for(const auto& V:FreeVolumes)for(const auto& E:V.Value.Cells)Add(V.Key,E.Key,E.Value);
    // Only exposed bottoms can form a foundation. Interior voxels in tall
    // solid structures need no terrain raycasts during world initialization.
    for(auto& E:SupportGraph->Nodes)
    {
        bool Covered=false;
        if(const auto* Edges=SupportGraph->Edges.Find(E.Key))for(const auto& Other:*Edges)
        {
            FVoxelContact Contact;const auto& Below=SupportGraph->Nodes.FindChecked(Other);
            if(FVoxelSupportGraph::Contact(E.Value.Min,Below.Min,Contact)&&Contact.Normal.Z<-.5&&Contact.Area>.0399){Covered=true;break;}
        }
        E.Value.bAnchor=!Covered&&IsGroundAnchor(E.Value.Min);AnchorCache.Add(E.Key,E.Value.bAnchor);
    }
    SupportGraph->SolveConnectivity();
}

bool AVoxelBuildWorld::CanPlaceAt(FVector Origin,const TArray<FIntVector>& Positions,FName Material,FString& Reason) const
{
    if(!bReady||!SupportGraph){Reason=Message;return false;}
    const auto* Definition=Palette->Find(Material);
    if(!Definition||Positions.IsEmpty()||Origin.ContainsNaN()){Reason=TEXT("请选择有效的建筑位置和材料");return false;}
    FVoxelSupportGraph Draft;const FGuid DraftId=FGuid::NewGuid();TSet<FIntVector> Seen;
    for(const auto& Cell:Positions)
    {
        if(Seen.Contains(Cell))continue;Seen.Add(Cell);
        const FVector Min=Origin+CellMin(Cell);
        if(SupportGraph->Overlaps(Min)){Reason=TEXT("位置与已有建筑重叠");return false;}
        bool Anchored=false;
        if(!ScenePlacementAllowed(Min,Reason,&Anchored))return false;
        for(const auto& Key:SupportGraph->Near(Min))
        {
            const auto& Existing=SupportGraph->Nodes.FindChecked(Key);FVoxelContact Contact;
            if(Existing.bBearing&&SupportGraph->Supported.Contains(Key)&&!Runtime->PendingCells.Contains(Key)
                &&FVoxelSupportGraph::Contact(Existing.Min,Min,Contact))Anchored=true;
        }
        Draft.Add({{DraftId,Cell},Min,Anchored,Definition->bSupportsWeight});
    }
    Draft.SolveConnectivity();
    if(Draft.Supported.Num()!=Draft.Nodes.Num()){Reason=TEXT("缺少与地基相连的接触面");return false;}
    Reason=FString::Printf(TEXT("可放置 %d 格 · 新增 %.1f kg · 放置后计算承重"),Seen.Num(),Seen.Num()*Palette->Physical(Material).DensityKgM3*.008f);
    return true;
}

bool AVoxelBuildWorld::EditVolumeCells(FGuid Volume,const TArray<FIntVector>& Positions,FName Material)
{
    if(!bReady||GetNetMode()!=NM_Standalone)return false;
    if(Volume.IsValid()&&!FreeVolumes.Contains(Volume)){Message=TEXT("目标建筑已改变");return false;}
    if(!Material.IsNone()&&!CanPlaceInVolume(Volume,Positions,Material,Message))return false;
    TArray<FVoxelEditCell> Edit;TSet<FIntVector> Seen;
    for(const auto& P:Positions)
    {
        if(Seen.Contains(P))continue;Seen.Add(P);
        const FName Before=VolumeMaterialAt(Volume,P);if(Before!=Material)Edit.Add({P,Before,Material,Volume});
    }
    if(Edit.IsEmpty()){Message=TEXT("没有可拆除的体素方块");return false;}
    return Commit(Edit,true);
}

bool AVoxelBuildWorld::PlaceFree(FVector Origin,const TArray<FIntVector>& Positions,FName Material)
{
    if(!bReady||GetNetMode()!=NM_Standalone)return false;
    if(!CanPlaceFree(Origin,Positions,Material,Message))return false;
    FVoxelFreeVolume Volume;Volume.Id=FGuid::NewGuid();Volume.Origin=Origin;FreeVolumes.Add(Volume.Id,Volume);
    if(!EditVolumeCells(Volume.Id,Positions,Material)){FreeVolumes.Remove(Volume.Id);return false;}
    return true;
}

bool AVoxelBuildWorld::CanCommit(const TArray<FVoxelEditCell>& Edit,FString& Reason) const
{
    for(const auto& E:Edit)
    {
        const FVoxelBuildKey Key{E.Volume,E.Position};
        if(VolumeMaterialAt(E.Volume,E.Position)!=E.Before||(E.Volume.IsValid()&&!FreeVolumes.Contains(E.Volume)))
        {Reason=TEXT("建筑已改变，本次编辑未生效");return false;}
        if(Runtime->PendingCells.Contains(Key)){Reason=TEXT("该结构正在倒塌，请稍候");return false;}
        if(!E.After.IsNone())
        {
            if(!Palette->Find(E.After)){Reason=TEXT("缺少建筑材料定义");return false;}
            const FVector Min=VolumeOrigin(E.Volume)+CellMin(E.Position);
            if(!ScenePlacementAllowed(Min,Reason))return false;
            if(E.Before.IsNone()&&SupportGraph->Overlaps(Min)){Reason=TEXT("编辑位置与已有建筑重叠");return false;}
        }
    }
    return true;
}

void AVoxelBuildWorld::SetCell(const FVoxelEditCell& E,bool bAfter)
{
    const FName Material=bAfter?E.After:E.Before;
    auto& Target=E.Volume.IsValid()?FreeVolumes.FindChecked(E.Volume).Cells:Cells;
    if(Material.IsNone())Target.Remove(E.Position);else Target.Add(E.Position,Material);
}

void AVoxelBuildWorld::ApplyChanges(const TArray<FVoxelEditCell>& Edit)
{
    for(const auto& E:Edit)
    {
        const FVoxelBuildKey Key{E.Volume,E.Position};
        Runtime->NodeEpoch.Add(Key,Revision+1);
        if(const auto* Existing=SupportGraph->Nodes.Find(Key);Existing&&Existing->AddedMassKg>0)
            for(auto It=Runtime->Loads.CreateIterator();It;++It)if(It.Value().Key==Key)It.RemoveCurrent();
        if(const auto* Edges=SupportGraph->Edges.Find(Key))
            for(const auto& Neighbor:*Edges){Runtime->DirtySupport.Add(Neighbor);Runtime->NodeEpoch.Add(Neighbor,Revision+1);}
        SupportGraph->Remove(Key);SetCell(E,true);AnchorCache.Remove(Key);CellDamage.Remove(Key);
        Runtime->LoadRatios.Remove(Key);LegacyProtected.Remove(Key);
        if(!E.After.IsNone())
        {
            // A newly built block has fresh joints; old debris has independent identities.
            for(auto It=SupportGraph->Broken.CreateIterator();It;++It)if(It->A==Key||It->B==Key)It.RemoveCurrent();
            const FVector Min=VolumeOrigin(E.Volume)+CellMin(E.Position);const bool Anchor=IsGroundAnchor(Min);
            const auto* Definition=Palette->Find(E.After);AnchorCache.Add(Key,Anchor);
            SupportGraph->Add({Key,Min,Anchor,Definition&&Definition->bSupportsWeight,E.After,Palette->Physical(E.After)});
            // Connectivity remains provisional until the worker publishes stresses.
            bool Supported=Anchor;
            if(const auto* Edges=SupportGraph->Edges.Find(Key))for(const auto& Neighbor:*Edges)
            {Supported|=SupportGraph->Supported.Contains(Neighbor);Runtime->NodeEpoch.Add(Neighbor,Revision+1);}
            if(Supported)SupportGraph->Supported.Add(Key);
            Runtime->DirtySupport.Add(Key);
        }
    }
    ++Revision;Runtime->NextIterations=256;Runtime->StructureAt=GetWorld()->GetTimeSeconds()+.08;
    RebuildAffected(Edit);MarkSaveDirty();
}

bool AVoxelBuildWorld::Commit(const TArray<FVoxelEditCell>& Edit,bool bRemember)
{
    if(!CanCommit(Edit,Message))return false;
    ApplyChanges(Edit);
    if(bRemember){History.Add(Edit);if(History.Num()>32)History.RemoveAt(0);}
    Message=FString::Printf(TEXT("已修改 %d 格 · 正在计算承重并保存"),Edit.Num());return true;
}

bool AVoxelBuildWorld::Undo()
{
    if(!bReady||History.IsEmpty()){Message=TEXT("没有可撤销的操作");return false;}
    TArray<FVoxelEditCell> Reverse;for(const auto& E:History.Last())Reverse.Add({E.Position,E.After,E.Before,E.Volume});
    if(!Commit(Reverse,false))return false;
    History.Pop();Message=TEXT("已撤销 · 正在保存");return true;
}

void AVoxelBuildWorld::Tick(float Delta)
{
    Super::Tick(Delta);if(!bReady||bClosing)return;
    for(const auto& E:Fragments)if(IsValid(E.Value))E.Value->SampleVelocity();
    TickDamage();TickMeshes();TickFragments();TickStructure();TickPersistence();
}

void AVoxelBuildWorld::EndPlay(const EEndPlayReason::Type Reason)
{
    bClosing=true;
    if(bReady)
    {
        while(!Runtime->DamageQueue.IsEmpty())TickDamage();
        // Join only at world teardown; workers own snapshots and never touch UObjects.
        if(Runtime->Stress.IsValid())Runtime->Stress.Wait();
        for(auto& Job:Runtime->MeshJobs)if(Job.Future.IsValid())Job.Future.Wait();
        for(auto& E:Runtime->PendingFragments)if(E.Value->Future.IsValid())E.Value->Future.Wait();
        TickPersistence(true);
    }
    Super::EndPlay(Reason);
}

FString AVoxelBuildWorld::StructureStatus() const
{
    if(Runtime->bSaveFailed)return TEXT("保存失败 · 建筑仍在内存中，将重试");
    if(!Runtime->PendingFragments.IsEmpty()||!Runtime->Activation.IsEmpty())
        return FString::Printf(TEXT("倒塌处理中 · 活动物理块 %d"),Runtime->AwakeBodies);
    if(Runtime->Stress.IsValid()||!Runtime->DirtySupport.IsEmpty()||!Runtime->GatherQueue.IsEmpty())return TEXT("正在计算承重");
    if(Runtime->bStressApproximate)return TEXT("结构求解未收敛 · 未应用估算破坏");
    if(!LegacyProtected.IsEmpty())return TEXT("旧建筑保留 · 编辑或破坏后计算承重");
    return Runtime->bSaveDirty||Runtime->SaveJob.IsValid()?TEXT("正在保存"):TEXT("承重已更新");
}
