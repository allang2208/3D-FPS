#include "TemperateHillsPCG.h"
#include "EastRiverRoad.h"
#include "TemperateVillageGround.h"
#include "VillageCanopyDetail.h"
#include "TemperateHillsWorld.h"
#include "GameFramework/PlayerController.h"
#include "GameFramework/Pawn.h"
#include "PCGComponent.h"
#include "PCGContext.h"
#include "Data/PCGPointData.h"
#include "Metadata/PCGMetadata.h"
#include "Metadata/PCGMetadataAttributeTpl.h"
#include "UObject/GCObject.h"

TOptional<FVector> UTemperateHillsGuestSource::GetPosition() const
{
    const APlayerController* PC=Controller.Get();
    if(const APawn* Pawn=PC?PC->GetPawn():nullptr)return Pawn->GetActorLocation();
    return {};
}

TOptional<FVector> UTemperateHillsGuestSource::GetDirection() const
{
    const APlayerController* PC=Controller.Get();
    if(const APawn* Pawn=PC?PC->GetPawn():nullptr)return Pawn->GetActorForwardVector();
    return {};
}

struct FTemperateHillsPointsContext : public FPCGContext
{
    TArray<FTemperatePlacement> Placements;
    TSharedPtr<HillsVegetation::FNeighborhood> Neighbors;
    FBox Bounds;
    double NextY=0;
    bool Started=false;
    bool Prepared=false;
    TObjectPtr<UPCGPointData> PointData=nullptr;
    FPCGMetadataAttribute<FSoftObjectPath>* MeshAttribute=nullptr;
    FPCGMetadataAttribute<int64>* KeyAttribute=nullptr;
    FPCGMetadataAttribute<float>* RegionAttribute=nullptr;
    int32 NextPlacement=0;

    virtual void AddExtraStructReferencedObjects(FReferenceCollector& Collector) override
    {
        Collector.AddReferencedObject(PointData);
    }

    void BeginOutput(bool bGroundCover)
    {
        PointData=NewObject<UPCGPointData>();
        PointData->GetMutablePoints().Reserve(Placements.Num());
        MeshAttribute=PointData->Metadata->CreateAttribute<FSoftObjectPath>(TEXT("Mesh"),FSoftObjectPath(),false,true);
        KeyAttribute=PointData->Metadata->CreateAttribute<int64>(TEXT("CandidateKey"),0,false,true);
        if(bGroundCover)RegionAttribute=PointData->Metadata->CreateAttribute<float>(TEXT("RainforestWeight"),0.f,false,true);
    }

    bool AppendOutput(const ATemperateHillsWorld& World)
    {
        const double SliceEnd=FPlatformTime::Seconds()+.0005;
        TArray<FPCGPoint>& Points=PointData->GetMutablePoints();
        while(NextPlacement<Placements.Num())
        {
            const int32 BatchEnd=FMath::Min(NextPlacement+32,Placements.Num());
            for(;NextPlacement<BatchEnd;++NextPlacement)
            {
                const FTemperatePlacement& Placement=Placements[NextPlacement];
                // Village display owns these candidates at landscape-view distances.
                if(Placement.bVillagePlanting)continue;
                FPCGPoint& Point=Points.Emplace_GetRef();
                Point.Transform=Placement.Transform;
                Point.Seed=int32(Placement.Key);
                Point.BoundsMin=FVector(-50);
                Point.BoundsMax=FVector(50);
                Point.MetadataEntry=PointData->Metadata->AddEntry();
                MeshAttribute->SetValue(Point.MetadataEntry,Placement.Mesh);
                KeyAttribute->SetValue(Point.MetadataEntry,int64(Placement.CandidateId));
                if(RegionAttribute)
                {
                    const FVector P=Placement.Transform.GetLocation();
                    RegionAttribute->SetValue(Point.MetadataEntry,float(World.RainforestWeight(P.X,P.Y)));
                }
            }
            if(NextPlacement<Placements.Num()&&(ShouldStop()||FPlatformTime::Seconds()>=SliceEnd))return false;
        }
        FPCGTaggedData& Output=OutputData.TaggedData.Emplace_GetRef();
        Output.Pin=PCGPinConstants::DefaultOutputLabel;
        Output.Data=PointData;
        return true;
    }
};

class FTemperateHillsPointsElement : public IPCGElement
{
public:
    virtual bool IsCacheable(const UPCGSettings*) const override { return false; }
    virtual bool CanExecuteOnlyOnMainThread(FPCGContext*) const override { return true; }
protected:
    virtual FPCGContext* CreateContext() override { return new FTemperateHillsPointsContext(); }
    virtual bool ExecuteInternal(FPCGContext* Context) const override
    {
        auto* Component = Cast<UPCGComponent>(Context->ExecutionSource.Get());
        auto* Original = Component ? Component->GetOriginalComponent() : nullptr;
        auto* World = Original ? Cast<ATemperateHillsWorld>(Original->GetOwner()) : nullptr;
        if (!World || !World->bSurfaceReady) return true;
        const auto* Settings = Context->GetInputSettings<UTemperateHillsPointsSettings>();
        auto* State=static_cast<FTemperateHillsPointsContext*>(Context);
        if(State->PointData)return State->AppendOutput(*World);
        auto& Placements=State->Placements;
        if(Settings->Layer>=2&&Settings->Layer<=4)
        {
            if(!State->Started)
            {
                State->Bounds=Component->GetGridBounds();
                if(!World->PrepareQuarryForVegetation(State->Bounds))return false;
                State->NextY=State->Bounds.Min.Y;State->Started=true;
                const double Began=FPlatformTime::Seconds();
                State->Neighbors=World->BeginVegetationCell(State->Bounds);
                if(!State->Neighbors)return true;
                // A cold rock window and understory competition each fit a
                // movement frame separately. Yield between them on a cache miss.
                if(Context->ShouldStop()||FPlatformTime::Seconds()-Began>.0005)return false;
            }
            if(!State->Prepared)
            {
                State->Prepared=World->AdvanceVegetationCell(State->Neighbors,Settings->Layer==3);
                return false;
            }
            // Keep 2 m work units, but use spare time in the native PCG budget
            // instead of imposing another frame of latency after every strip.
            // Half-open world-space bounds keep seeded results identical when
            // the scheduler yields or neighbours generate in another order.
            const double SliceEnd=FPlatformTime::Seconds()+.0005;
            do
            {
                FBox Strip=State->Bounds;
                Strip.Min.Y=State->NextY;
                Strip.Max.Y=Settings->Layer==2?State->Bounds.Max.Y:FMath::Min(State->NextY+200.0,State->Bounds.Max.Y);
                World->GetVegetationStrip(Settings->Layer,Strip,*State->Neighbors,Placements);
                if (Settings->Layer==3 && World->GetNetMode()!=NM_DedicatedServer)
                    EastRiverRoad::ForLegacyBounds(*World,Strip,[&](const FBox& Outside){TemperateVillageGround::GatherStrip(*World,Outside,Placements);});
                State->NextY=Strip.Max.Y;
            }
            while(State->NextY<State->Bounds.Max.Y&&!Context->ShouldStop()&&FPlatformTime::Seconds()<SliceEnd);
            if(State->NextY<State->Bounds.Max.Y)return false;
            if(Settings->Layer==3)EastRiverRoad::ScatterDecals(*World,*Component,State->Bounds);
        }
        else
        {
            if (Settings->Layer == 0 && World->GetNetMode() != NM_DedicatedServer)
                if (auto* Canopy = World->FindComponentByClass<UVillageCanopyDetail>())
                    Canopy->WatchForestCell(Component);
            World->GetPlacements(Settings->Layer,Component->GetGridBounds(),Placements);
        }
        State->BeginOutput(Settings->Layer==3);
        if(Placements.Num()>32&&Context->ShouldStop())return false;
        return State->AppendOutput(*World);
    }
};

FPCGElementPtr UTemperateHillsPointsSettings::CreateElement() const
{
    return MakeShared<FTemperateHillsPointsElement>();
}
