#pragma once
#include "CoreMinimal.h"
#include "KukriDualEquipBlade.h"

// Shared by dual kukris and the left blade beside a staff. Native hand_l has a 100x import scale.
namespace KukriOffhandDraw
{
    inline FTransform Grip()
    {
        return FTransform(FQuat(0.98366476,0.16943777,0.05378413,-0.02831518).GetNormalized(),
            FVector(0.07248716,-0.02259519,0.00225554),FVector(.01f));
    }
    inline FTransform Sample(float Time)
    {
        using namespace KukriDualEquipBlade;
        const float X=FMath::Clamp(Time*Hz,0.f,float(Samples-1));
        const int32 I=FMath::Min(int32(X),Samples-2);
        const float* A=Relative[I];const float* B=Relative[I+1];
        const FQuat Q=FQuat::Slerp(FQuat(A[0],A[1],A[2],A[3]),FQuat(B[0],B[1],B[2],B[3]),X-I).GetNormalized();
        return FTransform(Q,FMath::Lerp(FVector(A[4],A[5],A[6]),FVector(B[4],B[5],B[6]),X-I),FVector(.01f));
    }
}
