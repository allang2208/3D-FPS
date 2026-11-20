#include "TemperateHillsRiver.h"
#include "TemperateQuarryYard.h"
#include "TemperateVillageSite.h"
#include "DynamicMesh/DynamicMesh3.h"
#include "DynamicMesh/DynamicMeshAttributeSet.h"

namespace TemperateRiver
{
namespace
{
double Ease(double A,double B,double V)
{
    const double T=FMath::Clamp((V-A)/(B-A),0.,1.);
    return T*T*(3.-2.*T);
}
double SegmentDistance(FVector2D P,FVector2D A,FVector2D B)
{
    const FVector2D D=B-A;
    return (P-A-D*FMath::Clamp(FVector2D::DotProduct(P-A,D)/FMath::Max(1.,D.SizeSquared()),0.,1.)).Size();
}
FPoint AtDistance(const TArray<FPoint>& Points,double S)
{
    int32 Low=0,High=Points.Num()-1;
    while(Low+1<High){const int32 M=(Low+High)/2;if(Points[M].Distance<S)Low=M;else High=M;}
    const auto& A=Points[Low];const auto& B=Points[High];
    const double T=FMath::Clamp((S-A.Distance)/FMath::Max(1.,B.Distance-A.Distance),0.,1.);
    FPoint P=A;P.XY=FMath::Lerp(A.XY,B.XY,T);P.WaterZ=FMath::Lerp(A.WaterZ,B.WaterZ,T);
    P.HalfWidth=FMath::Lerp(A.HalfWidth,B.HalfWidth,T);P.Distance=S;
    P.Side=FMath::Lerp(A.Side,B.Side,T).GetSafeNormal();
    return P;
}
}
double FPlan::FLake::LayoutEdge(double X,double Y) const
{
    if(!Valid)return DBL_MAX;
    const FVector2D D=FVector2D(X,Y)-Center;
    const double U=FVector2D::DotProduct(D,Axis)/RadiusX;
    const double V=FVector2D::CrossProduct(Axis,D)/RadiusY;
    const double A=FMath::Atan2(V,U);
    // Three unequal coves and a low peninsula; source/outlet remain on the long axis.
    const double Shape=1.+.065*FMath::Sin(A*3.+Phase)+.035*FMath::Sin(A*5.-Phase)
        -.14*FMath::Pow(FMath::Max(0.,FMath::Cos(A-1.05)),12.);
    return (FMath::Sqrt(U*U+V*V)-Shape)*FMath::Min(RadiusX,RadiusY);
}
double FPlan::FLake::Edge(double X,double Y) const
{return bNaturalShore?NaturalEdge(X,Y):LayoutEdge(X,Y);}
FVector2D FPlan::FWhiteCliffs::Local(double X,double Y) const
{
    const FVector2D D=FVector2D(X,Y)-Center;
    return {FVector2D::DotProduct(D,Axis),FVector2D::CrossProduct(Axis,D)};
}
FVector2D FPlan::FWhiteCliffs::World(double X,double Y) const
{return Center+Axis*X+FVector2D(-Axis.Y,Axis.X)*Y;}
double FPlan::FWhiteCliffs::Weight(double X,double Y) const
{
    if(!Valid)return 0.;
    const auto P=Local(X,Y);
    return 1.-Ease(.64,1.,FMath::Sqrt(FMath::Square(P.X/11500.)+FMath::Square(P.Y/9000.)));
}
double FPlan::FWhiteCliffs::TrailDistance(double X,double Y) const
{
    if(!Valid)return DBL_MAX;
    const auto P=Local(X,Y);
    // A continuous six metre haul road climbs between the three benches.
    return FMath::Abs(P.X-TemperateQuarry::RoadX(P.Y));
}
double FPlan::FWhiteCliffs::Ground(double X,double Y,double Base) const
{
    const double W=Weight(X,Y);if(W<=0.)return Base;
    const auto P=Local(X,Y);
    return FMath::Lerp(Base,FloorZ+TemperateQuarry::CutHeight(P),W);
}
namespace
{
template<typename T>
double SampleSurveyGrid(const TArray<T>& Grid,int32 Side,double Half,double X,double Y)
{
    if(Grid.IsEmpty())return 0.;
    const double GX=FMath::Clamp((X+Half)/(2.*Half)*(Side-1),0.,double(Side-1));
    const double GY=FMath::Clamp((Y+Half)/(2.*Half)*(Side-1),0.,double(Side-1));
    const int32 IX=FMath::Min(int32(GX),Side-2),IY=FMath::Min(int32(GY),Side-2);
    return FMath::BiLerp(double(Grid[IY*Side+IX]),double(Grid[IY*Side+IX+1]),
        double(Grid[(IY+1)*Side+IX]),double(Grid[(IY+1)*Side+IX+1]),GX-IX,GY-IY);
}
}
double FPlan::Protection(double X,double Y) const
{
    return SampleSurveyGrid(ProtectedLand,ProtectedSize,WorldHalf,X,Y)/255.;
}
double FPlan::UplandOffset(double X,double Y) const
{
    const int32 FineSide=2*ProtectedSize-1;
    if(ProtectedSize>1 && UplandReliefCm.Num()==FineSide*FineSide)
        return .25*SampleSurveyGrid(UplandReliefCm,FineSide,WorldHalf,X,Y);
    return SampleSurveyGrid(UplandReliefCm,ProtectedSize,WorldHalf,X,Y);
}
void FPlan::BuildRiverLake(int32 Seed,double Half,const FTemperateVillageSite& Village,const FVector2D& Entry,
    TSharedPtr<const FPlan,ESPMode::ThreadSafe> Original)
{
    if(!Village.bPlaced||GenerationVersion<3)return;
    SettlementBaseline=Original;WorldHalf=Half;
    ProtectedSize=FMath::CeilToInt(2.*Half/400.)+1;
    ProtectedLand.SetNumUninitialized(ProtectedSize*ProtectedSize);
    const FVector2D Gate=Village.Mouth(-1.),Junction=Gate-Village.Axis*Village.FeederLength;
    TArray<FVector2D> Road;
    const double MinX=FMath::Min(Entry.X,Junction.X),MaxX=FMath::Max(Entry.X,Junction.X);
    for(double X=MinX;X<MaxX;X+=400.)Road.Add({X,TemperateHillsSurface::ValleyY(X,Seed)});
    Road.Add({MaxX,TemperateHillsSurface::ValleyY(MaxX,Seed)});
    Road.Add(Junction);Road.Add(Gate);
    for(int32 Y=0;Y<ProtectedSize;++Y)for(int32 X=0;X<ProtectedSize;++X)
    {
        const FVector2D P(-Half+2.*Half*X/(ProtectedSize-1),-Half+2.*Half*Y/(ProtectedSize-1));
        double RoadD=DBL_MAX;
        for(int32 I=1;I<Road.Num();++I)RoadD=FMath::Min(RoadD,SegmentDistance(P,Road[I-1],Road[I]));
        const double VillageEdge=Village.EdgeDistance(Village.Local(P.X,P.Y))-Village.Shoulder;
        const double W=FMath::Max(1.-Ease(800.,2200.,VillageEdge),
            FMath::Max(1.-Ease(2200.,3600.,RoadD),1.-Ease(6500.,8000.,(P-Entry).Size())));
        ProtectedLand[Y*ProtectedSize+X]=FMath::RoundToInt(W*255.);
    }
    if(Points.Num()<2)
    {
        SettlementBaseline.Reset();
        BuildUplandRelief(Seed);
        return;
    }
    const auto Old=Points;
    const double Length=Old.Last().Distance;
    // Place the terminal lake on the downstream half, leaving room for both shore
    // and a neighbouring quarry. This finite survey never relocates the settlement.
    double Best=-DBL_MAX;
    for(double S=Length*.35;S<=Length*.90;S+=2400.)
    {
        const auto P=AtDistance(Old,S);
        const FVector2D Forward(P.Side.Y,-P.Side.X);
        for(double Offset:{-3500.,0.,3500.})
        {
            FLake Candidate;Candidate.Valid=true;Candidate.Center=P.XY+P.Side*Offset;Candidate.Axis=Forward;
            Candidate.LandformSeed=Seed;
            Candidate.Phase=TemperateHillsSurface::Unit(TemperateHillsSurface::Key(0,0,Seed,3511))*6.28;
            double Low=DBL_MAX,High=-DBL_MAX,Sum=0.;bool Fits=true;
            // Include interior points: a clear shoreline alone cannot exclude a road crossing.
            for(int32 V=-4;V<=4&&Fits;++V)for(int32 U=-5;U<=5;++U)
            {
                const FVector2D Q=Candidate.Center+Forward*(U*Candidate.RadiusX/4.)+P.Side*(V*Candidate.RadiusY/3.);
                if(Candidate.Edge(Q.X,Q.Y)>3200.)continue;
                if(FMath::Abs(Q.X)>Half-800.||FMath::Abs(Q.Y)>Half-800.||Protection(Q.X,Q.Y)>.001){Fits=false;break;}
                const double Z=Original->Height(Q.X,Q.Y,Seed);Low=FMath::Min(Low,Z);High=FMath::Max(High,Z);Sum+=Z;
            }
            if(!Fits)continue;
            const double Score=S*.12-(High-Low)*2.-FMath::Abs(Offset)*.10;
            if(Score>Best){Best=Score;Lake=Candidate;Lake.Along=S;}
        }
    }
    if(!Lake.Valid)
    {
        // Constrained smaller worlds retain their old course rather than flood the
        // protected village. Production 1024 m worlds use the full 260 x 180 m lake.
        UE_LOG(LogTemp,Warning,TEXT("HILLS_RIVER_LAKE no protected lake site seed=%d"),Seed);
        SettlementBaseline.Reset();
        BuildUplandRelief(Seed);
        return;
    }
    // Broad seed-stable lateral lobes, continuous in arc length. Each lobe has
    // different amplitude and spacing; no per-point random jitter or periodic sine.
    struct FLobe{double Start,End,Amplitude;};
    TArray<FLobe> Lobes;
    FRandomStream Stream(Seed^0x534a17);
    for(double S=0.,Sign=Stream.RandRange(0,1)?1.:-1.;S<Length;Sign=-Sign)
    {
        const double End=FMath::Min(Length,S+Stream.FRandRange(11000.f,19000.f));
        const double Limit=FMath::Square(End-S)/(2.*PI*PI*3500.);
        Lobes.Add({S,End,Sign*FMath::Min(double(Stream.FRandRange(1800.f,3600.f)),Limit)});S=End;
    }
    TArray<FPoint> Curved;
    for(double S=0.;S<Length+199.;S+=200.)
    {
        auto P=AtDistance(Old,FMath::Min(S,Length));
        double Offset=0.;
        for(const auto& L:Lobes)if(S>=L.Start&&S<=L.End)
        {const double T=(S-L.Start)/(L.End-L.Start);Offset=L.Amplitude*FMath::Pow(FMath::Sin(PI*T),2.);break;}
        const double Head=Ease(0.,2400.,S)*(1.-Ease(Length-2800.,Length,S));
        Offset*=Head;
        const FVector2D Before=AtDistance(Old,FMath::Max(0.,S-2800.)).XY;
        const FVector2D After=AtDistance(Old,FMath::Min(Length,S+2800.)).XY;
        const FVector2D Tangent=(After-Before).GetSafeNormal();
        const FVector2D Side(-Tangent.Y,Tangent.X);
        const FVector2D Change=((Before+P.XY*2.+After)*.25-P.XY)*Head+Side*Offset;
        // Fade the displacement near immutable settlement/road corridors.
        double Allowed=1.;
        for(int32 J=0;J<=4;++J)
        {
            const FVector2D Q=P.XY+Change*(J/4.);
            Allowed=FMath::Min(Allowed,1.-Protection(Q.X,Q.Y));
        }
        P.XY+=Change*Allowed;
        P.XY=P.XY.ClampAxes(-Half+100.,Half-100.);
        Curved.Add(P);
        if(S>=Length)break;
    }
    // Remove short hairpin shortcuts and prevent distant reaches intersecting.
    // Reduced displacement retains the drainage identity if a proposed bend crowds another reach.
    for(int32 Pass=0;Pass<3;++Pass)
    {
        bool Changed=false;
        for(int32 I=1;I+1<Curved.Num();++I)
        {
            bool Close=false;
            for(int32 J=I+16;J<Curved.Num();++J)
                if((Curved[I].XY-Curved[J].XY).SizeSquared()<FMath::Square(2200.)){Close=true;break;}
            if(Close){Curved[I].XY=FMath::Lerp(Curved[I].XY,AtDistance(Old,Curved[I].Distance).XY,.65);Changed=true;}
        }
        if(!Changed)break;
    }
    Points=MoveTemp(Curved);
    // The lake uses the old drainage level at its last downstream crossing.
    double LastInside=Lake.Along;
    for(const auto& P:Points)if(Lake.Edge(P.XY.X,P.XY.Y)<0.)LastInside=P.Distance;
    Lake.WaterZ=AtDistance(Old,LastInside).WaterZ;
    Lake.Along=LastInside;
    double Water=DBL_MAX,Distance=0.;
    for(int32 I=0;I<Points.Num();++I)
    {
        auto& P=Points[I];
        const double Step=I?(P.XY-Points[I-1].XY).Size():0.;Distance+=Step;
        const double OldS=P.Distance;
        const double OriginalWater=AtDistance(Old,OldS).WaterZ;
        const auto OriginalPoint=AtDistance(Old,OldS);
        const double Preserve=Protection(P.XY.X,P.XY.Y);
        double Target=OriginalWater;
        if(OldS<=LastInside)
        {
            const double Approach=1.-Ease(0.,11000.,FMath::Max(0.,Lake.Edge(P.XY.X,P.XY.Y)));
            Target=FMath::Lerp(Target,Lake.WaterZ,Approach);
            Target=FMath::Max(Target,Lake.WaterZ);
        }
        if(Lake.Edge(P.XY.X,P.XY.Y)<0.)Target=Lake.WaterZ;
        Water=FMath::Min(Water,Target);
        P.WaterZ=FMath::Lerp(Water,OriginalWater,Preserve);P.Distance=Distance;
        const FVector2D Tangent=(Points[FMath::Min(I+1,Points.Num()-1)].XY-Points[FMath::Max(0,I-1)].XY).GetSafeNormal();
        P.Side={-Tangent.Y,Tangent.X};
        const auto In=(P.XY-Points[FMath::Max(0,I-8)].XY).GetSafeNormal();
        const auto Out=(Points[FMath::Min(I+8,Points.Num()-1)].XY-P.XY).GetSafeNormal();
        P.Bend=FMath::Clamp(FVector2D::CrossProduct(In,Out)*2.5,-.8,.8);
        const double Inlet=(1.-Ease(0.,4500.,FMath::Abs(Lake.Edge(P.XY.X,P.XY.Y))))*(OldS<LastInside?1.:0.);
        P.HalfWidth=FMath::Clamp(P.HalfWidth*1.25,380.,800.)+Inlet*350.;
        if(OldS>LastInside)P.HalfWidth*=.55; // quiet overflow beyond the main river's lake destination
        P.HalfWidth*=FMath::Lerp(.08,1.,Ease(0.,2200.,Distance));
        const double Noise=TemperateHillsSurface::Noise(Distance/3500.,2.,Seed,3547)*.14;
        P.LeftWidth=P.HalfWidth*(1.+Noise+P.Bend*.15);
        P.RightWidth=P.HalfWidth*(1.-Noise-P.Bend*.15);
        P.Depth=FMath::Lerp(38.,75.,Ease(0.,1800.,Distance));
        P.Speed=FMath::Lerp(55.,18.,Inlet);
        P.HalfWidth=FMath::Lerp(P.HalfWidth,OriginalPoint.HalfWidth,Preserve);
        P.LeftWidth=FMath::Lerp(P.LeftWidth,OriginalPoint.LeftWidth,Preserve);
        P.RightWidth=FMath::Lerp(P.RightWidth,OriginalPoint.RightWidth,Preserve);
        P.Depth=FMath::Lerp(P.Depth,OriginalPoint.Depth,Preserve);
        P.Speed=FMath::Lerp(P.Speed,OriginalPoint.Speed,Preserve);
    }
    bRiverLake=true;RebuildBuckets();
    // Pick a dry shore-side region whose entire terrain apron clears the preserved land.
    double CliffBest=-DBL_MAX;
    for(int32 Direction=0;Direction<16;++Direction)for(double Radius:{23000.,27000.,31000.})
    {
        FWhiteCliffs C;C.Valid=true;C.Axis=Lake.Axis;
        const double Angle=Direction*2.*PI/16.;
        const FVector2D Away(FMath::Cos(Angle),FMath::Sin(Angle));
        C.Center=Lake.Center+Away*Radius;
        C.Axis=FVector2D(Away.Y,-Away.X);
        bool Fits=true;
        for(int32 Y=-4;Y<=4&&Fits;++Y)for(int32 X=-5;X<=5;++X)
        {
            const auto Q=C.World(X*2300.,Y*2250.);
            if(C.Weight(Q.X,Q.Y)<=0.)continue;
            const auto R=Sample(Q.X,Q.Y);
            if(FMath::Abs(Q.X)>Half-1000.||FMath::Abs(Q.Y)>Half-1000.||Protection(Q.X,Q.Y)>.001||R.Bank>.01){Fits=false;break;}
        }
        if(!Fits)continue;
        // Quarry faces and access ramp open toward the lake.
        C.FloorZ=Original->Height(C.Center.X,C.Center.Y,Seed);
        const double Score=-FMath::Abs(C.FloorZ-Lake.WaterZ-800.)-Radius*.03;
        if(Score>CliffBest){WhiteCliffs=C;CliffBest=Score;}
    }
    // Keep the original site survey, water level, river and quarry anchors. The
    // finishing layer is enabled only after those deterministic choices are made.
    Lake.RiverMouths.Reset();
    for(int32 I=1;I<Points.Num();++I)
    {
        const auto A=Points[I-1].XY,B=Points[I].XY;
        const double EA=Lake.LayoutEdge(A.X,A.Y),EB=Lake.LayoutEdge(B.X,B.Y);
        if((EA<=0.)!=(EB<=0.))Lake.RiverMouths.Add(FMath::Lerp(A,B,EA/(EA-EB)));
    }
    Lake.bNaturalShore=true;
    Lake.BuildBankPatches();
    BuildUplandRelief(Seed);
    QuarryLakeSlope.Build(*this,Seed);
    UE_LOG(LogTemp,Display,TEXT("HILLS_RIVER_LAKE planned seed=%d river_samples=%d lake=(%.0f,%.0f) size_m=260x180 cliffs=%d village_preserved=1"),
        Seed,Points.Num(),Lake.Center.X,Lake.Center.Y,WhiteCliffs.Valid?1:0);
}

void FPlan::BuildRiverLakeMesh(double X,double Y,double Size,UE::Geometry::FDynamicMesh3& Mesh) const
{
    Mesh.EnableAttributes();Mesh.Attributes()->EnablePrimaryColors();
    auto* Normals=Mesh.Attributes()->PrimaryNormals();auto* UVs=Mesh.Attributes()->PrimaryUV();auto* Colors=Mesh.Attributes()->PrimaryColors();
    // Constant lattice along shared cell boundaries; interior lake cells can use
    // the same mesh cost (2 m) without a crack-prone mixed-resolution shoreline.
    const int32 N=FMath::RoundToInt(Size/200.);const double Step=Size/N;
    struct V{FVector3d P;double Edge;FSample S;};
    TArray<V> Grid;Grid.SetNumUninitialized((N+1)*(N+1));
    for(int32 J=0;J<=N;++J)for(int32 I=0;I<=N;++I)
    {
        auto& A=Grid[J*(N+1)+I];const double WX=X+I*Step,WY=Y+J*Step;
        A.S=Sample(WX,WY);A.Edge=FMath::Min(10000.,A.S.Distance-A.S.HalfWidth);
        A.P={WX,WY,A.S.WaterZ};
    }
    auto Emit=[&](TArray<V,TInlineAllocator<4>> Poly)
    {
        TArray<V,TInlineAllocator<4>> Out;
        V Prev=Poly.Last();
        for(const auto& Current:Poly)
        {
            if((Prev.Edge<=0.)!=(Current.Edge<=0.))
            {
                const double T=Prev.Edge/(Prev.Edge-Current.Edge);
                V Cut;Cut.P=FMath::Lerp(Prev.P,Current.P,T);Cut.S=Sample(Cut.P.X,Cut.P.Y);
                Cut.P.Z=Cut.S.WaterZ;Cut.Edge=0.;Out.Add(Cut);
            }
            if(Current.Edge<=0.)Out.Add(Current);
            Prev=Current;
        }
        for(int32 I=1;I+1<Out.Num();++I)
        {
            const FVector3d Cross=(Out[I].P-Out[0].P).Cross(Out[I+1].P-Out[0].P);
            if(Cross.SquaredLength()<.01)continue;
            const FVector3f Normal(-Cross.GetSafeNormal());
            const int32 Start=Mesh.VertexCount();
            for(const auto& A:{Out[0],Out[I],Out[I+1]})
            {
                Mesh.AppendVertex(A.P-FVector3d(X,Y,0.));Normals->AppendElement(Normal);
                UVs->AppendElement(FVector2f(A.P.X/400.,A.P.Y/400.));
                const FVector2D Flow=A.S.bLake?Lake.Axis:A.S.Flow;
                const double WetDepth=A.S.bLake?(Lake.bNaturalShore?A.S.Depth:A.S.Depth*Ease(0.,2800.,-A.Edge)):
                    A.S.Depth*(1.-Ease(.05,1.,A.S.Distance/FMath::Max(1.,A.S.HalfWidth)));
                const float Depth=FMath::Clamp(float(WetDepth/100.),0.f,1.f);
                Colors->AppendElement(FVector4f(Flow.X*.5+.5,Flow.Y*.5+.5,A.S.bLake?.025f:float(A.S.Speed/160.),Depth));
            }
            const int32 ID=Mesh.AppendTriangle(Start,Start+1,Start+2);
            const UE::Geometry::FIndex3i Indices(Start,Start+1,Start+2);
            Normals->SetTriangle(ID,Indices);UVs->SetTriangle(ID,Indices);Colors->SetTriangle(ID,Indices);
        }
    };
    for(int32 J=0;J<N;++J)for(int32 I=0;I<N;++I)
    {
        const int32 A=J*(N+1)+I,B=A+1,C=A+N+1,D=C+1;
        Emit({Grid[A],Grid[C],Grid[B]});Emit({Grid[B],Grid[C],Grid[D]});
    }
}
bool FPlan::IntersectRiverLake(const FVector& Start,const FVector& End,FVector& Position,FVector& Normal,double& Along) const
{
    const FVector Ray=End-Start;
    if(Ray.Z>=-KINDA_SMALL_NUMBER)return false;
    double Enter=0.,Exit=1.;
    for(int32 Axis=0;Axis<2;++Axis)
    {
        const double A=Start[Axis],D=Ray[Axis];
        if(FMath::Abs(D)<1.e-9){if(A<-WorldHalf||A>WorldHalf)return false;continue;}
        double T0=(-WorldHalf-A)/D,T1=(WorldHalf-A)/D;
        if(T0>T1)Swap(T0,T1);
        Enter=FMath::Max(Enter,T0);Exit=FMath::Min(Exit,T1);
    }
    if(Enter>Exit)return false;
    struct V{FVector P;double Edge;};
    auto Vertex=[&](double X,double Y)
    {
        const auto S=Sample(X,Y);
        return V{FVector(X,Y,S.WaterZ),FMath::Min(10000.,S.Distance-S.HalfWidth)};
    };
    double Best=2.;
    auto HitTriangle=[&](const FVector& A,const FVector& B,const FVector& C)
    {
        const FVector E1=B-A,E2=C-A,P=FVector::CrossProduct(Ray,E2);
        const double Det=FVector::DotProduct(E1,P);if(FMath::Abs(Det)<1.e-8)return;
        const FVector Offset=Start-A,Q=FVector::CrossProduct(Offset,E1);
        const double U=FVector::DotProduct(Offset,P)/Det,Vv=FVector::DotProduct(Ray,Q)/Det;
        const double T=FVector::DotProduct(E2,Q)/Det;
        if(U<0.||Vv<0.||U+Vv>1.||T<0.||T>1.||T>=Best)return;
        Best=T;Position=Start+Ray*T;
        Normal=FVector::CrossProduct(E1,E2).GetSafeNormal();if(Normal.Z<0.)Normal=-Normal;
        Along=Sample(Position.X,Position.Y).Along;
    };
    auto Clip=[&](TArray<V,TInlineAllocator<4>> Poly)
    {
        TArray<V,TInlineAllocator<4>> Out;auto Prev=Poly.Last();
        for(const auto& Current:Poly)
        {
            if((Prev.Edge<=0.)!=(Current.Edge<=0.))
            {
                const double T=Prev.Edge/(Prev.Edge-Current.Edge);
                auto P=FMath::Lerp(Prev.P,Current.P,T);P.Z=Sample(P.X,P.Y).WaterZ;
                Out.Add({P,0.});
            }
            if(Current.Edge<=0.)Out.Add(Current);
            Prev=Current;
        }
        for(int32 I=1;I+1<Out.Num();++I)HitTriangle(Out[0].P,Out[I].P,Out[I+1].P);
    };
    // Traverse only the crossed 2 m cells and use the exact rendered triangles.
    // A vertical contact visits one cell; a diagonal across the whole world is bounded.
    constexpr double Cell=200.;
    const FVector From=Start+Ray*Enter;
    int32 X=FMath::FloorToInt(From.X/Cell),Y=FMath::FloorToInt(From.Y/Cell);
    const int32 SX=Ray.X>=0.?1:-1,SY=Ray.Y>=0.?1:-1;
    const double DX=FMath::Abs(Ray.X)>1.e-9?Cell/FMath::Abs(Ray.X):DBL_MAX;
    const double DY=FMath::Abs(Ray.Y)>1.e-9?Cell/FMath::Abs(Ray.Y):DBL_MAX;
    double TX=DX==DBL_MAX?DBL_MAX:(((SX>0?X+1:X)*Cell-Start.X)/Ray.X);
    double TY=DY==DBL_MAX?DBL_MAX:(((SY>0?Y+1:Y)*Cell-Start.Y)/Ray.Y);
    for(int32 Step=0;Step<2048;++Step)
    {
        const auto A=Vertex(X*Cell,Y*Cell),B=Vertex((X+1)*Cell,Y*Cell);
        const auto C=Vertex(X*Cell,(Y+1)*Cell),D=Vertex((X+1)*Cell,(Y+1)*Cell);
        Clip({A,C,B});Clip({B,C,D});
        const double Next=FMath::Min(TX,TY);
        if(Next>Exit||Next>Best||Next==DBL_MAX)break;
        if(TX<=TY){X+=SX;TX+=DX;}else{Y+=SY;TY+=DY;}
    }
    return Best<=1.;
}
}
