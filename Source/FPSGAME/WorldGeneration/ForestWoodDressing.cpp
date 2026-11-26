#include "ForestWoodDressing.h"
#if WITH_EDITOR
#include "ForestVillageRegion.h"
#include "Engine/StaticMesh.h"
#include "MeshDescription.h"
#include "Math/RotationMatrix.h"

namespace ForestWoodDressing
{
EKind Kind(const UStaticMesh* Mesh)
{
    if(!Mesh)return EKind::None;
    FString Path=Mesh->GetOutermost()->GetName();
    if(Path.StartsWith(TEXT("/Game/ForestPathStudy/Scans/relu7/")) ||
       Path.StartsWith(TEXT("/Game/ForestPathStudy/Scans/rioqm/"))) return EKind::ReferenceTwig;
    if(!Path.RemoveFromStart(TEXT("/Game/ForestPathStudy/VillageRegion/WoodlandDressing/Wood/")))return EKind::None;
    if(Path.StartsWith(TEXT("branch/")))return EKind::Branch;
    if(Path.StartsWith(TEXT("stump/")))return EKind::Stump;
    if(Path.StartsWith(TEXT("log/")))return EKind::Log;
    if(Path.StartsWith(TEXT("large/")))return EKind::Large;
    return EKind::Trunk;
}

int32 CullEndCm(EKind Type)
{
    switch(Type)
    {
        case EKind::Large:return 17500;
        case EKind::Trunk:return 13500;
        case EKind::Log:return 10000;
        case EKind::Stump:return 7500;
        case EKind::Branch:return 5000;
        case EKind::ReferenceTwig:return 10000; // Preserve the original reference palette's cull distance.
        default:return 0;
    }
}

FSupport Measure(UStaticMesh* Mesh)
{
    FSupport Result;
    Result.Type=Kind(Mesh);
    if(Result.Type==EKind::None)return Result;
    const FMeshDescription* Desc=Mesh->GetMeshDescription(0);
    if(!Desc || Desc->Vertices().Num()==0)return Result;
    const auto Positions=Desc->GetVertexPositions();
    const FVector BuildScale=Mesh->GetSourceModel(0).BuildSettings.BuildScale3D;
    auto Position=[&](FVertexID Id){return FVector(Positions[Id])*BuildScale;};
    FVector2D Mean=FVector2D::ZeroVector;
    FBox Bounds(ForceInit);
    for(FVertexID Id:Desc->Vertices().GetElementIDs())
    {
        const FVector P=Position(Id);
        Mean+=FVector2D(P);
        Bounds+=P;
    }
    Result.Height=Bounds.GetSize().Z;
    Mean/=Desc->Vertices().Num();
    double XX=0.,YY=0.,XY=0.;
    for(FVertexID Id:Desc->Vertices().GetElementIDs())
    {
        const FVector2D D=FVector2D(Position(Id))-Mean;
        XX+=D.X*D.X;YY+=D.Y*D.Y;XY+=D.X*D.Y;
    }
    Result.AxisAngle=.5*FMath::Atan2(2.*XY,XX-YY);
    const FVector2D Axis(FMath::Cos(Result.AxisAngle),FMath::Sin(Result.AxisAngle));
    const FVector2D Side(-Axis.Y,Axis.X);
    double Low=DBL_MAX,High=-DBL_MAX,Left=DBL_MAX,Right=-DBL_MAX;
    for(FVertexID Id:Desc->Vertices().GetElementIDs())
    {
        const FVector2D Delta=FVector2D(Position(Id))-Mean;
        const double Along=FVector2D::DotProduct(Delta,Axis);
        const double Across=FVector2D::DotProduct(Delta,Side);
        Low=FMath::Min(Low,Along);High=FMath::Max(High,Along);
        Left=FMath::Min(Left,Across);Right=FMath::Max(Right,Across);
    }
    Result.Center=Mean+Axis*((Low+High)*.5);
    Result.Length=High-Low;
    // Keep separate supports across forked roots as well as along a fallen trunk.
    TArray<FVector> Patches[15];
    TArray<FVector> Sections[5];
    for(FVertexID Id:Desc->Vertices().GetElementIDs())
    {
        const FVector P=Position(Id);
        const FVector2D Delta=FVector2D(P)-Mean;
        const int32 I=FMath::Clamp(int32(5.*(FVector2D::DotProduct(Delta,Axis)-Low)/FMath::Max(1.,Result.Length)),0,4);
        const int32 J=FMath::Clamp(int32(3.*(FVector2D::DotProduct(Delta,Side)-Left)/FMath::Max(1.,Right-Left)),0,2);
        Patches[I*3+J].Add(P);
        Sections[I].Add(P);
    }
    const bool CheckTerrain=Result.Type!=EKind::ReferenceTwig;
    for(auto& Section:Sections)
    {
        if(Section.IsEmpty())continue;
        Section.Sort([](const FVector& A,const FVector& B){return A.Z<B.Z;});
        Result.Body.Add(Section[(Section.Num()-1)*45/100]);
        if(CheckTerrain)
        {
            // Preserve the original site eligibility for the authored fallen-wood distribution.
            const int32 N=FMath::Max(1,Section.Num()/20);
            FVector Foot=FVector::ZeroVector;
            for(int32 I=0;I<N;++I)Foot+=Section[I];
            Result.TerrainChecks.Add(Foot/N);
        }
    }
    // Upper forks can overhang naturally. Only the underside of the scan supports the log.
    const double RootBand=Bounds.Min.Z+Result.Height*(Result.Type==EKind::Stump?.32:.52);
    for(auto& Patch:Patches)
    {
        if(Patch.IsEmpty())continue;
        Patch.Sort([](const FVector& A,const FVector& B){return A.Z<B.Z;});
        const FVector& Foot=Patch[Patch.Num()/20];
        if(Foot.Z<=RootBand)Result.Feet.Add(Foot);
    }
    if(Result.Feet.IsEmpty())Result.Feet.Add(FVector(Bounds.GetCenter().X,Bounds.GetCenter().Y,Bounds.Min.Z));
    return Result;
}

bool Fit(const AForestVillageRegion& Region,const FSupport& S,FVector2D Center,double Heading,double Scale,FTransform& Out)
{
    if(S.Feet.IsEmpty())return false;
    const double Yaw=FMath::DegreesToRadians(Heading);
    const FVector2D Axis(FMath::Cos(Yaw),FMath::Sin(Yaw)),Side(-Axis.Y,Axis.X);
    auto Height=[&](FVector2D P){return Region.GroundHeight(P.X,P.Y);};
    const double D=FMath::Clamp(S.Length*Scale*.36,30.,900.);
    const double Along=(Height(Center+Axis*D)-Height(Center-Axis*D))/(2.*D);
    const double Across=(Height(Center+Side*45.)-Height(Center-Side*45.))/90.;
    FVector Up(-(Axis.X*Along+Side.X*Across),-(Axis.Y*Along+Side.Y*Across),1.);
    Up.Normalize();
    if(S.Type==EKind::Stump)Up=FMath::Lerp(FVector::UpVector,Up,.30).GetSafeNormal();
    const FQuat Frame=FRotationMatrix::MakeFromZX(Up,FVector(Axis,Along)).ToQuat();
    const FQuat Rotation=Frame*FQuat(FVector::UpVector,-S.AxisAngle);
    const FVector Anchor=Rotation.RotateVector(FVector(S.Center,0.)*Scale);
    FVector Pivot(Center.X-Anchor.X,Center.Y-Anchor.Y,0.);
    auto ContactZ=[&](const FVector& Local)
    {
        const FVector P=Pivot+Rotation.RotateVector(Local*Scale);
        return Height(FVector2D(P))-P.Z;
    };
    const bool Branch=S.Type==EKind::Branch || S.Type==EKind::ReferenceTwig;
    if(!S.TerrainChecks.IsEmpty())
    {
        double Min=DBL_MAX,Max=-DBL_MAX;
        for(const FVector& P:S.TerrainChecks)
        {
            const double Z=ContactZ(P);
            Min=FMath::Min(Min,Z);Max=FMath::Max(Max,Z);
        }
        if(Max-Min>(Branch?14.:FMath::Clamp(S.Length*Scale*.055,22.,65.)))return false;
    }
    TArray<double,TInlineAllocator<15>> Supports;
    for(const FVector& Foot:S.Feet)Supports.Add(ContactZ(Foot));
    Supports.Sort();
    const bool Stump=S.Type==EKind::Stump;
    const double Thickness=S.Height*Scale;
    const double Embed=FMath::Clamp(Thickness*(Stump?.19:.12),Branch?.6:3.,Branch?5.:Stump?24.:18.);
    TArray<double,TInlineAllocator<5>> BodyHeights;
    for(const FVector& P:S.Body)BodyHeights.Add(ContactZ(P));
    BodyHeights.Sort();
    const double Seat=FMath::Max(Supports[(Supports.Num()-1)/4]-Embed,BodyHeights[BodyHeights.Num()/2]);
    // Reject terrain that would swallow the body to seat the roots.
    if(Supports[Supports.Num()*3/4]-Seat>Thickness*(Stump?.68:.72)+Embed)return false;
    Pivot.Z=Seat;
    Out=FTransform(Rotation,Pivot,FVector(Scale));
    return true;
}
}
#endif

