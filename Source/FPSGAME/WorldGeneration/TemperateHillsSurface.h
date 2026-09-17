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
inline double Height(double X,double Y,int32 Seed)
{
    const double Warp=Noise(X*.000024,Y*.000024,Seed,14)*4200;
    const double Hill=Noise((X+Warp)*.000055,(Y-Warp*.5)*.000055,Seed,73);
    const double Large=Noise(X*.000020+1.31,Y*.000020-2.1,Seed,91);
    const double Valley=FMath::Exp(-FMath::Square(FMath::Abs(Y-ValleyY(X,Seed))/9000.0));
    const double Detail=Noise(X*.00035,Y*.00035,Seed,26)*95+Noise(X*.0011,Y*.0011,Seed,88)*14;
    return FMath::RoundToDouble(5400+Large*3200+Hill*2400-Valley*1200+Detail);
}
inline FVector Normal(double X,double Y,int32 Seed)
{ return FVector(-(Height(X+100,Y,Seed)-Height(X-100,Y,Seed))/200,-(Height(X,Y+100,Seed)-Height(X,Y-100,Seed))/200,1).GetSafeNormal(); }

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
