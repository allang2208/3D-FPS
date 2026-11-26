#pragma once
#include "CoreMinimal.h"

// Plain numerical state copied into worker jobs. No UObject or actor access.
namespace TemperateHillsSurface
{
inline uint32 Mix(uint32 V) { V^=V>>16;V*=0x7feb352dU;V^=V>>15;V*=0x846ca68bU;return V^(V>>16); }
inline uint32 Key(int32 X,int32 Y,uint32 Seed,uint32 Salt)
{ return Mix(Mix(uint32(X)*0x9e3779b9U)^Mix(uint32(Y)*0x85ebca6bU+0x1b873593U)^Mix(Seed+Salt)); }
inline double Unit(uint32 V) { return double(Mix(V)&0x00ffffffU)/16777216.0; }
inline double ValleyY(double X,int32 Seed) { return 1900*FMath::Sin(X*.000065+Unit(Seed)*3)+850*FMath::Sin(X*.00014); }
inline double Noise(double X,double Y,int32 Seed,uint32 Salt)
{
    const int32 IX=FMath::FloorToInt(X),IY=FMath::FloorToInt(Y);
    double FX=X-IX,FY=Y-IY;FX=FX*FX*(3-2*FX);FY=FY*FY*(3-2*FY);
    auto V=[&](int32 A,int32 B){return Unit(Key(A,B,uint32(Seed),Salt))*2-1;};
    return FMath::Lerp(FMath::Lerp(V(IX,IY),V(IX+1,IY),FX),FMath::Lerp(V(IX,IY+1),V(IX+1,IY+1),FX),FY);
}

// V2 primitives. The quintic fade removes the first and second derivative at
// the lattice, and the fixed 36.87-degree rotation stops the value-noise grid
// from lining up with the world axes (the visible parallel bands in V1).
inline double Quintic(double T) { return T*T*T*(T*(T*6-15)+10); }
inline double Noise5(double X,double Y,int32 Seed,uint32 Salt)
{
    const double RX=X*.8-Y*.6,RY=X*.6+Y*.8;
    const int32 IX=FMath::FloorToInt(RX),IY=FMath::FloorToInt(RY);
    const double FX=Quintic(RX-IX),FY=Quintic(RY-IY);
    auto V=[&](int32 A,int32 B){return Unit(Key(A,B,uint32(Seed),Salt))*2-1;};
    return FMath::Lerp(FMath::Lerp(V(IX,IY),V(IX+1,IY),FX),FMath::Lerp(V(IX,IY+1),V(IX+1,IY+1),FX),FY);
}
inline double Fbm(double X,double Y,int32 Seed,uint32 Salt,int32 Octaves)
{
    double Sum=0,Norm=0,Amp=1,F=1;
    for(int32 I=0;I<Octaves;++I)
    {
        Sum+=Amp*Noise5(X*F+I*13.7,Y*F-I*7.3,Seed,Salt+I*131);
        Norm+=Amp;Amp*=.5;F*=2.03;
    }
    return Sum/Norm;
}
inline double Ridged(double X,double Y,int32 Seed,uint32 Salt,int32 Octaves)
{
    double Sum=0,Norm=0,Amp=1,F=1;
    for(int32 I=0;I<Octaves;++I)
    {
        const double N=1.0-FMath::Abs(Noise5(X*F+I*17.3,Y*F+I*5.9,Seed,Salt+I*197));
        Sum+=Amp*N*N;Norm+=Amp;Amp*=.5;F*=2.03;
    }
    return Sum/Norm;
}

// V1 is frozen: existing saves must keep producing exactly the same terrain.
inline double HeightV1(double X,double Y,int32 Seed)
{
    const double Warp=Noise(X*.000024,Y*.000024,Seed,14)*4200;
    const double Hill=Noise((X+Warp)*.000055,(Y-Warp*.5)*.000055,Seed,73);
    const double Large=Noise(X*.000020+1.31,Y*.000020-2.1,Seed,91);
    const double Valley=FMath::Exp(-FMath::Square(FMath::Abs(Y-ValleyY(X,Seed))/9000.0));
    const double Detail=Noise(X*.00035,Y*.00035,Seed,26)*95+Noise(X*.0011,Y*.0011,Seed,88)*14;
    return FMath::RoundToDouble(5400+Large*3200+Hill*2400-Valley*1200+Detail);
}

// V2: continentalness (C) sets the base, erosion (E) flattens or roughens it,
// and a warped ridged field (R) supplies the actual hills and rock faces.
// Constants are tuned for 1-4 km worlds: ~84 m local relief at 1 km and
// ~147 m at 4 km on seed 122, with 0.2-0.5% of the surface above 45 degrees.
inline double HeightV2(double X,double Y,int32 Seed)
{
    const double C=Fbm(X/140000.0,Y/140000.0,Seed,2101,4);
    const double E=Fbm(X/90000.0,Y/90000.0,Seed,2102,4)*.5+.5;
    const double WX=Fbm(X/220000.0,Y/220000.0,Seed,2103,2)*12000.0;
    const double WY=Fbm(X/220000.0,Y/220000.0,Seed,2104,2)*12000.0;
    const double R=Ridged((X+WX)/52000.0,(Y+WY)/52000.0,Seed,2105,4);
    const double D=Fbm(X/6500.0,Y/6500.0,Seed,2106,3)*350.0
                  +Fbm(X/2400.0,Y/2400.0,Seed,2107,2)*90.0;
    const double Base=7000.0+3500.0*C;
    const double Roughness=FMath::Lerp(1.0,0.3,FMath::SmoothStep(0.2,0.8,E));
    const double Amp=FMath::Clamp(14000.0+14000.0*C,5000.0,28000.0)*Roughness;
    const double Valley=1500.0*FMath::Exp(-FMath::Square(FMath::Abs(Y-ValleyY(X,Seed))/9000.0));
    return FMath::RoundToDouble(FMath::Max(150.0,Base+Amp*(R-.35)+D-Valley));
}

// V3 uses broad signed hills, without the abs() cusps and short, tall ridges of V2.
// Keep V1/V2 frozen so a saved world's ground only changes by explicit migration.
inline double HeightV3(double X,double Y,int32 Seed)
{
    const double C=Fbm(X/180000.,Y/180000.,Seed,2101,3);
    const double WX=Fbm(X/220000.,Y/220000.,Seed,2103,2)*4500.;
    const double WY=Fbm(X/220000.,Y/220000.,Seed,2104,2)*4500.;
    const double Hills=Fbm((X+WX)/85000.,(Y+WY)/85000.,Seed,2105,3);
    const double Detail=Noise5(X/10000.,Y/10000.,Seed,2106)*60.
                       +Noise5(X/3500.,Y/3500.,Seed,2107)*12.;
    const double Valley=700.*FMath::Exp(-FMath::Square((Y-ValleyY(X,Seed))/14000.));
    return FMath::RoundToDouble(7000.+2200.*C+3800.*Hills+Detail-Valley);
}

inline double Height(double X,double Y,int32 Seed,int32 Version=1)
{ return Version>=3?HeightV3(X,Y,Seed):(Version>=2?HeightV2(X,Y,Seed):HeightV1(X,Y,Seed)); }
inline FVector Normal(double X,double Y,int32 Seed,int32 Version=1)
{ return FVector(-(Height(X+100,Y,Seed,Version)-Height(X-100,Y,Seed,Version))/200,-(Height(X,Y+100,Seed,Version)-Height(X,Y-100,Seed,Version))/200,1).GetSafeNormal(); }

// Runtime terrain edits layered on top of the generated height: explosion craters
// and grid-aligned shovel dig/refill steps. Plain numbers only, so worker mesh jobs
// copy them and never touch an actor or UObject. X/Y are world cm like Height().
//
// Amplitude is the signed height delta at the centre: negative digs down, positive
// raises. Lip is the opposite-sign collar just outside a circular crater.
struct FTerrainEdit
{
    int32 Type=0;             // 0 circular crater, 1 grid-aligned box step
    double X=0,Y=0;
    double Radius=0;          // circular only
    double HalfX=0,HalfY=0;   // box only
    double Amplitude=0;
    double Lip=0;
    uint32 Seed=0;
    bool operator==(const FTerrainEdit&) const = default;
};
inline bool TerrainEditValid(const FTerrainEdit& E)
{
    return E.Type==1?(E.HalfX>0&&E.HalfY>0&&E.Amplitude!=0):(E.Radius>0&&E.Amplitude!=0);
}
inline double TerrainEditReach(const FTerrainEdit& E)
{
    return E.Type==1?FMath::Max(E.HalfX,E.HalfY)+1:E.Radius*1.35+1;
}
// Smooth polynomial minimum: overlapping craters merge into one bowl instead of
// producing the crease that plain addition leaves at the intersection.
inline double SmoothMin(double A,double B,double K)
{
    const double H=FMath::Clamp(.5+.5*(B-A)/K,0.0,1.0);
    return FMath::Lerp(B,A,H)-K*H*(1-H);
}
// Height delta contributed by one edit. Circular craters vary their outline and
// depth with two low harmonics so repeated blasts do not read as perfect circles.
inline double TerrainEditOffset(const FTerrainEdit& E,double X,double Y)
{
    if(!TerrainEditValid(E))return 0;
    const double DX=X-E.X,DY=Y-E.Y;
    if(E.Type==1)
    {
        const double AX=FMath::Abs(DX),AY=FMath::Abs(DY);
        if(AX>=E.HalfX||AY>=E.HalfY)return 0;
        // One 50 cm band at the border keeps the grid step readable at the mesh
        // resolution instead of ending as a knife edge between two vertices.
        const double Edge=FMath::Min(E.HalfX-AX,E.HalfY-AY);
        const double W=FMath::Clamp(Edge/50.0,0.0,1.0);
        return E.Amplitude*(W*W*(3-2*W));
    }
    const double D2=DX*DX+DY*DY;
    const double Outer=TerrainEditReach(E);
    if(D2>=Outer*Outer)return 0;
    const double D=FMath::Sqrt(D2);
    const double Angle=FMath::Atan2(DY,DX);
    const double Phase=double(E.Seed%997)*.0173;
    const double Warp=1+.11*FMath::Sin(3*Angle+Phase)+.055*FMath::Sin(7*Angle-Phase*1.7);
    const double EffR=E.Radius*Warp;
    const double Depth=E.Amplitude*(1+.10*FMath::Sin(2*Angle-Phase*2.3));
    if(D<=EffR)return Depth*FMath::Square(1-FMath::Square(D/EffR));
    const double U=(D-EffR)/FMath::Max(1.0,Outer-EffR);
    return E.Lip*FMath::Square(1-U);
}
// Templated on the allocator so the hot paths can use an inline-allocated array.
template<typename Allocator>
inline double TerrainEditOffset(const TArray<FTerrainEdit,Allocator>& Edits,double X,double Y)
{
    double Steps=0,Collar=0,Bowl=0;
    bool bHasBowl=false;
    for(const FTerrainEdit& E:Edits)
    {
        const double Offset=TerrainEditOffset(E,X,Y);
        if(Offset==0)continue;
        if(E.Type==1){Steps+=Offset;continue;}
        if(Offset<0){Bowl=bHasBowl?SmoothMin(Bowl,Offset,60.0):Offset;bHasBowl=true;}
        else Collar+=Offset;
    }
    return Steps+Bowl+Collar;
}
// True when an edit (or its collar) can still move this point, including the
// finite-difference stencil used for normals.
inline bool TerrainEditTouches(const FTerrainEdit& E,double X,double Y,double Margin=110)
{
    if(!TerrainEditValid(E))return false;
    if(E.Type==1)return FMath::Abs(X-E.X)<E.HalfX+Margin&&FMath::Abs(Y-E.Y)<E.HalfY+Margin;
    const double R=TerrainEditReach(E)+Margin;
    return FMath::Square(X-E.X)+FMath::Square(Y-E.Y)<R*R;
}
template<typename Allocator>
inline bool TerrainEditTouches(const TArray<FTerrainEdit,Allocator>& Edits,double X,double Y,double Margin=110)
{
    for(const FTerrainEdit& E:Edits)if(TerrainEditTouches(E,X,Y,Margin))return true;
    return false;
}
template<typename THeightFn>
inline FVector NumericNormal(const THeightFn& HeightFn,double X,double Y,double Step=100)
{
    return FVector(-(HeightFn(X+Step,Y)-HeightFn(X-Step,Y))/(2*Step),-(HeightFn(X,Y+Step)-HeightFn(X,Y-Step))/(2*Step),1).GetSafeNormal();
}
}
