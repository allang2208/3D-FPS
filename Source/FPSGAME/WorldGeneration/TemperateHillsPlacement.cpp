#include "EastRiverRoad.h"
#include "TemperateHillsWorld.h"
#include "TemperateIronOutcrops.h"
#include "TemperateHillsStreamingPrivate.h"
#include "TemperateVegetationPlacement.h"
#include "TemperateHillsSurface.h"
#include "TemperateShoreHabitat.h"
#include "../Production/ProductionOreRocks.h"
#include "Engine/StaticMesh.h"
#include "Engine/SkeletalMesh.h"
#include "ProfilingDebugging/CpuProfilerTrace.h"

namespace HillsPlacement
{
constexpr double Clearance=18.0;
constexpr double BucketSize=800.0;

bool Overlaps(const FBox& A,const FBox& B)
{
    return A.Min.X<=B.Max.X&&A.Max.X>=B.Min.X&&A.Min.Y<=B.Max.Y&&A.Max.Y>=B.Min.Y;
}

FBox MeshBox(const FSoftObjectPath& Path)
{
    const UObject* Object=Path.ResolveObject();
    if(const auto* Mesh=Cast<UStaticMesh>(Object))return Mesh->GetBoundingBox();
    if(const auto* Mesh=Cast<USkeletalMesh>(Object))return Mesh->GetBounds().GetBox();
    return FBox(ForceInit);
}

double Reach(const FBox& Box)
{
    // Includes an off-centre pivot and all possible yaw/slope rotations.
    const FVector Far=Box.Min.GetAbs().ComponentMax(Box.Max.GetAbs());
    return Far.Size();
}

double RockReach(const UTemperateHillsAssets& Assets)
{
    double Max=0;
    const auto Add=[&](const TArray<TSoftObjectPtr<UStaticMesh>>& Meshes,double Scale)
    {
        for(const auto& Ref:Meshes)if(const auto* Mesh=Ref.Get())
            Max=FMath::Max(Max,Reach(Mesh->GetBoundingBox())*Scale);
    };
    Add(Assets.Rocks,2.0);Add(Assets.RiverRocks,.75);Add(Assets.Cliffs,1.4);Add(Assets.ForestRoots,.95);
    if (const auto* Mesh = Assets.RainforestBankBoulder.Get())
    {
        const FBox Box = Mesh->GetBoundingBox();
        const double AnchorScale = 350. / FMath::Max(1., FMath::Max(Box.GetSize().X, Box.GetSize().Y));
        Max = FMath::Max(Max, Reach(Box) * FMath::Max(1.15, AnchorScale));
    }
    for(const auto& Ref:Assets.FallenLogs)if(const auto* Mesh=Ref.Get())
    {
        const FBox Box=Mesh->GetBoundingBox();const FVector Size=Box.GetSize();
        Max=FMath::Max(Max,Reach(Box)*620.0/FMath::Max(1.0,FMath::Max(Size.X,Size.Y)));
    }
    for(const auto& Path:ProductionOreRocks::AllMeshes())if(const auto* Mesh=Cast<UStaticMesh>(Path.ResolveObject()))
    {
        const FBox Box=Mesh->GetBoundingBox();const FVector Size=Box.GetSize();
        const double Scale=FMath::Min(210.0/FMath::Max(1.0,FMath::Max(Size.X,Size.Y)*.90),
            145.0/FMath::Max(1.0,Size.Z*.82));
        Max=FMath::Max(Max,Reach(Box)*Scale*1.10);
    }
    return Max;
}

// A batch-local spatial index. No actor searches, physics queries, per-instance
// ticks or persistent caches that could outlive terrain edits or a seed change.
struct FFootprints
{
    TArray<FBox> Boxes;
    TMap<FIntPoint,TArray<int32>> Buckets;
    void Add(const FBox& Box)
    {
        const int32 Index=Boxes.Add(Box);
        for(int32 Y=FMath::FloorToInt(Box.Min.Y/BucketSize);Y<=FMath::FloorToInt(Box.Max.Y/BucketSize);++Y)
        for(int32 X=FMath::FloorToInt(Box.Min.X/BucketSize);X<=FMath::FloorToInt(Box.Max.X/BucketSize);++X)
            Buckets.FindOrAdd(FIntPoint(X,Y)).Add(Index);
    }
    bool Any(const FBox& Box,TFunctionRef<bool(int32)> Accept) const
    {
        for(int32 Y=FMath::FloorToInt(Box.Min.Y/BucketSize);Y<=FMath::FloorToInt(Box.Max.Y/BucketSize);++Y)
        for(int32 X=FMath::FloorToInt(Box.Min.X/BucketSize);X<=FMath::FloorToInt(Box.Max.X/BucketSize);++X)
            if(const auto* Indices=Buckets.Find(FIntPoint(X,Y)))for(const int32 Index:*Indices)
                if(Overlaps(Box,Boxes[Index])&&Accept(Index))return true;
        return false;
    }
};

struct FVegetationRockMask
{
    FBox Coverage=FBox(ForceInit);
    FFootprints Index;
    TArray<uint64> SolidIds;
    TArray<FTemperatePlacement> Supports;
    uint32 EditRevision=0;
    double RockRadius=0.;
    bool Ready=false;
};
}

void ATemperateHillsWorld::GetPlacements(int32 Layer,const FBox& Bounds,TArray<FTemperatePlacement>& Out,bool IncludeRegrowth) const
{
    if(IsForestVillage())
    {
        if(Layer==0)
        {
            GetForestStandingTrees(Bounds,Out);
            if(IncludeRegrowth)GetRegrowingTrees(Bounds,Out);
        }
        return;
    }
    if(!Assets||Layer<0||Layer>4)return;
    if(Layer==1)
    {
        GetRockPlacements(Bounds,Out);
        return;
    }
    if(Layer==0){GetBasePlacements(Layer,Bounds,Out,IncludeRegrowth);return;}
    GetVegetationPlacements(Layer,Bounds,Out);
}

void ATemperateHillsWorld::GetRockPlacements(const FBox& Bounds,TArray<FTemperatePlacement>& Out,bool IncludeDepleted) const
{
    TRACE_CPUPROFILER_EVENT_SCOPE(TemperateRockPlacement);
    using namespace HillsPlacement;
    // The halo covers the sum of two maximum footprints, not only this cell.
    // Conflict decisions therefore agree for adjacent PCG cells and mining's
    // tiny lookup box, independent of which layer/cell happened to load first.
    const double Halo=2*RockReach(*Assets)+2*Clearance;
    TArray<FTemperatePlacement> Raw;
    GetBasePlacements(1,Bounds.ExpandBy(FVector(Halo,Halo,0)),Raw);
    TArray<FTemperatePlacement> Supported;
    TArray<uint32> Priorities;
    FFootprints Index;
    TMap<FIntPoint,FTemperatePlacement> Trees;
    TSet<FIntPoint> EmptyTrees;
    for(auto& P:Raw)
    {
        const auto* Mesh=Cast<UStaticMesh>(P.Mesh.ResolveObject());if(!Mesh)continue;
        const auto In=[&](const TArray<TSoftObjectPtr<UStaticMesh>>& List)
        {return List.ContainsByPredicate([&](const auto& Ref){return Ref.Get()==Mesh;});};
        const bool Cliff=In(Assets->Cliffs),Wood=In(Assets->FallenLogs)||In(Assets->ForestRoots);
        const bool Ore=ProductionOreRocks::AllMeshes().Contains(P.Mesh);
        if(!Cliff&&!Wood)
        {
            if(bReady&&Streaming&&IsInGameThread()&&Streaming->Batches[HillsStreaming::Solids].Ready)
            {
                // Adjacent windows fit the same rocks in their competition halos.
                // A fixed-size table also caches rejected fits without retaining assets.
                auto& Fits=Streaming->RockFits;
                constexpr uint32 SlotCount=2048;
                if(Fits.IsEmpty())Fits.SetNum(SlotCount);
                auto& Fit=Fits[TemperateHillsSurface::Mix(GetTypeHash(P.CandidateId))&(SlotCount-1)];
                if(Fit.Id!=P.CandidateId||Fit.Mesh.Get()!=Mesh||Fit.Seed!=Seed||Fit.Revision!=TerrainEditRevision||!Fit.Input.Equals(P.Transform,0.))
                {
                    Fit.Id=P.CandidateId;Fit.Mesh=Mesh;Fit.Seed=Seed;Fit.Revision=TerrainEditRevision;
                    Fit.Input=Fit.Output=P.Transform;
                    Fit.Supported=FitRockPlacement(*Mesh,Fit.Output,Ore);
                }
                if(!Fit.Supported)continue;
                P.Transform=Fit.Output;
            }
            else if(!FitRockPlacement(*Mesh,P.Transform,Ore))continue;
        }
        const FBox Box=Mesh->GetBoundingBox().TransformBy(P.Transform);
        const FBox TrunkZone=Box.ExpandBy(120.0);
        bool TrunkOverlap=false;
        for(int32 Y=FMath::FloorToInt(TrunkZone.Min.Y/1200)-1;Y<=FMath::FloorToInt(TrunkZone.Max.Y/1200)+1&&!TrunkOverlap;++Y)
        for(int32 X=FMath::FloorToInt(TrunkZone.Min.X/1200)-1;X<=FMath::FloorToInt(TrunkZone.Max.X/1200)+1;++X)
        for(const auto Cell:EastRiverRoad::TreeKeys(*this,X,Y))
        {
            if(EmptyTrees.Contains(Cell))continue;
            auto* Tree=Trees.Find(Cell);
            if(!Tree)
            {
                FTemperatePlacement Candidate;
                if(!TreeCandidate(Cell.X,Cell.Y,Candidate)){EmptyTrees.Add(Cell);continue;}
                Tree=&Trees.Add(Cell,MoveTemp(Candidate));
            }
            const FVector T=Tree->Transform.GetLocation();
            if(T.X>=TrunkZone.Min.X&&T.X<=TrunkZone.Max.X&&T.Y>=TrunkZone.Min.Y&&T.Y<=TrunkZone.Max.Y)
            {TrunkOverlap=true;break;}
        }
        if(TrunkOverlap)continue;
        Index.Add(Box.ExpandBy(Clearance));
        // Keep scenery precedence explicit; seed breaks ties inside a family.
        Priorities.Add((Cliff?0U:Wood?0x40000000U:TemperateIronOutcrops::IsVeinRock(P.CandidateId)?0x80000000U:0xc0000000U)|
            (TemperateHillsSurface::Mix(P.Key^0x7f4a7c15U)&0x3fffffffU));
        Supported.Add(MoveTemp(P));
    }
    for(int32 I=0;I<Supported.Num();++I)
    {
        const auto& P=Supported[I];const FVector At=P.Transform.GetLocation();
        if(At.X<Bounds.Min.X||At.X>=Bounds.Max.X||At.Y<Bounds.Min.Y||At.Y>=Bounds.Max.Y)continue;
        // Compare with ALL supported raw neighbours, including rejected and
        // depleted ones: removal must not spawn a replacement or change winners
        // in another cell that has not regenerated yet.
        const bool Conflict=Index.Any(Index.Boxes[I],[&](int32 J)
        {return J!=I&&(Priorities[J]<Priorities[I]||
            (Priorities[J]==Priorities[I]&&Supported[J].CandidateId<P.CandidateId));});
        if(!Conflict&&(IncludeDepleted||!IsProductionDepleted(1,P.CandidateId)))Out.Add(P);
    }
}

bool ATemperateHillsWorld::FitRockPlacement(const UStaticMesh& Mesh,FTransform& Placement,bool Ore) const
{
    const FVector At=Placement.GetLocation();
    const auto Bank=RiverPlan?RiverPlan->Sample(At.X,At.Y):TemperateRiver::FSample();
    const bool River=Bank.Bank>.02;
    if(Ore&&SurfaceNormal(At.X,At.Y).Z<.86)return false;
    const double HeightCm=Mesh.GetBoundingBox().GetSize().Z*Placement.GetScale3D().Z;
    const double Burial=Ore?FMath::Clamp(HeightCm*(River?.22:.16),6.0,25.0):FMath::Clamp(HeightCm*.12,10.0,80.0);
    const double Relief=Ore?FMath::Clamp(HeightCm*.25,12.0,35.0):FMath::Clamp(HeightCm*.18,25.0,120.0);
    const double Half=SizeMeters*50-100;
    const FVector2D Start(GetStartLocation());
    const auto Ground=[&](const FVector& Probe,double& Z)
    {
        if(FMath::Abs(Probe.X)>Half||FMath::Abs(Probe.Y)>Half||PathDistance(Probe.X,Probe.Y)<350||
            FVector2D::DistSquared(FVector2D(Probe),Start)<1600.0*1600.0)return false;
        const auto Water=RiverPlan?RiverPlan->Sample(Probe.X,Probe.Y):TemperateRiver::FSample();
        if(!River&&Water.Bank>.03)return false;
        Z=Height(Probe.X,Probe.Y);
        // Ore remains reachable on exposed or shallow margins. Ordinary river
        // stones may remain submerged; this is not a ban on river ecology.
        return !Ore||Water.Bank<=0||Z>=Water.WaterZ-35;
    };
    return ProductionOreRocks::FitToSurface(Mesh,Placement,Ground,Burial,Relief);
}

const TArray<FTemperatePlacement>& ATemperateHillsWorld::UpdateVegetationRockMask(const FBox& Bounds,double PlantReach,
    TSharedPtr<HillsPlacement::FVegetationRockMask>& Mask,double UpcomingPlantReach) const
{
    using namespace HillsPlacement;
    // One mask per PCG cell job, also shared by its 2 m grass strips.
    // During initial streaming the available rock meshes can still change.
    if(!Mask||!Mask->Ready||Mask->EditRevision!=TerrainEditRevision)
    {
        Mask=MakeShared<FVegetationRockMask>();
        Mask->RockRadius=RockReach(*Assets);
        Mask->EditRevision=TerrainEditRevision;
        Mask->Ready=bReady;
    }
    const double Halo=FMath::Max(850.,Mask->RockRadius+PlantReach+Clearance);
    const FBox Required=Bounds.ExpandBy(FVector(Halo,Halo,0));
    if(!Mask->Coverage.IsValid||!Mask->Coverage.IsInsideOrOnXY(Required.Min)||!Mask->Coverage.IsInsideOrOnXY(Required.Max))
    {
        Mask->Coverage+=Required;
        Mask->Index=FFootprints();
        TArray<FTemperatePlacement> Rocks;
        // Keep depleted candidates in the mask so mining does not cause nearby
        // plants to reappear. Wait for the solid assets before retaining results.
        const auto GatherMaskRocks=[this](const FBox& Area,TArray<FTemperatePlacement>& Result)
        {
            GetRockPlacements(Area,Result,true);
            GetWhiteCliffPlacements(Area,Result);
        };
        if(!bReady||!Streaming||!Streaming->Batches[HillsStreaming::Solids].Ready||!IsInGameThread())
            GatherMaskRocks(Mask->Coverage,Rocks);
        else
        {
            auto& Windows=Streaming->VegetationRockWindows;
            if(Streaming->RockWindowRevision!=TerrainEditRevision)
            {
                Windows.Reset();
                Streaming->RockWindowRevision=TerrainEditRevision;
            }
            // Reserve room for the next understory footprint check while this
            // job can still yield. The local mask retains its exact bounds.
            const double Extra=FMath::Max(0.,UpcomingPlantReach-PlantReach);
            const FBox Lookup=Mask->Coverage.ExpandBy(FVector(Extra,Extra,0.));
            auto* Window=Windows.FindByPredicate([&](const auto& W)
            {
                return W.Area.IsInsideOrOnXY(Lookup.Min)&&W.Area.IsInsideOrOnXY(Lookup.Max);
            });
            if(!Window)
            {
                TRACE_CPUPROFILER_EVENT_SCOPE(HillsBuildVegetationRockWindow);
                if(Windows.Num()<8)Window=&Windows.Emplace_GetRef();
                else
                {
                    Window=&Windows[0];
                    for(auto& W:Windows)if(W.LastUse<Window->LastUse)Window=&W;
                }
                // Cover two extra grass cells on either side. Fit/priority
                // selection still includes the generator's full conflict halo.
                Window->Area=Lookup.ExpandBy(FVector(3200.,3200.,0.));
                Window->Rocks.Reset();
                GatherMaskRocks(Window->Area,Window->Rocks);
            }
            Window->LastUse=FPlatformTime::Cycles64();
            for(const auto& P:Window->Rocks)
            {
                // The white cliff kit is owned by its unpadded mesh bounds;
                // all other fitted rocks are owned by their final pivot.
                if((P.CandidateId>>60)==5)
                {
                    const FBox Box=HillsVegetation::BoundsOf(P.Mesh.ResolveObject());
                    if(Box.IsValid&&Box.TransformBy(P.Transform).Intersect(Mask->Coverage))Rocks.Add(P);
                    continue;
                }
                const FVector At=P.Transform.GetLocation();
                if(At.X>=Mask->Coverage.Min.X&&At.X<Mask->Coverage.Max.X&&
                   At.Y>=Mask->Coverage.Min.Y&&At.Y<Mask->Coverage.Max.Y)Rocks.Add(P);
            }
        }
        Mask->Supports.Reset();
        Mask->SolidIds.Reset(Rocks.Num());
        for(const auto& P:Rocks)
        {
            const FBox Shape=MeshBox(P.Mesh).TransformBy(P.Transform);
            Mask->Index.Add(Shape.ExpandBy(Clearance));
            Mask->SolidIds.Add(P.CandidateId);
            // Reuse the already-resolved rock neighbourhood as community
            // anchors. Nurse-log dressing keeps its own mesh-family filter.
            if(Shape.IsValid&&Shape.GetSize().GetMax()>80.)Mask->Supports.Add(P);
        }
    }
    return Mask->Supports;
}

void ATemperateHillsWorld::ExcludeRockFootprints(const FBox& Bounds,TArray<FTemperatePlacement>& Plants,
    TSharedPtr<HillsPlacement::FVegetationRockMask>& Mask) const
{
    TRACE_CPUPROFILER_EVENT_SCOPE(TemperateRockFootprints);
    if(Plants.IsEmpty())return;
    using namespace HillsPlacement;
    TMap<FSoftObjectPath,FBox> Boxes;
    double PlantReach=0;
    for(const auto& P:Plants)
    {
        // Rendering bounds may include metres of wind padding. Compare actual
        // plant geometry against the solid rock mask, as in root fitting.
        if(!Boxes.Contains(P.Mesh))Boxes.Add(P.Mesh,HillsVegetation::BoundsOf(P.Mesh.ResolveObject()));
        const FBox& Box=Boxes.FindChecked(P.Mesh);
        if(Box.IsValid)PlantReach=FMath::Max(PlantReach,Reach(Box)*P.Transform.GetScale3D().GetAbsMax());
    }
    UpdateVegetationRockMask(Bounds,PlantReach,Mask);
    Plants.RemoveAll([&](const FTemperatePlacement& P)
    {
        const FBox& Local=Boxes.FindChecked(P.Mesh);
        if(!Local.IsValid)return true;
        const bool bContact=TemperateShore::TouchesSupport(P.CandidateId);
        const uint64 Parent=bContact?TemperateShore::RiverParent(P.CandidateId):0;
        return Mask->Index.Any(Local.TransformBy(P.Transform),[&](int32 Index)
        {
            return !bContact||Mask->SolidIds[Index]!=Parent;
        });
    });
}
