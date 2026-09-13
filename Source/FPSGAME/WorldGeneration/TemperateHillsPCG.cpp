#include "TemperateHillsPCG.h"
#include "TemperateHillsWorld.h"
#include "PCGComponent.h"
#include "PCGContext.h"
#include "Data/PCGPointData.h"
#include "Metadata/PCGMetadata.h"
#include "Metadata/PCGMetadataAttributeTpl.h"

class FTemperateHillsPointsElement : public IPCGElement
{
public:
    virtual bool IsCacheable(const UPCGSettings*) const override { return false; }
    virtual bool CanExecuteOnlyOnMainThread(FPCGContext*) const override { return true; }
protected:
    virtual bool ExecuteInternal(FPCGContext* Context) const override
    {
        auto* Component = Cast<UPCGComponent>(Context->ExecutionSource.Get());
        auto* Original = Component ? Component->GetOriginalComponent() : nullptr;
        auto* World = Original ? Cast<ATemperateHillsWorld>(Original->GetOwner()) : nullptr;
        if (!World || !World->bSurfaceReady) return true;
        const auto* Settings = Context->GetInputSettings<UTemperateHillsPointsSettings>();
        TArray<FTemperatePlacement> Placements;
        World->GetPlacements(Settings->Layer, Component->GetGridBounds(), Placements);
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
