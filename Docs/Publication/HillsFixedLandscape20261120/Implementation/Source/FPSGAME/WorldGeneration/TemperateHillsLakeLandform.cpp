#include "TemperateHillsRiver.h"
#include "TemperateLakeCoveOutlet.h"
#include "TemperateHillsSurface.h"

namespace TemperateRiver
{
namespace
{
double Lobe(double Angle,double Center,double Width)
{return FMath::Exp((FMath::Cos(Angle-Center)-1.)/FMath::Square(Width));}

struct FCoast
{
    double Angle=0.,Bay=0.,Headland=0.;
};

FCoast Coast(const FPlan::FLake& Lake,double X,double Y)
{
    const FVector2D D=FVector2D(X,Y)-Lake.Center;
    const double A=FMath::Atan2(FVector2D::CrossProduct(Lake.Axis,D)/Lake.RadiusY,
        FVector2D::DotProduct(D,Lake.Axis)/Lake.RadiusX);
    const double P=Lake.Phase;
    return {A,Lobe(A,2.30+P*.23,.38)+.65*Lobe(A,-1.80+P*.19,.25),
        Lobe(A,.72+P*.17,.22)+.58*Lobe(A,-.48+P*.13,.29)};
}
}

double FPlan::FLake::NaturalEdge(double X,double Y) const
{
    if(!Valid)return DBL_MAX;
    const FVector2D D=FVector2D(X,Y)-Center;
    // Numerical queries outside the lake's conservative envelope need no detail.
    if(D.SizeSquared()>FMath::Square(FMath::Max(RadiusX,RadiusY)*1.4+MaxBankExtent))
        return LayoutEdge(X,Y);
    using namespace TemperateHillsSurface;
    const double LX=FVector2D::DotProduct(D,Axis),LY=FVector2D::CrossProduct(Axis,D);
    const double WX=LX+Noise5(LX/2900.,LY/2900.,LandformSeed,4451)*340.;
    const double WY=LY+Noise5(LX/2900.,LY/2900.,LandformSeed,4457)*340.;
    const double U=WX/RadiusX,V=WY/RadiusY;
    const auto C=Coast(*this,X,Y);
    const double Detail=Noise5(FMath::Cos(C.Angle)*3.1,FMath::Sin(C.Angle)*3.1,LandformSeed,4463);
    const double Outline=1.+.045*FMath::Sin(C.Angle*2.+Phase)+.035*Detail+.14*C.Bay-.28*C.Headland;
    const double Natural=(FMath::Sqrt(U*U+V*V)-Outline)*FMath::Min(RadiusX,RadiusY);
    double Freedom=1.;
    for(const auto& Mouth:RiverMouths)
        Freedom=FMath::Min(Freedom,FMath::SmoothStep(1100.,2600.,FVector2D::Distance(FVector2D(X,Y),Mouth)));
    // Keep the existing inlet/overflow wet; a new headland must not dam the river.
    double Edge=Natural+LakeShoreDetail::At(X,Y,LandformSeed).EdgeOffset();
    if(FMath::Abs(Edge)<230. && (LakeShoreDetail::CoveOutlet::Near(X,Y,LandformSeed)||HasBankTile(X,Y)))
    {
        // Project the mouth cross-section to a fixed edge station. Varying
        // the outlet axis with this displaced distance would fold the shore.
        const auto Mouth=BankProfile(X,Y,0.);
        Edge+=(108.*Mouth.DepositedGravel-43.*Mouth.Silt)*(1.-FMath::SmoothStep(60.,230.,FMath::Abs(Edge)));
    }
    return FMath::Lerp(LayoutEdge(X,Y),Edge,Freedom);
}

FPlan::FLake::FShore FPlan::FLake::Shore(double X,double Y) const
{
    FShore S;
    if(!bNaturalShore)return S;
    const auto C=Coast(*this,X,Y);
    const double Variation=TemperateHillsSurface::Noise5(FMath::Cos(C.Angle)*1.8,
        FMath::Sin(C.Angle)*1.8,LandformSeed,4481)*.5+.5;
    S.Rock=FMath::SmoothStep(.20,.82,C.Headland+.26*Variation);
    S.Beach=FMath::SmoothStep(.20,.85,C.Bay+.22*(1.-Variation))*(1.-S.Rock);
    // A 20-30 m height difference cannot fit into the old 6.5 m cut face.
    // Keep the shore types, but distribute their climb over a whole hillside.
    S.Reach=FMath::Lerp(8300.,6800.,S.Rock)*(.91+.18*Variation);
    S.Shelf=FMath::Lerp(550.,1500.,S.Beach)*(1.-.30*S.Rock);
    return S;
}

double FPlan::FLake::WaterDepth(double X,double Y,double SignedEdge,const FShore& S,const LakeShoreDetail::FProfile& ShoreProfile) const
{
    if(SignedEdge>=0.)return 0.;
    if(!bNaturalShore)return 8.+(Depth-8.)*FMath::SmoothStep(0.,2800.,-SignedEdge);
    using namespace TemperateHillsSurface;
    const double Inward=-SignedEdge;
    const double Shelf=FMath::Lerp(2800.+S.Beach*950.,750.,S.Rock);
    const double Basin=Depth*FMath::SmoothStep(0.,Shelf,Inward);
    // Shallow depositional lobes occupy bays; bottom variation fades at the
    // waterline and never creates a dry island beneath an uncut water mesh.
    const double Bar=S.Beach*32.*FMath::Exp(-FMath::Square((Inward-900.)/580.));
    const double Floor=Noise5(X/1900.,Y/1900.,LandformSeed,4493)*14.*FMath::SmoothStep(350.,1600.,Inward);
    const double Scour=FMath::SmoothStep(15.,145.,Inward)*(11.*ShoreProfile.Silt-4.*ShoreProfile.DepositedGravel);
    const double Skin=FMath::Min(2.,Inward*.015);
    return FMath::Clamp(FMath::Max(Skin,Basin-Bar+Floor)+Scour,Skin,Depth);
}

double FPlan::FLake::Ground(double X,double Y,double Base,const FSample& Sample,const FShore& S) const
{
    const double D=Sample.Distance-Sample.HalfWidth;
    if(D<0.)return WaterZ-Sample.Depth;
    if(D>=S.Reach)return Base;
    const double Foreshore=WaterZ+(35.+75.*S.Beach)*FMath::SmoothStep(0.,S.Shelf,D);
    const double Gentle=FMath::SmoothStep(S.Shelf*.25,S.Reach,D);
    const double Cut=.30*FMath::SmoothStep(S.Shelf*.5,S.Reach*.58,D)
        +.70*FMath::SmoothStep(S.Shelf,S.Reach,D);
    const double Join=FMath::Lerp(Gentle,Cut,S.Rock);
    const double Detail=TemperateHillsSurface::Noise5(X/1150.,Y/1150.,LandformSeed,4507)*42.
        +S.Rock*TemperateHillsSurface::Noise5(X/680.,Y/680.,LandformSeed,4513)*85.;
    const double Relief=Detail*FMath::SmoothStep(120.,550.,D)*(1.-Join);
    const double GroundZ=FMath::Lerp(Foreshore,Base,Join)+Relief;
    const auto& Local=Sample.LocalShore;
    const double Grade=FMath::SmoothStep(0.,135.,D);
    const double RunnelCut=FMath::Min(22.*Local.Runnel,FMath::Max(0.,GroundZ-WaterZ-1.5));
    return GroundZ+Grade*(26.*Local.Bar+55.*Local.Spine-RunnelCut);
}
}
