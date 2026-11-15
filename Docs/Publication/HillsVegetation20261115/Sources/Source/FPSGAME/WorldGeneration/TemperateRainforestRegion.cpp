#include "TemperateHillsRiver.h"
#include "TemperateEcologyConfig.h"
#include "TemperateHillsSurface.h"

namespace TemperateRiver
{
// The drainage has an inland source and one boundary outlet. Close the source
// end against the map edge so there are still two distinct sides upstream.
static TArray<FVector2D> BankDivider(const TArray<FPoint>& Points, double Half)
{
    TArray<FVector2D> Line;
    if(Points.Num()<2)return Line;
    const FVector2D Head=Points[0].XY;
    const FVector2D Upstream=(Head-Points[FMath::Min(5,Points.Num()-1)].XY).GetSafeNormal();
    auto EdgeTime=[Half](double Position,double Direction)
    {
        return FMath::Abs(Direction)>UE_SMALL_NUMBER?
            ((Direction>0?Half:-Half)-Position)/Direction:DBL_MAX;
    };
    // A stream may double back towards its head. Use the nearest upstream
    // heading that does not cut across a downstream meander.
    FVector2D HeadEdge=Head;
    for(int32 I=0;I<24;++I)
    {
        const double Angle=15.*((I+1)/2)*(I%2?1:-1);
        const FVector2D Dir=Upstream.GetRotated(Angle);
        const double Reach=FMath::Min(EdgeTime(Head.X,Dir.X),EdgeTime(Head.Y,Dir.Y));
        if(Reach==DBL_MAX)continue;
        const FVector2D Ray=Reach*Dir, End=(Head+Ray).ClampAxes(-Half,Half);
        if(I==0)HeadEdge=End;
        bool Crosses=false;
        for(int32 J=1;J+1<Points.Num();++J)
        {
            const FVector2D Segment=Points[J+1].XY-Points[J].XY, Offset=Points[J].XY-Head;
            const double Det=FVector2D::CrossProduct(Ray,Segment);
            if(FMath::IsNearlyZero(Det))continue;
            const double T=FVector2D::CrossProduct(Offset,Segment)/Det;
            const double U=FVector2D::CrossProduct(Offset,Ray)/Det;
            if(T>0.&&T<=1.&&U>=0.&&U<=1.){Crosses=true;break;}
        }
        if(!Crosses){HeadEdge=End;break;}
    }
    Line.Add(HeadEdge);
    for(const FPoint& P:Points)Line.Add(P.XY.ClampAxes(-Half,Half));
    // The drainage grid can end a fraction of one grid spacing inside a
    // non-aligned map. Carry the outlet to its nearest actual boundary.
    FVector2D Outlet=Line.Last();
    if(FMath::Abs(Outlet.X)>FMath::Abs(Outlet.Y))Outlet.X=FMath::Sign(Outlet.X)*Half;
    else Outlet.Y=FMath::Sign(Outlet.Y)*Half;
    if(!Outlet.Equals(Line.Last(),.01))Line.Add(Outlet);
    // Close the divider along the square perimeter. Even/odd scan conversion
    // handles bends and rivers whose source and outlet touch the same edge.
    auto Perimeter=[Half](FVector2D P)
    {
        const double S=2*Half;
        if(FMath::Abs(P.Y+Half)<.01)return P.X+Half;
        if(FMath::Abs(P.X-Half)<.01)return S+P.Y+Half;
        if(FMath::Abs(P.Y-Half)<.01)return 2*S+Half-P.X;
        return 3*S+Half-P.Y;
    };
    const double Start=Perimeter(Line.Last());
    double End=Perimeter(Line[0]);
    if(End<Start)End+=8*Half;
    const FVector2D Corners[]={{-Half,-Half},{Half,-Half},{Half,Half},{-Half,Half}};
    for(int32 I=1;I<8;++I)
        if(2*Half*I>Start&&2*Half*I<End)Line.Add(Corners[I%4]);
    return Line;
}

void FPlan::BuildRainforest(int32 Seed,double Half)
{
    const auto& R=Ecology.Rainforest;
    ForestHalfSize=Half;
    const double Inset=Half*.10;
    ForestAnchor=FVector2D(R.CenterX,TemperateHillsSurface::ValleyY(R.CenterX,Seed)+R.NorthOfValleyCm)
        .ClampAxes(-Half+Inset,Half-Inset);
    if(R.Strength<=0||R.AreaFraction<=0)return;
    const int32 N=FMath::Max(2,FMath::CeilToInt(2.*Half/400.));
    ForestGridSize=N;
    const double Step=2.*Half/N;
    auto Center=[&](int32 X,int32 Y){return FVector2D(-Half+(X+.5)*Step,-Half+(Y+.5)*Step);};
    const int32 Count=N*N;
    RainforestMask.Init(0,Count);
    TArray<int8> Sides;Sides.Init(-1,Count);
    TArray<bool> Inland;Inland.Init(false,Count);
    TArray<bool> NearBank;NearBank.Init(false,Count);
    const auto Line=BankDivider(Points,Half);
    TArray<double> Crossings;
    for(int32 Y=0;Y<N;++Y)
    {
        Crossings.Reset();
        const double WY=Center(0,Y).Y;
        for(int32 I=0,J=Line.Num()-1;I<Line.Num();J=I++)
        {
            const auto& A=Line[J];const auto& B=Line[I];
            if((A.Y>WY)!=(B.Y>WY))
                Crossings.Add(A.X+(WY-A.Y)*(B.X-A.X)/(B.Y-A.Y));
        }
        Crossings.Sort();
        int32 Crossing=0;
        for(int32 X=0;X<N;++X)
        {
            const FVector2D P=Center(X,Y);
            while(Crossing<Crossings.Num()&&Crossings[Crossing]<=P.X)++Crossing;
            const auto Bank=Sample(P.X,P.Y);
            const double DryDistance=Bank.Distance-Bank.HalfWidth;
            // Even the bilinear support footprint of a nonzero texel must
            // end on dry land (also allow for asymmetric widths at bends).
            if(DryDistance<1.5*Step+200.)continue;
            const int32 Side=Crossing&1;
            Sides[Y*N+X]=Side;
            Inland[Y*N+X]=DryDistance>2200.;
            NearBank[Y*N+X]=DryDistance<3.5*Step+200.;
        }
    }
    const int32 Target=FMath::Clamp(FMath::RoundToInt(Count*R.AreaFraction),1,Count);
    // Count connected land: meanders and the upstream extension can cut off
    // pockets too small for the quota. Prefer the side containing the old grove.
    TArray<int32> Labels;Labels.Init(INDEX_NONE,Count);
    TArray<int32> Queue;
    int32 Chosen=INDEX_NONE,BestSize=0,BankSeed=INDEX_NONE;
    double BestDistance=DBL_MAX;
    const FVector2D Preferred=ForestAnchor;
    for(int32 Start=0;Start<Count;++Start)
    {
        if(Sides[Start]<0||Labels[Start]!=INDEX_NONE)continue;
        Queue.Reset();Queue.Add(Start);Labels[Start]=Start;
        double Distance=DBL_MAX,BankDistance=DBL_MAX;
        int32 NearestBank=INDEX_NONE;
        FVector2D Anchor=Center(Start%N,Start/N);
        auto Visit=[&](int32 I)
        {
            if(Labels[I]==INDEX_NONE&&Sides[I]==Sides[Start]){Labels[I]=Start;Queue.Add(I);}
        };
        for(int32 Head=0;Head<Queue.Num();++Head)
        {
            const int32 I=Queue[Head],X=I%N,Y=I/N;
            const auto P=Center(X,Y);
            const double D=FVector2D::DistSquared(P,Preferred);
            if(Inland[I]&&D<Distance){Distance=D;Anchor=P;}
            if(NearBank[I]&&D<BankDistance){BankDistance=D;NearestBank=I;}
            if(X>0)Visit(I-1);
            if(X+1<N)Visit(I+1);
            if(Y>0)Visit(I-N);
            if(Y+1<N)Visit(I+N);
        }
        if((Queue.Num()>=Target&&(BestSize<Target||Distance<BestDistance))||
            (BestSize<Target&&Queue.Num()>BestSize))
        {Chosen=Start;BestSize=Queue.Num();BestDistance=Distance;ForestAnchor=Anchor;BankSeed=NearestBank;}
    }
    if(Chosen==INDEX_NONE)return;
    const int32 PreferredCell=FMath::FloorToInt((Preferred.Y+Half)/Step)*N+
        FMath::FloorToInt((Preferred.X+Half)/Step);
    if(Labels[PreferredCell]==Chosen && Inland[PreferredCell])ForestAnchor=Preferred;
    int32 StartCell=FMath::FloorToInt((ForestAnchor.Y+Half)/Step)*N+
        FMath::FloorToInt((ForestAnchor.X+Half)/Step);
    FVector2D GrowthCenter=ForestAnchor;
    if(BankSeed!=INDEX_NONE)
    {
        StartCell=BankSeed;
        const FVector2D BankCenter=Center(BankSeed%N,BankSeed/N);
        GrowthCenter=BankCenter+((ForestAnchor-BankCenter)*.5).GetClampedToMaxSize(.35*Half);
    }

    // Grow a connected footprint around the old grove. The priority queue
    // follows broad seeded contours; the sorted acceptance order provides
    // both a map-area quota and a feathered inland boundary.
    struct FCell
    {
        double Score;
        int32 Index;
        bool operator<(const FCell& B) const {return Score==B.Score?Index<B.Index:Score<B.Score;}
    };
    TArray<FCell> Frontier;
    TArray<int32> Order;
    auto Enqueue=[&](int32 X,int32 Y)
    {
        if(X<0||X>=N||Y<0||Y>=N)return;
        const int32 I=Y*N+X;
        if(Labels[I]!=Chosen)return;
        Labels[I]=INDEX_NONE;
        const FVector2D P=Center(X,Y);
        const FVector2D Delta=(P-GrowthCenter)*FVector2D(.88,1.12);
        const double Irregularity=TemperateHillsSurface::Noise5(P.X/(Half*.25),P.Y/(Half*.25),Seed,3511);
        Frontier.HeapPush({Delta.Size()+Half*.10*Irregularity,I});
    };
    const int32 Blend=FMath::Max(1,FMath::RoundToInt(Target*R.EdgeBlend*.5));
    Enqueue(StartCell%N,StartCell/N);
    while(!Frontier.IsEmpty()&&Order.Num()<Target+Blend)
    {
        FCell Cell;Frontier.HeapPop(Cell,EAllowShrinking::No);
        Order.Add(Cell.Index);
        const int32 X=Cell.Index%N,Y=Cell.Index/N;
        Enqueue(X-1,Y);Enqueue(X+1,Y);Enqueue(X,Y-1);Enqueue(X,Y+1);
    }
    for(int32 Rank=0;Rank<Order.Num();++Rank)
    {
        const double Weight=1.-FMath::SmoothStep(double(Target-Blend),double(Target+Blend),Rank+.5);
        RainforestMask[Order[Rank]]=FMath::RoundToInt(255.*Weight);
    }
    // The old grove can lie far from the river on a different seed. Keep
    // the pond search and visit anchor inside the generated forest.
    if(!Order.IsEmpty()&&RainforestWeight(ForestAnchor.X,ForestAnchor.Y)<.75*R.Strength)
    {
        double Nearest=DBL_MAX;
        for(int32 I:Order)
        {
            if(!Inland[I]||RainforestMask[I]<224)continue;
            const FVector2D P=Center(I%N,I/N);
            const double D=FVector2D::DistSquared(P,Preferred);
            if(D<Nearest){Nearest=D;ForestAnchor=P;}
        }
    }
}

double FPlan::RainforestWeight(double X,double Y) const
{
    const int32 N=ForestGridSize;
    if(!N||FMath::Abs(X)>ForestHalfSize||FMath::Abs(Y)>ForestHalfSize)return 0.;
    const double Scale=N/(2.*ForestHalfSize);
    const double U=FMath::Clamp((X+ForestHalfSize)*Scale-.5,0.,double(N-1));
    const double V=FMath::Clamp((Y+ForestHalfSize)*Scale-.5,0.,double(N-1));
    const int32 IX=int32(U),IY=int32(V),JX=FMath::Min(IX+1,N-1),JY=FMath::Min(IY+1,N-1);
    const double A=FMath::Lerp(double(RainforestMask[IY*N+IX]),double(RainforestMask[IY*N+JX]),U-IX);
    const double B=FMath::Lerp(double(RainforestMask[JY*N+IX]),double(RainforestMask[JY*N+JX]),U-IX);
    return FMath::Lerp(A,B,V-IY)*(Ecology.Rainforest.Strength/255.);
}
}
