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
}
