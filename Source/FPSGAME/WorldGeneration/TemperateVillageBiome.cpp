#include "TemperateHillsRiver.h"
#include "TemperateHillsMap.h"
#include "TemperateVillageSite.h"

namespace TemperateRiver
{
void FPlan::BuildVillageRainforest(int32 Seed,double Half,const FTemperateVillageSite& Village,const FVector2D& Entry)
{
    if(!Village.bPlaced||!Village.bHilltop)return;
    constexpr int32 Rays=64;
    constexpr double SurveyStep=800.,BlendWidth=1800.,RoadHalfWidth=1600.;
    TArray<double,TInlineAllocator<Rays>> Foot,Minimum;
    Foot.SetNumUninitialized(Rays);Minimum.SetNumUninitialized(Rays);
    const FVector2D Center(Village.Ground);
    for(int32 I=0;I<Rays;++I)
    {
        const double Angle=2.*UE_PI*I/Rays;
        const FVector2D Dir(FMath::Cos(Angle),FMath::Sin(Angle));
        const FVector2D LocalDir(Dir.X*Village.Axis.X+Dir.Y*Village.Axis.Y,
                                Dir.Y*Village.Axis.X-Dir.X*Village.Axis.Y);
        // Solve the rounded rectangle's outer shoulder, not its square AABB.
        double Low=0.,High=FVector2D(Village.PadHalfX,Village.PadHalfY).Size()+Village.Shoulder;
        for(int32 J=0;J<12;++J)
        {
            const double R=(Low+High)*.5;
            if(Village.EdgeDistance(LocalDir*R)<Village.Shoulder)Low=R;else High=R;
        }
        const double Start=High;
        Minimum[I]=Start+1800.;
        const double End=Start+12000.;
        auto Ground=[&](double Radius)
        {
            const FVector2D P=Center+Dir*Radius;
            auto H=[&](const FVector2D& Q){return Village.Grade(Q.X,Q.Y,Height(Q.X,Q.Y,Seed));};
            // Broad terrain samples stop centimetre-scale noise masquerading as a hill foot.
            return (2.*H(P)+H(P+Dir*400.)+H(P-Dir*400.))*.25;
        };
        double Previous=Ground(Start),Lowest=Previous,LowestRadius=Start;
        double FootRadius=End;
        for(double R=Start+SurveyStep;R<=End;R+=SurveyStep)
        {
            const double Z=Ground(R);
            if(Z<Lowest){Lowest=Z;LowestRadius=R;}
            const double Drop=Village.Ground.Z-Lowest;
            if(R>=Minimum[I] && Drop>=200. && Z-Lowest>=80.)
            {FootRadius=FMath::Max(Minimum[I],LowestRadius);break;}
            if(R>=Minimum[I]+1600. && Drop>=400. && FMath::Abs(Z-Previous)/SurveyStep<.025)
            {FootRadius=R;break;}
            const FVector2D P=Center+Dir*R;
            const auto Bank=Sample(P.X,P.Y);
            if(R>=Minimum[I] && Bank.Distance<Bank.HalfWidth+200.){FootRadius=R;break;}
            Previous=Z;
        }
        Foot[I]=FootRadius;
    }
    // Smooth adjacent survey directions while preserving the entire graded shoulder.
    const auto Original=Foot;
    for(int32 I=0;I<Rays;++I)
        Foot[I]=FMath::Max(Minimum[I],(Original[(I+Rays-1)%Rays]+2.*Original[I]+Original[(I+1)%Rays])*.25);

    const FVector2D Gate=Village.Mouth(-1.),Junction=Gate-Village.Axis*Village.FeederLength;
    const FVector2D Feeder=Junction-Gate;
    const double FromX=FMath::Min(Entry.X,Junction.X),ToX=FMath::Max(Entry.X,Junction.X);
    ForestHalfSize=Half;ForestGridSize=FMath::Max(2,FMath::CeilToInt(2.*Half/400.));
    const int32 N=ForestGridSize;
    const double Step=2.*Half/N;
    RainforestMask.SetNumUninitialized(N*N);
    const FVector2D Preferred=ForestAnchor;
    double AnchorDistance=DBL_MAX;
    for(int32 Y=0;Y<N;++Y)for(int32 X=0;X<N;++X)
    {
        const FVector2D P(-Half+(X+.5)*Step,-Half+(Y+.5)*Step),D=P-Center;
        double Angle=FMath::Atan2(D.Y,D.X);
        if(Angle<0.)Angle+=2.*UE_PI;
        const double A=Angle*Rays/(2.*UE_PI);
        const int32 I=FMath::Min(int32(A),Rays-1);
        const double Radius=FMath::Lerp(Foot[I],Foot[(I+1)%Rays],A-I);
        const double T=FMath::Clamp(FVector2D::DotProduct(P-Gate,Feeder)/FMath::Max(1.,Feeder.SizeSquared()),0.,1.);
        const double FeederEdge=(P-Gate-T*Feeder).Size()-RoadHalfWidth;
        const double RouteX=FMath::Clamp(P.X,FromX,ToX);
        const FVector2D Route(RouteX,TemperateHillsSurface::ValleyY(RouteX,Seed));
        const double ValleyEdge=(P-Route).Size()-RoadHalfWidth;
        const double RoadEdge=FMath::Min(FeederEdge,ValleyEdge);
        const double Edge=FMath::Min(D.Size()-Radius,RoadEdge);
        double Start=Step*.71,Width=BlendWidth,CoreClearance=1.;
        const auto Bank=Sample(P.X,P.Y);
        // Shape the western hill foot and incoming valley with the same field
        // that feeds ground colour, grass, saplings and distant terrain.
        if(Edge>-2200.&&Edge<8200.&&Bank.Wet<=.01&&Bank.Bank<.68&&Bank.CliffWeight<=0.&&WhiteCliffs.Weight(P.X,P.Y)<=0.)
        {
            const auto Local=Village.Local(P.X,P.Y);
            const double West=1.-FMath::SmoothStep(2500.,9500.,Local.X);
            const double Near=1.-FMath::SmoothStep(9000.,15000.,FVector2D::Distance(P,Junction));
            double Focus=FMath::Max(West*(1.-FMath::SmoothStep(23000.,32000.,D.Size())),Near);
            if(Seed==TemperateHillsMap::Seed && Half==51200.)
            {
                // The opposite side used the survey radius alone, leaving a
                // constant-width treeline. Let shallow draws carry green into
                // the margin and exposed spurs carry dry grass out between them.
                const double East=FMath::SmoothStep(3500.,12200.,Local.X);
                Focus=FMath::Max(Focus,.83*East*(1.-FMath::SmoothStep(25500.,35000.,D.Size())));
            }
            Focus*=1.-FMath::SmoothStep(.12,.68,Bank.Bank);
            if(Focus>0.)
            {
                using TemperateHillsSurface::Noise5;
                const double Lobe=Noise5(Local.X/3200.,Local.Y/2200.,Seed,4721);
                const double Pocket=Noise5(P.X/1400.,P.Y/1400.,Seed,4733);
                // The final upland mesh is built after this mask. Sample the
                // surveyed terrain itself for a shallow hollow or convex spur.
                const FVector2D Along=RoadEdge<D.Size()-Radius?Village.Axis:D.GetSafeNormal();
                const FVector2D A0=P-Along*1100.,A1=P+Along*1100.;
                const double Sag=.5*(Height(A0.X,A0.Y,Seed)+Height(A1.X,A1.Y,Seed))-Height(P.X,P.Y,Seed);
                const double Fold=FMath::Clamp(Sag/45.,-1.,1.);
                const double Inset=FMath::Clamp(500.-1650.*Lobe-570.*Pocket-680.*Fold,-800.,2400.);
                // Green can reach into a hollow, but never breach the dry
                // road core or graded village shoulder, even on coarse texels.
                const double Clearance=FMath::Min(RoadEdge,Village.EdgeDistance(Local)-Village.Shoulder);
                Start+=Focus*Inset;
                Width+=Focus*(1450.+440.*Lobe);
                CoreClearance=FMath::SmoothStep(Step*.71,Step*.71+520.,Clearance);
            }
        }
        // Half a texel diagonal protects the yellow core from bilinear bleed.
        const double Weight=FMath::Min(CoreClearance,FMath::SmoothStep(Start,Start+Width,Edge));
        RainforestMask[Y*N+X]=FMath::RoundToInt(255.*Weight);
        if(Weight>.99 && Bank.Distance>Bank.HalfWidth+2200.)
        {
            const double Distance=(P-Preferred).SizeSquared();
            if(Distance<AnchorDistance){AnchorDistance=Distance;ForestAnchor=P;}
        }
    }
    bVillageRainforest=true;
}
}
