#pragma once
#include "CoreMinimal.h"

class FJsonObject;
class UGroomComponent;
class ULODSyncComponent;
class USkeletalMeshComponent;

namespace FPSBodyAppearance
{
// Body, head and all recipe resources have already streamed in.
ULODSyncComponent* AssembleHeadGrooms(USkeletalMeshComponent& Body,USkeletalMeshComponent& Head,
    const TArray<TSharedPtr<FJsonObject>>& Recipes,int32 ScalpStart,TArray<TObjectPtr<UGroomComponent>>& Grooms);
}
