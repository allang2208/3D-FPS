#include "TemperateHillsWorld.h"
#include "TemperateHillsChapel.h"

namespace
{
using namespace TemperateVillageLayout;

FTemperateVillageSite ValleySite(double X,int32 Seed)
{
    const FVector2D West(X-HalfX,TemperateHillsSurface::ValleyY(X-HalfX,Seed));
    constexpr double Span=2.*HalfX,Rise=500.;
    double EastX=West.X+Span;
    for(int32 I=0;I<7;++I)
    {
        const double DY=TemperateHillsSurface::ValleyY(EastX,Seed)-West.Y;
        EastX=West.X+FMath::Sqrt(Span*Span+Rise*Rise-DY*DY);
    }
    const double Angle=FMath::Atan2(TemperateHillsSurface::ValleyY(EastX,Seed)-West.Y,EastX-West.X)-FMath::Atan2(Rise,Span);
    FTemperateVillageSite Site;
    Site.Axis={FMath::Cos(Angle),FMath::Sin(Angle)};
    Site.Ground=FVector(West+Site.Axis*HalfX,0.);
    return Site;
}

// Test clearances against the complete rounded shoulder, including between survey points.
bool LandAvailable(const FTemperateVillageSite& Site,double Half,const FVector& Spawn,
                   const TemperateRiver::FPlanPtr& River,
                   const TemperateForestWater::FPlanPtr& Water)
{
    const auto Extent=Site.Extent();
    if(FMath::Abs(Site.Ground.X)+Extent.X>Half-100. || FMath::Abs(Site.Ground.Y)+Extent.Y>Half-100.)return false;
    auto Distance=[&](const FVector2D& P){return Site.EdgeDistance(Site.Local(P.X,P.Y));};
    if(Distance(FVector2D(Spawn))<Site.Shoulder+225.)return false;
    if(River)for(int32 I=1;I<River->Points.Num();++I)
    {
        const auto& A=River->Points[I-1];const auto& B=River->Points[I];
        const double Bank=FMath::Max(FMath::Max(A.LeftWidth,A.RightWidth),FMath::Max(B.LeftWidth,B.RightWidth));
        if(Distance(A.XY)<=Site.Shoulder+Bank+200.+(B.XY-A.XY).Size()*.5 ||
           Distance(B.XY)<=Site.Shoulder+Bank+200.+(B.XY-A.XY).Size()*.5)return false;
    }
    if(!Water)return true;
    for(const auto& Basin:Water->Basins)
        if(Distance(Basin.Center)<=Site.Shoulder+Basin.Radius)return false;
    for(const auto& Pool:Water->Pools)
    {
        const FVector2D C=Pool.Bounds.GetCenter();
        if(Distance(C)>Site.Shoulder+Pool.Bounds.GetExtent().Size())continue;
        for(const auto Cell:Pool.Cells)
        {
            const auto P=Water->Origin+(FVector2D(Cell)+FVector2D(.5))*TemperateForestWater::Step;
            if(Distance(P)<=Site.Shoulder+TemperateForestWater::Step*.71)return false;
        }
    }
    return true;
}
#include "TemperateVillageHilltop.inl"
}

void ATemperateHillsWorld::PlanAbandonedVillage(const TemperateForestWater::FPlanPtr& SeedWater)
{
    bSettlementPlanned=true;
    VillageSite={};
    ChapelSite={};
    if(!TemperateHillsChapel::IsChapelWorld(GetWorld()))return;
    using namespace TemperateVillageLayout;
    const double Half=SizeMeters*50.;
    const FVector Start=GetGenerationAnchor();
    if(GeneratorVersion>=3)
    {
        VillageSite=HilltopSite(Seed,Half,Start,RiverPlan,SeedWater,
            [this,&SeedWater](const FVector2D& P)
            {
                const double Z=RiverPlan?RiverPlan->Height(P.X,P.Y,Seed):TemperateHillsSurface::Height(P.X,P.Y,Seed,GeneratorVersion);
                return SeedWater?SeedWater->ShapeGround(P.X,P.Y,Z):Z;
            },[this](const FVector2D& P){return RainforestWeight(P.X,P.Y);});
        ChapelSite=VillageSite.ChapelLot();
        if(VillageSite.bPlaced)
        {
            UE_LOG(LogTemp,Display,TEXT("HILLS_VILLAGE hilltop seed=%d center=%s reserve_m=140x110 shoulder_m=%.1f feeder_m=%.1f"),
                Seed,*VillageSite.Ground.ToCompactString(),VillageSite.Shoulder/100.,VillageSite.FeederLength/100.);
        }
        else
        {
            UE_LOG(LogTemp,Warning,TEXT("HILLS_VILLAGE no dry gentle hilltop seed=%d"),Seed);
        }
        return;
    }
    const double PreferredX=FMath::Clamp(Start.X+19000.,-Half+HalfX,Half-HalfX);
    // Compare walking routes, not just the straight-line distance to spawn.
    // Prefix lengths let every candidate share one survey of the valley.
    constexpr double TrailStep=200.;
    TArray<double> WetLength;
    WetLength.Add(0.);
    for(double WX=-Half+TrailStep;WX<=Half;WX+=TrailStep)
    {
        const auto Water=SampleRiver(WX-TrailStep*.5,TemperateHillsSurface::ValleyY(WX-TrailStep*.5,Seed));
        const double Previous=WetLength.Last();
        WetLength.Add(Previous+(Water.Distance<=Water.HalfWidth?TrailStep:0.));
    }
    auto WetAt=[&](double WX){return WetLength[FMath::Clamp(FMath::RoundToInt((WX+Half)/TrailStep),0,WetLength.Num()-1)];};
    const double StartWet=WetAt(Start.X);
    double Best=DBL_MAX;
    FTemperateVillageSite Selected;
    double BestPeak=DBL_MAX;
    auto Evaluate=[&](FTemperateVillageSite Candidate)
    {
        const double X=Candidate.Ground.X;
        const auto Junction=Candidate.Mouth(-1.)-Candidate.Axis*Candidate.FeederLength;
        double RouteWet=FMath::Abs(WetAt(Junction.X)-StartWet);
        if(!Candidate.bSideLane)RouteWet=FMath::Min(RouteWet,FMath::Abs(WetAt(Candidate.Mouth(1.).X)-StartWet));
        Candidate.Shoulder=900.;
        if(!LandAvailable(Candidate,Half,Start,RiverPlan,SeedWater))return;
        auto Raw=[this](const FVector2D& P){return BaseHeight(P.X,P.Y);};
        double Low=DBL_MAX,High=-DBL_MAX,Sum=0.;
        for(int32 IX=-4;IX<=4;++IX)for(int32 IY=-3;IY<=3;++IY)
        {
            const double H=Raw(Candidate.World(HalfX*IX/4.,HalfY*IY/3.));
            Low=FMath::Min(Low,H);High=FMath::Max(High,H);Sum+=H;
        }
        const double Landing=(Raw(Candidate.Approach(-1.,1400.,Seed))+Raw(Candidate.Approach(1.,1400.,Seed)))*.5;
        const double Mean=Sum/63.;
        const double CutFill=FMath::Max(High-Mean,Mean-Low);
        const double PreferredShoulder=FMath::Clamp(5.*CutFill,1400.,3500.);
        Candidate.bPlaced=true;
        // A narrower shoulder may fit the same dry site beside a river.
        // Retain it only when the resulting entrances are competitive.
        for(double Width:{PreferredShoulder,PreferredShoulder*.72,900.})
        {
            Candidate.Shoulder=Width;
            if(Width>900. && !LandAvailable(Candidate,Half,Start,RiverPlan,SeedWater))continue;
            struct FApproach { FVector2D P; double Z,Run; bool First; };
            TArray<FApproach,TInlineAllocator<80>> Approaches;
            bool bDryApproaches=true;
            for(double Side:{-1.,1.})
            {
                FVector2D Prev=Candidate.Mouth(Side);
                for(int32 J=1;J<=FMath::CeilToInt(FMath::Max(Width,Side<0.?Candidate.FeederLength:0.)/100.)+1;++J)
                {
                    const auto P=Candidate.Approach(Side,100.*J,Seed);
                    const auto River=SampleRiver(P.X,P.Y);
                    if(Candidate.FeederLength>0. && Side<0.)
                    {
                        const double Clear=650.;
                        const bool Pond=SeedWater && SeedWater->Pools.ContainsByPredicate([&](const auto& Pool)
                            {return Pool.Bounds.ExpandBy(Clear).IsInside(P);});
                        const bool Basin=SeedWater && SeedWater->Basins.ContainsByPredicate([&](const auto& B)
                            {return (B.Center-P).SizeSquared()<FMath::Square(B.Radius+Clear);});
                        if(Pond || Basin || (FVector2D(Start)-P).SizeSquared()<FMath::Square(Clear)
                            || River.Distance<=River.HalfWidth+Clear || FMath::Max(FMath::Abs(P.X),FMath::Abs(P.Y))>=Half-Clear)
                        {bDryApproaches=false;break;}
                    }
                    if(FMath::Max(FMath::Abs(P.X),FMath::Abs(P.Y))>=Half-100.
                        || River.Distance<=River.HalfWidth+225. || (SeedWater && SeedWater->Sample(P.X,P.Y).Wet))
                    {
                        bDryApproaches=false;
                        break;
                    }
                    Approaches.Add({P,Raw(P),(P-Prev).Size(),J==1});
                    Prev=P;
                }
            }
            if(!bDryApproaches)continue;
            // Check the middle of the blend on all four flanks; its steepest
            // artificial cut can be opposite a perfectly gentle road entrance.
            struct FFlank { double Inner,Outer; };
            TArray<FFlank,TInlineAllocator<20>> Flanks;
            for(double Side:{-1.,1.})for(int32 I=-2;I<=2;++I)
            {
                const double T=I*.5;
                Flanks.Add({Raw(Candidate.World(Side*(HalfX+.4*Width),T*HalfY)),
                            Raw(Candidate.World(Side*(HalfX+.6*Width),T*HalfY))});
                Flanks.Add({Raw(Candidate.World(T*HalfX,Side*(HalfY+.4*Width))),
                            Raw(Candidate.World(T*HalfX,Side*(HalfY+.6*Width)))});
            }
            for(double Datum:{Mean,Landing,(Mean+Landing)*.5})
            {
                Candidate.Ground.Z=Datum;
                double Peak=0.,PrevZ=Datum;
                for(const auto& A:Approaches)
                {
                    if(A.First)PrevZ=Datum;
                    const double Z=Candidate.Grade(A.P.X,A.P.Y,A.Z);
                    Peak=FMath::Max(Peak,FMath::Abs(Z-PrevZ)/A.Run);
                    PrevZ=Z;
                }
                double FlankGrade=0.;
                for(const auto& F:Flanks)
                {
                    const double Inner=FMath::Lerp(Datum,F.Inner,FMath::SmoothStep(0.,1.,.4));
                    const double Outer=FMath::Lerp(Datum,F.Outer,FMath::SmoothStep(0.,1.,.6));
                    FlankGrade=FMath::Max(FlankGrade,FMath::Abs(Outer-Inner)/(.2*Width));
                }
                const double Earthwork=FMath::Max(High-Datum,Datum-Low);
                const double Score=Earthwork+1800.*FlankGrade+1600.*FMath::Max(0.,FlankGrade-.55)+3400.*Peak+18000.*FMath::Max(0.,Peak-.18)
                    +2.*RouteWet+.035*FMath::Abs(X-PreferredX)+1200.*RainforestWeight(Candidate.Ground.X,Candidate.Ground.Y);
                if(Score<Best){Best=Score;BestPeak=Peak;Selected=Candidate;}
            }
        }
    };
    for(double X=-Half+HalfX+900.;X<=Half-HalfX-900.;X+=400.)
        Evaluate(ValleySite(X,Seed));

    // Where a through-village would occupy the only dry valley crossing, branch
    // from the valley. The western gate forms the junction; the back lane opens uphill.
    if(!Selected.bPlaced || BestPeak>FMath::Tan(FMath::DegreesToRadians(15.)))
    {
        for(double X=-Half+1100.;X<Half-1100.;X+=650.)
        {
            const FVector2D Junction(X,TemperateHillsSurface::ValleyY(X,Seed));
            for(double Angle:{55.,90.,125.,-55.,-90.,-125.})
            {
                FTemperateVillageSite Side;
                Side.bSideLane=true;
                Side.Axis=FVector2D(1.,0.).GetRotated(Angle);
                Side.Ground=FVector(Junction+Side.Axis*HalfX,0.);
                Evaluate(Side);
            }
        }
    }
    if(!Selected.bPlaced || (SizeMeters<=384. && BestPeak>FMath::Tan(FMath::DegreesToRadians(20.))))
    {
        // Tight seeds may only have a buildable shelf farther up a side valley.
        // Keep the buildings full size and connect the shelf to a real valley junction.
        for(double X=-Half+1100.;X<Half-1100.;X+=350.)
        {
            const FVector2D Junction(X,TemperateHillsSurface::ValleyY(X,Seed));
            const double JunctionZ=BaseHeight(Junction.X,Junction.Y);
            for(double Angle=30.;Angle<360.;Angle+=15.)for(double Setback:{0.,1700.,3200.,4900.})
            {
                FTemperateVillageSite Side;
                Side.bSideLane=true; Side.Axis=FVector2D(1.,0.).GetRotated(Angle);
                Side.FeederLength=Setback;Side.JunctionZ=JunctionZ;
                Side.Ground=FVector(Junction+Side.Axis*(HalfX+Setback),0.);
                Evaluate(Side);
            }
        }
    }
    VillageSite=Selected;
    ChapelSite=VillageSite.ChapelLot();
    if(VillageSite.bPlaced)
    {
        UE_LOG(LogTemp,Display,TEXT("HILLS_VILLAGE seed=%d center=%s shoulder_m=%.1f west_entry=%s"),Seed,
            *VillageSite.Ground.ToCompactString(),VillageSite.Shoulder/100.,*VillageSite.World(-HalfX,0.).ToString());
    }
    else
    {
        UE_LOG(LogTemp,Warning,TEXT("HILLS_VILLAGE no dry valley reach seed=%d"),Seed);
    }
}
