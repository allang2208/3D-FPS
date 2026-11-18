#include "TemperateHillsRiver.h"
#include "TemperateHillsLandform.h"

namespace TemperateRiver
{
namespace
{
double ChannelGround(double X,double Y,int32 Seed,double Base,const FSample& S,double BankRelief)
{
    if(S.Bank<=0.)return Base;
    const double Inner=S.Bend*(S.SignedDistance>=0.?1.:-1.);
    const double Rough=TemperateHillsSurface::Noise(X*.004,Y*.004,Seed,1963)*4.;
    double Bed;
    if(S.Distance<S.HalfWidth)
    {
        const double T=FMath::SmoothStep(.05,1.,S.Distance/FMath::Max(1.,S.HalfWidth));
        const double Depth=FMath::Clamp(S.Depth*(1.-Inner*.42),25.,90.);
        Bed=S.WaterZ-Depth+(Depth+4.)*T+Rough*(1.-T);
    }
    else
    {
        const double Shelf=FMath::Clamp(650.+Inner*450.,300.,1100.);
        Bed=S.WaterZ+4.+55.*FMath::SmoothStep(S.HalfWidth,S.HalfWidth+Shelf,S.Distance)
            +Rough*FMath::SmoothStep(S.HalfWidth,S.HalfWidth+200.,S.Distance);
        const double Edge=S.Distance-S.HalfWidth;
        const double Mound=TemperateHillsSurface::Noise(X*.0014,Y*.0014,Seed,2309);
        const double Pocket=TemperateHillsSurface::Noise(X*.0031,Y*.0031,Seed,2311);
        Bed+=BankRelief*(Mound+.38*Pocket)*FMath::SmoothStep(40.,300.,Edge)
            *(1.-FMath::SmoothStep(1200.,S.BankExtent,Edge));
    }
    return FMath::Lerp(Base,Bed,S.Bank);
}
}

double FPlan::Height(double X,double Y,int32 Seed) const
{
    if(bRiverLake&&Lake.bNaturalShore)return NaturalGround(X,Y,Seed);

    const double Protected=Protection(X,Y);
    if(SettlementBaseline&&Protected>=.999)return SettlementBaseline->Height(X,Y,Seed);
    const FSample S=Sample(X,Y);
    const double Raw=TemperateHillsSurface::Height(X,Y,Seed,GenerationVersion);
    const double Shaped=WhiteCliffs.Ground(X,Y,Raw);
    const double Base=SettlementBaseline&&Protected>0.?
        FMath::Lerp(Shaped,SettlementBaseline->Height(X,Y,Seed),Protected):Shaped;
    if(S.bLake&&S.Bank>0.)
    {
        const double Edge=S.Distance-S.HalfWidth;
        const double Bed=Edge<0.?S.WaterZ-8.-(S.Depth-8.)*FMath::SmoothStep(0.,2800.,-Edge):
            S.WaterZ-8.+95.*FMath::SmoothStep(0.,1800.,Edge);
        return FMath::Lerp(Base,Bed,S.Bank);
    }
    return ChannelGround(X,Y,Seed,Base,S,BankReliefCm);
}

double FPlan::NaturalGround(double X,double Y,int32 Seed) const
{
    const double Protected=Protection(X,Y);
    if(SettlementBaseline&&Protected>=.999)return SettlementBaseline->Height(X,Y,Seed);
    const auto Channel=SampleChannel(X,Y);
    const double Edge=Lake.Edge(X,Y);
    const auto Shore=Lake.Shore(X,Y);
    const double LakeWeight=Lake.Valid?1.-FMath::SmoothStep(120.,Shore.Reach,Edge):0.;
    const double Quarry=WhiteCliffs.Weight(X,Y);
    const double Raw=TemperateHillsSurface::Height(X,Y,Seed,GenerationVersion);
    const double Relief=TemperateHillsLandform::Relief(X,Y,Seed)
        *(1.-FMath::SmoothStep(0.,.08,FMath::Max(Channel.Bank,LakeWeight)))*(1.-Quarry);
    const double Base=WhiteCliffs.Ground(X,Y,Raw+Relief);
    double Ground=ChannelGround(X,Y,Seed,Base,Channel,BankReliefCm);
    if(Lake.Valid&&Edge<Shore.Reach)
    {
        // Evaluate both continuous surfaces at a river mouth. Choosing the
        // nearest water body switched unrelated bank heights along a hard seam.
        FSample LakeSample;
        LakeSample.HalfWidth=Lake.RadiusY;
        LakeSample.Distance=Lake.RadiusY+Edge;
        LakeSample.Depth=Lake.WaterDepth(X,Y,Edge);
        const double LakeGround=Lake.Ground(X,Y,Base,LakeSample);
        const double Wet=FMath::Max(Channel.Wet,Edge<0.?1.:0.);
        const double Blend=180.*(1.-Wet)*Channel.Bank*LakeWeight;
        const double H=Blend>0.?FMath::Max(0.,1.-FMath::Abs(Ground-LakeGround)/Blend):0.;
        Ground=FMath::Min(Ground,LakeGround)-Blend*H*H*.25;
        // Retain the quarry benches; the surrounding hillside absorbs the
        // enlarged lake apron. Prop support and terrain use this same field.
        Ground=FMath::Lerp(Ground,Base,Quarry);
    }
    return SettlementBaseline&&Protected>0.?
        FMath::Lerp(Ground,SettlementBaseline->Height(X,Y,Seed),Protected):Ground;
}
}
