#pragma once
#include "CoreMinimal.h"

class USkeletalMeshComponent;
class UMaterialInstanceDynamic;

/** One bounded inertia field shared by each cuff's outer fabric and lining. */
struct FFPSOutfitSecondaryMotion
{
    void Initialize(USkeletalMeshComponent* InSource,USkeletalMeshComponent* InShirt,bool bSoftRobe=false);
    void Tick(float DeltaSeconds);
private:
    struct FHand
    {
        int32 Bone=INDEX_NONE;
        FVector PreviousAnchor=FVector::ZeroVector;
        FVector AnchorVelocity=FVector::ZeroVector;
        FVector Offset=FVector::ZeroVector;
        FVector Velocity=FVector::ZeroVector;
        bool bInitialized=false;
    };
    TWeakObjectPtr<USkeletalMeshComponent> Source,Shirt;
    TArray<TWeakObjectPtr<UMaterialInstanceDynamic>> Materials;
    FHand Hands[2];
    FVector LastSent[4];
    bool bActive=false;
    bool bHaveParameters=false;
    bool bRobe=false;
    void Push(const FVector& Left,const FVector& Right,const FVector& PreviousLeft,const FVector& PreviousRight);
    void Reset();
};
