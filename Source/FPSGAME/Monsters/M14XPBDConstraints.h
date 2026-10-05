#pragma once
#include "CoreMinimal.h"

// Adapted from PositionBasedDynamics XPBD.cpp (MIT, 2015-present contributors).
// Upstream snapshot, complete license and hashes: Source/ThirdParty/PositionBasedDynamics/.
// Compliance replaces inverse stiffness; volume gradients include their 1/6 factor.
namespace M14XPBD
{
inline void Distance(FVector& A,FVector& B,double WA,double WB,double Rest,double Compliance,double Dt,float& Lambda)
{
    const FVector Delta=A-B;const double Length=Delta.Length();
    if(Length<1.e-8||WA+WB<=0.)return;
    const double Alpha=Compliance/(Dt*Dt);
    const double DL=(-(Length-Rest)-Alpha*Lambda)/(WA+WB+Alpha);
    Lambda+=float(DL);const FVector Correction=Delta*(DL/Length);
    A+=WA*Correction;B-=WB*Correction;
}
inline double Volume(const FVector& A,const FVector& B,const FVector& C,const FVector& D)
{return FVector::DotProduct(FVector::CrossProduct(B-A,C-A),D-A)/6.;}
inline void VolumeConstraint(FVector* P[4],const double W[4],double Rest,double Compliance,double Dt,float& Lambda,float& BarrierLambda)
{
    if(FMath::Abs(Rest)<1.e-10)return;
    const double Sign=Rest>0.?1.:-1.;
    auto Project=[&](double Target,double Softness,bool Unilateral,float& Accumulated)
    {
        const FVector G1=Sign*FVector::CrossProduct(*P[2]-*P[0],*P[3]-*P[0])/6.;
        const FVector G2=Sign*FVector::CrossProduct(*P[3]-*P[0],*P[1]-*P[0])/6.;
        const FVector G3=Sign*FVector::CrossProduct(*P[1]-*P[0],*P[2]-*P[0])/6.;
        const FVector G[4]={-G1-G2-G3,G1,G2,G3};
        double Denom=0.;for(int32 J=0;J<4;++J)Denom+=W[J]*G[J].SquaredLength();
        const double Alpha=Softness/(Dt*Dt);
        if(Denom+Alpha<1.e-16)return;
        const double C=Sign*Volume(*P[0],*P[1],*P[2],*P[3])-Target;
        double DL=(-C-Alpha*Accumulated)/(Denom+Alpha);
        if(Unilateral)DL=FMath::Max(0.,double(Accumulated)+DL)-Accumulated;
        double Largest=0.;for(int32 J=0;J<4;++J)Largest=FMath::Max(Largest,(G[J]*(W[J]*DL)).Length());
        if(Largest>.01)DL*=.01/Largest;
        Accumulated+=float(DL);
        for(int32 J=0;J<4;++J)*P[J]+=G[J]*(W[J]*DL);
    };
    // Compression and inversion are separate constraints. Reusing an equality
    // multiplier while toggling to a hard barrier pumped energy at every crossing.
    Project(FMath::Abs(Rest),Compliance,false,Lambda);
    Project(FMath::Abs(Rest)*.08,1.e-8,true,BarrierLambda);
}
}
