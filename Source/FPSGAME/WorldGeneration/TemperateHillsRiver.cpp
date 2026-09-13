#include "TemperateHillsRiver.h"
#include "TemperateHillsSurface.h"
#include "DynamicMesh/DynamicMesh3.h"
#include "DynamicMesh/DynamicMeshAttributeSet.h"
#include <queue>
#include <vector>

// Design references: Red Blob Games mapgen4 (drainage ordering / accumulated flow)
// and Bona Fyrvall InstantRiver (curve ribbon / arc-length UVs).
// Independent UE implementation; references and licenses in Docs/WorldGeneration/temperate-rivers.md.
namespace TemperateRiver
{
namespace
{
constexpr double BucketSize = 6400;
constexpr double BankReach = 2000;
double Smooth(double A, double B, double V)
{
    const double T = FMath::Clamp((V-A)/(B-A), 0.0, 1.0);
    return T*T*(3-2*T);
}
FIntPoint Bucket(double X, double Y)
{ return FIntPoint(FMath::FloorToInt(X/BucketSize), FMath::FloorToInt(Y/BucketSize)); }
struct FDrainNode
{
    double Height = 0;
    double Flood = 0;
    double Flow = 1;
    int32 Parent = INDEX_NONE;
    bool Visited = false;
};
struct FQueueNode
{
    double Elevation;
    int32 Index;
    bool operator<(const FQueueNode& Other) const
    { return Elevation == Other.Elevation ? Index > Other.Index : Elevation > Other.Elevation; }
};
struct FWaterVertex
{
    FVector3d Position;
    FVector2f UV;
    FVector4f Color;
};
}

FPlanPtr Generate(int32 Seed, double Half, const FVector2D& Spawn)
{
    auto Plan = MakeShared<FPlan, ESPMode::ThreadSafe>();
    constexpr double Grid = 1600;
    const int32 N = FMath::RoundToInt(2*Half/Grid)+1;
    TArray<FDrainNode> Nodes;
    Nodes.SetNum(N*N);
    auto XY = [=](int32 I) { return FVector2D(-Half+(I%N)*Grid, -Half+(I/N)*Grid); };
    std::priority_queue<FQueueNode> Queue;
    TArray<int32> Order;
    Order.Reserve(N*N);
    for(int32 I=0; I<Nodes.Num(); ++I)
    {
        const FVector2D P = XY(I);
        auto& Node = Nodes[I];
        Node.Height = TemperateHillsSurface::Height(P.X, P.Y, Seed);
        Node.Flood = Node.Height;
        // Keep the existing spawn, return portal and approach on dry unmodified ground.
        if(FVector2D::Distance(P, Spawn)<6000) { Node.Visited=true; continue; }
        if(I%N==0 || I%N==N-1 || I/N==0 || I/N==N-1)
        { Node.Visited=true; Queue.push({Node.Flood,I}); }
    }
    // Boundary-outward priority flood gives each interior sample an acyclic outlet,
    // including local noise depressions. Ties have stable integer ordering.
    while(!Queue.empty())
    {
        const int32 I=Queue.top().Index; Queue.pop(); Order.Add(I);
        const int32 X=I%N, Y=I/N;
        for(int32 DY=-1; DY<=1; ++DY) for(int32 DX=-1; DX<=1; ++DX)
        {
            if((DX==0&&DY==0)||X+DX<0||Y+DY<0||X+DX>=N||Y+DY>=N)continue;
            const int32 J=(Y+DY)*N+X+DX;
            if(Nodes[J].Visited)continue;
            auto& Next=Nodes[J]; Next.Visited=true; Next.Parent=I;
            Next.Flood=FMath::Max(Next.Height,Nodes[I].Flood+.01);
            Queue.push({Next.Flood,J});
        }
    }
    for(int32 I=Order.Num()-1; I>=0; --I)
    {
        const int32 Node=Order[I], Parent=Nodes[Node].Parent;
        if(Parent!=INDEX_NONE)Nodes[Parent].Flow+=Nodes[Node].Flow;
    }

    // Choose one substantial, nearby drainage course for the initial biome. No
    // all-world fluid simulation, nor a new per-cell random river on every visit.
    int32 Source=INDEX_NONE;
    double Best=-DBL_MAX;
    for(int32 I=0; I<Nodes.Num(); ++I)
    {
        if(Nodes[I].Parent==INDEX_NONE || Nodes[I].Flow>24)continue;
        const FVector2D P=XY(I);
        if(FMath::Abs(P.X)>Half*.82 || FMath::Abs(P.Y)>Half*.82)continue;
        double Length=0, Near=DBL_MAX, Water=Nodes[I].Height-25, Cut=0, MaxCut=0;
        for(int32 J=I; Nodes[J].Parent!=INDEX_NONE; J=Nodes[J].Parent)
        {
            const int32 Parent=Nodes[J].Parent;
            const double Step=FVector2D::Distance(XY(J),XY(Parent));
            Length+=Step; Near=FMath::Min(Near,FVector2D::Distance(XY(J),Spawn));
            Water=FMath::Min(Water-Step*.001,Nodes[Parent].Height-25);
            const double Carve=Nodes[Parent].Height-Water;
            Cut+=Carve; MaxCut=FMath::Max(MaxCut,Carve);
        }
        if(Length<Half*.6)continue;
        const double Score=Length*.35-Near*2.5-Cut*.06-MaxCut*5
            +TemperateHillsSurface::Unit(TemperateHillsSurface::Key(I%N,I/N,Seed,901))*1200;
        if(Score>Best){Best=Score;Source=I;}
    }
    // Small worlds can have short drainage basins: use the longest available
    // course outside the protected spawn instead of holding loading forever.
    if(Source==INDEX_NONE)
    {
        int32 Longest=0;
        for(int32 I=0; I<Nodes.Num(); ++I)
        {
            int32 Steps=0;
            for(int32 J=I; Nodes[J].Parent!=INDEX_NONE; J=Nodes[J].Parent)++Steps;
            if(Steps>Longest){Longest=Steps;Source=I;}
        }
    }
    if(Source==INDEX_NONE)return Plan;
    struct FCurvePoint { FVector2D XY; double Flow; };
    TArray<FCurvePoint> Curve;
    for(int32 I=Source; I!=INDEX_NONE; I=Nodes[I].Parent)Curve.Add({XY(I),Nodes[I].Flow});
    // Corner cutting stays within the drainage corridor, unlike an overshooting
    // interpolating spline. Keep both source and boundary outlet fixed.
    for(int32 Pass=0; Pass<2; ++Pass)
    {
        TArray<FCurvePoint> Next;Next.Add(Curve[0]);
        for(int32 I=0; I+1<Curve.Num(); ++I)
        {
            const auto& A=Curve[I];const auto& B=Curve[I+1];
            Next.Add({FMath::Lerp(A.XY,B.XY,.25),FMath::Lerp(A.Flow,B.Flow,.25)});
            Next.Add({FMath::Lerp(A.XY,B.XY,.75),FMath::Lerp(A.Flow,B.Flow,.75)});
        }
        Next.Add(Curve.Last());Curve=MoveTemp(Next);
    }
    // Spatially bounded samples also bound the amount of geometry in a streamed cell.
    double Distance=0, Water=DBL_MAX;
    for(int32 I=0; I<Curve.Num(); ++I)
    {
        if(I>0)Distance+=FVector2D::Distance(Curve[I-1].XY,Curve[I].XY);
        FPoint P;P.XY=Curve[I].XY;P.Distance=Distance;
        const double Step=I>0?FVector2D::Distance(Curve[I-1].XY,P.XY):0;
        Water=FMath::Min(Water-Step*.001,TemperateHillsSurface::Height(P.XY.X,P.XY.Y,Seed)-25);
        P.WaterZ=Water;
        P.HalfWidth=FMath::Clamp(320+FMath::Sqrt(Curve[I].Flow)*19,350.0,650.0)
            *FMath::Lerp(.08,1.0,Smooth(0,2200,Distance));
        // Shallow stream in this release; the existing walking character can wade.
        P.Depth=FMath::Lerp(35.0,75.0,Smooth(0,1800,Distance));
        const FVector2D Tangent=(Curve[FMath::Min(I+1,Curve.Num()-1)].XY-Curve[FMath::Max(0,I-1)].XY).GetSafeNormal();
        P.Side=FVector2D(-Tangent.Y,Tangent.X);
        Plan->Points.Add(P);
    }
    for(int32 I=0; I+1<Plan->Points.Num(); ++I)
    {
        const auto& A=Plan->Points[I];const auto& B=Plan->Points[I+1];
        const double Reach=FMath::Max(A.HalfWidth,B.HalfWidth)+BankReach;
        const FIntPoint Min=Bucket(FMath::Min(A.XY.X,B.XY.X)-Reach,FMath::Min(A.XY.Y,B.XY.Y)-Reach);
        const FIntPoint Max=Bucket(FMath::Max(A.XY.X,B.XY.X)+Reach,FMath::Max(A.XY.Y,B.XY.Y)+Reach);
        for(int32 Y=Min.Y;Y<=Max.Y;++Y)for(int32 X=Min.X;X<=Max.X;++X)
            Plan->Buckets.FindOrAdd(FIntPoint(X,Y)).Add(I);
    }
    return Plan;
}

FSample FPlan::Sample(double X,double Y) const
{
    FSample R;
    const auto* Candidates=Buckets.Find(Bucket(X,Y));if(!Candidates)return R;
    const FVector2D P(X,Y);
    for(int32 I:*Candidates)
    {
        const auto& A=Points[I];const auto& B=Points[I+1];
        const FVector2D Delta=B.XY-A.XY;
        const double T=FMath::Clamp(FVector2D::DotProduct(P-A.XY,Delta)/FMath::Max(1.0,Delta.SizeSquared()),0.0,1.0);
        const double D=FVector2D::Distance(P,FMath::Lerp(A.XY,B.XY,T));
        if(D>=R.Distance)continue;
        R.Distance=D;R.WaterZ=FMath::Lerp(A.WaterZ,B.WaterZ,T);
        R.HalfWidth=FMath::Lerp(A.HalfWidth,B.HalfWidth,T);R.Depth=FMath::Lerp(A.Depth,B.Depth,T);
        R.Along=FMath::Lerp(A.Distance,B.Distance,T);
    }
    if(R.Distance<DBL_MAX)
    {
        R.Bank=1-Smooth(R.HalfWidth+400,R.HalfWidth+BankReach,R.Distance);
        R.Wet=1-Smooth(R.HalfWidth-80,R.HalfWidth+300,R.Distance);
    }
    return R;
}

double FPlan::Height(double X,double Y,int32 Seed) const
{
    const double Base=TemperateHillsSurface::Height(X,Y,Seed);
    const FSample S=Sample(X,Y);
    if(S.Bank<=0)return Base;
    double Bed=0;
    if(S.Distance<S.HalfWidth)
        Bed=S.WaterZ-S.Depth+(S.Depth+8)*Smooth(.10,1.0,S.Distance/FMath::Max(1.0,S.HalfWidth));
    else
        Bed=S.WaterZ+8+92*Smooth(S.HalfWidth,S.HalfWidth+400,S.Distance);
    return FMath::Lerp(Base,Bed,S.Bank);
}
FVector FPlan::Normal(double X,double Y,int32 Seed) const
{ return FVector(-(Height(X+50,Y,Seed)-Height(X-50,Y,Seed))/100,-(Height(X,Y+50,Seed)-Height(X,Y-50,Seed))/100,1).GetSafeNormal(); }

bool FPlan::IntersectsCell(double X,double Y,double Size) const
{
    const FIntPoint Min=Bucket(X,Y),Max=Bucket(X+Size,Y+Size);
    for(int32 BY=Min.Y;BY<=Max.Y;++BY)for(int32 BX=Min.X;BX<=Max.X;++BX)
        if(const auto* List=Buckets.Find(FIntPoint(BX,BY)))for(int32 I:*List)
        {
            const auto& A=Points[I];const auto& B=Points[I+1];
            const double Reach=FMath::Max(A.HalfWidth,B.HalfWidth)+BankReach;
            if(FMath::Max(A.XY.X,B.XY.X)+Reach>=X&&FMath::Min(A.XY.X,B.XY.X)-Reach<=X+Size&&
                FMath::Max(A.XY.Y,B.XY.Y)+Reach>=Y&&FMath::Min(A.XY.Y,B.XY.Y)-Reach<=Y+Size)return true;
        }
    return false;
}

void FPlan::BuildWaterMesh(double X,double Y,double Size,UE::Geometry::FDynamicMesh3& Mesh) const
{
    Mesh.EnableAttributes();Mesh.Attributes()->EnablePrimaryColors();
    auto* Normals=Mesh.Attributes()->PrimaryNormals();auto* UVs=Mesh.Attributes()->PrimaryUV();
    auto* Colors=Mesh.Attributes()->PrimaryColors();
    TSet<int32> Unique;
    const FIntPoint Min=Bucket(X,Y),Max=Bucket(X+Size,Y+Size);
    for(int32 BY=Min.Y;BY<=Max.Y;++BY)for(int32 BX=Min.X;BX<=Max.X;++BX)
        if(const auto* List=Buckets.Find(FIntPoint(BX,BY)))for(int32 I:*List)Unique.Add(I);
    TArray<int32> Segments=Unique.Array();Segments.Sort();
    auto Vertex=[](const FPoint& P,double Across)
    {
        const FVector2D XY=P.XY+P.Side*(P.HalfWidth*Across);
        return FWaterVertex{FVector3d(XY.X,XY.Y,P.WaterZ),FVector2f(P.Distance/400,Across*P.HalfWidth/400),
            FVector4f(FMath::Pow(FMath::Abs(Across),6.0),0,0,1)};
    };
    auto Emit=[&](const FWaterVertex& A,const FWaterVertex& B,const FWaterVertex& C)
    {
        const FVector3d Cross=(B.Position-A.Position).Cross(C.Position-A.Position);
        if(Cross.SquaredLength()<.01)return;
        // Match the terrain's UE clockwise front-face convention, with upward shading normals.
        const FVector3f Normal=FVector3f(-Cross.GetSafeNormal());
        const int32 Start=Mesh.VertexCount();
        for(const auto& V:{A,B,C})
        {
            Mesh.AppendVertex(V.Position-FVector3d(X,Y,0));Normals->AppendElement(Normal);
            UVs->AppendElement(V.UV);Colors->AppendElement(V.Color);
        }
        const int32 ID=Mesh.AppendTriangle(Start,Start+1,Start+2);
        const UE::Geometry::FIndex3i Indices(Start,Start+1,Start+2);
        Normals->SetTriangle(ID,Indices);UVs->SetTriangle(ID,Indices);Colors->SetTriangle(ID,Indices);
    };
    auto Clip=[&](TArray<FWaterVertex> Polygon)
    {
        // Exact cell clipping preserves UVs at cell boundaries, avoiding duplicate
        // transparent ribbons where two terrain cells meet.
        for(int32 Plane=0;Plane<4;++Plane)
        {
            if(Polygon.IsEmpty())return;
            auto Signed=[&](const FWaterVertex& V)
            {return Plane==0?V.Position.X-X:Plane==1?X+Size-V.Position.X:Plane==2?V.Position.Y-Y:Y+Size-V.Position.Y;};
            TArray<FWaterVertex> Next;
            FWaterVertex Previous=Polygon.Last();double DP=Signed(Previous);
            for(const auto& Current:Polygon)
            {
                const double DC=Signed(Current);
                if((DP>=0)!=(DC>=0))
                {
                    const double T=DP/(DP-DC);
                    Next.Add({FMath::Lerp(Previous.Position,Current.Position,T),FMath::Lerp(Previous.UV,Current.UV,float(T)),FMath::Lerp(Previous.Color,Current.Color,float(T))});
                }
                if(DC>=0)Next.Add(Current);
                Previous=Current;DP=DC;
            }
            Polygon=MoveTemp(Next);
        }
        for(int32 I=1;I+1<Polygon.Num();++I)Emit(Polygon[0],Polygon[I],Polygon[I+1]);
    };
    for(int32 I:Segments)
    {
        const auto& A=Points[I];const auto& B=Points[I+1];
        constexpr double Across[]={-1,-.65,0,.65,1};
        for(int32 J=0;J<4;++J)
        {
            const auto AL=Vertex(A,Across[J]),AR=Vertex(A,Across[J+1]);
            const auto BL=Vertex(B,Across[J]),BR=Vertex(B,Across[J+1]);
            Clip({AL,AR,BL});Clip({AR,BR,BL});
        }
    }
}
}
