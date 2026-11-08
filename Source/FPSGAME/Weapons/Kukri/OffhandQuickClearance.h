#pragma once
#include "CoreMinimal.h"

// Main-hand clearance only. Blade poses, contact times and damage keep their
// existing source clocks. Camera axes: +X forward, +Y right, +Z up, centimetres.
namespace OffhandQuickClearance
{
    struct FKey {float T;FVector Offset,Angles;}; // Angles: pitch, yaw, roll, degrees.
    struct FPose {FVector Offset=FVector::ZeroVector,Angles=FVector::ZeroVector;};

    // Leave the crossed axe first, follow the descending arm, then keep height
    // while the left fist crosses home. Lower the gun last, inside the action.
    inline const FKey Chop[]={
        {0.f,   FVector::ZeroVector,FVector::ZeroVector},
        {.045f, FVector(-.5,4.5,1.4),FVector(.7,1.5,-1.5)},
        {.13f,  FVector(-2.2,17,5.5),FVector(3,7,-7)},
        {.26f,  FVector(-3.6,22,8),FVector(4.5,10,-10)},
        {.39f,  FVector(-3.8,19,9),FVector(3.8,9,-8)},
        {.58f,  FVector(-3,14,9.5),FVector(2.8,6.5,-5.5)},
        {.77f,  FVector(-1.9,10,9),FVector(1.8,4,-3.5)},
        {.89f,  FVector(-.8,5,5),FVector(.7,1.8,-1.5)},
        {1.f,   FVector::ZeroVector,FVector::ZeroVector}
    };
    inline const FKey Thrust[]={
        {0.f,   FVector::ZeroVector,FVector::ZeroVector},
        {.10f,  FVector(-1.2,7,3),FVector(1.5,3,-3)},
        {.22f,  FVector(-3.8,18,7),FVector(3.5,9,-10)},
        {.38f,  FVector(-4.8,21,8.5),FVector(4,12,-13)},
        {.49f,  FVector(-4.5,20,8),FVector(3.2,11,-11)},
        {.65f,  FVector(-3,14,8.5),FVector(2.3,7,-6)},
        {.82f,  FVector(-1.1,5,4),FVector(.8,2.5,-2)},
        {1.f,   FVector::ZeroVector,FVector::ZeroVector}
    };

    inline double Tangent(double Before,double Value,double After,double H0,double H1)
    {
        const double A=(Value-Before)/H0,B=(After-Value)/H1;
        if(A*B<=0.)return 0.;
        const double W0=2.*H1+H0,W1=H1+2.*H0;
        return (W0+W1)/(W0/A+W1/B);
    }

    template<int32 N> inline FPose SampleKeys(const FKey (&Keys)[N],float Time)
    {
        const float T=FMath::Clamp(Time,0.f,1.f);
        int32 I=0;while(I<N-2&&T>Keys[I+1].T)++I;
        const double Span=Keys[I+1].T-Keys[I].T;
        const float U=float((T-Keys[I].T)/Span);
        const auto Curve=[&](bool Rotation)
        {
            const auto Value=[&](int32 K){return Rotation?Keys[K].Angles:Keys[K].Offset;};
            FVector Result;
            for(int32 Axis=0;Axis<3;++Axis)
            {
                const double A=Value(I)[Axis],B=Value(I+1)[Axis];
                const double DA=I==0?0.:Tangent(Value(I-1)[Axis],A,B,Keys[I].T-Keys[I-1].T,Span);
                const double DB=I+1==N-1?0.:Tangent(A,B,Value(I+2)[Axis],Span,Keys[I+2].T-Keys[I+1].T);
                Result[Axis]=FMath::CubicInterp(A,DA*Span,B,DB*Span,U);
            }
            return Result;
        };
        // Shared tangents through knots: no stop/restart at every key and no
        // overshooting the authored clearance. End velocity is exactly zero.
        return {Curve(false),Curve(true)};
    }

    inline FPose Sample(float Progress,bool Hatchet)
    {return Hatchet?SampleKeys(Chop,Progress):SampleKeys(Thrust,Progress);}

    inline FTransform PistolFrame(const FTransform& Carry,float Progress,bool Hatchet)
    {
        const auto Pose=Sample(Progress,Hatchet);
        const FQuat Turn=FRotator(Pose.Angles.X,Pose.Angles.Y,Pose.Angles.Z).Quaternion();
        // The accepted donor palm, not the camera origin, is the cant pivot.
        const FVector Pivot(21.894,8.746,-10.291);
        return FTransform((Turn*Carry.GetRotation()).GetNormalized(),
            Pivot+Turn.RotateVector(Carry.GetLocation()-Pivot)+Pose.Offset);
    }

    inline FPose Staff(float Progress,bool Hatchet)
    {
        auto Pose=Sample(Progress,Hatchet);
        Pose.Offset*=FVector(1.15,.85,-.80);
        Pose.Angles*=FVector(.35,.30,1.5);
        return Pose;
    }
}
