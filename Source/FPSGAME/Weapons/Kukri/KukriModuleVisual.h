#pragma once
#include "CoreMinimal.h"
#include "KukriRhythm.h"
class UStaticMeshComponent;
struct FColdSteelItem;
struct FStreamableHandle;

// One bounded request per held knife. Item payload changes refresh the assembly
// without replaying the draw animation or touching the attack clock.
struct FKukriModuleVisual
{
    FString ItemId,ItemData;
    // Cached with this hand's assembly, so length variants use their actual edge.
    FVector TraceBase=KukriRhythm::BladeRoot,TraceTip=KukriRhythm::BladeTip;
    TSharedPtr<FStreamableHandle> Load;
    void Refresh(UStaticMeshComponent* Root,const FColdSteelItem* Item);
    void Clear(UStaticMeshComponent* Root);
};
