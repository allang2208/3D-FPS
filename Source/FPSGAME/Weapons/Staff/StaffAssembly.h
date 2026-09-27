#pragma once
#include "CoreMinimal.h"
struct FColdSteelItem;
class UStaticMeshComponent;
namespace ColdSteelStaffAssembly
{
    void Gather(const FColdSteelItem& Item,TArray<FSoftObjectPath>& Paths);
    bool Apply(UStaticMeshComponent* Root,const FColdSteelItem& Item);
    void Clear(UStaticMeshComponent* Root);
    TArray<UStaticMeshComponent*> Components(UStaticMeshComponent* Root);
    FBox Bounds(UStaticMeshComponent* Root);
}
