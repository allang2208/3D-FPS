#pragma once
#include "CoreMinimal.h"

// Cached equipment-space frames and owned cosmetic components. Ammo remains
// authoritative in the native hand controller, including partial reloads.
struct FFPSBodyRevolverReload
{
    int32 Cylinder=INDEX_NONE;
    TArray<int32> Cases,Rounds,Mechanisms,LoaderBones;
    TArray<FTransform> CaseInCylinder,RoundInCase,PresentedParts;
    TArray<FVector> InsertTravel;
    TArray<TWeakObjectPtr<class UStaticMesh>> CaseAssets,LiveAssets;
    TArray<TWeakObjectPtr<class UStaticMeshComponent>> IncomingRounds;
    TWeakObjectPtr<class UStaticMeshComponent> Loader;
    FTransform GunInHand=FTransform::Identity,LoaderInCylinder=FTransform::Identity,ReleasedLoaderInGun=FTransform::Identity;
    float StartedAt=-100.f,HoldWeight=0.f;
    int32 InitialLive=0,InitialCases=0;
    bool bPrepared=false,bDropArmed=false,bDropped=false,bDiscardLive=false,bLoaderReleased=false;
};
