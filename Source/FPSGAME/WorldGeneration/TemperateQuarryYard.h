#pragma once
#include "CoreMinimal.h"

// All distances in quarry-local centimetres. The same toes govern rock exposure,
// the collision heightfield and the transition from bare spoil to old grass.
namespace TemperateQuarry
{
struct FStation { double Y, West, East, WestLift, EastLift, Road, Floor; };
inline constexpr FStation Stations[]={
#include "TemperateQuarryBanks.inl"
};
inline constexpr double EntryY=-2900., EntryPitch=-2.;
inline const FVector2D EntryLook(-140.,860.), Shed(-1260.,-1510.), Hoist(1050.,-1430.);
inline const FVector2D ShedElbow(-530.,-1870.), HoistElbow(520.,-1680.);
inline constexpr double ShedJunction=-2110., HoistJunction=-2070.;

inline FStation Section(double Y)
{
    int32 I=1;
    while(I<UE_ARRAY_COUNT(Stations)-1 && Y>Stations[I].Y)++I;
    const auto& A=Stations[I-1];
    const auto& B=Stations[I];
    const double T=FMath::SmoothStep(A.Y,B.Y,Y);
    return {Y,FMath::Lerp(A.West,B.West,T),FMath::Lerp(A.East,B.East,T),
        FMath::Lerp(A.WestLift,B.WestLift,T),FMath::Lerp(A.EastLift,B.EastLift,T),
        FMath::Lerp(A.Road,B.Road,T),FMath::Lerp(A.Floor,B.Floor,T)};
}
inline double RoadX(double Y){return Section(Y).Road;}
inline double Pad(FVector2D P,FVector2D Center,FVector2D Radius)
{
    const double D=((P-Center)/Radius).SizeSquared();
    return 1.-FMath::SmoothStep(.48,1.,D);
}
inline double CutHeight(FVector2D P)
{
    const auto S=Section(P.Y);
    const double West=S.West-P.X, East=P.X-S.East;
    // The upper humus rolls over the rock cap. Below it, the limestone skin
    // returns into a real stepped embankment shared by rendering and collision.
    auto Bank=[](double Depth,double Lift)
    {
        return Lift*(.49*FMath::SmoothStep(65.,320.,Depth)+.38*FMath::SmoothStep(350.,570.,Depth)
            +.13*FMath::SmoothStep(650.,860.,Depth));
    };
    const double OldSoil=FMath::SmoothStep(700.,1730.,FMath::Max(West,East));
    const double Rim=OldSoil*(96.*FMath::Sin(P.Y/650.+P.X/810.)+49.*FMath::Sin(P.Y/325.-P.X/470.));
    const double Workshop=Pad(P,Shed,{870,730}), Crane=Pad(P,Hoist,{650,570});
    static const double ShedFloor=Section(Shed.Y).Floor, HoistFloor=Section(Hoist.Y).Floor;
    const double Floor=FMath::Lerp(FMath::Lerp(S.Floor,ShedFloor,Workshop),HoistFloor,Crane);
    const double FromRoad=FMath::Abs(P.X-S.Road);
    const double Wear=-4.*(1.-FMath::SmoothStep(18.,74.,FMath::Abs(FromRoad-110.)));
    const double BrokenFloor=9.*FMath::Sin(P.X/490.+.65*FMath::Sin(P.Y/575.))*FMath::Sin(P.Y/360.);
    const double SwaleX=S.Road+560.+60.*FMath::Sin(P.Y/460.);
    const double Swale=FMath::SmoothStep(-1070.,-690.,P.Y)*(1.-FMath::SmoothStep(1130.,1580.,P.Y))*
        (1.-FMath::SmoothStep(18.,82.,FMath::Abs(P.X-SwaleX)));
    const double Cutback=245.*FMath::SmoothStep(-1000.,-650.,P.Y)*(1.-FMath::SmoothStep(950.,1300.,P.Y));
    return Floor+Bank(West-Cutback,S.WestLift)+Bank(East,S.EastLift)+Rim+
        (Wear-11.*Swale+BrokenFloor*FMath::SmoothStep(255.,670.,FromRoad))*(1.-Workshop-Crane);
}
inline double SegmentDistance(const FVector2D& P,FVector2D A,FVector2D B)
{
    const FVector2D Line=B-A;
    const double T=FMath::Clamp(FVector2D::DotProduct(P-A,Line)/Line.SizeSquared(),0.,1.);
    return (P-A-Line*T).Size();
}
inline double SpoilFan(FVector2D P,FVector2D Head,FVector2D End,double Width,double Patch)
{
    const FVector2D Axis=End-Head;
    const double Length=Axis.Size();
    const FVector2D Dir=Axis/Length,Offset=P-Head;
    const double T=FVector2D::DotProduct(Offset,Dir)/Length;
    if(T<=-.24||T>=1.12)return 0.;
    const double Side=FMath::Abs(FVector2D::CrossProduct(Dir,Offset)+
        Width*((Patch-.5)*.64+.16*FMath::Sin(3.6*T)));
    const double Radius=Width*(.40+.55*FMath::SmoothStep(-.20,.59,T));
    return FMath::SmoothStep(-.24,.06,T)*(1.-FMath::SmoothStep(.67,1.12,T))*
        (1.-FMath::SmoothStep(Radius*.52,Radius*1.28,Side));
}
inline double ServiceDistance(FVector2D P)
{
    // Each loading spur has a gentle elbow and retains its connection to the main road.
    const bool West=P.X<RoadX(P.Y);
    static const FVector2D WestStart(RoadX(ShedJunction),ShedJunction), EastStart(RoadX(HoistJunction),HoistJunction);
    const FVector2D Elbow=West?ShedElbow:HoistElbow;
    return FMath::Min(SegmentDistance(P,West?WestStart:EastStart,Elbow),SegmentDistance(P,Elbow,West?Shed:Hoist));
}
struct FFinish { double Wear=0, Talus=0, Bed=0, Turf=0; };
inline FFinish Finish(FVector2D P,double Up,double Patch)
{
    const FStation T=Section(P.Y);
    const double Depth=FMath::Max(T.West-P.X,P.X-T.East);
    const double Edge=(Patch-.5)*180.;
    const double Haul=FMath::Abs(P.X-T.Road);
    FFinish F;
    const double Paths=FMath::Max(1.-FMath::SmoothStep(235.,435.,Haul+Edge*.42),
                                  1.-FMath::SmoothStep(110.,285.,ServiceDistance(P)+Edge*.55));
    const double Apron=FMath::Max(Pad(P,Shed,{860,740}),Pad(P,Hoist,{660,570}));
    F.Wear=FMath::Max(Paths,.83*Apron);
    const double Run=290.+340.*Patch+130.*FMath::Sin(P.Y/610.+P.X/1500.);
    F.Talus=FMath::SmoothStep(-Run,-150.,Depth+Edge)*(1.-FMath::SmoothStep(45.,410.,Depth))*(1.-F.Wear);
    // The worked bay sheds spoil well past the geomorphic toe. Its two lobes
    // and the old stockpile end in feathered silt before reaching the cart track.
    const double Fans=FMath::Max3(SpoilFan(P,{-1750,290},{-1060,10},280.,Patch),
        SpoilFan(P,{-1710,670},{-1085,490},245.,Patch),
        SpoilFan(P,{-1950,-2020},{-1370,-2340},190.,Patch));
    F.Talus=FMath::Max(F.Talus,Fans*(1.-F.Wear));
    F.Bed=FMath::Max(1.-FMath::SmoothStep(.60,.91,Up),FMath::SmoothStep(20.,280.,Depth)*(1.-FMath::SmoothStep(900.,1620.,Depth))*.72);
    F.Turf=FMath::SmoothStep(650.,1230.,Depth+Edge)*FMath::SmoothStep(.72,.96,Up)*(1.-F.Wear);
    return F;
}
}
