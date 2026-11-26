#include "ForestRootFit.h"
#include "Data/PCGBasePointData.h"
#include "Engine/StaticMesh.h"
#include "EngineUtils.h"
#include "LandscapeProxy.h"
#include "PCGComponent.h"
#include "PCGContext.h"
#include "PCGElement.h"
#if WITH_EDITOR
#include "MeshDescription.h"
#include "WorldPartition/WorldPartitionHelpers.h"
#endif

double ForestRootFit::Seat(FVector2D Center,double Radius,double CollarZ,TFunctionRef<double(double,double)> Height)
{
    constexpr double D=.7071067811865475;
    static const FVector2D Ring[]={{1,0},{D,D},{0,1},{-D,D},{-1,0},{-D,-D},{0,-1},{D,-D}};
    const double Mid=Height(Center.X,Center.Y);
    double Lowest=Mid;
    for(const FVector2D Dir:Ring)
    {
        const FVector2D P=Center+Dir*Radius;
        Lowest=FMath::Min(Lowest,Height(P.X,P.Y));
    }
    return Lowest-CollarZ-FMath::Clamp(Radius*.28,4.,24.);
}

#if WITH_EDITOR
FVector2D ForestRootFit::Measure(UStaticMesh* Mesh)
{
    // Use basal vertices and discard far-off foliage when sizing the contact ring.
    const FBox Bounds=Mesh->GetBoundingBox();
    const double Limit=FMath::Clamp(Bounds.GetSize().Z*.085,30.,140.);
    TArray<double> Radii;
    const auto* Desc=Mesh->GetMeshDescription(0);
    const double Bottom=Bounds.Min.Z+Mesh->GetNegativeBoundsExtension().Z;
    const double Collar=FMath::Max(0.,Bottom);
    if(Desc)
    {
        const auto Vertices=Desc->GetVertexPositions();
        for(const auto Id:Desc->Vertices().GetElementIDs())
        {
            const FVector3f P=Vertices[Id];
            const double R=FVector2D(P.X,P.Y).Size();
            if(P.Z<Collar+35. && R<=Limit) Radii.Add(R);
        }
    }
    Radii.Sort();
    const double Radius=Radii.Num()>=8?Radii[(Radii.Num()-1)*9/10]:Limit*.55;
    return {FMath::Clamp(Radius,12.,Limit),Collar};
}
#endif

FVector2D UForestRootFitSettings::MeasureRoot(UStaticMesh* Mesh)
{
#if WITH_EDITOR
    if(Mesh) return ForestRootFit::Measure(Mesh);
#endif
    return FVector2D::ZeroVector;
}

bool UForestRootFitSettings::RegenerateTrees(UPCGComponent* Component)
{
#if WITH_EDITOR
    if(!Component || !Component->GetWorld()) return false;
    auto* World=Component->GetWorld();
    Component->CleanupLocalImmediate(true);
    FWorldPartitionHelpers::FakeEngineTick(World);
    if(Component->GenerateLocalGetTaskId(true)==InvalidPCGTaskId) return false;
    const double End=FPlatformTime::Seconds()+240.;
    while(Component->IsGenerating() && FPlatformTime::Seconds()<End)
    {
        FWorldPartitionHelpers::FakeEngineTick(World);
        FPlatformProcess::Sleep(.005f);
    }
    return !Component->IsGenerating();
#else
    return false;
#endif
}

namespace
{
class FForestRootFitElement final : public IPCGElement
{
    virtual bool IsCacheable(const UPCGSettings*) const override { return false; }
    virtual bool CanExecuteOnlyOnMainThread(FPCGContext*) const override { return true; }
    virtual bool ExecuteInternal(FPCGContext* Context) const override
    {
        const auto* Settings=Context->GetInputSettings<UForestRootFitSettings>();
        const auto* Owner=Context->GetTargetActor(nullptr);
        ALandscapeProxy* Land=nullptr;
        if(Owner)
            for(TActorIterator<ALandscapeProxy> It(Owner->GetWorld());It;++It)
                if(It->GetLevel()==Owner->GetLevel()) { Land=*It; break; }
        for(const auto& Input:Context->InputData.GetInputsByPin(PCGPinConstants::DefaultInputLabel))
        {
            auto& Out=Context->OutputData.TaggedData.Add_GetRef(Input);
            Out.Pin=PCGPinConstants::DefaultOutputLabel;
            const auto* Data=Cast<UPCGBasePointData>(Input.Data);
            if(!Land || !Data) continue;
            auto* Copy=CastChecked<UPCGBasePointData>(Data->DuplicateData(Context));
            auto Poses=Copy->GetTransformValueRange(true);
            for(int32 I=0;I<Copy->GetNumPoints();++I)
            {
                FTransform T=Poses[I];
                FVector P=T.GetLocation();
                const auto Center=Land->GetHeightAtLocation(P);
                if(!Center.IsSet()) continue;
                const FVector S=T.GetScale3D().GetAbs();
                const double Z=ForestRootFit::Seat(FVector2D(P),Settings->RootRadius*FMath::Max(S.X,S.Y),
                    Settings->RootCollarZ*S.Z,[&](double X,double Y)
                    { return double(Land->GetHeightAtLocation(FVector(X,Y,0.)).Get(Center.GetValue())); });
                P.Z=FMath::Min(P.Z,Z);
                T.SetLocation(P);
                Poses[I]=T;
            }
            Out.Data=Copy;
        }
        return true;
    }
};
}

FPCGElementPtr UForestRootFitSettings::CreateElement() const { return MakeShared<FForestRootFitElement>(); }
