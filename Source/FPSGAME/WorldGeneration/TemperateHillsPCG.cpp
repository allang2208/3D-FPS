#include "TemperateHillsPCG.h"
#include "TemperateHillsWorld.h"
#include "PCGComponent.h"
#include "PCGContext.h"
#include "Data/PCGPointData.h"
#include "Metadata/PCGMetadata.h"
#include "Metadata/PCGMetadataAttributeTpl.h"

struct FTemperateHillsPointsContext : public FPCGContext
{
    TArray<FTemperatePlacement> Placements;
    FBox Bounds;
    double NextY=0;
    bool Started=false;
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
        auto& Placements=State->Placements;
        if(Settings->Layer==3)
        {
            if(!State->Started)
            {
                State->Bounds=Component->GetGridBounds();
                State->NextY=State->Bounds.Min.Y;State->Started=true;
            }
            // Process at most a 16 m x 2 m strip per scheduler invocation.
            // Half-open world-space bounds keep seeded results identical when
            // the scheduler yields or neighbours generate in another order.
            FBox Strip=State->Bounds;
            Strip.Min.Y=State->NextY;
            Strip.Max.Y=FMath::Min(State->NextY+200.0,State->Bounds.Max.Y);
            World->GetPlacements(3,Strip,Placements);
            State->NextY=Strip.Max.Y;
            if(State->NextY<State->Bounds.Max.Y)return false;
        }
        else World->GetPlacements(Settings->Layer,Component->GetGridBounds(),Placements);
        auto* Data = NewObject<UPCGPointData>();
        auto* MeshAttribute = Data->Metadata->CreateAttribute<FSoftObjectPath>(TEXT("Mesh"), FSoftObjectPath(), false, true);
        auto* KeyAttribute = Data->Metadata->CreateAttribute<int64>(TEXT("CandidateKey"), 0, false, true);
        TArray<FPCGPoint>& Points = Data->GetMutablePoints();
        Points.Reserve(Placements.Num());
        for (const FTemperatePlacement& Placement : Placements)
        {
            FPCGPoint& Point = Points.Emplace_GetRef();
            Point.Transform = Placement.Transform;
            Point.Seed = int32(Placement.Key);
            Point.BoundsMin = FVector(-50);
            Point.BoundsMax = FVector(50);
            Point.MetadataEntry = Data->Metadata->AddEntry();
            MeshAttribute->SetValue(Point.MetadataEntry, Placement.Mesh);
            KeyAttribute->SetValue(Point.MetadataEntry, int64(Placement.CandidateId));
        }
        FPCGTaggedData& Output = Context->OutputData.TaggedData.Emplace_GetRef();
        Output.Pin = PCGPinConstants::DefaultOutputLabel;
        Output.Data = Data;
        return true;
    }
};

FPCGElementPtr UTemperateHillsPointsSettings::CreateElement() const
{
    return MakeShared<FTemperateHillsPointsElement>();
}
