#include "TemperateHillsRiver.h"

namespace TemperateRiver
{
bool FPlan::IntersectWaterSegment(const FVector& Start,const FVector& End,double AlongMin,double AlongMax,
    FVector& Position,FVector& Normal,double& Along) const
{
    const FVector Ray=End-Start;
    if(Ray.IsNearlyZero())return false;
    // Same 64 m spatial buckets as river generation. A round is clipped to its
    // first blocking hit by the caller, so walls cannot produce splashes behind them.
    constexpr double Cell=6400.;
    const int32 MinX=FMath::FloorToInt(FMath::Min(Start.X,End.X)/Cell);
    const int32 MaxX=FMath::FloorToInt(FMath::Max(Start.X,End.X)/Cell);
    const int32 MinY=FMath::FloorToInt(FMath::Min(Start.Y,End.Y)/Cell);
    const int32 MaxY=FMath::FloorToInt(FMath::Max(Start.Y,End.Y)/Cell);
    TSet<int32> Candidates;
    for(int32 Y=MinY;Y<=MaxY;++Y)for(int32 X=MinX;X<=MaxX;++X)
        if(const auto* List=Buckets.Find(FIntPoint(X,Y)))for(int32 I:*List)
            if(Points[I+1].Distance>=AlongMin&&Points[I].Distance<=AlongMax)Candidates.Add(I);
    double Best=2.;
    auto Vertex=[](const FPoint& P,double Across)
    {
        const FVector2D XY=P.XY+P.Side*((Across>=0?P.LeftWidth:P.RightWidth)*Across);
        return FVector(XY.X,XY.Y,P.WaterZ);
    };
    auto Triangle=[&](const FVector& A,const FVector& B,const FVector& C,double DA,double DB,double DC)
    {
        const FVector E1=B-A,E2=C-A;
        FVector N=FVector::CrossProduct(E1,E2).GetSafeNormal();
        if(N.Z<0)N=-N;
        if(FVector::DotProduct(Ray,N)>=-KINDA_SMALL_NUMBER)return; // Entry only.
        const FVector P=FVector::CrossProduct(Ray,E2);
        const double Det=FVector::DotProduct(E1,P);
        if(FMath::Abs(Det)<1.e-8)return;
        const FVector S=Start-A;
        const double U=FVector::DotProduct(S,P)/Det;
        if(U<0||U>1)return;
        const FVector Q=FVector::CrossProduct(S,E1);
        const double V=FVector::DotProduct(Ray,Q)/Det;
        if(V<0||U+V>1)return;
        const double T=FVector::DotProduct(E2,Q)/Det;
        const double Distance=DA*(1-U-V)+DB*U+DC*V;
        if(T<0||T>1||T>=Best||Distance<AlongMin||Distance>AlongMax)return;
        Best=T;Position=Start+Ray*T;Normal=N;Along=Distance;
    };
    for(int32 I:Candidates)
    {
        const auto& A=Points[I];const auto& B=Points[I+1];
        constexpr double Across[]={-1,-.65,0,.65,1};
        for(int32 J=0;J<4;++J)
        {
            const FVector AL=Vertex(A,Across[J]),AR=Vertex(A,Across[J+1]);
            const FVector BL=Vertex(B,Across[J]),BR=Vertex(B,Across[J+1]);
            Triangle(AL,AR,BL,A.Distance,A.Distance,B.Distance);
            Triangle(AR,BR,BL,A.Distance,B.Distance,B.Distance);
        }
    }
    return Best<=1;
}
}
