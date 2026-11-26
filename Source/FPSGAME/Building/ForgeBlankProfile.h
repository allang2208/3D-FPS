#pragma once
#include "CoreMinimal.h"

// Shared with the blank authoring data: centimetres, tang on -X, anvil contact at Z=0.
struct FColdSteelForgeBlankSection
{
    double X=0,MinY=0,MaxY=0,Height=0,EdgeHeight=0;
};
struct FColdSteelForgeBlankStage
{
    FString Mesh;
    TArray<FColdSteelForgeBlankSection> Sections;
};
struct FColdSteelForgeBlank
{
    FName Id;
    FString Label;
    TArray<FColdSteelForgeBlankStage> Stages;
    TArray<FVector2D> Points;
    FVector2D Crown=FVector2D(.5,.5);
    FVector2D EyeCenter=FVector2D::ZeroVector,EyeRadius=FVector2D::ZeroVector;
    FVector2D AimMin=FVector2D(.37,.1),AimMax=FVector2D(.63,.65);
    float StrikeRadius=1.85f;
    FVector Grip=FVector(-24,0,.475);
    FVector QuenchTip=FVector(30,0,.475),QuenchHeel=FVector(-21,0,.475);
    float QuenchDrop=30;
    FVector2D HeatSpan=FVector2D(-19,25);
    FVector HeatCenter=FVector(0,0,8),VeilScale=FVector(.65,.22,1);

    double CenterY(double X,int32 Stage) const
    {
        if(!Stages.IsValidIndex(Stage))return 0;
        const auto& Sections=Stages[Stage].Sections;
        for(int32 I=1;I<Sections.Num();++I)
        {
            const auto& A=Sections[I-1];const auto& B=Sections[I];
            if(X<A.X||X>B.X)continue;
            return FMath::Lerp((A.MinY+A.MaxY)*.5,(B.MinY+B.MaxY)*.5,(X-A.X)/(B.X-A.X));
        }
        return 0;
    }

    bool SurfaceHeight(double X,double Y,int32 Stage,double& Height) const
    {
        if(!Stages.IsValidIndex(Stage))return false;
        const auto& Sections=Stages[Stage].Sections;
        if(Sections.Num()<2||X<Sections[0].X||X>Sections.Last().X)return false;
        if(EyeRadius.X>0&&EyeRadius.Y>0
            &&FMath::Square((X-EyeCenter.X)/EyeRadius.X)+FMath::Square((Y-EyeCenter.Y)/EyeRadius.Y)<1)return false;
        for(int32 I=1;I<Sections.Num();++I)
        {
            if(X>Sections[I].X)continue;
            const auto& A=Sections[I-1];const auto& B=Sections[I];
            const double T=(X-A.X)/(B.X-A.X);
            const double MinY=FMath::Lerp(A.MinY,B.MinY,T),MaxY=FMath::Lerp(A.MaxY,B.MaxY,T);
            if(Y<MinY||Y>MaxY)return false;
            const double Across=(Y-MinY)/(MaxY-MinY);
            const double CrownWeight=Across<Crown.X?Across/Crown.X:
                Across>Crown.Y?(1-Across)/(1-Crown.Y):1;
            Height=FMath::Lerp(FMath::Lerp(A.EdgeHeight,B.EdgeHeight,T),FMath::Lerp(A.Height,B.Height,T),CrownWeight);
            return true;
        }
        return false;
    }
};
