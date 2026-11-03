#pragma once
#include "CoreMinimal.h"
#include "Components/SkeletalMeshComponent.h"
#include "Engine/SkeletalMesh.h"

// Geometry and hand-contact times authored together in M24Bipod20261029.
namespace M24Bipod
{
inline constexpr const TCHAR* Id=TEXT("m24_foldable_bipod");
inline constexpr const TCHAR* Profile=TEXT("/Game/Weapons/M24/ContactRepair20261101/DA_M24_Bipod");
inline constexpr const TCHAR* Base=TEXT("/Game/Weapons/M24/Bipod20261029/SM_M24_Bipod_Base");
inline constexpr const TCHAR* LegA=TEXT("/Game/Weapons/M24/Bipod20261029/SM_M24_Bipod_LegA");
inline constexpr const TCHAR* LegB=TEXT("/Game/Weapons/M24/Bipod20261029/SM_M24_Bipod_LegB");
// Animation remains in its authored 0.48 s clock; the reversible action plays
// over 0.72 s. Seat while the hand returns, rather than snapping in the last 40 ms.
inline constexpr float PoseDuration=.48f;
inline constexpr float Duration=.72f, GripContact=.18f, PullComplete=.45f, HandReturned=.66f;
inline constexpr double MinimumLegScale=.92,MaximumLegScale=1.08,MinimumLegDirectionDot=.78;
inline const FVector Hinge(0,-45,2.2);
inline const FVector Pivots[]={FVector(-2.2345008,-45,2.2),FVector(2.2454996,-45,2.2)};
inline const FVector Tips[]={FVector(-4.187518,-.4112539,-23.36971),FVector(4.1875196,-.4112545,-23.369718)};
inline bool Matches(const USkeletalMeshComponent* Mesh)
{return Mesh&&Mesh->GetSkeletalMeshAsset()&&Mesh->GetSkeletalMeshAsset()->GetPathName().StartsWith(TEXT("/Game/Weapons/M24/"));}
inline float Ease(float A,float B,float T)
{const float X=FMath::Clamp((T-A)/(B-A),0.f,1.f);return X*X*X*(10.f+X*(-15.f+6.f*X));}
// One near-side pull opens the pair; the support hand never transfers across the barrel.
inline float LegWeight(int32 /*I*/,float T){return Ease(GripContact,PullComplete,T);}
inline FQuat LegRotation(int32 I,float OpenWeight)
{
    const FQuat Closed=FQuat::FindBetweenNormals(Tips[I].GetSafeNormal(),FVector(I==0?-.5:.5,-Tips[I].Size(),0).GetSafeNormal());
    return FQuat::Slerp(Closed,FQuat::Identity,OpenWeight);
}
inline float Seat(float Phase){return Ease(PullComplete,Duration,Phase*Duration);}
inline bool CanReachLeg(const FVector& Rest,const FVector& Target)
{
    const double Ratio=Target.Size()/FMath::Max(.01,Rest.Size());
    return Ratio>=MinimumLegScale&&Ratio<=MaximumLegScale
        && FVector::DotProduct(Rest.GetSafeNormal(),Target.GetSafeNormal())>=MinimumLegDirectionDot;
}
}
