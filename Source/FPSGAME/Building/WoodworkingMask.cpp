#include "WoodworkingMask.h"
#include "Serialization/MemoryReader.h"

namespace ColdSteelWoodworking
{
double FMetrics::Quality(const FSettings& S,double Elapsed) const
{
    const double Total=S.IntegrityWeight+S.EdgeWeight+S.ClearanceWeight+S.SpeedWeight;
    const double Speed=FMath::Clamp(1.0-Elapsed/S.Seconds,0.0,1.0);
    return Total>0?100.0*(Integrity*S.IntegrityWeight+EdgeFit*S.EdgeWeight+Clearance*S.ClearanceWeight+Speed*S.SpeedWeight)/Total:0;
}
void FMask::Neighbours(int32 Cell,TArray<int32,TInlineAllocator<4>>& Out) const
{
    Out.Reset();const int32 X=Cell%Config.Width,Y=Cell/Config.Width;
    if(X>0)Out.Add(Cell-1);if(X+1<Config.Width)Out.Add(Cell+1);
    if(Y>0)Out.Add(Cell-Config.Width);if(Y+1<Config.Height)Out.Add(Cell+Config.Width);
}
bool FMask::Initialize(const FSettings& Settings,const TArray<FVector2D>& Polygon,const TArray<FVector2D>& Anchors,FString& Error)
{
    *this=FMask();Config=Settings;Error=TEXT("木工轮廓配置无效");
    if(Config.Width<64||Config.Height<64||Config.Width>768||Config.Height>512||Polygon.Num()<3||Polygon.Num()>128||Anchors.Num()<2||Anchors.Num()>16)return false;
    for(const auto& P:Polygon)if(!FMath::IsFinite(P.X)||!FMath::IsFinite(P.Y)||P.X<0||P.Y<0||P.X>1||P.Y>1)return false;
    const int32 Count=Config.Width*Config.Height;
    WoodMask.Init(1,Count);TargetMask.Init(0,Count);DamageMask.Init(0,Count);TargetBoundary.Init(0,Count);EdgeBand.Init(0,Count);
    for(int32 Y=0;Y<Config.Height;++Y)for(int32 X=0;X<Config.Width;++X)
    {
        const FVector2D P((X+.5)/Config.Width,(Y+.5)/Config.Height);bool Inside=false;
        for(int32 I=0,J=Polygon.Num()-1;I<Polygon.Num();J=I++)
        {
            const auto A=Polygon[I],B=Polygon[J];
            if((A.Y>P.Y)!=(B.Y>P.Y)&&P.X<(B.X-A.X)*(P.Y-A.Y)/(B.Y-A.Y)+A.X)Inside=!Inside;
        }
        if(Inside){TargetMask[Y*Config.Width+X]=1;++TargetCount;}
    }
    if(TargetCount<16||TargetCount>=Count)return false;
    for(const auto& P:Anchors)
    {
        if(!FMath::IsFinite(P.X)||!FMath::IsFinite(P.Y)||P.X<0||P.Y<0||P.X>=1||P.Y>=1)return false;
        const int32 Cell=int32(P.Y*Config.Height)*Config.Width+int32(P.X*Config.Width);
        if(!TargetMask[Cell])return false;CriticalCells.Add(Cell);
    }
    TArray<int32> Distance,Queue;Distance.Init(-1,Count);Queue.Reserve(Count);
    TArray<int32,TInlineAllocator<4>> Adjacent;
    for(int32 I=0;I<Count;++I)if(TargetMask[I])
    {
        Distance[I]=0;Queue.Add(I);Neighbours(I,Adjacent);
        bool Edge=Adjacent.Num()<4;for(int32 N:Adjacent)Edge|=!TargetMask[N];
        if(Edge){TargetBoundary[I]=1;++BoundaryCount;}
    }
    for(int32 Head=0;Head<Queue.Num();++Head)
    {
        const int32 I=Queue[Head];if(Distance[I]>=Config.EdgeBandPixels)continue;
        Neighbours(I,Adjacent);
        for(int32 N:Adjacent)if(Distance[N]<0){Distance[N]=Distance[I]+1;Queue.Add(N);EdgeBand[N]=1;++BandCount;}
    }
    WasteCount=Count-TargetCount;KeptTarget=TargetCount;RemainingWaste=WasteCount;KeptBoundary=BoundaryCount;RemainingBand=BandCount;
    UndoRemaining=Config.UndoLimit;ChangeSerial=1;
    if(!ConnectionsIntact())return false;
    Error.Reset();return true;
}
void FMask::SerializeNetwork(FArchive& Ar)
{
    Ar<<WoodMask<<DamageMask<<LastStroke<<KeptTarget<<RemainingWaste<<KeptBoundary<<RemainingBand<<UndoRemaining<<bStroke;
}

bool FMask::RestoreNetwork(const TArray<uint8>& Bytes)
{
    FMask Next=*this;FMemoryReader Ar(Bytes);Next.SerializeNetwork(Ar);
    const int32 Count=Config.Width*Config.Height;
    if(Ar.IsError()||Next.WoodMask.Num()!=Count||Next.DamageMask.Num()!=Count||Next.LastStroke.Num()>Count)return false;
    for(int32 Cell:Next.LastStroke)if(Cell<0||Cell>=Count)return false;
    const bool Changed=WoodMask!=Next.WoodMask||DamageMask!=Next.DamageMask;
    Next.ChangeSerial=ChangeSerial+(Changed?1:0);Next.CutFeedback={};
    *this=MoveTemp(Next);return true;
}

void FMask::BeginStroke(){if(bStroke)return;LastStroke.Reset();bStroke=true;}
void FMask::Remove(int32 Cell)
{
    if(!WoodMask[Cell])return;
    WoodMask[Cell]=0;LastStroke.Add(Cell);
    if(TargetMask[Cell]){DamageMask[Cell]=1;--KeptTarget;}else --RemainingWaste;
    if(TargetBoundary[Cell])--KeptBoundary;if(EdgeBand[Cell])--RemainingBand;
}
namespace
{
// Translation sweeps a finite line segment into a convex quad. Inflating its boundary
// by half the game's kerf covers the entire interval, including a large input delta.
struct FSawSweep
{
    FVector2D P[4];double RadiusSquared=0,Area=0;
    int32 MinX=0,MaxX=-1,MinY=0,MaxY=-1;
    FSawSweep(FVector2D A0,FVector2D B0,FVector2D A1,FVector2D B1,double Radius,int32 Width,int32 Height)
    {
        P[0]=A0;P[1]=B0;P[2]=B1;P[3]=A1;
        if(!FMath::IsFinite(Radius)||Radius<=0)return;
        FVector2D Lo=A0,Hi=A0;
        for(int32 I=0;I<4;++I)
        {
            if(!FMath::IsFinite(P[I].X)||!FMath::IsFinite(P[I].Y))return;
            Lo.X=FMath::Min(Lo.X,P[I].X);Lo.Y=FMath::Min(Lo.Y,P[I].Y);
            Hi.X=FMath::Max(Hi.X,P[I].X);Hi.Y=FMath::Max(Hi.Y,P[I].Y);
            Area+=FVector2D::CrossProduct(P[I],P[(I+1)%4]);
        }
        if(Hi.X+Radius<0||Hi.Y+Radius<0||Lo.X-Radius>=Width||Lo.Y-Radius>=Height)return;
        MinX=FMath::Clamp(FMath::FloorToInt(Lo.X-Radius),0,Width-1);
        MaxX=FMath::Clamp(FMath::CeilToInt(Hi.X+Radius),0,Width-1);
        MinY=FMath::Clamp(FMath::FloorToInt(Lo.Y-Radius),0,Height-1);
        MaxY=FMath::Clamp(FMath::CeilToInt(Hi.Y+Radius),0,Height-1);RadiusSquared=Radius*Radius;
    }
    bool Contains(FVector2D Point) const
    {
        bool Positive=false,Negative=false;
        for(int32 I=0;I<4;++I)
        {
            const FVector2D D=P[(I+1)%4]-P[I],Offset=Point-P[I];
            const double Cross=FVector2D::CrossProduct(D,Offset);Positive|=Cross>1.e-8;Negative|=Cross<-1.e-8;
            const double Length=D.SizeSquared(),T=Length>0?FMath::Clamp(FVector2D::DotProduct(Offset,D)/Length,0.0,1.0):0;
            if((Offset-D*T).SizeSquared()<=RadiusSquared)return true;
        }
        return FMath::Abs(Area)>1.e-8&&!(Positive&&Negative);
    }
};
}
bool FMask::SawTouches(const FVector2D& A0,const FVector2D& B0,const FVector2D& A1,const FVector2D& B1,double HalfKerf,bool IncludeRemoved) const
{
    if(WoodMask.IsEmpty())return false;
    const FSawSweep Sweep(A0,B0,A1,B1,HalfKerf,Config.Width,Config.Height);
    for(int32 Y=Sweep.MinY;Y<=Sweep.MaxY;++Y)for(int32 X=Sweep.MinX;X<=Sweep.MaxX;++X)
        if((IncludeRemoved||WoodMask[Y*Config.Width+X])&&Sweep.Contains(FVector2D(X+.5,Y+.5)))return true;
    return false;
}
bool FMask::SawEntersWood(const FVector2D& A0,const FVector2D& B0,const FVector2D& A1,const FVector2D& B1,double HalfKerf) const
{
    if(WoodMask.IsEmpty())return false;
    const FSawSweep Sweep(A0,B0,A1,B1,HalfKerf,Config.Width,Config.Height);
    const FSawSweep Initial(A0,B0,A0,B0,HalfKerf,Config.Width,Config.Height);
    for(int32 Y=Sweep.MinY;Y<=Sweep.MaxY;++Y)for(int32 X=Sweep.MinX;X<=Sweep.MaxX;++X)
    {
        const FVector2D Point(X+.5,Y+.5);
        if(WoodMask[Y*Config.Width+X]&&Sweep.Contains(Point)&&!Initial.Contains(Point))return true;
    }
    return false;
}
bool FMask::CutSawSweep(const FVector2D& A0,const FVector2D& B0,const FVector2D& A1,const FVector2D& B1,double HalfKerf)
{
    CutFeedback={};if(!bStroke||WoodMask.IsEmpty())return false;
    const FSawSweep Sweep(A0,B0,A1,B1,HalfKerf,Config.Width,Config.Height);
    for(int32 Y=Sweep.MinY;Y<=Sweep.MaxY;++Y)for(int32 X=Sweep.MinX;X<=Sweep.MaxX;++X)
    {
        const int32 Cell=Y*Config.Width+X;const FVector2D Point(X+.5,Y+.5);
        if(!WoodMask[Cell]||!Sweep.Contains(Point))continue;
        ++CutFeedback.Removed;
        if(TargetMask[Cell]){++CutFeedback.Damaged;CutFeedback.DamagePoint=Point;}
        if(CutFeedback.Samples.Num()<8)CutFeedback.Samples.Add(Point);
        else if((CutFeedback.Removed%23)==0)CutFeedback.Samples[(CutFeedback.Removed/23)%8]=Point;
        Remove(Cell);
    }
    if(CutFeedback.Removed>0){++ChangeSerial;++CutGeneration;return true;}return false;
}
void FMask::PeelWaste()
{
    const int32 Count=WoodMask.Num();TArray<uint8> Seen;Seen.Init(0,Count);
    TArray<uint8> Detached;Detached.Init(0,Count);bool Any=false;
    TArray<int32> Queue;Queue.Reserve(Count);TArray<int32,TInlineAllocator<4>> Adjacent;
    for(int32 Seed=0;Seed<Count;++Seed)if(WoodMask[Seed]&&!Seen[Seed])
    {
        Queue.Reset();Queue.Add(Seed);Seen[Seed]=1;bool HasTarget=false;
        for(int32 Head=0;Head<Queue.Num();++Head)
        {
            const int32 I=Queue[Head];HasTarget|=TargetMask[I]!=0;Neighbours(I,Adjacent);
            for(int32 N:Adjacent)if(WoodMask[N]&&!Seen[N]){Seen[N]=1;Queue.Add(N);}
        }
        // Any surviving target cell retains its whole component. Never auto-delete a detached piece of the subject.
        if(!HasTarget)for(int32 I:Queue){Detached[I]=1;Any=true;Remove(I);}
    }
    if(Any){PeeledMask=MoveTemp(Detached);++PeelGeneration;}
}
void FMask::EndStroke()
{
    if(!bStroke)return;bStroke=false;
    if(!LastStroke.IsEmpty()&&Config.bAutoPeel){const int32 Before=LastStroke.Num();PeelWaste();if(LastStroke.Num()!=Before)++ChangeSerial;}
}
bool FMask::Undo()
{
    if(!CanUndo())return false;
    for(int32 I:LastStroke)
    {
        WoodMask[I]=1;DamageMask[I]=0;
        if(TargetMask[I])++KeptTarget;else ++RemainingWaste;
        if(TargetBoundary[I])++KeptBoundary;if(EdgeBand[I])++RemainingBand;
    }
    LastStroke.Reset();--UndoRemaining;++ChangeSerial;return true;
}
FMetrics FMask::Metrics() const
{
    FMetrics M;M.Integrity=TargetCount?double(KeptTarget)/TargetCount:1;
    M.Clearance=WasteCount?1.0-double(RemainingWaste)/WasteCount:0;
    M.EdgeFit=.5*(BoundaryCount?double(KeptBoundary)/BoundaryCount:0)+.5*(BandCount?1.0-double(RemainingBand)/BandCount:0);return M;
}
bool FMask::ConnectionsIntact() const
{
    if(CriticalCells.Num()<2)return false;
    for(int32 I:CriticalCells)if(!WoodMask.IsValidIndex(I)||!WoodMask[I])return false;
    TArray<uint8> Seen;Seen.Init(0,WoodMask.Num());TArray<int32> Queue;Queue.Reserve(TargetCount);
    Queue.Add(CriticalCells[0]);Seen[CriticalCells[0]]=1;TArray<int32,TInlineAllocator<4>> Adjacent;
    for(int32 Head=0;Head<Queue.Num();++Head)
    {
        Neighbours(Queue[Head],Adjacent);
        for(int32 N:Adjacent)if(TargetMask[N]&&WoodMask[N]&&!Seen[N]){Seen[N]=1;Queue.Add(N);}
    }
    for(int32 I:CriticalCells)if(!Seen[I])return false;return true;
}
}
