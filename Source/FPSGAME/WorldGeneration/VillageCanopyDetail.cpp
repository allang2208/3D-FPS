#include "VillageCanopyDetail.h"
#include "TemperateHillsWorld.h"
#include "ProfilingDebugging/CpuProfilerTrace.h"
#include "Components/InstancedSkinnedMeshComponent.h"
#include "Components/InstancedStaticMeshComponent.h"
#include "Engine/StaticMesh.h"
#include "Math/GenericOctree.h"
#include "PCGComponent.h"
#include "PCGManagedResource.h"
#include "Subsystems/PCGSubsystem.h"

UVillageCanopyDetail::UVillageCanopyDetail()
{
    PrimaryComponentTick.bCanEverTick = true;
    PrimaryComponentTick.TickGroup = TG_PostUpdateWork;
}

UVillageCanopyDetail* UVillageCanopyDetail::For(ATemperateHillsWorld& Hills)
{
    if (auto* Current = Hills.FindComponentByClass<UVillageCanopyDetail>()) return Current;
    auto* Detail = NewObject<UVillageCanopyDetail>(&Hills, NAME_None, RF_Transient);
    Hills.AddInstanceComponent(Detail);
    Detail->RegisterComponent();
    return Detail;
}

void UVillageCanopyDetail::SetForest(UPCGComponent* TreeLayer)
{
    if (Forest.Get() == TreeLayer) return;
    ReleaseForest();
    Forest = TreeLayer;
    bDiscoverExisting = TreeLayer != nullptr;
}

void UVillageCanopyDetail::AddTree(UPrimitiveComponent* Tree)
{
    if (!Tree) return;
    // The planting actor also calls this after a batch expands existing bounds.
    bTreesChanged = true;
    if (Trees.Contains(Tree)) return;
    float Scale = 1.f;
    if (auto* Static = Cast<UInstancedStaticMeshComponent>(Tree))
    {
        if (!Static->GetStaticMesh() || Static->GetStaticMesh()->GetNumLODs() <= 1) return;
        Scale = Static->GetLODDistanceScale();
    }
    else if (!Tree->IsA<UInstancedSkinnedMeshComponent>()) return;
    Trees.Add(Tree, FTreeDetail{Tree, Scale, false});
}

void UVillageCanopyDetail::FTreeDetail::Apply(bool bReduce)
{
    if (bReduce == bReduced) return;
    if (auto* Skinned = Cast<UInstancedSkinnedMeshComponent>(Tree.Get()))
        Skinned->SetAnimationMinScreenSize(bReduce ? .145f : 0.f);
    else if (auto* Static = Cast<UInstancedStaticMeshComponent>(Tree.Get()))
        Static->SetLODDistanceScale(NormalScale * (bReduce ? .85f : 1.f));
    bReduced = bReduce;
}

void UVillageCanopyDetail::ForgetTree(FTreeKey Tree)
{
    if (auto* Group = Trees.Find(Tree))
    {
        if (Tree.IsValid()) Group->Apply(false);
        Trees.Remove(Tree);
    }
}

void UVillageCanopyDetail::RemoveTree(UPrimitiveComponent* Tree)
{
    ForgetTree(Tree);
}

void UVillageCanopyDetail::WatchForestCell(UPCGComponent* Cell)
{
    if (!Cell || !Forest.IsValid() || Cell->GetOriginalComponent() != Forest.Get() || CellTrees.Contains(Cell)) return;
    const auto& Site = CastChecked<ATemperateHillsWorld>(GetOwner())->GetVillageSite();
    const FVector Extent(Site.Extent() + FVector2D(24000.), 25000.);
    if (!FBox::BuildAABB(Site.Ground, Extent).Intersect(Cell->GetGridBounds())) return;

    CellTrees.Add(Cell);
    Cell->OnPCGGraphGeneratedDelegate.AddUObject(this, &ThisClass::QueueCell);
    Cell->OnPCGGraphCancelledDelegate.AddUObject(this, &ThisClass::QueueCell);
    Cell->OnPCGGraphCleanedDelegate.AddUObject(this, &ThisClass::ReleaseCell);
    QueueCell(Cell);
}

void UVillageCanopyDetail::QueueCell(UPCGComponent* Cell)
{
    PendingCells.Add(Cell);
}

void UVillageCanopyDetail::ReleaseCell(UPCGComponent* Cell)
{
    PendingCells.Remove(Cell);
    Cell->OnPCGGraphGeneratedDelegate.RemoveAll(this);
    Cell->OnPCGGraphCancelledDelegate.RemoveAll(this);
    Cell->OnPCGGraphCleanedDelegate.RemoveAll(this);
    if (auto* Members = CellTrees.Find(Cell))
        for (const FTreeKey& Tree : *Members) ForgetTree(Tree);
    CellTrees.Remove(Cell);
}

void UVillageCanopyDetail::ReleaseForest()
{
    TArray<FCellKey> Cells;
    CellTrees.GenerateKeyArray(Cells);
    for (const FCellKey& Key : Cells)
    {
        if (auto* Cell = Key.Get()) ReleaseCell(Cell);
        else if (auto* Members = CellTrees.Find(Key))
            for (const FTreeKey& Tree : *Members) ForgetTree(Tree);
    }
    PendingCells.Reset();
    CellTrees.Reset();
}

void UVillageCanopyDetail::RefreshCells()
{
    TRACE_CPUPROFILER_EVENT_SCOPE(VillageCanopy_DiscoverCells);
    if (bDiscoverExisting)
    {
        if (auto* PCG = UPCGSubsystem::GetInstance(GetWorld()))
        {
            bDiscoverExisting = false;
            const auto& Site = CastChecked<ATemperateHillsWorld>(GetOwner())->GetVillageSite();
            const FVector Extent(Site.Extent() + FVector2D(24000.), 25000.);
            if (Forest.IsValid())
                PCG->ForAllRegisteredIntersectingLocalComponents(Forest.Get(), FBoxCenterAndExtent(Site.Ground, Extent),
                    [this](UPCGComponent* Cell) { WatchForestCell(Cell); });
        }
    }
    for (const FCellKey& Key : PendingCells)
    {
        auto* Cell = Key.Get();
        if (!Cell) continue;
        TSet<FTreeKey> Current;
        Cell->ForEachManagedResource([&Current](UPCGManagedResource* Resource)
        {
            if (!Resource || Resource->IsMarkedUnused()) return;
            UPrimitiveComponent* Tree = nullptr;
            if (auto* Skin = Cast<UPCGManagedISKMComponent>(Resource)) Tree = Skin->GetComponent();
            else if (auto* Static = Cast<UPCGManagedISMComponent>(Resource)) Tree = Static->GetComponent();
            if (Tree) Current.Add(Tree);
        });
        auto& Previous = CellTrees.FindChecked(Key);
        for (const FTreeKey& Tree : Previous)
            if (!Current.Contains(Tree)) ForgetTree(Tree);
        for (const FTreeKey& Tree : Current) AddTree(Tree.Get());
        Previous = MoveTemp(Current);
    }
    PendingCells.Reset();
    // Teardown can destroy a partition actor without a graph cleanup notification.
    for (auto It = CellTrees.CreateIterator(); It; ++It)
        if (!It.Key().IsValid())
        {
            for (const FTreeKey& Tree : It.Value()) ForgetTree(Tree);
            It.RemoveCurrent();
        }
}

void UVillageCanopyDetail::TickComponent(float Dt, ELevelTick Type, FActorComponentTickFunction* TickFunction)
{
    Super::TickComponent(Dt, Type, TickFunction);
    if (bDiscoverExisting || !PendingCells.IsEmpty()) RefreshCells();
    if (Trees.IsEmpty()) return;
    bool bDiscontinuity = false;
    const bool bViewChanged = PreviousView.Update(*GetWorld(), bDiscontinuity);
    bPendingView |= bDiscontinuity || (bViewChanged && !PreviousView.bScoped);
    const double Now = GetWorld()->GetTimeSeconds();
    if (!bTreesChanged && (!bPendingView || (!bDiscontinuity && Now < NextMovingUpdate))) return;

    TRACE_CPUPROFILER_EVENT_SCOPE(VillageCanopy_ClassifyDistance);
    NextMovingUpdate = Now + .20;
    bTreesChanged = false;
    bPendingView = false;
    for (auto It = Trees.CreateIterator(); It; ++It)
    {
        auto& Group = It.Value();
        auto* Tree = Group.Tree.Get();
        if (!Tree) { It.RemoveCurrent(); continue; }
        // A batch that crosses the near zone retains its authored static LOD thresholds.
        const bool bReduce = !PreviousView.bScoped &&
            VillagePresentationView::Distance(*GetWorld(), Tree->Bounds.Origin, Tree->Bounds.SphereRadius) >
            (Group.bReduced ? 5200. : 6400.);
        Group.Apply(bReduce);
    }
}

void UVillageCanopyDetail::EndPlay(const EEndPlayReason::Type Reason)
{
    ReleaseForest();
    for (auto& Pair : Trees) if (Pair.Key.IsValid()) Pair.Value.Apply(false);
    Trees.Reset();
    Super::EndPlay(Reason);
}
