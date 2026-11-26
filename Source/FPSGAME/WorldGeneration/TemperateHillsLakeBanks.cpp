#include "TemperateHillsRiver.h"
#include "TemperateLakeCoveOutlet.h"

namespace TemperateRiver
{
namespace
{
FIntPoint BankTile(double X,double Y)
{
    constexpr double TileSize=900.;
    return {FMath::FloorToInt32(X/TileSize),FMath::FloorToInt32(Y/TileSize)};
}

double Band(double Offset,double Core,double Width)
{
    return 1.-FMath::SmoothStep(Core,Width,FMath::Abs(Offset));
}

void AddDeposit(LakeShoreDetail::FProfile& P,const LakeShoreDetail::CoveOutlet::FDeposit& D,
    double Ledge,double Weight,float StoneYaw)
{
    P.Silt=FMath::Max(P.Silt,float(Weight*D.Silt));
    P.DepositedGravel=FMath::Max(P.DepositedGravel,float(Weight*D.Gravel));
    P.ShortGrass=FMath::Max(P.ShortGrass,float(Weight*D.Grass));
    if(float(Weight*D.Stones)>P.Stones)
    {
        P.Stones=float(Weight*D.Stones);
        P.StoneYaw=StoneYaw;
    }
    P.Runnel=FMath::Max(P.Runnel,P.Silt);
    P.Bar=FMath::Max(P.Bar,P.DepositedGravel);
    P.Roots=FMath::Max(P.Roots,P.ShortGrass);
    P.Spine=FMath::Max(P.Spine,float(Weight*Ledge));
}
}

void FPlan::FLake::BuildBankPatches()
{
    BankTiles.Reset();
    BankPatches.Reset();
    if(!Valid||!bNaturalShore)return;
    FRandomStream Stream(LandformSeed^0x317dd52);
    const double Turn=2.*UE_PI;
    const int32 Count=FMath::Max(6,FMath::RoundToInt(Turn*FMath::Sqrt((RadiusX*RadiusX+RadiusY*RadiusY)*.5)/2460.));
    const FVector2D Side(-Axis.Y,Axis.X);
    const double Start=Stream.FRandRange(0.f,float(Turn));
    // Read the established waterline for every site before publishing any new
    // patch into the spatial index. Neighbouring sites cannot move each other.
    for(int32 Index=0;Index<Count;++Index)
    {
        const double Angle=Start+Turn*(Index+Stream.FRandRange(-.18f,.18f))/Count;
        const FVector2D Ray=RadiusX*FMath::Cos(Angle)*Axis+RadiusY*FMath::Sin(Angle)*Side;
        double Lo=.45,Hi=1.65;
        for(int32 Step=0;Step<12;++Step)
        {
            const double Mid=(Lo+Hi)*.5;
            const auto XY=Center+Ray*Mid;
            if(Edge(XY.X,XY.Y)<0.)Lo=Mid;else Hi=Mid;
        }
        const auto XY=Center+Ray*((Lo+Hi)*.5);
        const FVector2D Gradient((Edge(XY.X+75.,XY.Y)-Edge(XY.X-75.,XY.Y))/150.,
            (Edge(XY.X,XY.Y+75.)-Edge(XY.X,XY.Y-75.))/150.);
        const double Slope=Gradient.Size();
        if(Slope<.15)continue;
        const auto ShoreType=Shore(XY.X,XY.Y);
        auto& Patch=BankPatches.AddDefaulted_GetRef();
        Patch.Frame={XY,Gradient/Slope};
        const double Arc=Turn/Count*FMath::Sqrt(FMath::Square(RadiusX*FMath::Sin(Angle))+FMath::Square(RadiusY*FMath::Cos(Angle)));
        Patch.HalfLength=Arc*Stream.FRandRange(.44f,.66f);
        Patch.CrossScale=Stream.FRandRange(.71f,1.08f)*FMath::Lerp(1.,.84,ShoreType.Rock);
        Patch.HalfDepth=1290.*Patch.CrossScale/FMath::Max(.4,Slope)+480.;
        Patch.Hand=Stream.FRand()<.5f?-1.:1.;
        Patch.Strength=Stream.FRandRange(.70f,1.f);
        const double Choice=Stream.FRand();
        if(ShoreType.Rock>.5 || (ShoreType.Rock>.15 && Choice<ShoreType.Rock))
            Patch.Form=EBankForm::RockShelf;
        else if(Choice<.13+.75*ShoreType.Beach)
            Patch.Form=EBankForm::Outlet;
        const double AlongRun=Patch.Form==EBankForm::Outlet?
            1.25*(Patch.HalfLength/1292.5)/(Patch.CrossScale/Slope):1.;
        const double InlandRun=Patch.Form==EBankForm::Outlet?1.:Patch.Form==EBankForm::RockShelf?.27:.14;
        const auto Bearing=Patch.Frame.Inland*InlandRun+Patch.Frame.Along()*(Patch.Hand*AlongRun);
        Patch.StoneYaw=float(FMath::Atan2(Bearing.Y,Bearing.X));
    }
    for(int32 Index=0;Index<BankPatches.Num();++Index)
    {
        const auto& Patch=BankPatches[Index];
        const auto Tangent=Patch.Frame.Along(),Inland=Patch.Frame.Inland;
        // Include half of the widest PCG candidate tile on all sides. A
        // candidate's density and identity must agree across generation strips.
        const FVector2D Radius(FMath::Abs(Tangent.X)*Patch.HalfLength+FMath::Abs(Inland.X)*Patch.HalfDepth+255.,
            FMath::Abs(Tangent.Y)*Patch.HalfLength+FMath::Abs(Inland.Y)*Patch.HalfDepth+255.);
        const auto Min=Patch.Frame.Anchor-Radius,Max=Patch.Frame.Anchor+Radius;
        const FIntPoint First=BankTile(Min.X,Min.Y),Last=BankTile(Max.X,Max.Y);
        for(int32 Y=First.Y;Y<=Last.Y;++Y)for(int32 X=First.X;X<=Last.X;++X)
            BankTiles.FindOrAdd(FIntPoint(X,Y)).Add(Index);
    }
}

bool FPlan::FLake::HasBankTile(double X,double Y) const
{
    return !BankTiles.IsEmpty()&&BankTiles.Contains(BankTile(X,Y));
}

LakeShoreDetail::FProfile FPlan::FLake::BankProfile(double X,double Y,double EdgeCm) const
{
    using namespace LakeShoreDetail;
    FProfile P=At(X,Y,LandformSeed);
    if(!bNaturalShore||EdgeCm<=-1100.||EdgeCm>=1460.)return P;
    if(CoveOutlet::Near(X,Y,LandformSeed))
    {
        const auto Bearing=Cove.Inland+Cove.Along()*1.25;
        AddDeposit(P,CoveOutlet::Sample(X,Y,LandformSeed,EdgeCm),0.,1.,float(FMath::Atan2(Bearing.Y,Bearing.X)));
    }
    const auto* Sites=BankTiles.Find(BankTile(X,Y));
    if(!Sites)return P;
    const FVector2D XY(X,Y);
    double Freedom=1.;
    for(const auto& Mouth:RiverMouths)
        Freedom=FMath::Min(Freedom,FMath::SmoothStep(1100.,2600.,FVector2D::Distance(XY,Mouth)));
    if(LandformSeed==SurveySeed)
    {
        const auto Delta=XY-Cove.Anchor;
        const auto Nearest=Cove.Point(FMath::Clamp(FVector2D::DotProduct(Delta,Cove.Along()),0.,2580.),0.);
        Freedom*=FMath::SmoothStep(1720.,2250.,FVector2D::Distance(XY,Nearest))
            *FMath::SmoothStep(1450.,2000.,FVector2D::Distance(XY,Cape.Anchor));
    }
    if(Freedom<=0.)return P;
    for(int32 Site:*Sites)
    {
        const auto& Patch=BankPatches[Site];
        const auto Delta=XY-Patch.Frame.Anchor;
        const double U=Patch.Hand*FVector2D::DotProduct(Delta,Patch.Frame.Along())/Patch.HalfLength;
        const double V=FMath::Abs(FVector2D::DotProduct(Delta,Patch.Frame.Inland))/Patch.HalfDepth;
        if(FMath::Abs(U)>=1. || V>=1.)continue;
        const double E=EdgeCm/Patch.CrossScale;
        const double Weight=Freedom*Patch.Strength*Band(U,.68,1.)*Band(V,.80,1.);
        CoveOutlet::FDeposit Deposit;
        double Ledge=0.;
        if(Patch.Form==EBankForm::Outlet)
            Deposit=CoveOutlet::Section(1387.5+1292.5*U,E);
        else if(Patch.Form==EBankForm::RockShelf)
        {
            const double Ridge=E-(45.+310.*U+83.*FMath::Sin(3.3*U));
            const double Break=1.-.74*Band(U-.25,.06,.30);
            Ledge=Band(Ridge,58.,248.)*Break;
            Deposit.Stones=Ledge;
            Deposit.Gravel=.67*Band(Ridge+155.,55.,204.)*Break;
            Deposit.Grass=.82*Band(Ridge-236.,53.,212.)*FMath::SmoothStep(30.,170.,E);
        }
        else
        {
            // Alongshore drift with a coarser toe and intermittent rooted
            // pockets on the upper margin. The waterward end thins into silt.
            const double Ridge=E-(92.+128.*U+93.*FMath::Sin(3.7*U));
            const double Tail=.46+.54*Band(U+.24,.14,.79);
            Deposit.Gravel=Band(Ridge,76.,290.)*Tail;
            Deposit.Silt=.62*Band(Ridge+201.,64.,227.)*Band(U-.30,.12,.68);
            Deposit.Stones=.85*Band(Ridge-67.,49.,176.)*Band(U+.35,.09,.53);
            Deposit.Grass=.79*Band(Ridge-292.,63.,260.)*(1.-.69*Band(U+.13,.10,.43))
                *FMath::SmoothStep(40.,180.,E);
        }
        AddDeposit(P,Deposit,Ledge,Weight,Patch.StoneYaw);
    }
    return P;
}

LakeShoreDetail::FProfile FPlan::FLake::BankAtChannel(double X,double Y,double SignedEdge,const FSample& Channel) const
{
    auto P=BankProfile(X,Y,SignedEdge);
    const auto& Upstream=Channel.LocalShore;
    if(SignedEdge<=-80. || SignedEdge>=1050. ||
        (Upstream.Bar<=0.f && Upstream.Silt<=0.f && Upstream.Roots<=0.f && Upstream.Stones<=0.f))return P;
    const double ChannelEdge=Channel.Distance-Channel.HalfWidth;
    if(ChannelEdge-SignedEdge>=1050.)return P;
    double MouthDistanceSq=DBL_MAX;
    for(const FVector2D& Mouth:RiverMouths)
        MouthDistanceSq=FMath::Min(MouthDistanceSq,FVector2D::DistSquared(FVector2D(X,Y),Mouth));
    // The lake has its own shore patches. Where the two shorelines meet, let
    // the stream's deposits thin out over the shallow margin between them.
    const double Taper=FMath::SmoothStep(-80.,15.,SignedEdge)*(1.-FMath::SmoothStep(0.,1050.,ChannelEdge-SignedEdge))*
        (1.-FMath::SmoothStep(1100.*1100.,2500.*2500.,MouthDistanceSq));
    if(Taper<=0.)return P;
    LakeShoreDetail::CoveOutlet::FDeposit D;
    D.Silt=Upstream.Silt;
    D.Gravel=Upstream.DepositedGravel;
    D.Stones=Upstream.Stones;
    D.Grass=Upstream.ShortGrass;
    const float Yaw=D.Stones>0.?float(FMath::Atan2(Channel.Flow.Y,Channel.Flow.X)):0.f;
    AddDeposit(P,D,Upstream.Spine,Taper,Yaw);
    return P;
}
}
