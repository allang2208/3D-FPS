#include "TemperateHillsRiver.h"
#include "TemperateHillsLandform.h"
#include "TemperateHillsSurface.h"

namespace TemperateHillsLandform
{
namespace
{
// Coordinates and plan widths are in metres, cut and fill in centimetres.
// The two lateral Bezier controls follow bends measured on the fixed terrain.
struct FRun
{
    FVector2D Head, Axis, Across;
    FBox2D Bounds;
    double Length, BendA, BendB, Neck, FanWidth, Cut, Shoulder, Fill, Hand;

    FRun(FVector2D HeadM, FVector2D ToeM, double A, double B, double NeckM, double FanM,
        double CutCm, double ShoulderCm, double FillCm, double Side)
        : Head(HeadM), Axis((ToeM-HeadM).GetSafeNormal()), Across(-Axis.Y,Axis.X),
          Length((ToeM-HeadM).Size()), BendA(A), BendB(B), Neck(NeckM), FanWidth(FanM),
          Cut(CutCm), Shoulder(ShoulderCm), Fill(FillCm), Hand(Side)
    {
        // The curve lies in its four controls' convex hull. Allow the same
        // lateral margin as the cross-section reject below for slanted cuts.
        Bounds=FBox2D(ForceInit);
        Bounds+=Head; Bounds+=ToeM;
        Bounds+=Head+Axis*(Length/3.)+Across*A;
        Bounds+=Head+Axis*(Length*2./3.)+Across*B;
        Bounds=Bounds.ExpandBy(4.*FanWidth);
    }
};

const FRun Runs[] = {
    // Two incisions join on the northwest slope. The tributary has no terminal fan.
    {{-315,320}, {-301,222}, 49,4, 6.8,15., 124,52,22, 1.},
    {{-258,296}, {-291,255}, -5,3, 6.1,6., 64,18,0, -1.},
    // A high, one-sided shoulder and a shallower hollow beneath the north ridge.
    {{-104,265}, {-166,218}, -16,-2, 8.4,13., 47,118,14, -1.},
    {{-30,420}, {-40,351}, -3,26, 7.2,20., 58,18,12, 1.},
    // The eastern scarp drains to a broad apron. A much shorter shoulder breaks its skyline.
    {{360,209}, {335,104}, -9,-17, 6.4,23., 98,64,32, -1.},
    {{400,426}, {334,366}, -1,-18, 8.,12., 36,97,12, 1.},
    // Two separate southern slopes have different exits: an open fan and a narrow runout.
    {{312,-247}, {263,-155}, 14,7, 7.2,21., 86,38,29, 1.},
    {{385,-432}, {378,-326}, 10,-19, 5.6,11., 103,42,17, -1.}
};
}

FRunoff SurveyedRunoff(double X, double Y)
{
    const FVector2D P(X*.01,Y*.01);
    FRunoff Out;
    double Cut=0., Fill=0., Strongest=0.;
    for (const FRun& R : Runs)
    {
        if (!R.Bounds.IsInsideOrOn(P)) continue;
        const FVector2D D=P-R.Head;
        const double T=FVector2D::DotProduct(D,R.Axis)/R.Length;
        if (T<=0. || T>=1.) continue;
        const double U=1.-T;
        const double Bend=3.*T*U*(U*R.BendA+T*R.BendB);
        const double Lateral=FVector2D::DotProduct(D,R.Across)-Bend;
        if (FMath::Abs(Lateral)>4.*R.FanWidth) continue;
        const double BendSlope=3.*(U*(1.-3.*T)*R.BendA+T*(2.-3.*T)*R.BendB)/R.Length;
        const double Cross=Lateral/FMath::Sqrt(1.+BendSlope*BendSlope);
        const double Neck=R.Neck*FMath::Lerp(.62,1.22,FMath::SmoothStep(.04,.72,T));
        const double Fade=FMath::SmoothStep(0.,.17,T)*(1.-FMath::SmoothStep(.75,1.,T));
        const double Hollow=Fade*(1.-FMath::SmoothStep(.04,1.,FMath::Abs(Cross)/Neck));
        const double Shoulder=Fade*(1.-FMath::SmoothStep(.08,1.,FMath::Abs(R.Hand*Cross-1.25*Neck)/(1.32*Neck)));
        const double Apron=FMath::SmoothStep(.53,.80,T)*(1.-FMath::SmoothStep(.82,1.,T))*
            (1.-FMath::SmoothStep(.12,1.,FMath::Abs(Cross+.31*R.Hand*Neck)/R.FanWidth));
        // Keep a single bed where two runs meet. The shoulder tapers before the fan widens.
        Cut=FMath::Max(Cut,R.Cut*Hollow);
        Fill=FMath::Max(Fill,R.Shoulder*Shoulder*(1.-.78*T)+R.Fill*Apron);
        Out.Hollow=FMath::Max(Out.Hollow,Hollow*(1.-.65*Apron));
        Out.Shoulder=FMath::Max(Out.Shoulder,Shoulder*FMath::Min(1.,R.Shoulder/90.));
        const double Deposit=R.Fill>0.?Apron:0.;
        Out.Apron=FMath::Max(Out.Apron,Deposit);
        const double Weight=FMath::Max3(Hollow,Shoulder,Deposit);
        if (Weight>Strongest)
        {
            Strongest=Weight;
            Out.Downstream=(R.Axis+R.Across*BendSlope).GetSafeNormal();
        }
    }
    Out.HeightCm=Fill-Cut;
    return Out;
}
}

namespace TemperateRiver
{
void FPlan::BuildUplandRelief(int32 Seed)
{
    if(!bVillageRainforest||ProtectedSize<2)return;
    const int32 Side=ProtectedSize;
    const double Step=2.*WorldHalf/(Side-1);
    TArray<float> DryLand;
    DryLand.Init(1.f,Side*Side);

    // Reserve the full channel apron, plus a grid diagonal so interpolation
    // cannot lift the bed. Rasterize short segments once on the planning worker.
    for(int32 I=1;I<Points.Num();++I)
    {
        const FPoint& A=Points[I-1];
        const FPoint& B=Points[I];
        const FVector2D Span=B.XY-A.XY;
        const double LengthSq=FMath::Max(1.,Span.SizeSquared());
        const double Bank=ChannelReach(A,B)+1.5*Step;
        const double Reach=Bank+1800.;
        const auto GridIndex=[&](double V){return FMath::Clamp(FMath::FloorToInt((V+WorldHalf)/Step),0,Side-1);};
        const int32 MinX=GridIndex(FMath::Min(A.XY.X,B.XY.X)-Reach),MaxX=GridIndex(FMath::Max(A.XY.X,B.XY.X)+Reach);
        const int32 MinY=GridIndex(FMath::Min(A.XY.Y,B.XY.Y)-Reach),MaxY=GridIndex(FMath::Max(A.XY.Y,B.XY.Y)+Reach);
        for(int32 Y=MinY;Y<=MaxY;++Y)for(int32 X=MinX;X<=MaxX;++X)
        {
            float& Weight=DryLand[Y*Side+X];
            if(Weight<=0.f)continue;
            const FVector2D Delta=FVector2D(X*Step-WorldHalf,Y*Step-WorldHalf)-A.XY;
            const double T=FMath::Clamp(FVector2D::DotProduct(Delta,Span)/LengthSq,0.,1.);
            Weight=FMath::Min(Weight,float(FMath::SmoothStep(Bank,Reach,(Delta-T*Span).Size())));
        }
    }

    UplandReliefCm.SetNumZeroed(Side*Side);
    using namespace TemperateHillsSurface;
    const bool HasRunoff=TemperateHillsLandform::HasSurveyedRunoff(Seed,GenerationVersion,WorldHalf);
    TArray<float> RunoffMask;
    if(HasRunoff)RunoffMask.SetNumZeroed(Side*Side);
    for(int32 I=0;I<UplandReliefCm.Num();++I)
    {
        const double X=(I%Side)*Step-WorldHalf,Y=(I/Side)*Step-WorldHalf;
        double Weight=DryLand[I]*(1.-ProtectedLand[I]/255.);
        const double EndX=WorldHalf-FMath::Abs(X),EndY=WorldHalf-FMath::Abs(Y);
        const double Rim=FMath::Min(EndX,EndY),Road=FMath::Abs(Y-ValleyY(X,Seed));
        double Join=FMath::SmoothStep(600.,2800.,Rim)*FMath::SmoothStep(700.,2200.,Road);
        if(HasRunoff && Join>0. && (Rim<7600. || Road<4550.))
        {
            // Let the distant hill and its continuation meet over a rounded
            // flank. A fixed-width border or road reserve left a straight ridge.
            const double Vary=Noise5(X/9100.,Y/13600.,Seed,6427);
            const double EdgeJoin=FMath::SmoothStep(600.,5750.+1650.*Vary,EndX)*
                FMath::SmoothStep(600.,5900.-1550.*Vary,EndY);
            const double LaneJoin=FMath::SmoothStep(700.,3500.+950.*Vary,Road);
            Join=FMath::Lerp(Join,EdgeJoin*LaneJoin,TemperateHillsLandform::PoolClearance(X,Y));
        }
        Weight*=Join;
        if(WhiteCliffs.Valid)
        {
            const FVector2D P=WhiteCliffs.Local(X,Y);
            const double RadiusSq=FMath::Square(P.X/11500.)+FMath::Square(P.Y/9000.);
            Weight*=FMath::SmoothStep(1.24,1.82,RadiusSq);
        }
        if(Weight<=0.)continue;
        if(Lake.Valid)
            Weight*=FMath::SmoothStep(FLake::MaxBankExtent+800.,FLake::MaxBankExtent+3200.,Lake.Edge(X,Y));
        if(Weight<=0.)continue;

        // Long, rounded spurs alternate with shallow swales. The broad field
        // leaves some hills quiet; the warped axes avoid parallel contour bands.
        const double Province=.5+.5*Noise5(X/17400.,Y/17400.,Seed,4751);
        const double WX=X+1450.*Noise5(X/8700.,Y/8700.,Seed,4759);
        const double WY=Y+1450.*Noise5(X/8700.,Y/8700.,Seed,4783);
        const double Fold=Noise5(WX/4800.,WY/9700.,Seed,4787);
        const double Shoulder=FMath::SmoothStep(.02,.72,Fold);
        const double Swale=FMath::SmoothStep(.02,.66,-Fold);
        const double Amplitude=FMath::SmoothStep(.18,.80,Province);
        UplandReliefCm[I]=int16(FMath::RoundToInt(Weight*Amplitude*(355.*Shoulder-175.*Swale)));
        if(HasRunoff)RunoffMask[I]=float(Weight);
    }
    if(!HasRunoff)return;

    // The narrow tributary is visible from both sides of a joined valley. Its
    // cut must be sampled on the playable near mesh's 2 m grid, instead of
    // following 4 m survey edges. Runtime still reads one bilinear height.
    const int32 FineSide=2*Side-1;
    TArray<int16> FineRelief;
    FineRelief.SetNumUninitialized(FineSide*FineSide);
    for(int32 Y=0;Y<FineSide;++Y)for(int32 X=0;X<FineSide;++X)
    {
        const int32 IX=FMath::Min(X/2,Side-2),IY=FMath::Min(Y/2,Side-2),I=IY*Side+IX;
        const double U=X*.5-IX,V=Y*.5-IY;
        const auto At=[&](const auto& Grid)
        {
            return FMath::BiLerp(double(Grid[I]),double(Grid[I+1]),double(Grid[I+Side]),double(Grid[I+Side+1]),U,V);
        };
        const double Mask=At(RunoffMask);
        const double Cut=Mask>0.?Mask*TemperateHillsLandform::SurveyedRunoff(X*Step*.5-WorldHalf,Y*Step*.5-WorldHalf).HeightCm:0.;
        FineRelief[Y*FineSide+X]=int16(FMath::RoundToInt(4.*(At(UplandReliefCm)+Cut)));
    }
    UplandReliefCm=MoveTemp(FineRelief);
}
}
