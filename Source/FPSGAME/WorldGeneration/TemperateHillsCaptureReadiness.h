#pragma once
#include "TemperateHillsWorld.h"
#include "TemperateHillsVisibility.h"
#include "Components/DynamicMeshComponent.h"
#include "PCGComponent.h"
#include "PCGGraph.h"
#include "PCGGraphExecutionStateInterface.h"

namespace HillsLandscapeCapture
{
struct FReadiness
{
    int32 TerrainRequired=0,TerrainReady=0,VegetationRequired=0,VegetationReady=0;
    double MaxGroundError=0.;
    bool Complete() const {return TerrainRequired>0&&TerrainReady==TerrainRequired&&VegetationRequired>0&&VegetationReady==VegetationRequired;}
};

inline bool GroundHit(ATemperateHillsWorld* Hills,FVector2D XY,FHitResult& Hit)
{
    const double Z=Hills->Height(XY.X,XY.Y);
    TInlineComponentArray<UDynamicMeshComponent*> Components(Hills);
    FCollisionQueryParams Q(SCENE_QUERY_STAT(HillsCaptureGround),true);
    for(auto* C:Components)
    {
        if(!C->ComponentHasTag(TEXT("HillsGround"))||!C->IsVisible()||C->GetCollisionEnabled()==ECollisionEnabled::NoCollision)continue;
        const auto B=C->Bounds.GetBox();
        if(XY.X<B.Min.X||XY.X>B.Max.X||XY.Y<B.Min.Y||XY.Y>B.Max.Y)continue;
        if(C->LineTraceComponent(Hit,FVector(XY,Z+1200.),FVector(XY,Z-1200.),Q))return true;
    }
    return false;
}

inline FReadiness Readiness(ATemperateHillsWorld* Hills,FVector Anchor,FVector Target,double MaxVegetationRadius=DBL_MAX)
{
    FReadiness R;
    for(int32 Y=-1;Y<=1;++Y)for(int32 X=-1;X<=1;++X)
    {
        const FVector2D P=FVector2D(Target)+FVector2D(X,Y)*2200.;
        if(FMath::Abs(P.X)>Hills->SizeMeters*50.-100.||FMath::Abs(P.Y)>Hills->SizeMeters*50.-100.)continue;
        ++R.TerrainRequired;FHitResult Hit;
        if(!GroundHit(Hills,P,Hit))continue;
        const double Error=FMath::Abs(Hills->Height(P.X,P.Y)-Hit.ImpactPoint.Z);
        R.MaxGroundError=FMath::Max(R.MaxGroundError,Error);
        if(Error<35.)++R.TerrainReady;
    }
    TInlineComponentArray<UPCGComponent*> Components(Hills);
    int32 Layer=0;
    for(auto* C:Components)
    {
        if(Layer>=4)break;
        auto& State=C->GetExecutionState();const auto* Graph=State.GetGraph();if(!Graph)continue;
        const uint32 Grid=Graph->GetDefaultGridSize();if(!Grid||Grid==PCGHiGenGrid::UnboundedGridSize())continue;
        const double Radius=FMath::Min<double>(TemperateHillsVisibility::Layers[Layer++].VisibleEnd,MaxVegetationRadius);
        const double Half=Hills->SizeMeters*50.;
        const auto Descriptor=FPCGGridDescriptor().SetGridSize(Grid).SetIs2DGrid(true).SetIsRuntime(true);
        for(int32 Y=FMath::FloorToInt(FMath::Max(-Half,Anchor.Y-Radius)/Grid);Y<=FMath::FloorToInt(FMath::Min(Half-1.,Anchor.Y+Radius)/Grid);++Y)
        for(int32 X=FMath::FloorToInt(FMath::Max(-Half,Anchor.X-Radius)/Grid);X<=FMath::FloorToInt(FMath::Min(Half-1.,Anchor.X+Radius)/Grid);++X)
        {
            const double DX=FMath::Max(0.,FMath::Abs(Anchor.X-(X+.5)*Grid)-Grid*.5);
            const double DY=FMath::Max(0.,FMath::Abs(Anchor.Y-(Y+.5)*Grid)-Grid*.5);
            if(DX*DX+DY*DY>Radius*Radius)continue;
            ++R.VegetationRequired;
            if(auto* Local=State.GetLocalSource(Descriptor,FIntVector(X,Y,0)))
                if(Local->GetExecutionState().IsGenerated()&&!Local->GetExecutionState().IsGenerating())++R.VegetationReady;
        }
    }
    return R;
}
}
