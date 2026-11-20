#include "TemperateQuarryLakeSlope.h"
#include "TemperateHillsRiver.h"
#include "TemperateHillsSurface.h"
#include "TemperateQuarryYard.h"

namespace TemperateQuarryLakeSlope
{
namespace
{
constexpr double Step=160., HalfWidth=8000., EndY=0.;
constexpr int32 Columns=101;

double Band(double Distance,double Inner,double Outer)
{
    return 1.-FMath::SmoothStep(Inner,Outer,FMath::Abs(Distance));
}

double Lens(double X,double T,double CentreX,double CentreT,double Width,double Length)
{
    return 1.-FMath::SmoothStep(.12,1.,FMath::Square((X-CentreX)/Width)+FMath::Square((T-CentreT)/Length));
}

FProfile Section(double X,double Y,double Shore,double Crest,double Freedom,double Phase)
{
    // Relative shore distance follows coves and promontories. T rises towards
    // the quarry; the two watersheds spread into separate fans towards the lake.
    const double T=Shore/(Shore+Crest-Y);
    const double Fringe=240.*FMath::Sin(Y/1740.+Phase)+190.*FMath::Sin(Y/3370.-Phase);
    const double Width=FMath::Lerp(7200.,6100.,T);
    const double W=Freedom*Band(X-Fringe,Width-1020.,Width+240.)*
        FMath::SmoothStep(490.,1300.,Shore)*FMath::SmoothStep(0.,1200.,Crest-Y);
    if(W<=0.)return {};
    const double Drift=TemperateHillsSurface::Noise5(X/1060.,Y/1320.,int32(Phase*1600.),9637);
    const double Left=-2700.+1160.*T+395.*FMath::Sin(5.3*T+Phase*.27)+115.*Drift;
    const double Right=2410.+850.*T-540.*FMath::Sin(5.7*T-.7)+85.*Drift;
    const double Fork=Left-FMath::Max(0.,T-.32)*(3580.+310.*FMath::Sin(4.*T));
    const double Tail=FMath::SmoothStep(.025,.19,T);
    const double LeftGully=Band(X-Left,95.,640.-170.*T)*Tail*(1.-FMath::SmoothStep(.77,.98,T));
    const double ForkGully=Band(X-Fork,55.,470.)*FMath::SmoothStep(.31,.48,T)*(1.-FMath::SmoothStep(.69,.90,T));
    const double RightGully=Band(X-Right,65.,510.+115.*(1.-T))*Tail*(1.-FMath::SmoothStep(.67,.89,T));
    const double Gully=FMath::Max3(LeftGully,.69*ForkGully,.87*RightGully);

    // A long broken rib runs down the left bank; the opposite shoulder has
    // one blunt spur and a shorter detached outcrop. Their toes shed scree.
    const double Rib=Lens(X,T,Left+950.+380.*T,.57,1050.,.35);
    const double Spur=Lens(X,T,Right-1120.+260.*FMath::Sin(4.*T),.72,1420.,.29);
    const double Knuckle=Lens(X,T,Right+790.,.43,845.,.20);
    const double Rock=FMath::Max3(Rib,Spur,Knuckle)*(.79+.21*Drift);
    const double LeftFan=Lens(X,T,Left-260.+520.*T,.19,1430.,.17);
    const double RightFan=Lens(X,T,Right+280.,.24,1060.,.20);
    const double Scree=FMath::Max(Lens(X,T,Left+770.,.37,1060.,.17),Lens(X,T,Right-880.,.49,1300.,.18));
    const double Apron=FMath::Max(LeftFan,RightFan);
    const double Gravel=FMath::Max3(Apron*(1.-.69*Gully),Scree*(1.-.74*Rock),.36*Gully);
    const double Soil=FMath::Clamp(.50+.29*Drift+.22*Lens(X,T,Left-950.,.54,1220.,.32),0.,1.);
    const double Turf=Soil*(1.-Gully)*(1.-Rock)*(1.-.83*Gravel);
    const double Damp=Gully*(.43+.51*(1.-T))+.14*Apron;
    const double Relief=139.*Rib+176.*Spur+93.*Knuckle-109.*Gully+42.*Apron+37.*Scree+
        (22.+19.*Rock)*Drift;
    return {float(W*Relief),float(W),float(W*Gully),float(W*Gravel),float(W*Rock),float(W*Turf),float(W*Damp)};
}
}

void FField::Build(const TemperateRiver::FPlan& Plan,int32 Seed)
{
    Cells.Reset();Outcrops.Reset();Rows=0;
    if(!Plan.WhiteCliffs.Valid||!Plan.Lake.Valid||!Plan.Lake.bNaturalShore)return;
    Origin=Plan.WhiteCliffs.Center;Across=Plan.WhiteCliffs.Axis;
    const double Distance=FVector2D::Distance(Origin,Plan.Lake.Center);
    MinY=FMath::FloorToDouble((-Distance+1400.)/Step)*Step;
    Rows=FMath::CeilToInt((EndY-MinY)/Step)+1;
    if(Rows<2)return;
    Cells.SetNumZeroed(Rows*Columns);
    const double Phase=TemperateHillsSurface::Unit(TemperateHillsSurface::Key(0,0,Seed,9631))*2.*PI;
    const double Hand=Phase>PI?1.:-1.;
    for(int32 J=1;J<Rows-1;++J)for(int32 I=1;I<Columns-1;++I)
    {
        const double X=I*Step-HalfWidth,Y=MinY+J*Step;
        const FVector2D World=Plan.WhiteCliffs.World(X,Y);
        const double Shore=Plan.Lake.Edge(World.X,World.Y);
        if(Shore<=490.||Y>=EndY)continue;
        // The open approach stops below the gate. On either side the natural
        // ground continues behind the rock caps, well clear of their foundations.
        const auto Station=TemperateQuarry::Section(Y);
        const double BehindToe=FMath::Max(Station.West-X,X-Station.East);
        const double Crest=FMath::Lerp(-3600.,EndY,FMath::SmoothStep(1400.,2450.,BehindToe));
        if(Y>=Crest)continue;
        const double Protected=Plan.Protection(World.X,World.Y);
        if(Protected>=.999)continue;
        const auto River=Plan.SampleChannel(World.X,World.Y);
        const double RiverEdge=River.Distance-River.HalfWidth;
        const double Dry=FMath::SmoothStep(390.,1210.,RiverEdge);
        // The haul approach emerges from the quarry apron. Keep its deck and
        // shoulders at the surveyed height; release the reserve below its end.
        const double Road=FMath::SmoothStep(TemperateQuarry::Stations[0].Y-780.,TemperateQuarry::Stations[0].Y,Y)*
            Band(X-Station.Road,470.,970.);
        const auto S=Section(X*Hand,Y,Shore,Crest,(1.-Protected)*Dry*(1.-Road),Phase);
        const auto Byte=[](float V){return uint8(FMath::RoundToInt(FMath::Clamp(V,0.f,1.f)*255.f));};
        Cells[J*Columns+I]={int16(FMath::RoundToInt(S.HeightCm)),Byte(S.Coverage),Byte(S.Gully),
            Byte(S.Gravel),Byte(S.Ledge),Byte(S.Turf),Byte(S.Damp)};
    }
    // Pick a few coherent exposures on the actual ribs, above their scree.
    // A wider separation than the length of one rib keeps a long ridge from
    // acquiring a row of equally spaced boulders.
    for(int32 Head=0;Head<3;++Head)
    {
        int32 Best=120;
        FVector2D Centre;
        for(int32 J=2;J<Rows-1;J+=3)for(int32 I=2;I<Columns-1;I+=3)
        {
            const FCell& Cell=Cells[J*Columns+I];
            if(Cell.Ledge<=Best)continue;
            const FVector2D P(I*Step-HalfWidth,MinY+J*Step);
            if(Outcrops.ContainsByPredicate([&](FVector2D Other)
                {return FVector2D::DistSquared(Other,P)<FMath::Square(2650.);}))continue;
            Centre=P;Best=Cell.Ledge;
        }
        if(Best==120)break;
        Outcrops.Add(Centre);
    }
}

bool FField::IntersectsCell(double WorldMinX,double WorldMinY,double Size) const
{
    if(Cells.IsEmpty())return false;
    const double HalfCell=Size*.5,HalfLength=(EndY-MinY)*.5;
    const FVector2D Along(-Across.Y,Across.X);
    const FVector2D Delta=FVector2D(WorldMinX+HalfCell,WorldMinY+HalfCell)-Origin-Along*(MinY+HalfLength);
    const double AX=FMath::Abs(Across.X),AY=FMath::Abs(Across.Y);
    const double CellProjection=HalfCell*(AX+AY);
    return FMath::Abs(Delta.X)<=HalfCell+AX*HalfWidth+AY*HalfLength &&
        FMath::Abs(Delta.Y)<=HalfCell+AY*HalfWidth+AX*HalfLength &&
        FMath::Abs(FVector2D::DotProduct(Delta,Across))<=HalfWidth+CellProjection &&
        FMath::Abs(FVector2D::DotProduct(Delta,Along))<=HalfLength+CellProjection;
}

bool FField::GridPosition(double X,double Y,int32& Index,float& U,float& V) const
{
    if(Cells.IsEmpty())return false;
    const FVector2D D(X-Origin.X,Y-Origin.Y);
    const double Column=(FVector2D::DotProduct(D,Across)+HalfWidth)/Step;
    const double Row=(FVector2D::CrossProduct(Across,D)-MinY)/Step;
    if(Column<0.||Column>=Columns-1||Row<0.||Row>=Rows-1)return false;
    const int32 I=int32(Column),J=int32(Row);
    Index=J*Columns+I;U=float(Column-I);V=float(Row-J);
    return true;
}

double FField::Height(double X,double Y) const
{
    int32 I;float U,V;
    if(!GridPosition(X,Y,I,U,V))return 0.;
    return FMath::BiLerp(float(Cells[I].HeightCm),float(Cells[I+1].HeightCm),
        float(Cells[I+Columns].HeightCm),float(Cells[I+Columns+1].HeightCm),U,V);
}

FProfile FField::Sample(double X,double Y) const
{
    int32 I;float U,V;
    if(!GridPosition(X,Y,I,U,V))return {};
    const auto& A=Cells[I];const auto& B=Cells[I+1];
    const auto& C=Cells[I+Columns];const auto& D=Cells[I+Columns+1];
    if(!(A.Coverage|B.Coverage|C.Coverage|D.Coverage))return {};
    const auto Blend=[&](auto Member)
    {
        return FMath::BiLerp(float(A.*Member),float(B.*Member),float(C.*Member),float(D.*Member),U,V);
    };
    return {Blend(&FCell::HeightCm),Blend(&FCell::Coverage)/255.f,Blend(&FCell::Gully)/255.f,
        Blend(&FCell::Gravel)/255.f,Blend(&FCell::Ledge)/255.f,Blend(&FCell::Turf)/255.f,Blend(&FCell::Damp)/255.f};
}

}
