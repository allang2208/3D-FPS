#pragma once
#include "CoreMinimal.h"
class UStaticMeshComponent;
class UMeshComponent;
struct FColdSteelItem;

/** Reference-pose presentation of a resolved recipe. No player or inventory writes. */
namespace ColdSteelBowAssembly
{
    bool IsBowRoot(const UStaticMeshComponent* Root);
    FString Key(const FColdSteelItem& Resolved);
    void GatherResources(const FColdSteelItem& Resolved,TArray<FSoftObjectPath>& Out);
    bool Apply(UStaticMeshComponent* Root,const FColdSteelItem& Resolved);
    TArray<UMeshComponent*> Components(UStaticMeshComponent* Root);
    FBox LocalBounds(UStaticMeshComponent* Root);
    void Clear(UStaticMeshComponent* Root);
    FQuat Rotation();
}
