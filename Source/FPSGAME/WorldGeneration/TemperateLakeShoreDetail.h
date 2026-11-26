#pragma once

#include "CoreMinimal.h"
#include "TemperateHillsMap.h"

namespace TemperateRiver::LakeShoreDetail
{
// Two surveyed 20 m stretches in the inhabited hills save. Coordinates are cm.
// Positive cross-shore distance points uphill. These two sections retain
// their authored relief inside the generated lake shore.
inline constexpr int32 SurveySeed=TemperateHillsMap::Seed;
struct FSection
{
    FVector2D Anchor,Inland;
    FVector2D Along() const {return {-Inland.Y,Inland.X};}
    FVector2D Point(double S,double D) const {return Anchor+Along()*S+Inland*D;}
};
inline const FSection Cove{{-24510.,-28028.},{.67255,-.74005}};
inline const FSection Cape{{-41654.,-22261.},{-.46367,-.88601}};
// Tile centres include a border wider than the largest ecology tile so that
// selecting a PCG strip never clips a group at its edge.
inline bool NearSurveyTile(double X,double Y,int32 Seed)
{
    if(Seed!=SurveySeed)return false;
    const FVector2D XY(X,Y);
    return FVector2D::DistSquared(XY,Cove.Anchor)<1700.*1700. ||
        FVector2D::DistSquared(XY,Cape.Anchor)<1700.*1700. ||
        FVector2D::DistSquared(XY,FVector2D(-9380.,2810.))<2080.*2080.;
}
struct FProfile
{
    float Runnel=0.f,Bar=0.f,Spine=0.f,Roots=0.f;
    float Silt=0.f,DepositedGravel=0.f,Stones=0.f,ShortGrass=0.f,StoneYaw=0.f;
    double EdgeOffset() const {return -199.*Runnel+94.*Bar+235.*Spine;}
};

inline FProfile At(double X,double Y,int32 Seed)
{
    FProfile P;
    if(Seed!=SurveySeed)return P;
    const bool bCove=FMath::Abs(X-Cove.Anchor.X)<1480. && FMath::Abs(Y-Cove.Anchor.Y)<1480.;
    if(!bCove && (FMath::Abs(X-Cape.Anchor.X)>=1480. || FMath::Abs(Y-Cape.Anchor.Y)>=1480.))return P;
    const FSection& Site=bCove?Cove:Cape;
    const FVector2D Delta=FVector2D(X,Y)-Site.Anchor;
    const double S=FVector2D::DotProduct(Delta,Site.Along()),D=FVector2D::DotProduct(Delta,Site.Inland);
    if(FMath::Abs(S)>=1000. || D<=-620. || D>=760.)return P;
    const double Fade=(1.-FMath::SmoothStep(800.,1000.,FMath::Abs(S)))*
        FMath::SmoothStep(-620.,-390.,D)*(1.-FMath::SmoothStep(475.,760.,D));
    const auto Band=[](double Offset,double Core,double Radius){return 1.-FMath::SmoothStep(Core,Radius,FMath::Abs(Offset));};
    if(bCove)
    {
        // The swale bends across the beach; the gravel tongue banks up along
        // one side and loses its turf towards open water.
        const double Axis=235.+.35*D-70.*FMath::Sin(D/260.);
        P.Runnel=Fade*Band(S-Axis,58.,300.);
        P.Bar=Fade*Band(S-Axis+420.,105.,335.);
        P.Roots=P.Bar*FMath::SmoothStep(25.,235.,D);
    }
    else
    {
        // Oblique bedrock runs beneath the existing Nordic outcrop, turns
        // lakeward at the end and shelters a narrow soil pocket behind it.
        const double Spine=.62*(D-35.)+70.*FMath::Sin((D-35.)/190.);
        P.Spine=Fade*Band(S-Spine,90.,320.);
        P.Roots=Fade*Band(S-Spine-260.,55.,260.)*FMath::SmoothStep(25.,225.,D);
    }
    return P;
}
// Channel margins use signed distance to the real waterline. Confine each
// surveyed treatment to its own side of the bend and taper at both ends.
inline FProfile AtBend(double X,double Y,int32 Seed,double Edge,double Inside)
{
    FProfile P;
    if(Seed!=SurveySeed || FMath::Abs(Inside)<.18 || Edge<=-90. || Edge>=530.)return P;
    const bool Inner=Inside>0.;
    const FVector2D Offset=FVector2D(X,Y)-(Inner?FVector2D(-9390.,3380.):FVector2D(-9360.,2270.));
    if(Offset.SizeSquared()>1250.*1250.)return P;
    const double S=FVector2D::DotProduct(Offset,Inner?FVector2D(.78,.625):FVector2D(.97,-.243));
    const double Fade=(1.-FMath::SmoothStep(700.,1000.,FMath::Abs(S)))*
        (1.-FMath::SmoothStep(810.,1250.,Offset.Size()))*FMath::SmoothStep(.18,.5,FMath::Abs(Inside));
    const auto Band=[](double D,double Core,double Width){return 1.-FMath::SmoothStep(Core,Width,FMath::Abs(D));};
    if(Inner)
    {
        const double Axis=135.+64.*FMath::Sin(S/310.)+.07*S;
        P.Bar=Fade*Band(Edge-Axis,50.,180.);
        P.Roots=Fade*Band(Edge-Axis-175.,25.,105.)*(.62+.38*FMath::Cos(S/158.));
    }
    else
    {
        const double Toe=65.+32.*FMath::Sin(S/230.);
        P.Spine=Fade*Band(Edge-Toe,28.,122.)*(.61+.39*FMath::Cos((S-90.)/151.));
        P.Roots=Fade*Band(Edge-Toe-175.,35.,145.)*(.65+.35*FMath::Sin(S/182.));
    }
    return P;
}

}
